"""
Management command to sync manual workouts for a specific user and date range.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

from peloton.models import PelotonConnection
from workouts.models import Workout, RideDetail, WorkoutType, Instructor

User = get_user_model()
logger = logging.getLogger('peloton')


class Command(BaseCommand):
    help = 'Sync manual workouts for a specific user and date range'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            required=True,
            help='Username/email of the user to sync workouts for'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year to sync (e.g., 2023, 2024, 2025)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of workouts to process (default: 100)'
        )

    def handle(self, *args, **options):
        username = options['username']
        year = options.get('year')
        start_date_str = options.get('start_date')
        end_date_str = options.get('end_date')
        limit = options['limit']

        # Get user
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')

        # Get Peloton connection
        try:
            peloton_conn = PelotonConnection.objects.get(user=user)
        except PelotonConnection.DoesNotExist:
            raise CommandError(f'No Peloton connection found for user "{username}"')

        # Determine date range
        if year:
            start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        elif start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        elif start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_date = timezone.now()
        else:
            # Default to current year
            current_year = timezone.now().year
            start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
            end_date = timezone.now()

        self.stdout.write(f"Syncing manual workouts for: {username}")
        self.stdout.write(f"Date range: {start_date.date()} to {end_date.date()}")
        self.stdout.write(f"Limit: {limit} workouts")
        self.stdout.write("")

        # Get Peloton client
        client = peloton_conn.get_client()

        # Generic RideDetail mapping
        MANUAL_RIDE_DETAIL_MAP = {
            'running': 9999999,
            'walking': 9999997,
            'cycling': 9999998,
            'bike': 9999998,
            'ride': 9999998,
            'rowing': 9999996,
            'strength': 9999995,
            'yoga': 9999994,
            'meditation': 9999993,
            'stretching': 9999992,
            'cardio': 9999991,
        }

        manual_count = 0
        processed_count = 0
        skipped_count = 0

        try:
            # Iterate through user's workouts
            for workout_data in client.iter_user_workouts(peloton_conn.peloton_user_id):
                processed_count += 1
                
                if processed_count > limit:
                    self.stdout.write(self.style.WARNING(f"\n⚠ Reached limit of {limit} workouts"))
                    break

                # Get workout timestamp
                start_time = workout_data.get('start_time') or workout_data.get('created_at')
                if isinstance(start_time, (int, float)):
                    workout_datetime = datetime.fromtimestamp(start_time, tz=timezone.utc)
                else:
                    continue

                # Check if workout is in date range
                if workout_datetime < start_date or workout_datetime > end_date:
                    continue

                # Get ride_id
                ride_data = workout_data.get('ride', {})
                ride_id = ride_data.get('id') if ride_data else None

                # Check if it's a placeholder ride_id (manual workout indicator)
                if ride_id and ride_id == '00000000000000000000000000000000':
                    ride_id = None

                # Skip non-manual workouts
                if ride_id:
                    continue

                manual_count += 1
                workout_id = workout_data.get('id')

                # Check if already exists
                if Workout.objects.filter(peloton_workout_id=workout_id, user=user).exists():
                    skipped_count += 1
                    self.stdout.write(f"  [{manual_count}] Skipped (already exists): {workout_id}")
                    continue

                # Get discipline
                fitness_discipline = workout_data.get('fitness_discipline', 'other')
                
                # Map to generic RideDetail
                generic_ride_id = MANUAL_RIDE_DETAIL_MAP.get(fitness_discipline.lower(), 9999990)
                generic_peloton_ride_id = f"manual_{fitness_discipline.lower()}_{generic_ride_id}"

                try:
                    ride_detail = RideDetail.objects.get(peloton_ride_id=generic_peloton_ride_id)
                except RideDetail.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"  ✗ Generic RideDetail '{generic_peloton_ride_id}' not found!"))
                    continue

                # Get workout type
                workout_type = None
                if ride_detail.workout_type:
                    workout_type = ride_detail.workout_type

                # Get dates
                if isinstance(start_time, (int, float)):
                    dt_utc = datetime.fromtimestamp(start_time, tz=timezone.utc)
                    completed_date = dt_utc.date()
                else:
                    completed_date = workout_datetime.date()

                # Create workout
                peloton_url = f"https://members.onepeloton.com/profile/workouts/{workout_id}"

                with transaction.atomic():
                    workout, created = Workout.objects.update_or_create(
                        peloton_workout_id=workout_id,
                        user=user,
                        defaults={
                            'ride_detail': ride_detail,
                            'peloton_url': peloton_url,
                            'recorded_date': completed_date,
                            'completed_date': completed_date,
                        }
                    )

                # Fetch performance data for duration
                try:
                    from workouts.models import WorkoutDetails
                    
                    performance_graph = client.fetch_performance_graph(workout_id, every_n=5)
                    
                    if performance_graph:
                        duration_seconds = performance_graph.get('duration')
                        if duration_seconds:
                            details, _ = WorkoutDetails.objects.get_or_create(workout=workout)
                            details.duration_seconds = int(duration_seconds)
                            details.save()
                            
                            duration_minutes = int(duration_seconds / 60)
                            self.stdout.write(self.style.SUCCESS(
                                f"  [{manual_count}] ✓ {fitness_discipline.title()} - {duration_minutes}min - {completed_date} (ID: {workout.id})"
                            ))
                        else:
                            self.stdout.write(self.style.SUCCESS(
                                f"  [{manual_count}] ✓ {fitness_discipline.title()} - {completed_date} (ID: {workout.id}) - No duration"
                            ))
                    else:
                        self.stdout.write(self.style.SUCCESS(
                            f"  [{manual_count}] ✓ {fitness_discipline.title()} - {completed_date} (ID: {workout.id}) - No perf data"
                        ))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"  [{manual_count}] ⚠ {fitness_discipline.title()} - {completed_date} (ID: {workout.id}) - Error: {e}"
                    ))

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n⚠ Interrupted by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Error: {e}"))
            raise

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 50)
        self.stdout.write(self.style.SUCCESS(f"✓ Sync complete!"))
        self.stdout.write(f"  Total workouts processed: {processed_count}")
        self.stdout.write(f"  Manual workouts found: {manual_count}")
        self.stdout.write(f"  Skipped (already exist): {skipped_count}")
        self.stdout.write(f"  New manual workouts: {manual_count - skipped_count}")
        self.stdout.write("")
