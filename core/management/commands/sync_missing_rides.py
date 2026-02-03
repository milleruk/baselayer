"""
Management command to sync missing ride details from Peloton API.

This processes the RideSyncQueue and fetches ride details for any pending
class IDs, storing them in the local RideDetail database. Entries are marked
as synced or failed based on the result.

Usage:
    python manage.py sync_missing_rides
    python manage.py sync_missing_rides --limit 50
"""
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient, PelotonAPIError
from core.models import RideSyncQueue
from core.services.ride_detail import get_pending_ride_syncs, get_sync_queue_status
from workouts.models import RideDetail, WorkoutType, Instructor
from workouts.views import _store_playlist_from_data, detect_class_type
from challenges.utils import generate_peloton_url

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Sync pending ride details from Peloton API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of pending rides to sync (default: 100)'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID whose Peloton connection to use (required)'
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry previously failed syncs'
        )
    
    def handle(self, *args, **options):
        limit = options.get('limit', 100)
        user_id = options.get('user_id')
        retry_failed = options.get('retry_failed', False)
        
        # Get user and connection
        if not user_id:
            self.stdout.write(
                self.style.ERROR('Error: --user-id is required to get Peloton credentials')
            )
            return
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with ID {user_id} not found')
            )
            return
        
        connection = PelotonConnection.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if not connection:
            self.stdout.write(
                self.style.ERROR(f'No active Peloton connection found for user {user}')
            )
            return
        
        # Get Peloton client
        try:
            client = connection.get_client()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to initialize Peloton client: {e}')
            )
            return
        
        # Get pending syncs
        if retry_failed:
            pending = RideSyncQueue.objects.filter(
                status__in=['pending', 'failed']
            ).order_by('status', 'created_at')[:limit]
            status_text = 'pending or failed'
        else:
            pending = get_pending_ride_syncs(limit=limit)
            status_text = 'pending'
        
        count = pending.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No pending rides to sync'))
            queue_status = get_sync_queue_status()
            self.stdout.write(
                f"Queue status: {queue_status['pending_count']} pending, "
                f"{queue_status['synced_count']} synced, "
                f"{queue_status['failed_count']} failed"
            )
            return
        
        self.stdout.write(
            f"Processing {count} {status_text} ride syncs..."
        )
        
        synced_count = 0
        failed_count = 0
        
        for queue_entry in pending:
            class_id = queue_entry.class_id
            self.stdout.write(f"  Syncing {class_id}...", ending=' ')
            
            try:
                # Fetch ride details from Peloton API
                ride_details = client.fetch_ride_details(class_id)
                ride_data = ride_details.get('ride', {})
                
                if not ride_data:
                    error_msg = 'No ride data in API response'
                    self.stdout.write(self.style.WARNING('FAILED (no data)'))
                    queue_entry.mark_failed(error_msg)
                    failed_count += 1
                    continue
                
                # Extract metadata
                class_type_ids = ride_data.get('class_type_ids', [])
                if not isinstance(class_type_ids, list):
                    class_type_ids = []
                
                equipment_ids = ride_data.get('equipment_ids', [])
                if not isinstance(equipment_ids, list):
                    equipment_ids = []
                
                equipment_tags = ride_data.get('equipment_tags', [])
                if not isinstance(equipment_tags, list):
                    equipment_tags = []
                
                # Generate Peloton class URL
                peloton_class_url = ''
                fitness_discipline = ride_data.get('fitness_discipline', '').lower()
                if fitness_discipline and class_id:
                    discipline_paths = {
                        'cycling': 'cycling',
                        'running': 'treadmill',
                        'walking': 'walking',
                        'yoga': 'yoga',
                        'strength': 'strength',
                        'stretching': 'stretching',
                        'meditation': 'meditation',
                        'cardio': 'cardio',
                    }
                    # Generate standardized Peloton URL in UK format
                    peloton_class_url = generate_peloton_url(class_id)
                
                # Create or update RideDetail
                ride_detail, created = RideDetail.objects.update_or_create(
                    peloton_id=class_id,
                    defaults={
                        'title': ride_data.get('title', ''),
                        'description': ride_data.get('description', ''),
                        'duration_seconds': ride_data.get('duration', 0),
                        'workout_type': WorkoutType.objects.get_or_create(
                            slug=fitness_discipline,
                            defaults={'name': fitness_discipline.title()}
                        )[0],
                        'fitness_discipline': fitness_discipline,
                        'fitness_discipline_display_name': ride_data.get('fitness_discipline_display_name', ''),
                        'difficulty_rating_avg': ride_data.get('difficulty_rating_avg'),
                        'difficulty_rating_count': ride_data.get('difficulty_rating_count', 0),
                        'difficulty_level': ride_data.get('difficulty_level') or None,
                        'overall_estimate': ride_data.get('overall_estimate'),
                        'difficulty_estimate': ride_data.get('difficulty_estimate'),
                        'image_url': ride_data.get('image_url', ''),
                        'home_peloton_id': ride_data.get('home_peloton_id') or '',
                        'peloton_class_url': peloton_class_url,
                        'original_air_time': ride_data.get('original_air_time'),
                        'scheduled_start_time': ride_data.get('scheduled_start_time'),
                        'created_at_timestamp': ride_data.get('created_at'),
                        'class_type': detect_class_type(ride_data, ride_details),
                        'class_type_ids': class_type_ids,
                        'equipment_ids': equipment_ids,
                        'equipment_tags': equipment_tags,
                        'target_metrics_data': ride_details.get('target_metrics_data', {}),
                        'target_class_metrics': ride_details.get('target_class_metrics', {}),
                        'pace_target_type': ride_details.get('pace_target_type'),
                        'segments_data': ride_details.get('segments', {}),
                        'is_archived': ride_data.get('is_archived', False),
                        'is_power_zone_class': ride_data.get('is_power_zone_class', False),
                    }
                )
                
                # Update instructor if available
                instructor_id = ride_data.get('instructor_id')
                if instructor_id:
                    instructor_obj = ride_data.get('instructor', {})
                    instructor_name = instructor_obj.get('name') or instructor_obj.get('full_name') or 'Unknown'
                    instructor, _ = Instructor.objects.get_or_create(
                        peloton_id=instructor_id,
                        defaults={
                            'name': instructor_name,
                            'image_url': instructor_obj.get('image_url', ''),
                        }
                    )
                    if ride_detail.instructor != instructor:
                        ride_detail.instructor = instructor
                        ride_detail.save()
                
                # Store playlist if available
                playlist_data = ride_details.get('playlist')
                if playlist_data:
                    _store_playlist_from_data(playlist_data, ride_detail, logger)
                
                # Mark queue entry as synced
                queue_entry.mark_synced()
                self.stdout.write(self.style.SUCCESS('OK'))
                synced_count += 1
                
            except PelotonAPIError as e:
                error_msg = f'Peloton API error: {str(e)}'
                self.stdout.write(self.style.WARNING(f'FAILED ({str(e)[:50]})'))
                queue_entry.mark_failed(error_msg)
                failed_count += 1
            except Exception as e:
                error_msg = f'Unexpected error: {str(e)}'
                self.stdout.write(self.style.WARNING(f'FAILED ({str(e)[:50]})'))
                queue_entry.mark_failed(error_msg)
                failed_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Sync complete: {synced_count} synced, {failed_count} failed'
            )
        )
        
        queue_status = get_sync_queue_status()
        self.stdout.write(
            f"Final queue status: {queue_status['pending_count']} pending, "
            f"{queue_status['synced_count']} synced, "
            f"{queue_status['failed_count']} failed"
        )
