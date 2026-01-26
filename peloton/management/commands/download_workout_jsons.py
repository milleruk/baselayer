"""
Management command to download performance graph JSON files for multiple workouts.
Downloads JSON files to ./jsons/ folder for inspection and testing.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient, PelotonAPIError
import json
import os
from pathlib import Path

User = get_user_model()


class Command(BaseCommand):
    help = 'Download performance graph JSON files for multiple workouts to ./jsons/ folder'

    def add_arguments(self, parser):
        parser.add_argument(
            'workout_ids',
            nargs='+',
            type=str,
            help='One or more Peloton workout IDs to download'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Peloton username (if not provided, uses first connected user)'
        )
        parser.add_argument(
            '--every-n',
            type=int,
            default=5,
            help='Sampling interval in seconds for performance graph (default: 5)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='jsons',
            help='Directory to save JSON files (default: jsons)'
        )

    def handle(self, *args, **options):
        workout_ids = options['workout_ids']
        username = options.get('username')
        every_n = options.get('every_n', 5)
        output_dir = options.get('output_dir', 'jsons')

        # Get project root directory (BASE_DIR from settings)
        project_root = Path(settings.BASE_DIR)
        output_path = project_root / output_dir
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f'Output directory: {output_path}')

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

        # Download each workout
        successful = []
        failed = []
        
        for i, workout_id in enumerate(workout_ids, 1):
            self.stdout.write(f'\n[{i}/{len(workout_ids)}] Fetching workout: {workout_id}')
            
            try:
                # Fetch the raw performance graph directly from API to ensure we get the full unmodified response
                # Use _get() directly to bypass any normalization in fetch_performance_graph()
                raw_performance_graph = client._get(
                    f"/api/workout/{workout_id}/performance_graph",
                    params={"every_n": every_n}
                )
                
                # Save the raw JSON response to file (exactly as returned by API)
                filename = f'{workout_id}_performance_graph.json'
                filepath = output_path / filename
                
                with open(filepath, 'w') as f:
                    json.dump(raw_performance_graph, f, indent=2)
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Saved to: {filepath}'))
                
                # Print brief summary
                top_keys = list(raw_performance_graph.keys())[:10]
                metrics_count = len(raw_performance_graph.get('metrics', []))
                summaries_count = len(raw_performance_graph.get('summaries', []))
                
                self.stdout.write(f'  Keys: {", ".join(top_keys[:5])}...')
                self.stdout.write(f'  Metrics: {metrics_count}, Summaries: {summaries_count}')
                self.stdout.write(f'  Raw JSON size: {len(json.dumps(raw_performance_graph))} characters')
                
                successful.append(workout_id)
                
            except PelotonAPIError as e:
                error_msg = f'  ✗ Peloton API error: {e}'
                self.stdout.write(self.style.ERROR(error_msg))
                failed.append((workout_id, str(e)))
            except Exception as e:
                error_msg = f'  ✗ Error: {e}'
                self.stdout.write(self.style.ERROR(error_msg))
                failed.append((workout_id, str(e)))

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Summary:')
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Successful: {len(successful)}'))
        if successful:
            for workout_id in successful:
                self.stdout.write(f'  - {workout_id}')
        
        if failed:
            self.stdout.write(self.style.ERROR(f'✗ Failed: {len(failed)}'))
            for workout_id, error in failed:
                self.stdout.write(f'  - {workout_id}: {error}')
        
        self.stdout.write(f'\nAll files saved to: {output_path}')
