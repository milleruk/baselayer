"""Audit recent workout syncs against Peloton API and optionally fix date mismatches.

Usage:
    python manage.py audit_workout_syncs --days 90 [--fix]

This command compares local `Workout.completed_date` to Peloton's recorded start_time
for workouts in the last `--days` days. With `--fix` it updates `recorded_date` and
`completed_date` to match Peloton's computed local date (America/New_York).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from peloton.models import PelotonConnection
from workouts.models import Workout

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Audit recent workouts against Peloton API for date mismatches'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90, help='Lookback in days')
        parser.add_argument('--fix', action='store_true', help='Automatically correct mismatched dates')
        parser.add_argument('--limit', type=int, default=None, help='Limit number of workouts processed')

    def handle(self, *args, **options):
        days = options.get('days', 90)
        do_fix = options.get('fix', False)
        limit = options.get('limit')

        self.stdout.write(f'Auditing workouts from last {days} days (fix={do_fix})')

        since_date = (timezone.now() - timedelta(days=days)).date()
        qs = Workout.objects.filter(completed_date__gte=since_date).order_by('-completed_date')
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f'  Found {total} workouts to check')

        mismatches = []
        fixed = 0
        skipped = 0

        # Timezone helpers (fall back to UTC if ZoneInfo not available)
        try:
            from zoneinfo import ZoneInfo
            ET = ZoneInfo('America/New_York')
        except Exception:
            try:
                import pytz
                ET = pytz.timezone('America/New_York')
            except Exception:
                from datetime import timezone as _tz
                ET = _tz.utc

        UTC = timezone.utc

        for idx, workout in enumerate(qs, start=1):
            if not workout.peloton_workout_id:
                skipped += 1
                continue

            self.stdout.write(f'[{idx}/{total}] Checking workout id={workout.id} peloton_workout_id={workout.peloton_workout_id} user={workout.user.email}')

            # Find Peloton connection for user
            try:
                connection = PelotonConnection.objects.get(user=workout.user, is_active=True)
            except PelotonConnection.DoesNotExist:
                self.stdout.write(self.style.WARNING('  No active Peloton connection for user - skipping'))
                skipped += 1
                continue

            try:
                client = connection.get_client()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Could not build Peloton client: {e} - skipping'))
                skipped += 1
                continue

            # Fetch workout from Peloton API
            try:
                remote = client.fetch_workout(workout.peloton_workout_id)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Peloton API error fetching workout: {e} - skipping'))
                skipped += 1
                continue

            # Determine Peloton start_time (prefer start_time, then created_at)
            start_time = remote.get('start_time') or remote.get('created_at') or remote.get('start_time_timestamp')

            if not start_time:
                self.stdout.write(self.style.WARNING('  No start_time in Peloton payload - skipping'))
                skipped += 1
                continue

            # Parse start_time into date in ET (match application behavior)
            peloton_date = None
            try:
                if isinstance(start_time, (int, float)):
                    # Handle milliseconds vs seconds
                    ts = start_time
                    if ts >= 1e12:  # milliseconds
                        ts = ts / 1000.0
                    dt_utc = datetime.fromtimestamp(ts, tz=UTC)
                    dt_et = dt_utc.astimezone(ET) if ET != UTC else dt_utc
                    peloton_date = dt_et.date()
                else:
                    # ISO string
                    dt_str = str(start_time).replace('Z', '+00:00')
                    dt = datetime.fromisoformat(dt_str)
                    if dt.tzinfo is None:
                        dt = timezone.make_aware(dt, UTC)
                    else:
                        dt = dt.astimezone(UTC)
                    dt_et = dt.astimezone(ET) if ET != UTC else dt
                    peloton_date = dt_et.date()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Error parsing start_time: {e} - skipping'))
                skipped += 1
                continue

            if peloton_date != workout.completed_date:
                mismatches.append((workout.id, workout.user.email, workout.completed_date.isoformat(), peloton_date.isoformat()))
                self.stdout.write(self.style.ERROR(f'  MISMATCH: local={workout.completed_date} peloton={peloton_date}'))
                if do_fix:
                    # Update both recorded_date and completed_date to peloton_date
                    workout.recorded_date = peloton_date
                    workout.completed_date = peloton_date
                    workout.save()
                    fixed += 1
                    self.stdout.write(self.style.SUCCESS('  Fixed dates to match Peloton'))
            else:
                self.stdout.write(self.style.SUCCESS('  OK'))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Audit complete. Scanned: {total}, mismatches: {len(mismatches)}, fixed: {fixed}, skipped: {skipped}'))
        if mismatches and not do_fix:
            self.stdout.write('First 20 mismatches:')
            for m in mismatches[:20]:
                self.stdout.write(f'  Workout id={m[0]} user={m[1]} local={m[2]} peloton={m[3]}')
