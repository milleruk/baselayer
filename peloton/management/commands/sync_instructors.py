"""
Management command to sync Peloton instructors list.

This fetches all instructors from the Peloton API and stores/updates them in the database.
Since instructors don't change often, this can be run periodically (e.g., weekly/monthly).

Usage:
    python manage.py sync_instructors
    python manage.py sync_instructors --update-existing
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from peloton.models import PelotonConnection
from workouts.models import Instructor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Peloton instructors list from API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing instructors (by default, only creates new ones)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of instructors to fetch (for testing)'
        )

    def handle(self, *args, **options):
        update_existing = options['update_existing']
        limit = options.get('limit')
        
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
        
        # Fetch all instructors
        self.stdout.write('Fetching instructors from Peloton API...')
        instructors_created = 0
        instructors_updated = 0
        instructors_skipped = 0
        total_fetched = 0
        
        try:
            with transaction.atomic():
                for instructor_data in client.iter_all_instructors():
                    total_fetched += 1
                    
                    if limit and total_fetched > limit:
                        self.stdout.write(self.style.WARNING(f'Reached limit of {limit} instructors'))
                        break
                    
                    peloton_id = instructor_data.get('id')
                    if not peloton_id:
                        self.stdout.write(self.style.WARNING(f'  Skipping instructor without ID: {instructor_data.get("name", "Unknown")}'))
                        instructors_skipped += 1
                        continue
                    
                    name = instructor_data.get('name') or instructor_data.get('full_name') or 'Unknown Instructor'
                    image_url = instructor_data.get('image_url') or instructor_data.get('profile_image_url') or ''
                    username = instructor_data.get('username') or instructor_data.get('peloton_username') or ''
                    bio = instructor_data.get('bio') or instructor_data.get('biography') or ''
                    location = instructor_data.get('location') or instructor_data.get('city') or ''
                    
                    # Optionally fetch detailed instructor information
                    try:
                        detailed_instructor = client.fetch_instructor(peloton_id)
                        # Override with detailed data if available
                        if detailed_instructor:
                            name = detailed_instructor.get('name') or detailed_instructor.get('full_name') or name
                            image_url = detailed_instructor.get('image_url') or detailed_instructor.get('profile_image_url') or image_url
                            username = detailed_instructor.get('username') or detailed_instructor.get('peloton_username') or username
                            bio = detailed_instructor.get('bio') or detailed_instructor.get('biography') or bio
                            location = detailed_instructor.get('location') or detailed_instructor.get('city') or location
                    except Exception as e:
                        logger.debug(f'Could not fetch detailed info for instructor {peloton_id}: {e}')
                    
                    # Try to get existing instructor
                    try:
                        instructor = Instructor.objects.get(peloton_id=peloton_id)
                        
                        if update_existing:
                            # Update existing instructor
                            updated = False
                            if instructor.name != name:
                                instructor.name = name
                                updated = True
                            if instructor.image_url != image_url and image_url:
                                instructor.image_url = image_url
                                updated = True
                            if instructor.username != username and username:
                                instructor.username = username
                                updated = True
                            if instructor.bio != bio and bio:
                                instructor.bio = bio
                                updated = True
                            if instructor.location != location and location:
                                instructor.location = location
                                updated = True
                            
                            if updated:
                                instructor.last_synced_at = timezone.now()
                                instructor.save()
                                instructors_updated += 1
                                self.stdout.write(f'  ↻ Updated: {name} ({peloton_id})')
                            else:
                                instructors_skipped += 1
                        else:
                            instructors_skipped += 1
                            self.stdout.write(f'  ⊙ Exists: {name} ({peloton_id})')
                    
                    except Instructor.DoesNotExist:
                        # Create new instructor
                        now = timezone.now()
                        instructor = Instructor.objects.create(
                            peloton_id=peloton_id,
                            name=name,
                            image_url=image_url,
                            username=username,
                            bio=bio,
                            location=location,
                            synced_at=now,
                            last_synced_at=now
                        )
                        instructors_created += 1
                        self.stdout.write(f'  ✓ Created: {name} ({peloton_id})')
                    
                    # Progress update every 50 instructors
                    if total_fetched % 50 == 0:
                        self.stdout.write(f'  ... Processed {total_fetched} instructors so far ...')
        
        except Exception as e:
            raise CommandError(f'Error syncing instructors: {e}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Instructor Sync Complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Total fetched from API: {total_fetched}')
        self.stdout.write(f'New instructors created: {instructors_created}')
        if update_existing:
            self.stdout.write(f'Existing instructors updated: {instructors_updated}')
        self.stdout.write(f'Skipped (already exists): {instructors_skipped}')
        self.stdout.write('')
        self.stdout.write(f'Total instructors in database: {Instructor.objects.count()}')
