"""
Management command to remove non-Power Zone cycling classes from the library.

This command identifies and removes cycling classes that are not Power Zone classes,
since the timer only works for Power Zone classes.

Usage:
    python manage.py clean_non_power_zone --dry-run  # Preview what will be deleted
    python manage.py clean_non_power_zone  # Actually delete them
"""

from django.core.management.base import BaseCommand
from workouts.models import RideDetail


class Command(BaseCommand):
    help = 'Remove non-Power Zone cycling classes from the library'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def is_power_zone_class(self, ride_detail):
        """
        Check if a RideDetail is a Power Zone class.
        Uses similar logic to sync_class_library command.
        """
        # Check fitness discipline
        if ride_detail.fitness_discipline and ride_detail.fitness_discipline.lower() != 'cycling':
            return False
        
        title_lower = (ride_detail.title or '').lower()
        
        # Check title for Power Zone keywords
        if 'power zone' in title_lower or ' pz ' in title_lower or \
           title_lower.startswith('pz ') or title_lower.endswith(' pz'):
            return True
        
        # Check class_type field
        if ride_detail.class_type:
            class_type_lower = ride_detail.class_type.lower()
            if 'power' in class_type_lower and 'zone' in class_type_lower:
                return True
            if class_type_lower == 'pz' or class_type_lower.startswith('pz_'):
                return True
        
        # Check class_type_ids if available
        if hasattr(ride_detail, 'class_type_ids') and ride_detail.class_type_ids:
            if isinstance(ride_detail.class_type_ids, list):
                pz_keywords = ['power_zone', 'powerzone', 'pz']
                for class_type_id in ride_detail.class_type_ids:
                    if isinstance(class_type_id, str) and any(kw in class_type_id.lower() for kw in pz_keywords):
                        return True
        
        return False

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.stdout.write('')
        
        # Get all cycling classes
        cycling_classes = RideDetail.objects.filter(
            fitness_discipline__iexact='cycling'
        )
        
        total_cycling = cycling_classes.count()
        self.stdout.write(f'Total cycling classes in library: {total_cycling}')
        self.stdout.write('')
        
        # Identify non-Power Zone classes
        non_pz_classes = []
        pz_classes = []
        
        for ride in cycling_classes:
            if self.is_power_zone_class(ride):
                pz_classes.append(ride)
            else:
                non_pz_classes.append(ride)
        
        self.stdout.write(f'Power Zone classes: {len(pz_classes)}')
        self.stdout.write(f'Non-Power Zone classes: {len(non_pz_classes)}')
        self.stdout.write('')
        
        if not non_pz_classes:
            self.stdout.write(self.style.SUCCESS('No non-Power Zone cycling classes found. Nothing to clean.'))
            return
        
        # Show some examples
        self.stdout.write('Sample non-Power Zone classes to be removed:')
        for ride in non_pz_classes[:10]:
            self.stdout.write(f'  - {ride.title} (ID: {ride.peloton_ride_id})')
        if len(non_pz_classes) > 10:
            self.stdout.write(f'  ... and {len(non_pz_classes) - 10} more')
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would delete {len(non_pz_classes)} non-Power Zone cycling classes'))
            self.stdout.write(self.style.SUCCESS(f'Would keep {len(pz_classes)} Power Zone cycling classes'))
        else:
            # Actually delete them
            self.stdout.write(self.style.WARNING(f'Deleting {len(non_pz_classes)} non-Power Zone cycling classes...'))
            
            deleted_count = 0
            for ride in non_pz_classes:
                try:
                    ride.delete()
                    deleted_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error deleting {ride.title} (ID: {ride.peloton_ride_id}): {e}'))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} non-Power Zone cycling classes'))
            self.stdout.write(self.style.SUCCESS(f'Kept {len(pz_classes)} Power Zone cycling classes'))
        
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
        else:
            self.stdout.write(self.style.SUCCESS('Cleanup complete!'))
