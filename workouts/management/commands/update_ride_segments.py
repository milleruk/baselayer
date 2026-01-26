"""
Management command to update existing RideDetail objects with segments_data.

This fetches ride details from the Peloton API to populate the segments_data field
for rides that were synced before this field was added.

Usage:
    python manage.py update_ride_segments
    python manage.py update_ride_segments --ride-id <peloton_ride_id>
    python manage.py update_ride_segments --limit 10
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from peloton.models import PelotonConnection
from workouts.models import RideDetail

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update existing RideDetail objects with segments_data from Peloton API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ride-id',
            type=str,
            default=None,
            help='Update segments for a specific ride ID only (Peloton ride_id)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of rides to update (for testing)'
        )
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Use specific user\'s Peloton connection (by Peloton leaderboard name)'
        )

    def handle(self, *args, **options):
        ride_id = options.get('ride_id')
        limit = options.get('limit')
        username = options.get('username')
        
        # Get authenticated client
        try:
            if username:
                from accounts.models import Profile
                try:
                    profile = Profile.objects.get(peloton_leaderboard_name=username)
                    user = profile.user
                except Profile.DoesNotExist:
                    raise CommandError(f'User with Peloton leaderboard name "{username}" not found')
                
                connection = PelotonConnection.objects.get(user=user)
            else:
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
        
        # Get RideDetail queryset
        if ride_id:
            ride_details = RideDetail.objects.filter(peloton_ride_id=ride_id)
            if not ride_details.exists():
                raise CommandError(f'RideDetail with peloton_ride_id "{ride_id}" not found')
        else:
            # Get all RideDetails without segments_data
            ride_details = RideDetail.objects.filter(segments_data__isnull=True).exclude(segments_data={})
        
        total_count = ride_details.count()
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No RideDetails found to update.'))
            return
        
        self.stdout.write(f'Found {total_count} RideDetail{"s" if total_count != 1 else ""} to update')
        self.stdout.write('')
        
        # Process rides
        updated = 0
        failed = 0
        skipped = 0
        processed = 0
        
        try:
            with transaction.atomic():
                for ride_detail in ride_details.select_related('workout_type', 'instructor'):
                    processed += 1
                    
                    if limit and processed > limit:
                        self.stdout.write(self.style.WARNING(f'Reached limit of {limit} rides'))
                        break
                    
                    # Check if already has segments_data
                    if ride_detail.segments_data and ride_detail.segments_data.get('segment_list'):
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [{processed}/{total_count}] Skipping {ride_detail.title} (already has segments_data)'
                            )
                        )
                        skipped += 1
                        continue
                    
                    # Fetch ride details
                    self.stdout.write(f'  [{processed}/{total_count}] Fetching segments for: {ride_detail.title}')
                    try:
                        ride_details_data = client.fetch_ride_details(ride_detail.peloton_ride_id)
                        segments_data = ride_details_data.get('segments', {})
                        
                        if segments_data and segments_data.get('segment_list'):
                            ride_detail.segments_data = segments_data
                            ride_detail.save(update_fields=['segments_data'])
                            updated += 1
                            segment_count = len(segments_data.get('segment_list', []))
                            self.stdout.write(
                                self.style.SUCCESS(f'    ✓ Updated with {segment_count} segments')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'    No segments data in response')
                            )
                            skipped += 1
                    
                    except Exception as e:
                        failed += 1
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ Failed: {e}')
                        )
                        logger.exception(f'Error updating segments for ride_id {ride_detail.peloton_ride_id}')
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nInterrupted by user'))
            raise CommandError('Command interrupted')
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Updated: {updated}')
        self.stdout.write(f'  Skipped: {skipped}')
        self.stdout.write(f'  Failed: {failed}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
