from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, models
import os
import json
import time
from datetime import datetime


class Command(BaseCommand):
    help = 'Backfill peloton_created_at and peloton_timezone for a user\'s workouts (DB-first, with optional Peloton API fetch)'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='User ID to backfill')
        parser.add_argument('--username', type=str, help='Username/email to backfill')
        parser.add_argument('--workout-id', type=int, help='Only backfill a single workout id')
        parser.add_argument('--dry-run', action='store_true', help='Do not write changes, just show what would be done')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of workouts processed (0 = no limit)')
        parser.add_argument('--delay', type=float, default=1.0, help='Seconds to wait between API calls')
        parser.add_argument('--use-api', action='store_true', help='Allow calling Peloton API for missing payloads (throttled)')

    def handle(self, *args, **options):
        User = get_user_model()
        user = None
        if options.get('user_id'):
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                raise CommandError('User id not found')
        elif options.get('username'):
            try:
                user = User.objects.get(username=options['username'])
            except Exception:
                try:
                    user = User.objects.get(email=options['username'])
                except Exception:
                    raise CommandError('User not found for username/email')
        else:
            raise CommandError('Please specify --user-id or --username')

        from workouts.models import Workout

        qs = Workout.objects.filter(user=user)
        if options.get('workout_id'):
            qs = qs.filter(id=options['workout_id'])
        else:
            # Only process workouts missing peloton_created_at or peloton_timezone
            qs = qs.filter(models.Q(peloton_created_at__isnull=True) | models.Q(peloton_timezone__isnull=True))

        total = qs.count()
        self.stdout.write(f'Found {total} workouts to inspect for user {user} (dry_run={options.get("dry_run")})')

        if total == 0:
            return

        # Prepare Peloton client if requested
        peloton_client = None
        if options.get('use_api'):
            try:
                from peloton.models import PelotonConnection
                pc = PelotonConnection.objects.get(user=user)
                peloton_client = pc.get_client()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not build Peloton client for user {user}: {e}'))
                peloton_client = None

        processed = 0
        limit = options.get('limit') or 0

        json_dir = os.path.join(os.getcwd(), 'jsons')

        for w in qs.order_by('-id'):
            if limit and processed >= limit:
                break

            processed += 1
            self.stdout.write(f'[{processed}/{total}] Inspecting workout id={w.id} peloton_workout_id={w.peloton_workout_id}')

            payload = None
            # Try to find saved JSON payloads in jsons/ directory
            if w.peloton_workout_id and os.path.isdir(json_dir):
                for fname in os.listdir(json_dir):
                    if w.peloton_workout_id in fname:
                        try:
                            with open(os.path.join(json_dir, fname), 'r') as fh:
                                data = json.load(fh)
                                # prefer payload that contains 'workout' key
                                if isinstance(data, dict) and ('workout' in data or 'start_time' in data or 'created_at' in data):
                                    payload = data
                                    self.stdout.write(self.style.NOTICE(f'  Found saved JSON: {fname}'))
                                    break
                        except Exception:
                            continue

            # If not found, optionally call Peloton API
            if payload is None and peloton_client:
                try:
                    self.stdout.write('  Fetching from Peloton API...')
                    payload = peloton_client.fetch_workout(w.peloton_workout_id)
                    time.sleep(options.get('delay', 1.0))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  API fetch failed: {e} - skipping'))
                    payload = None

            # Extract timestamps
            created_at = None
            start_time = None
            tz_str = None
            if payload:
                # payload may wrap workout under 'workout' key
                if isinstance(payload, dict) and 'workout' in payload:
                    data = payload.get('workout')
                else:
                    data = payload

                # keys may be numeric seconds or iso strings
                for key in ['created_at', 'createdAt', 'start_time', 'startTime', 'timezone', 'tz']:
                    if key in data and data.get(key) is not None:
                        if key in ['created_at', 'createdAt'] and created_at is None:
                            created_at = data.get(key)
                        if key in ['start_time', 'startTime'] and start_time is None:
                            start_time = data.get(key)
                        if key in ['timezone', 'tz'] and tz_str is None:
                            tz_str = data.get(key)

            # Determine values to set
            value_created_dt = None
            value_completed_dt = None

            def parse_ts(val):
                if val is None:
                    return None
                try:
                    if isinstance(val, (int, float)):
                        ts = float(val)
                        if ts >= 1e12:
                            ts = ts / 1000.0
                        return datetime.fromtimestamp(ts, tz=timezone.utc)
                    else:
                        s = str(val).replace('Z', '+00:00')
                        dt = datetime.fromisoformat(s)
                        if dt.tzinfo is None:
                            return timezone.make_aware(dt, timezone.utc)
                        return dt.astimezone(timezone.utc)
                except Exception:
                    return None

            value_created_dt = parse_ts(created_at) or None
            value_completed_dt = parse_ts(start_time) or value_created_dt

            # If no information found, skip
            if not value_created_dt and not value_completed_dt:
                self.stdout.write(self.style.WARNING('  No timestamp data available - skipping'))
                continue

            # Prepare update
            updates = {}
            if value_created_dt and w.peloton_created_at != value_created_dt:
                updates['peloton_created_at'] = value_created_dt
            if tz_str and (not w.peloton_timezone or w.peloton_timezone != tz_str):
                updates['peloton_timezone'] = tz_str
            if value_completed_dt and w.completed_at != value_completed_dt:
                updates['completed_at'] = value_completed_dt
            # completed_date computed in America/New_York
            try:
                from zoneinfo import ZoneInfo
                ET = ZoneInfo('America/New_York')
                completed_date = (value_completed_dt.astimezone(ET).date() if value_completed_dt else None)
            except Exception:
                completed_date = value_completed_dt.date() if value_completed_dt else None

            if completed_date and w.completed_date != completed_date:
                updates['completed_date'] = completed_date

            if not updates:
                self.stdout.write('  Nothing to update')
                continue

            self.stdout.write(f'  Would update: {list(updates.keys())}' if options.get('dry_run') else f'  Updating: {list(updates.keys())}')

            if not options.get('dry_run'):
                for k, v in updates.items():
                    setattr(w, k, v)
                w.save(update_fields=list(updates.keys()))

        self.stdout.write(self.style.SUCCESS(f'Processed {processed} workouts'))
