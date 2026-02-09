"""
Django management command to fetch Peloton overview data and save to JSON file.
This is useful for debugging and understanding the API response structure.

Usage:
    python manage.py fetch_peloton_overview <peloton_username> [--output /tmp/peloton_overview.json]
    python manage.py fetch_peloton_overview --list
"""
import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonAPIError

User = get_user_model()


class Command(BaseCommand):
    help = 'Fetch Peloton overview data for a user and save to JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'peloton_username',
            type=str,
            nargs='?',
            help='Peloton leaderboard name (username) of the user to fetch data for (use --list to see available users)'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all users with Peloton connections'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='/tmp/peloton_overview.json',
            help='Output file path (default: /tmp/peloton_overview.json)'
        )
        parser.add_argument(
            '--workout-id',
            type=str,
            help='Optional Peloton workout id to fetch and include in the output JSON'
        )

    def handle(self, *args, **options):
        # List users if requested
        if options['list']:
            connections = PelotonConnection.objects.select_related('user', 'user__profile').all()
            if not connections:
                self.stdout.write(self.style.WARNING('No users with Peloton connections found.'))
                return
            
            self.stdout.write(self.style.SUCCESS('Users with Peloton connections:'))
            for conn in connections:
                peloton_name = conn.user.profile.peloton_leaderboard_name if hasattr(conn.user, 'profile') else 'N/A'
                self.stdout.write(f'  - Email: {conn.user.email}')
                self.stdout.write(f'    Peloton: {peloton_name}')
                self.stdout.write(f'    User ID: {conn.peloton_user_id or "N/A"}')
                self.stdout.write('')
            return
        
        peloton_username = options['peloton_username']
        if not peloton_username:
            raise CommandError('Please provide a Peloton username, or use --list to see available users')
        
        output_path = options['output']

        try:
            # Find user by Peloton leaderboard name
            from accounts.models import Profile
            try:
                profile = Profile.objects.get(peloton_leaderboard_name=peloton_username)
                user = profile.user
            except Profile.DoesNotExist:
                # List available users
                connections = PelotonConnection.objects.select_related('user', 'user__profile').all()
                available = []
                for conn in connections:
                    peloton_name = conn.user.profile.peloton_leaderboard_name if hasattr(conn.user, 'profile') and conn.user.profile.peloton_leaderboard_name else 'N/A'
                    if peloton_name != 'N/A':
                        available.append(peloton_name)
                
                raise CommandError(
                    f'Peloton username "{peloton_username}" not found.\n'
                    f'Available Peloton usernames: {", ".join(available) if available else "None"}'
                )

            # Get Peloton connection
            try:
                connection = PelotonConnection.objects.get(user=user)
            except PelotonConnection.DoesNotExist:
                raise CommandError(f'No Peloton connection found for user "{user_email}"')

            self.stdout.write(f'Fetching Peloton data for user: {user.email}')

            # Get client
            client = connection.get_client()

            # Fetch current user to get user ID
            user_data = client.fetch_current_user()
            peloton_user_id = (
                user_data.get('id') or
                user_data.get('user_id') or
                user_data.get('sub') or
                user_data.get('peloton_user_id')
            )

            if not peloton_user_id:
                raise CommandError('Could not determine Peloton user ID')

            self.stdout.write(f'Peloton User ID: {peloton_user_id}')

            # Fetch overview data
            self.stdout.write('Fetching overview data...')
            overview_data = client.fetch_user_overview(str(peloton_user_id))

            # Fetch user details
            self.stdout.write('Fetching user details...')
            user_details = client.fetch_user(str(peloton_user_id))

            # Optionally fetch a particular workout
            workout_id = options.get('workout_id')
            workout_data = None
            if workout_id:
                try:
                    self.stdout.write(f'Fetching workout data for workout id: {workout_id}...')
                    workout_data = client.fetch_workout(str(workout_id))
                    self.stdout.write(self.style.SUCCESS(f'Fetched workout {workout_id}'))
                except PelotonAPIError as e:
                    self.stdout.write(self.style.ERROR(f'Failed to fetch workout {workout_id}: {e}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error fetching workout {workout_id}: {e}'))

            # Combine data
            combined_data = {
                'peloton_user_id': peloton_user_id,
                'overview': overview_data,
                'user_details': user_details,
            }
            if workout_data is not None:
                combined_data['workout'] = workout_data

            # Save to file
            self.stdout.write(f'Saving data to {output_path}...')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)

            file_size = os.path.getsize(output_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully saved {file_size:,} bytes to {output_path}'
                )
            )
            self.stdout.write(f'You can now inspect the file: cat {output_path} | jq .')
            self.stdout.write(f'Or view it in a text editor.')

        except PelotonAPIError as e:
            raise CommandError(f'Peloton API error: {e}')
        except Exception as e:
            raise CommandError(f'Error: {e}')
