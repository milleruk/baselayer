"""
Management command to re-fetch and update performance graph data for a specific workout.
This is useful for updating performance data without re-syncing all workouts.
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
    help = 'Re-fetch and update performance graph data for a specific workout'

    def add_arguments(self, parser):
        parser.add_argument(
            'workout_id',
            type=str,
            help='Workout ID (Django workout ID or Peloton workout ID)'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Peloton username (if not provided, uses workout owner)'
        )
        parser.add_argument(
            '--every-n',
            type=int,
            default=5,
            help='Sampling interval in seconds for performance graph (default: 5)'
        )
        parser.add_argument(
            '--django-id',
            action='store_true',
            help='Treat workout_id as Django workout ID (look up peloton_workout_id from database)'
        )

    def handle(self, *args, **options):
        workout_id = options['workout_id']
        username = options.get('username')
        every_n = options.get('every_n', 5)
        is_django_id = options.get('django_id', False)

        # Find the workout
        workout = None
        peloton_workout_id = None
        
        if is_django_id:
            try:
                workout = Workout.objects.select_related('ride_detail', 'user').get(id=int(workout_id))
                peloton_workout_id = workout.peloton_workout_id
                if not peloton_workout_id:
                    raise CommandError(f'Workout {workout_id} does not have a peloton_workout_id')
                self.stdout.write(f'Found Django workout {workout_id}: {workout.ride_detail.title if workout.ride_detail else "N/A"}')
                self.stdout.write(f'User: {workout.user.username}')
                self.stdout.write(f'Peloton workout ID: {peloton_workout_id}')
            except Workout.DoesNotExist:
                raise CommandError(f'Workout with Django ID {workout_id} not found')
            except ValueError:
                raise CommandError(f'Invalid Django workout ID: {workout_id}')
        else:
            # Try to find by Peloton workout ID
            try:
                workout = Workout.objects.select_related('ride_detail', 'user').get(peloton_workout_id=workout_id)
                peloton_workout_id = workout_id
                self.stdout.write(f'Found workout by Peloton ID: {workout.ride_detail.title if workout.ride_detail else "N/A"}')
                self.stdout.write(f'Django workout ID: {workout.id}')
                self.stdout.write(f'User: {workout.user.username}')
            except Workout.DoesNotExist:
                # If not found, we can still proceed if username is provided
                peloton_workout_id = workout_id
                if not username:
                    raise CommandError(
                        f'Workout with Peloton ID {workout_id} not found in database. '
                        'Provide --username to fetch data anyway, or use --django-id if you meant a Django ID.'
                    )
                self.stdout.write(self.style.WARNING(
                    f'Workout {workout_id} not found in database. Will fetch data but cannot update database.'
                ))

        # Get user for Peloton connection
        if workout:
            user = workout.user
            username = user.username
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User with username "{username}" not found')
        else:
            raise CommandError('Cannot determine user. Provide --username or use a workout ID that exists in database.')

        # Get Peloton connection
        try:
            connection = PelotonConnection.objects.get(user=user, is_active=True)
        except PelotonConnection.DoesNotExist:
            raise CommandError(f'No active Peloton account found for user "{username}"')

        self.stdout.write(f'Using Peloton account for user: {username}')

        # Get Peloton client
        try:
            client = connection.get_client()
        except Exception as e:
            raise CommandError(f'Failed to get Peloton client: {e}')

        # Fetch performance graph
        self.stdout.write(f'Fetching performance graph for Peloton workout: {peloton_workout_id} (every_n={every_n})...')
        try:
            performance_graph = client.fetch_performance_graph(peloton_workout_id, every_n=every_n)
        except PelotonAPIError as e:
            raise CommandError(f'Peloton API error: {e}')
        except Exception as e:
            raise CommandError(f'Failed to fetch performance graph: {e}')

        self.stdout.write(self.style.SUCCESS('✓ Performance graph fetched successfully'))

        # If workout not in database, just show summary and exit
        if not workout:
            self.stdout.write('\n' + '='*60)
            self.stdout.write('Performance Graph Summary:')
            self.stdout.write('='*60)
            seconds_array = performance_graph.get('seconds_since_pedaling_start', [])
            metrics_array = performance_graph.get('metrics', [])
            self.stdout.write(f'Time points: {len(seconds_array)}')
            self.stdout.write(f'Metrics: {len(metrics_array)}')
            target_metrics_perf = performance_graph.get('target_metrics_performance_data', {})
            target_metrics_list = target_metrics_perf.get('target_metrics', [])
            self.stdout.write(f'Target metrics segments: {len(target_metrics_list)}')
            self.stdout.write('\nWorkout not in database - cannot update. Use sync_workouts to import it first.')
            return

        # Update performance data
        self.stdout.write(f'\nUpdating performance data for workout {workout.id}...')
        
        # Extract metrics from performance graph
        metrics_array = performance_graph.get('metrics', [])
        seconds_array = performance_graph.get('seconds_since_pedaling_start', [])
        
        if not seconds_array or not metrics_array:
            self.stdout.write(self.style.WARNING(
                f'No time-series data available (seconds_array: {len(seconds_array) if seconds_array else 0}, '
                f'metrics_array: {len(metrics_array) if metrics_array else 0})'
            ))
            return

        # Delete existing performance data for this workout
        deleted_count, _ = WorkoutPerformanceData.objects.filter(workout=workout).delete()
        if deleted_count > 0:
            self.stdout.write(f'Deleted {deleted_count} existing performance data entries')

        # Build a dict of metric values by slug for easier access
        metric_values_by_slug = {}
        for metric in metrics_array:
            slug = metric.get('slug')
            values = metric.get('values', [])
            if slug and values:
                metric_values_by_slug[slug] = values
                self.stdout.write(f'  Found metric: {slug} ({len(values)} values)')
            
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
                            self.stdout.write(f'  Found speed in pace metric alternatives ({len(alt_values)} values)')

        # Create performance data entries for each timestamp
        performance_data_entries = []
        for idx, timestamp in enumerate(seconds_array):
            if not isinstance(timestamp, (int, float)):
                continue
            
            # Extract values for this timestamp from each metric
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
            self.stdout.write(self.style.SUCCESS(
                f'✓ Stored {len(performance_data_entries)} time-series data points'
            ))
        else:
            self.stdout.write(self.style.WARNING('No time-series data to store'))

        # Check target_metrics_performance_data
        target_metrics_perf = performance_graph.get('target_metrics_performance_data', {})
        target_metrics_list = target_metrics_perf.get('target_metrics', [])
        
        if target_metrics_list:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Found {len(target_metrics_list)} target metric segments (available for power zone graph)'
            ))
        elif workout.ride_detail and workout.ride_detail.is_power_zone_class:
            self.stdout.write(self.style.WARNING(
                '⚠ Power zone class but no target_metrics_performance_data found in API response'
            ))
        else:
            self.stdout.write('  (Not a power zone class - target metrics not applicable)')

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ Performance data updated successfully'))
        self.stdout.write('='*60)
        self.stdout.write(f'Workout: {workout.ride_detail.title if workout.ride_detail else "N/A"}')
        self.stdout.write(f'Data points: {len(performance_data_entries)}')
        self.stdout.write(f'Target metrics segments: {len(target_metrics_list)}')
        self.stdout.write('='*60)
