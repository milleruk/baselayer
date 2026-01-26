"""
Management command to update existing RideDetail objects with class_type.

This detects and sets class_type for rides that were synced before this field was added.

Usage:
    python manage.py update_class_types
    python manage.py update_class_types --ride-id <peloton_ride_id>
    python manage.py update_class_types --limit 10
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workouts.models import RideDetail
from workouts.views import detect_class_type

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update existing RideDetail objects with class_type from existing data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ride-id',
            type=str,
            default=None,
            help='Update class_type for a specific ride ID only (Peloton ride_id)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of rides to update (for testing)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if class_type is already set'
        )

    def handle(self, *args, **options):
        ride_id = options.get('ride_id')
        limit = options.get('limit')
        force = options.get('force', False)
        
        # Get RideDetail queryset
        if ride_id:
            ride_details = RideDetail.objects.filter(peloton_ride_id=ride_id)
            if not ride_details.exists():
                raise CommandError(f'RideDetail with peloton_ride_id "{ride_id}" not found')
        else:
            # Get all RideDetails without class_type (or force update all)
            if force:
                ride_details = RideDetail.objects.all()
            else:
                ride_details = RideDetail.objects.filter(class_type__isnull=True).exclude(class_type='')
        
        total_count = ride_details.count()
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No RideDetails found to update.'))
            return
        
        self.stdout.write(f'Found {total_count} RideDetail{"s" if total_count != 1 else ""} to update')
        self.stdout.write('')
        
        # Process rides
        updated = 0
        skipped = 0
        failed = 0
        processed = 0
        
        try:
            with transaction.atomic():
                for ride_detail in ride_details.select_related('workout_type', 'instructor'):
                    processed += 1
                    
                    if limit and processed > limit:
                        self.stdout.write(self.style.WARNING(f'Reached limit of {limit} rides'))
                        break
                    
                    # Check if already has class_type (unless forcing)
                    if not force and ride_detail.class_type:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [{processed}/{total_count}] Skipping {ride_detail.title} (already has class_type: {ride_detail.class_type})'
                            )
                        )
                        skipped += 1
                        continue
                    
                    # Build ride_data dict from existing fields
                    ride_data = {
                        'title': ride_detail.title,
                        'fitness_discipline': ride_detail.fitness_discipline,
                        'is_power_zone_class': ride_detail.is_power_zone_class,
                        'pace_target_type': ride_detail.pace_target_type,
                        'target_metrics_data': ride_detail.target_metrics_data or {},
                    }
                    
                    # Build ride_details dict
                    ride_details_dict = {
                        'pace_target_type': ride_detail.pace_target_type,
                        'target_metrics_data': ride_detail.target_metrics_data or {},
                    }
                    
                    # Detect class type
                    detected_class_type = detect_class_type(ride_data, ride_details_dict)
                    
                    if detected_class_type:
                        ride_detail.class_type = detected_class_type
                        ride_detail.save(update_fields=['class_type'])
                        updated += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [{processed}/{total_count}] ✓ Updated {ride_detail.title}: {detected_class_type}'
                            )
                        )
                    else:
                        skipped += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [{processed}/{total_count}] Could not detect class_type for: {ride_detail.title}'
                            )
                        )
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nInterrupted by user'))
            raise CommandError('Command interrupted')
        except Exception as e:
            failed += 1
            self.stdout.write(
                self.style.ERROR(f'    ✗ Failed: {e}')
            )
            logger.exception(f'Error updating class_type for ride_id {ride_detail.peloton_ride_id if "ride_detail" in locals() else "unknown"}')
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Updated: {updated}')
        self.stdout.write(f'  Skipped: {skipped}')
        self.stdout.write(f'  Failed: {failed}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
