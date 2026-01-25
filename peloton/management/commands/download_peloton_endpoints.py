"""
Management command to download JSON responses from Peloton API endpoints
for debugging and understanding the data structure.

Usage:
    python manage.py download_peloton_endpoints <peloton_username> [--limit N] [--output-dir DIR]
"""

import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient

User = get_user_model()


class Command(BaseCommand):
    help = 'Download JSON responses from Peloton API endpoints for debugging'

    def add_arguments(self, parser):
        parser.add_argument(
            'peloton_username',
            type=str,
            help='Peloton leaderboard name/username'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of workouts to fetch (default: 5)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='peloton_debug_data',
            help='Directory to save JSON files (default: peloton_debug_data)'
        )

    def handle(self, *args, **options):
        peloton_username = options['peloton_username']
        limit = options['limit']
        output_dir = Path(options['output_dir'])
        
        # Create output directory
        output_dir.mkdir(exist_ok=True)
        self.stdout.write(self.style.SUCCESS(f'Output directory: {output_dir.absolute()}'))
        
        # Find user by Peloton leaderboard name
        try:
            profile = User.objects.get(profile__peloton_leaderboard_name=peloton_username).profile
        except User.DoesNotExist:
            raise CommandError(f'User with Peloton leaderboard name "{peloton_username}" not found')
        
        # Get Peloton connection
        try:
            connection = PelotonConnection.objects.get(user=profile.user)
        except PelotonConnection.DoesNotExist:
            raise CommandError(f'No Peloton connection found for user "{peloton_username}"')
        
        # Get authenticated client
        client = connection.get_client()
        if not client:
            raise CommandError('Failed to get authenticated Peloton client')
        
        user_id = connection.peloton_user_id
        if not user_id:
            raise CommandError('No Peloton user ID found in connection')
        
        self.stdout.write(self.style.SUCCESS(f'Found user: {profile.user.email}'))
        self.stdout.write(self.style.SUCCESS(f'Peloton user ID: {user_id}'))
        self.stdout.write('')
        
        # 1. Fetch user overview
        self.stdout.write('1. Fetching user overview...')
        try:
            overview = client.fetch_user_overview(user_id)
            overview_file = output_dir / '01_user_overview.json'
            with open(overview_file, 'w') as f:
                json.dump(overview, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Saved to {overview_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Error: {e}'))
        
        # 2. Fetch user details
        self.stdout.write('2. Fetching user details...')
        try:
            user_details = client.fetch_user(user_id)
            user_file = output_dir / '02_user_details.json'
            with open(user_file, 'w') as f:
                json.dump(user_details, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Saved to {user_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Error: {e}'))
        
        # 3. Fetch workout list (first page)
        self.stdout.write('3. Fetching workout list (first page)...')
        try:
            workouts_page = client.fetch_user_workouts_page(user_id, limit=limit)
            workouts_list_file = output_dir / '03_workouts_list.json'
            with open(workouts_list_file, 'w') as f:
                json.dump(workouts_page, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Saved to {workouts_list_file}'))
            
            # Extract workout IDs from the list
            workouts_data = workouts_page.get('data', [])
            self.stdout.write(f'   Found {len(workouts_data)} workouts in list')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Error: {e}'))
            workouts_data = []
        
        # 4. For each workout, fetch detailed workout and ride details
        for idx, workout_data in enumerate(workouts_data[:limit], 1):
            workout_id = workout_data.get('id')
            if not workout_id:
                self.stdout.write(self.style.WARNING(f'   Workout {idx}: No ID found, skipping'))
                continue
            
            self.stdout.write(f'4.{idx}. Processing workout {workout_id}...')
            
            # Get ride_id from workout data
            ride_id = None
            if 'ride' in workout_data and workout_data.get('ride'):
                ride_id = workout_data.get('ride', {}).get('id')
            
            # Save initial workout data from list
            workout_list_file = output_dir / f'04_{idx:02d}_workout_{workout_id}_from_list.json'
            with open(workout_list_file, 'w') as f:
                json.dump(workout_data, f, indent=2)
            self.stdout.write(f'   ✓ Saved list data to {workout_list_file.name}')
            
            # Fetch detailed workout
            try:
                detailed_workout = client.fetch_workout(workout_id)
                detailed_file = output_dir / f'04_{idx:02d}_workout_{workout_id}_detailed.json'
                with open(detailed_file, 'w') as f:
                    json.dump(detailed_workout, f, indent=2)
                self.stdout.write(f'   ✓ Saved detailed workout to {detailed_file.name}')
                
                # Try to get ride_id from detailed workout if not already found
                if not ride_id and 'ride' in detailed_workout:
                    ride_id = detailed_workout.get('ride', {}).get('id')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ Error fetching detailed workout: {e}'))
            
            # Fetch ride details if we have a ride_id
            if ride_id:
                try:
                    ride_details = client.fetch_ride_details(ride_id)
                    ride_file = output_dir / f'04_{idx:02d}_ride_{ride_id}_details.json'
                    with open(ride_file, 'w') as f:
                        json.dump(ride_details, f, indent=2)
                    self.stdout.write(f'   ✓ Saved ride details to {ride_file.name}')
                    
                    # Extract and display key fields for quick reference
                    title = ride_details.get('title') or ride_details.get('name') or 'N/A'
                    duration = ride_details.get('duration') or ride_details.get('length') or 'N/A'
                    self.stdout.write(f'   → Title: {title}')
                    self.stdout.write(f'   → Duration: {duration}s')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ✗ Error fetching ride details: {e}'))
            else:
                self.stdout.write(self.style.WARNING(f'   → No ride_id found for workout {workout_id}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Download complete!'))
        self.stdout.write(f'All files saved to: {output_dir.absolute()}')
