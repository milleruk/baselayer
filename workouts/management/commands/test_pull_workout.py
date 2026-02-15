"""
Management command to pull a specific workout by ID for testing.
Bypasses the sync cutoff date to allow testing with older workouts.

Usage:
    python manage.py test_pull_workout <workout_id> --username <peloton_username>
    python manage.py test_pull_workout 6fccb9b41e734a3b84d383468da08ba9 --username root@haresign.dev
"""

import logging
from django.core.management.base import BaseCommand, CommandError

from django.db import transaction
from django.utils import timezone
from peloton.models import PelotonConnection
from workouts.models import Workout, WorkoutType, Instructor, RideDetail, WorkoutDetails
from accounts.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Pull a specific workout by ID for testing (bypasses sync cutoff)'

    def add_arguments(self, parser):
        parser.add_argument(
            'workout_id',
            type=str,
            help='Peloton workout ID to pull'
        )
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='User email/username to sync for'
        )

    def handle(self, *args, **options):
        workout_id = options['workout_id']
        username = options.get('username')
        
        # Get user
        if username:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                raise CommandError(f'User with email "{username}" not found')
        else:
            # Use first user with Peloton connection
            try:
                connection = PelotonConnection.objects.filter(is_active=True).first()
                if not connection:
                    raise CommandError('No active Peloton connections found')
                user = connection.user
            except Exception as e:
                raise CommandError(f'Could not find user: {e}')
        
        self.stdout.write(f"Testing workout pull for user: {user.email}")
        self.stdout.write(f"Workout ID: {workout_id}")
        self.stdout.write("")
        
        # Get Peloton connection
        try:
            connection = PelotonConnection.objects.get(user=user, is_active=True)
        except PelotonConnection.DoesNotExist:
            raise CommandError(f'No active Peloton connection found for user {user.email}')
        
        # Get client
        client = connection.get_client()
        
        # Check if workout already exists
        existing_workout = Workout.objects.filter(
            user=user,
            peloton_workout_id=workout_id
        ).first()
        
        if existing_workout:
            self.stdout.write(self.style.WARNING(f"⚠ Workout already exists in database (ID: {existing_workout.id})"))
            self.stdout.write(f"   Title: {existing_workout.title}")
            # Safely handle missing ride_detail or workout_type
            type_name = 'Unknown'
            if getattr(existing_workout, 'ride_detail', None) and getattr(existing_workout.ride_detail, 'workout_type', None):
                try:
                    type_name = existing_workout.ride_detail.workout_type.name
                except Exception:
                    type_name = 'Unknown'
            self.stdout.write(f"   Type: {type_name}")
            self.stdout.write(f"   Date: {existing_workout.completed_date}")
            if existing_workout.ride_detail and 'manual_' in existing_workout.ride_detail.peloton_ride_id:
                self.stdout.write(self.style.SUCCESS(f"   ✓ This is a MANUAL workout"))
            self.stdout.write("")
            
            response = input("Workout exists. Re-sync it? (y/N): ")
            if response.lower() != 'y':
                self.stdout.write("Cancelled.")
                return
        
        # Fetch workout data from API
        self.stdout.write("Fetching workout data from Peloton API...")
        try:
            workout_data = client.fetch_workout(workout_id)
        except Exception as e:
            raise CommandError(f'Failed to fetch workout from API: {e}')
        
        if not workout_data:
            raise CommandError(f'Workout {workout_id} not found or no data returned')

        self.stdout.write(self.style.SUCCESS("✓ Workout data fetched"))

        # --- Save API JSON to file for debugging ---
        import os, json
        json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'jsons')
        os.makedirs(json_dir, exist_ok=True)
        json_path = os.path.join(json_dir, f"peloton_api_workout_{workout_id}.json")
        try:
            with open(json_path, "w") as f:
                json.dump(workout_data, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f"[DEBUG] Saved API JSON to {json_path}"))
            logger.warning(f"[DEBUG] Saved API JSON to {json_path}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[DEBUG] Failed to save API JSON: {e}"))
            logger.error(f"[DEBUG] Failed to save API JSON: {e}")

        self.stdout.write("")
        
        # Display workout info
        ride_id = workout_data.get('ride', {}).get('id') if workout_data.get('ride') else None
        fitness_discipline = workout_data.get('fitness_discipline', 'unknown')
        
        # Check if ride_id is a placeholder (all zeros)
        if ride_id and ride_id == '00000000000000000000000000000000':
            self.stdout.write(self.style.WARNING("  ⚠ Ride ID is placeholder (all zeros) - treating as manual workout"))
            ride_id = None
        
        self.stdout.write("Workout Information:")
        self.stdout.write(f"  Discipline: {fitness_discipline}")
        self.stdout.write(f"  Has ride_id: {bool(ride_id)}")
        if ride_id:
            self.stdout.write(f"  Ride ID: {ride_id}")
        else:
            self.stdout.write(self.style.WARNING("  ⚠ No ride_id - this is a MANUAL workout"))
        self.stdout.write("")
        
        # Process workout (similar to sync logic)
        self.stdout.write("Processing workout...")
        
        # Get or create workout type
        workout_type_slug = fitness_discipline.lower()
        type_mapping = {
            'cycling': 'cycling',
            'running': 'running',
            'walking': 'walking',
            'yoga': 'yoga',
            'strength': 'strength',
            'stretching': 'stretching',
            'meditation': 'meditation',
            'cardio': 'cardio',
            'rowing': 'rowing',
        }
        workout_type_slug = type_mapping.get(workout_type_slug, 'other')
        
        workout_type, _ = WorkoutType.objects.get_or_create(
            slug=workout_type_slug,
            defaults={'name': workout_type_slug.title()}
        )
        
        # Handle ride_detail
        ride_detail = None
        
        if ride_id:
            # Regular class-based workout
            self.stdout.write(f"  Looking up RideDetail for ride_id: {ride_id}...")
            try:
                ride_detail = RideDetail.objects.get(peloton_ride_id=ride_id)
                self.stdout.write(self.style.SUCCESS(f"  ✓ Found existing RideDetail: {ride_detail.title}"))
            except RideDetail.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  ⚠ RideDetail not found, would need to fetch from API"))
                self.stdout.write(f"  (Skipping ride detail creation for this test)")
        else:
            # Manual workout (Garmin Tacx Training, etc.)
            self.stdout.write(self.style.WARNING(f"  No ride_id - using workout_data['ride'] fields for manual RideDetail..."))
            ride_data = workout_data.get('ride', {})
            manual_title = ride_data.get('title', 'Manual Workout')
            manual_discipline = workout_type_slug
            manual_peloton_ride_id = f"manual_{manual_discipline}_{workout_id}"
            ride_detail, created = RideDetail.objects.get_or_create(
                peloton_ride_id=manual_peloton_ride_id,
                defaults={
                    'title': manual_title,
                    'fitness_discipline': manual_discipline,
                    'workout_type': workout_type,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created manual RideDetail: {manual_title}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Found existing manual RideDetail: {ride_detail.title}"))
        
        if not ride_detail:
            raise CommandError('Could not determine ride_detail for this workout')
        
        # Get dates
        start_time = workout_data.get('start_time') or workout_data.get('created_at')
        if isinstance(start_time, (int, float)):
            from datetime import datetime
            from zoneinfo import ZoneInfo
            dt_utc = datetime.fromtimestamp(start_time, tz=timezone.utc)
            ET = ZoneInfo("America/New_York")
            dt_et = dt_utc.astimezone(ET)
            completed_date = dt_et.date()
        else:
            completed_date = timezone.now().date()
        
        # Create or update workout
        peloton_url = f"https://members.onepeloton.com/profile/workouts/{workout_id}"
        
        with transaction.atomic():
            # Only set title_override for manual workouts if it is currently blank/null
            new_title = ride_detail.title if ride_detail and ride_detail.title else workout_data.get('title', 'Manual Workout')
            existing_workout = Workout.objects.filter(peloton_workout_id=workout_id, user=user).first()
            defaults = {
                'ride_detail': ride_detail,
                'peloton_url': peloton_url,
                'recorded_date': completed_date,
                'completed_date': completed_date,
            }
            if ride_detail and str(ride_detail.peloton_ride_id).startswith('manual_'):
                if not existing_workout or not existing_workout.title_override:
                    defaults['title_override'] = new_title
            workout, created = Workout.objects.update_or_create(
                peloton_workout_id=workout_id,
                user=user,
                defaults=defaults
            )
        
        self.stdout.write("")
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ WORKOUT CREATED (Database ID: {workout.id})"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ WORKOUT UPDATED (Database ID: {workout.id})"))
        
        # Fetch performance data to get actual duration
        self.stdout.write("")
        self.stdout.write("Fetching performance data...")
        try:
            from workouts.models import WorkoutPerformanceData, WorkoutDetails
            
            performance_graph = client.fetch_performance_graph(workout_id, every_n=5)
            
            if performance_graph:
                # Check for duration directly in performance graph
                duration_seconds = performance_graph.get('duration')
                if duration_seconds:
                    duration_minutes = int(duration_seconds / 60)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Duration from performance graph: {duration_seconds} seconds ({duration_minutes} minutes)"))
                    
                    # Save duration to WorkoutDetails
                    workout_details, _ = WorkoutDetails.objects.get_or_create(workout=workout)
                    workout_details.duration_seconds = duration_seconds
                    workout_details.save()
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Saved duration to WorkoutDetails"))
                else:
                    self.stdout.write(f"  Duration: {duration_seconds}")
                
                summaries_array = performance_graph.get('summaries', [])
                metrics_array = performance_graph.get('metrics', [])
                
                self.stdout.write(f"  Summaries count: {len(summaries_array)}")
                self.stdout.write(f"  Metrics count: {len(metrics_array)}")
                
                # Show summary data
                if summaries_array:
                    self.stdout.write("")
                    self.stdout.write("  Summary metrics:")
                    for summary in summaries_array[:10]:  # Show first 10
                        if isinstance(summary, dict):
                            slug = summary.get('slug')
                            value = summary.get('value')
                            self.stdout.write(f"    {slug}: {value}")
                
                # Check splits data
                splits_data = performance_graph.get('splits_data', {})
                if splits_data:
                    self.stdout.write("")
                    self.stdout.write(f"  Splits data available: {list(splits_data.keys())}")
                
                self.stdout.write("")
                
                # Clear existing performance data
                WorkoutPerformanceData.objects.filter(workout=workout).delete()
                
                # Process each metric type
                performance_data_to_create = []
                for metric in metrics_array:
                    if not isinstance(metric, dict):
                        continue
                    
                    slug = metric.get('slug')
                    values = metric.get('values', [])
                    
                    if not values:
                        continue
                    
                    self.stdout.write(f"  Processing metric: {slug} ({len(values)} data points)")
                    
                    # Create performance data points
                    for point in values:
                        if not isinstance(point, dict):
                            continue
                        
                        timestamp = point.get('seconds_since_pedaling_start')
                        value = point.get('value')
                        
                        if timestamp is None or value is None:
                            continue
                        
                        # Find or create performance data point at this timestamp
                        perf_data = next(
                            (p for p in performance_data_to_create if p['timestamp'] == timestamp),
                            None
                        )
                        
                        if not perf_data:
                            perf_data = {'timestamp': timestamp, 'workout': workout}
                            performance_data_to_create.append(perf_data)
                        
                        # Map metric slug to field
                        field_mapping = {
                            'output': 'output',
                            'cadence': 'cadence',
                            'resistance': 'resistance',
                            'speed': 'speed',
                            'pace': 'pace',
                            'heart_rate': 'heart_rate',
                        }
                        
                        field = field_mapping.get(slug)
                        if field:
                            perf_data[field] = value
                
                # Bulk create performance data
                if performance_data_to_create:
                    objs = [WorkoutPerformanceData(**data) for data in performance_data_to_create]
                    WorkoutPerformanceData.objects.bulk_create(objs)
                    
                    # Calculate max timestamp (actual duration)
                    max_timestamp = max(p['timestamp'] for p in performance_data_to_create)
                    duration_minutes = int(max_timestamp / 60)
                    
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Saved {len(objs)} performance data points"))
                    self.stdout.write(f"  Max timestamp: {max_timestamp} seconds ({duration_minutes} minutes)")
                else:
                    self.stdout.write(self.style.WARNING("  ⚠ No performance data points found"))
            else:
                self.stdout.write(self.style.WARNING("  ⚠ No performance graph data returned"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error fetching performance data: {e}"))
        
        self.stdout.write("")
        self.stdout.write("Workout Details:")
        self.stdout.write(f"  Title: {workout.title}")
        self.stdout.write(f"  Type: {workout.workout_type.name if workout.workout_type else 'Unknown'}")
        self.stdout.write(f"  Instructor: {workout.instructor.name if workout.instructor else 'Manual'}")
        self.stdout.write(f"  Duration: {workout.duration_minutes} min (from class) / {workout.actual_duration_minutes} min (actual)")
        self.stdout.write(f"  Completed: {workout.completed_date}")
        
        if ride_detail.peloton_ride_id.startswith('manual_'):
            self.stdout.write(self.style.SUCCESS(f"  🏷️ MANUAL WORKOUT"))
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ Test complete! View workout at: /workouts/{workout.id}/"))
