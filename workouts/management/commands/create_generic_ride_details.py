"""
Management command to create generic RideDetail records for manual workouts.

Manual workouts (Just Run, Just Walk, Just Ride, etc.) don't have a ride_id from Peloton API.
This command creates placeholder RideDetail records that manual workouts can be linked to.

Usage:
    python manage.py create_generic_ride_details
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from workouts.models import RideDetail, WorkoutType, Instructor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create generic RideDetail records for manual workouts (Just Run, Just Walk, etc.)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Creating generic RideDetail records for manual workouts...'))
        
        # Define generic ride details with discipline-specific IDs
        GENERIC_RIDE_DETAILS = [
            {
                'id': 9999999,
                'discipline': 'running',
                'title': 'Manual Running Workout',
                'description': 'Generic placeholder for manual running workouts created on the Peloton app',
            },
            {
                'id': 9999998,
                'discipline': 'cycling',
                'title': 'Manual Cycling Workout',
                'description': 'Generic placeholder for manual cycling workouts created on the Peloton app',
            },
            {
                'id': 9999997,
                'discipline': 'walking',
                'title': 'Manual Walking Workout',
                'description': 'Generic placeholder for manual walking workouts created on the Peloton app',
            },
            {
                'id': 9999996,
                'discipline': 'rowing',
                'title': 'Manual Rowing Workout',
                'description': 'Generic placeholder for manual rowing workouts created on the Peloton app',
            },
            {
                'id': 9999995,
                'discipline': 'strength',
                'title': 'Manual Strength Workout',
                'description': 'Generic placeholder for manual strength workouts created on the Peloton app',
            },
            {
                'id': 9999994,
                'discipline': 'yoga',
                'title': 'Manual Yoga Workout',
                'description': 'Generic placeholder for manual yoga workouts created on the Peloton app',
            },
            {
                'id': 9999993,
                'discipline': 'meditation',
                'title': 'Manual Meditation Workout',
                'description': 'Generic placeholder for manual meditation workouts created on the Peloton app',
            },
            {
                'id': 9999992,
                'discipline': 'stretching',
                'title': 'Manual Stretching Workout',
                'description': 'Generic placeholder for manual stretching workouts created on the Peloton app',
            },
            {
                'id': 9999991,
                'discipline': 'cardio',
                'title': 'Manual Cardio Workout',
                'description': 'Generic placeholder for manual cardio workouts created on the Peloton app',
            },
            {
                'id': 9999990,
                'discipline': 'other',
                'title': 'Manual Workout',
                'description': 'Generic placeholder for other manual workouts created on the Peloton app',
            },
        ]
        
        created_count = 0
        existing_count = 0
        
        with transaction.atomic():
            for ride_config in GENERIC_RIDE_DETAILS:
                discipline = ride_config['discipline']
                ride_id = ride_config['id']
                peloton_ride_id = f"manual_{discipline}_{ride_id}"
                
                # Check if already exists
                if RideDetail.objects.filter(peloton_ride_id=peloton_ride_id).exists():
                    self.stdout.write(f"  ✓ Generic {discipline} RideDetail already exists: {peloton_ride_id}")
                    existing_count += 1
                    continue
                
                # Get or create WorkoutType
                workout_type, created = WorkoutType.objects.get_or_create(
                    slug=discipline,
                    defaults={'name': discipline.title()}
                )
                
                # Create generic RideDetail
                ride_detail = RideDetail.objects.create(
                    peloton_ride_id=peloton_ride_id,
                    title=ride_config['title'],
                    description=ride_config['description'],
                    duration_seconds=0,  # Manual workouts calculate duration from performance data
                    workout_type=workout_type,
                    instructor=None,  # No instructor for manual workouts
                    fitness_discipline=discipline,
                    fitness_discipline_display_name=discipline.title(),
                    difficulty_rating_avg=None,
                    difficulty_rating_count=0,
                    class_type='',
                    is_power_zone_class=False,
                )
                
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created generic {discipline} RideDetail: {peloton_ride_id}"))
                created_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Summary:'))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Already existed: {existing_count}")
        self.stdout.write(f"  Total: {created_count + existing_count}")
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Generic RideDetail records are ready for manual workout sync'))
