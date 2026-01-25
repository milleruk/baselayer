"""
Management command to download ride/class details JSON from Peloton API
for debugging and understanding what class information is available.

Usage:
    python manage.py download_ride_details <ride_id> [--output-dir DIR]
    python manage.py download_ride_details --from-workout <workout_id> [--output-dir DIR]
"""

import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient


class Command(BaseCommand):
    help = 'Download ride/class details JSON from Peloton API for debugging'

    def add_arguments(self, parser):
        parser.add_argument(
            'ride_id',
            type=str,
            nargs='?',
            help='Ride/class ID to fetch details for'
        )
        parser.add_argument(
            '--from-workout',
            type=str,
            help='Workout ID - will extract ride_id from workout and fetch ride details'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='peloton_debug_data',
            help='Directory to save JSON files (default: peloton_debug_data)'
        )
        parser.add_argument(
            '--list-fields',
            action='store_true',
            help='List all available fields in the ride details response'
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir'])
        ride_id = options['ride_id']
        workout_id = options.get('from_workout')
        list_fields = options.get('list_fields', False)
        
        # Create output directory
        output_dir.mkdir(exist_ok=True)
        self.stdout.write(self.style.SUCCESS(f'Output directory: {output_dir.absolute()}'))
        
        # Get authenticated client (use first available connection)
        try:
            connection = PelotonConnection.objects.select_related('user').first()
            if not connection:
                raise CommandError('No Peloton connection found. Please connect a Peloton account first.')
        except PelotonConnection.DoesNotExist:
            raise CommandError('No Peloton connection found. Please connect a Peloton account first.')
        
        client = connection.get_client()
        if not client:
            raise CommandError('Failed to get authenticated Peloton client')
        
        self.stdout.write(self.style.SUCCESS(f'Using connection for user: {connection.user.email}'))
        self.stdout.write('')
        
        # If --from-workout, fetch workout first to get ride_id
        if workout_id:
            self.stdout.write(f'Fetching workout {workout_id} to extract ride_id...')
            try:
                workout = client.fetch_workout(workout_id)
                ride_id = workout.get('ride', {}).get('id')
                if not ride_id:
                    raise CommandError(f'No ride_id found in workout {workout_id}')
                self.stdout.write(self.style.SUCCESS(f'Found ride_id: {ride_id}'))
                self.stdout.write('')
            except Exception as e:
                raise CommandError(f'Error fetching workout: {e}')
        
        if not ride_id:
            raise CommandError('Please provide either a ride_id or use --from-workout <workout_id>')
        
        # Fetch ride details
        self.stdout.write(f'Fetching ride details for ride_id: {ride_id}...')
        try:
            ride_details = client.fetch_ride_details(ride_id)
        except Exception as e:
            raise CommandError(f'Error fetching ride details: {e}')
        
        # Save full response
        output_file = output_dir / f'ride_{ride_id}_details.json'
        with open(output_file, 'w') as f:
            json.dump(ride_details, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f'✓ Saved to {output_file}'))
        
        # Extract and display key information
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Key Information:'))
        self.stdout.write('=' * 60)
        
        # Get ride data (nested structure)
        ride_data = ride_details.get('ride', {})
        
        if ride_data:
            self.stdout.write(f"Title: {ride_data.get('title', 'N/A')}")
            self.stdout.write(f"Duration: {ride_data.get('duration', 'N/A')} seconds ({int(ride_data.get('duration', 0) / 60) if ride_data.get('duration') else 0} minutes)")
            self.stdout.write(f"Description: {ride_data.get('description', 'N/A')[:100]}...")
            self.stdout.write(f"Fitness Discipline: {ride_data.get('fitness_discipline', 'N/A')}")
            self.stdout.write(f"Instructor ID: {ride_data.get('instructor_id', 'N/A')}")
            self.stdout.write(f"Difficulty Rating: {ride_data.get('difficulty_rating_avg', 'N/A')} ({ride_data.get('difficulty_rating_count', 0)} ratings)")
            self.stdout.write(f"Image URL: {ride_data.get('image_url', 'N/A')}")
            self.stdout.write(f"Created At: {ride_data.get('created_at', 'N/A')}")
            self.stdout.write(f"Original Air Time: {ride_data.get('original_air_time', 'N/A')}")
        
        # List all fields if requested
        if list_fields:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('All Top-Level Keys:'))
            self.stdout.write('=' * 60)
            for key in sorted(ride_details.keys()):
                value = ride_details[key]
                if isinstance(value, dict):
                    self.stdout.write(f"  {key}: (dict with {len(value)} keys)")
                elif isinstance(value, list):
                    self.stdout.write(f"  {key}: (list with {len(value)} items)")
                else:
                    self.stdout.write(f"  {key}: {type(value).__name__}")
            
            if ride_data:
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('All Ride Object Keys:'))
                self.stdout.write('=' * 60)
                for key in sorted(ride_data.keys()):
                    value = ride_data[key]
                    if isinstance(value, dict):
                        self.stdout.write(f"  {key}: (dict with {len(value)} keys)")
                    elif isinstance(value, list):
                        self.stdout.write(f"  {key}: (list with {len(value)} items)")
                    else:
                        sample = str(value)[:50] if value is not None else 'None'
                        self.stdout.write(f"  {key}: {type(value).__name__} = {sample}")
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Download complete!'))
        self.stdout.write(f'Full JSON saved to: {output_file.absolute()}')
