"""
Management command to fix completed_date for existing workouts to use raw UTC dates.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from workouts.models import Workout
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix completed_date for existing workouts to use raw UTC dates from peloton_created_at'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username/email to fix workouts for (optional, fixes all users if not specified)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        dry_run = options['dry_run']

        # Get workouts to update
        workouts = Workout.objects.exclude(peloton_created_at__isnull=True)
        if username:
            try:
                user = User.objects.get(email=username)
                workouts = workouts.filter(user=user)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" does not exist'))
                return

        total_workouts = workouts.count()
        self.stdout.write(f"Found {total_workouts} workouts with peloton_created_at timestamps")

        if total_workouts == 0:
            self.stdout.write("No workouts to update")
            return

        updated_count = 0
        skipped_count = 0

        for workout in workouts:
            utc_date = workout.peloton_created_at.date()
            if workout.completed_date != utc_date:
                if dry_run:
                    self.stdout.write(f"Would update workout {workout.id}: {workout.completed_date} -> {utc_date}")
                else:
                    with transaction.atomic():
                        workout.completed_date = utc_date
                        workout.save()
                    self.stdout.write(f"Updated workout {workout.id}: {workout.completed_date} -> {utc_date}")
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Summary:"))
        self.stdout.write(f"  Total workouts checked: {total_workouts}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write(f"  Skipped (already correct): {skipped_count}")
        if dry_run:
            self.stdout.write(self.style.WARNING("This was a dry run - no changes made"))