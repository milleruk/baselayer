"""
Management command to re-fetch and update performance graph data for all running and walking workouts.
This is useful for updating performance data after fixing speed extraction from pace metric alternatives.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient, PelotonAPIError
from workouts.models import Workout, WorkoutPerformanceData
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Re-fetch and update performance graph data for all running and walking workouts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Peloton username (if not provided, processes all users)'
        )
        parser.add_argument(
            '--every-n',
            type=int,
            default=5,
            help='Sampling interval in seconds for performance graph (default: 5)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of workouts to process (for testing)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually updating'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        every_n = options.get('every_n', 5)
        limit = options.get('limit')
        dry_run = options.get('dry_run', False)

        # Get running/walking workouts
        workouts_query = Workout.objects.filter(
            ride_detail__fitness_discipline__in=['running', 'walking', 'run']
        ).select_related('ride_detail', 'user').order_by('-completed_date')

        if username:
            try:
                user = User.objects.get(username=username)
                workouts_query = workouts_query.filter(user=user)
            except User.DoesNotExist:
                raise CommandError(f'User with username "{username}" not found')

        # Filter to only workouts with peloton_workout_id
        workouts_query = workouts_query.exclude(peloton_workout_id__isnull=True).exclude(peloton_workout_id='')

        total_workouts = workouts_query.count()
        self.stdout.write(f'Found {total_workouts} running/walking workouts to process')

        if limit:
            workouts_query = workouts_query[:limit]
            self.stdout.write(f'Limited to {limit} workouts for processing')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN MODE - No changes will be made\n'))
            for workout in workouts_query:
                self.stdout.write(f'  Would process: {workout.id} - {workout.ride_detail.title if workout.ride_detail else "N/A"} ({workout.peloton_workout_id})')
            return

        # Group workouts by user to minimize API client creation
        workouts_by_user = {}
        for workout in workouts_query:
            user_id = workout.user_id
            if user_id not in workouts_by_user:
                workouts_by_user[user_id] = []
            workouts_by_user[user_id].append(workout)

        self.stdout.write(f'Processing {len(workouts_by_user)} users with running/walking workouts\n')

        successful = 0
        failed = 0
        skipped = 0

        for user_id, workouts in workouts_by_user.items():
            user = workouts[0].user
            self.stdout.write(f'\nProcessing user: {user.username} ({len(workouts)} workouts)')

            # Get Peloton connection for this user
            try:
                connection = PelotonConnection.objects.get(user=user, is_active=True)
            except PelotonConnection.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠ No active Peloton connection for {user.username} - skipping'))
                skipped += len(workouts)
                continue

            # Get Peloton client
            try:
                client = connection.get_client()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to get Peloton client for {user.username}: {e}'))
                skipped += len(workouts)
                continue

            # Process each workout
            for i, workout in enumerate(workouts, 1):
                peloton_workout_id = workout.peloton_workout_id
                self.stdout.write(f'\n  [{i}/{len(workouts)}] Workout {workout.id}: {workout.ride_detail.title if workout.ride_detail else "N/A"}')

                try:
                    # Fetch performance graph
                    performance_graph = client.fetch_performance_graph(peloton_workout_id, every_n=every_n)

                    # Extract metrics from performance graph
                    metrics_array = performance_graph.get('metrics', [])
                    seconds_array = performance_graph.get('seconds_since_pedaling_start', [])

                    if not seconds_array or not metrics_array:
                        self.stdout.write(self.style.WARNING(
                            f'    ⚠ No time-series data available (seconds: {len(seconds_array) if seconds_array else 0}, '
                            f'metrics: {len(metrics_array) if metrics_array else 0})'
                        ))
                        skipped += 1
                        continue

                    # Delete existing performance data
                    deleted_count, _ = WorkoutPerformanceData.objects.filter(workout=workout).delete()
                    if deleted_count > 0:
                        self.stdout.write(f'    Deleted {deleted_count} existing performance data entries')

                    # Build a dict of metric values by slug for easier access
                    metric_values_by_slug = {}
                    for metric in metrics_array:
                        slug = metric.get('slug')
                        values = metric.get('values', [])
                        if slug and values:
                            metric_values_by_slug[slug] = values

                        # For running classes, speed might be in the 'pace' metric's alternatives array
                        if slug == 'pace':
                            alternatives = metric.get('alternatives', [])
                            for alt in alternatives:
                                alt_slug = alt.get('slug')
                                alt_values = alt.get('values', [])
                                if alt_slug == 'speed' and alt_values:
                                    # Use speed from alternatives if not already found
                                    if 'speed' not in metric_values_by_slug:
                                        metric_values_by_slug['speed'] = alt_values

                    # Create performance data entries
                    performance_data_entries = []
                    for idx, timestamp in enumerate(seconds_array):
                        if not isinstance(timestamp, (int, float)):
                            continue

                        perf_data = WorkoutPerformanceData(
                            workout=workout,
                            timestamp=int(timestamp),
                            output=metric_values_by_slug.get('output', [None])[idx] if idx < len(metric_values_by_slug.get('output', [])) else None,
                            cadence=int(metric_values_by_slug.get('cadence', [None])[idx]) if idx < len(metric_values_by_slug.get('cadence', [])) and metric_values_by_slug.get('cadence', [None])[idx] is not None else None,
                            resistance=metric_values_by_slug.get('resistance', [None])[idx] if idx < len(metric_values_by_slug.get('resistance', [])) else None,
                            speed=metric_values_by_slug.get('speed', [None])[idx] if idx < len(metric_values_by_slug.get('speed', [])) else None,
                            heart_rate=int(metric_values_by_slug.get('heart_rate', [None])[idx]) if idx < len(metric_values_by_slug.get('heart_rate', [])) and metric_values_by_slug.get('heart_rate', [None])[idx] is not None else None,
                        )
                        performance_data_entries.append(perf_data)

                    # Bulk create performance data
                    if performance_data_entries:
                        WorkoutPerformanceData.objects.bulk_create(performance_data_entries, ignore_conflicts=True)
                        speed_count = sum(1 for e in performance_data_entries if e.speed is not None)
                        self.stdout.write(self.style.SUCCESS(
                            f'    ✓ Stored {len(performance_data_entries)} data points ({speed_count} with speed)'
                        ))
                        successful += 1
                    else:
                        self.stdout.write(self.style.WARNING('    ⚠ No time-series data to store'))
                        skipped += 1

                except PelotonAPIError as e:
                    self.stdout.write(self.style.ERROR(f'    ✗ Peloton API error: {e}'))
                    failed += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ✗ Error: {e}'))
                    failed += 1

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Summary:')
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Successful: {successful}'))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f'✗ Failed: {failed}'))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'⚠ Skipped: {skipped}'))
        self.stdout.write(f'Total processed: {successful + failed + skipped} / {total_workouts}')
