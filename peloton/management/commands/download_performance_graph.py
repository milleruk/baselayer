"""
Management command to download performance graph JSON from Peloton API for a specific workout.
This helps inspect the structure of the performance graph response to understand how metrics are stored.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient, PelotonAPIError
import json
import os
from datetime import datetime

User = get_user_model()


class Command(BaseCommand):
    help = 'Download performance graph JSON from Peloton API for a specific workout'

    def add_arguments(self, parser):
        parser.add_argument(
            'workout_id',
            type=str,
            help='Workout ID (Django workout ID or Peloton workout ID)'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Peloton username (if not provided, uses first connected user)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/tmp/peloton_data',
            help='Directory to save JSON files (default: /tmp/peloton_data)'
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
        output_dir = options['output_dir']
        every_n = options['every_n']
        is_django_id = options.get('django_id', False)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # If it's a Django workout ID, look up the Peloton workout ID
        peloton_workout_id = workout_id
        if is_django_id:
            try:
                from workouts.models import Workout
                django_workout = Workout.objects.get(id=int(workout_id))
                peloton_workout_id = django_workout.peloton_workout_id
                if not peloton_workout_id:
                    raise CommandError(f'Workout {workout_id} does not have a peloton_workout_id')
                self.stdout.write(f'Found Django workout {workout_id}: {django_workout.ride_detail.title if django_workout.ride_detail else "N/A"}')
                self.stdout.write(f'Using Peloton workout ID: {peloton_workout_id}')
            except Workout.DoesNotExist:
                raise CommandError(f'Workout with Django ID {workout_id} not found')
            except ValueError:
                raise CommandError(f'Invalid Django workout ID: {workout_id}')

        # Get Peloton connection
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User with username "{username}" not found')
        else:
            # Get first user with Peloton connection
            connection = PelotonConnection.objects.filter(is_active=True).first()
            if not connection:
                raise CommandError('No active Peloton account found. Please provide --username or connect an account.')
            user = connection.user
            username = user.username

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

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{timestamp}_performance_graph_{peloton_workout_id}.json'
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(performance_graph, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'✓ Performance graph saved to: {filepath}'))

        # Print summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Performance Graph Structure Summary:')
        self.stdout.write('='*60)
        self.stdout.write(f'Top-level keys: {list(performance_graph.keys())[:20]}')
        
        # Check for metrics
        if 'metrics' in performance_graph:
            metrics = performance_graph['metrics']
            self.stdout.write(f'\nMetrics type: {type(metrics)}')
            if isinstance(metrics, list):
                self.stdout.write(f'Metrics array length: {len(metrics)}')
                if len(metrics) > 0:
                    self.stdout.write(f'First metric keys: {list(metrics[0].keys()) if isinstance(metrics[0], dict) else "Not a dict"}')
                    self.stdout.write(f'\nFirst metric sample:')
                    self.stdout.write(json.dumps(metrics[0], indent=2)[:500])
            elif isinstance(metrics, dict):
                self.stdout.write(f'Metrics dict keys: {list(metrics.keys())[:20]}')
        
        # Check for summaries
        if 'summaries' in performance_graph:
            summaries = performance_graph['summaries']
            self.stdout.write(f'\nSummaries type: {type(summaries)}')
            if isinstance(summaries, list):
                self.stdout.write(f'Summaries array length: {len(summaries)}')
                if len(summaries) > 0:
                    self.stdout.write(f'First summary keys: {list(summaries[0].keys()) if isinstance(summaries[0], dict) else "Not a dict"}')
                    self.stdout.write(f'\nFirst summary sample:')
                    self.stdout.write(json.dumps(summaries[0], indent=2)[:500])
        
        # Check for common metric fields at top level
        metric_fields = ['tss', 'total_output', 'avg_output', 'max_output', 'distance', 
                        'total_calories', 'avg_heart_rate', 'max_heart_rate', 'avg_cadence', 
                        'max_cadence', 'avg_resistance', 'max_resistance', 'avg_speed', 'max_speed']
        self.stdout.write('\n\nTop-level metric fields found:')
        found_metrics = []
        for field in metric_fields:
            if field in performance_graph:
                found_metrics.append(f'{field}: {performance_graph[field]}')
        if found_metrics:
            for metric in found_metrics:
                self.stdout.write(f'  {metric}')
        else:
            self.stdout.write('  None found at top level')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'Full JSON saved to: {filepath}')
        self.stdout.write('='*60)
