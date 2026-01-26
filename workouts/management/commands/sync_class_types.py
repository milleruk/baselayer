"""
Management command to sync class types from Peloton API /api/ride/filters endpoint.

This fetches all available class types from Peloton and stores them in the ClassType model.
This should be run periodically to keep class types in sync with Peloton's current offerings.

Usage:
    python manage.py sync_class_types
    python manage.py sync_class_types --username <peloton_username>
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from peloton.models import PelotonConnection
from workouts.models import ClassType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync class types from Peloton API /api/ride/filters endpoint'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Use specific user\'s Peloton connection (by Peloton leaderboard name)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        dry_run = options.get('dry_run', False)
        
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
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        self.stdout.write('')
        
        # Fetch filters from API
        self.stdout.write('Fetching ride filters from Peloton API...')
        try:
            filters_data = client.fetch_ride_filters()
        except Exception as e:
            raise CommandError(f'Failed to fetch ride filters: {e}')
        
        # Extract class types from filters
        # Structure: filters_data['filters'] is a list of filter objects
        # We need to find the one with name='class_type_id' and extract its 'values'
        class_types_data = []
        
        if isinstance(filters_data, dict):
            filters_list = filters_data.get('filters', [])
            
            # Find the class_type_id filter
            for filter_obj in filters_list:
                if isinstance(filter_obj, dict):
                    filter_name = filter_obj.get('name', '')
                    if filter_name == 'class_type_id':
                        # Extract the values array
                        values = filter_obj.get('values', [])
                        if isinstance(values, list):
                            class_types_data = values
                            self.stdout.write(self.style.SUCCESS(f'Found class_type_id filter with {len(values)} class types'))
                            break
            
            if not class_types_data:
                self.stdout.write(self.style.WARNING(f'No class_type_id filter found. Available filters: {[f.get("name") for f in filters_list if isinstance(f, dict)]}'))
        
        if not class_types_data:
            # Log the full response for debugging
            self.stdout.write(self.style.ERROR('No class types found in API response'))
            self.stdout.write(f'Response structure: {type(filters_data)}')
            if isinstance(filters_data, dict):
                self.stdout.write(f'Top-level keys: {list(filters_data.keys())}')
            # Save full response to a file for inspection
            import json
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(filters_data, f, indent=2)
                self.stdout.write(self.style.WARNING(f'Full response saved to: {f.name}'))
            raise CommandError('No class types found in API response. Check the saved JSON file for structure.')
        
        self.stdout.write(f'Found {len(class_types_data)} class types in API response')
        self.stdout.write('')
        
        # Process class types
        created = 0
        updated = 0
        deactivated = 0
        errors = 0
        
        # Get all existing class type IDs to track which ones to deactivate
        existing_ids = set(ClassType.objects.filter(is_active=True).values_list('peloton_id', flat=True))
        found_ids = set()
        
        try:
            with transaction.atomic():
                for class_type_data in class_types_data:
                    try:
                        # Extract data - structure may vary
                        peloton_id = None
                        name = None
                        fitness_discipline = None
                        metadata = {}
                        
                        if isinstance(class_type_data, dict):
                            # Structure from API: {'value': 'id', 'display_name': 'Name', 'list_order': 123}
                            peloton_id = class_type_data.get('value') or class_type_data.get('id') or ''
                            name = class_type_data.get('display_name') or class_type_data.get('name') or ''
                            
                            # Fitness discipline is not in the class_type_id values, we'll need to infer it
                            # or get it from elsewhere. For now, leave it empty and let it be inferred.
                            fitness_discipline = ''
                            
                            # Store all data as metadata
                            metadata = class_type_data.copy()
                            # Remove fields we're storing separately
                            for key in ['value', 'id', 'display_name', 'name']:
                                metadata.pop(key, None)
                        elif isinstance(class_type_data, str):
                            # If it's just a string, use it as both ID and name
                            peloton_id = class_type_data
                            name = class_type_data
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'  Skipping unexpected class type format: {type(class_type_data)}')
                            )
                            continue
                        
                        if not peloton_id:
                            self.stdout.write(
                                self.style.WARNING(f'  Skipping class type without ID: {class_type_data}')
                            )
                            continue
                        
                        if not name:
                            name = peloton_id  # Fallback to ID if no name
                        
                        found_ids.add(str(peloton_id))
                        
                        if dry_run:
                            self.stdout.write(
                                f'  Would sync: {name} (ID: {peloton_id}, Discipline: {fitness_discipline or "N/A"})'
                            )
                            continue
                        
                        # Create or update class type
                        class_type, created_flag = ClassType.objects.update_or_create(
                            peloton_id=str(peloton_id),
                            defaults={
                                'name': name,
                                'slug': slugify(name),
                                'fitness_discipline': fitness_discipline or '',
                                'metadata': metadata,
                                'is_active': True,
                            }
                        )
                        
                        if created_flag:
                            created += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Created: {name} (ID: {peloton_id})')
                            )
                        else:
                            updated += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  ↻ Updated: {name} (ID: {peloton_id})')
                            )
                    
                    except Exception as e:
                        errors += 1
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error processing class type: {e}')
                        )
                        logger.exception(f'Error processing class type: {class_type_data}')
                
                # Deactivate class types that are no longer in the API response
                if not dry_run:
                    ids_to_deactivate = existing_ids - found_ids
                    if ids_to_deactivate:
                        deactivated_count = ClassType.objects.filter(
                            peloton_id__in=ids_to_deactivate
                        ).update(is_active=False)
                        deactivated = deactivated_count
                        if deactivated > 0:
                            self.stdout.write('')
                            self.stdout.write(
                                self.style.WARNING(f'  Deactivated {deactivated} class types no longer in API')
                            )
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nInterrupted by user'))
            raise CommandError('Command interrupted')
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary:'))
        if dry_run:
            self.stdout.write(f'  Would create/update: {len(class_types_data)}')
        else:
            self.stdout.write(f'  Created: {created}')
            self.stdout.write(f'  Updated: {updated}')
            self.stdout.write(f'  Deactivated: {deactivated}')
        self.stdout.write(f'  Errors: {errors}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if not dry_run:
            # Show some statistics
            self.stdout.write('')
            self.stdout.write('Current class types by discipline:')
            from django.db.models import Count
            for item in ClassType.objects.filter(is_active=True).values('fitness_discipline').annotate(
                count=Count('id')
            ).order_by('-count'):
                discipline = item['fitness_discipline'] or '(No discipline)'
                self.stdout.write(f'  {discipline}: {item["count"]}')
