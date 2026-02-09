"""Re-enqueue ride-detail fetches for workouts missing RideDetail.

Scans recent workouts that do not have `ride_detail` populated, attempts to
resolve the ride_id via Peloton API, and enqueues `fetch_ride_details_task`.

Usage:
    python manage.py reenqueue_failed_ride_details --days 30
    python manage.py reenqueue_failed_ride_details --days 7 --limit 100 --dry-run
"""
from __future__ import annotations

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from peloton.models import PelotonConnection
from workouts.models import Workout
from workouts.tasks import fetch_ride_details_task


class Command(BaseCommand):
    help = 'Re-enqueue ride-detail fetches for workouts missing RideDetail'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Lookback in days to scan')
        parser.add_argument('--limit', type=int, default=None, help='Limit number of workouts processed')
        parser.add_argument('--dry-run', action='store_true', help='Do not enqueue tasks, just show what would be done')

    def handle(self, *args, **options):
        days = options.get('days', 30)
        limit = options.get('limit')
        dry_run = options.get('dry_run', False)

        cutoff = (timezone.now() - timedelta(days=days)).date()
        qs = Workout.objects.filter(ride_detail__isnull=True, completed_date__gte=cutoff).order_by('-completed_date')
        total = qs.count()
        if limit:
            qs = qs[:limit]

        self.stdout.write(f'Found {total} workouts without RideDetail in last {days} days (processing {qs.count()})')

        enqueued = 0
        skipped = 0

        for w in qs:
            # Need peloton_workout_id to resolve ride_id
            if not w.peloton_workout_id:
                skipped += 1
                continue

            # Get user's Peloton connection
            try:
                conn = PelotonConnection.objects.get(user=w.user, is_active=True)
            except PelotonConnection.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  No active Peloton connection for user {w.user.email} - skipping workout {w.id}'))
                skipped += 1
                continue

            try:
                client = conn.get_client()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Could not build Peloton client for user {w.user.email}: {e} - skipping'))
                skipped += 1
                continue

            # Fetch workout details to get ride_id
            try:
                remote = client.fetch_workout(w.peloton_workout_id)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Peloton API error fetching workout {w.peloton_workout_id}: {e} - skipping'))
                skipped += 1
                continue

            ride_id = remote.get('ride', {}).get('id') or remote.get('ride_id')
            if not ride_id:
                self.stdout.write(self.style.WARNING(f'  No ride_id for workout {w.id} ({w.peloton_workout_id}) - skipping'))
                skipped += 1
                continue

            self.stdout.write(f'  Enqueue fetch_ride_details for workout {w.id} ride_id={ride_id} user={w.user.email}')
            if not dry_run:
                fetch_ride_details_task.delay(w.user.id, str(ride_id), w.id)
                enqueued += 1

        self.stdout.write(self.style.SUCCESS(f'Done. Enqueued: {enqueued}, skipped: {skipped}'))
