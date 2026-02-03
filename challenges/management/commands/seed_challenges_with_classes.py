"""
Management command to seed challenges with random Peloton classes.

This updates existing challenges (or creates them if needed) with real workout
assignments from the local RideDetail library, randomly selecting classes
appropriate for each week and day.

Can also create test RideDetail objects if the library is empty.

Usage:
    python manage.py seed_challenges_with_classes
    python manage.py seed_challenges_with_classes --challenge-id 1
    python manage.py seed_challenges_with_classes --clear
    python manage.py seed_challenges_with_classes --seed-classes  # Create test classes
"""
import logging
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from challenges.models import Challenge, ChallengeWorkoutAssignment, ChallengeBonusWorkout
from challenges.utils import generate_peloton_url
from workouts.models import RideDetail, WorkoutType, Instructor
from plans.models import PlanTemplate
from core.models import RideSyncQueue

logger = logging.getLogger(__name__)

# Sample test classes for seeding
SAMPLE_RIDES = [
    {"title": "Power Zone Endurance", "discipline": "cycling", "duration": 45, "instructor": "Matt Wilpers"},
    {"title": "30 Min HIIT Ride", "discipline": "cycling", "duration": 30, "instructor": "Denis Morton"},
    {"title": "45 Min Climb Ride", "discipline": "cycling", "duration": 45, "instructor": "Jess King"},
    {"title": "20 Min Core Power", "discipline": "cycling", "duration": 20, "instructor": "Olivia Amick"},
]

SAMPLE_RUNS = [
    {"title": "20 Min Tempo Run", "discipline": "running", "duration": 20, "instructor": "Becs Gentry"},
    {"title": "30 Min Steady Run", "discipline": "running", "duration": 30, "instructor": "Matty Maggiacomo"},
    {"title": "45 Min Long Run", "discipline": "running", "duration": 45, "instructor": "Andy Speer"},
    {"title": "15 Min Speed Intervals", "discipline": "running", "duration": 15, "instructor": "Christine D'Ercole"},
]

SAMPLE_YOGA = [
    {"title": "20 Min Yoga Flow", "discipline": "yoga", "duration": 20, "instructor": "Kristin McGee"},
    {"title": "30 Min Flexibility", "discipline": "yoga", "duration": 30, "instructor": "Aditi Shah"},
]

SAMPLE_STRENGTH = [
    {"title": "20 Min Upper Body", "discipline": "strength", "duration": 20, "instructor": "Jess Sims"},
    {"title": "30 Min Lower Body", "discipline": "strength", "duration": 30, "instructor": "Robin Arzón"},
    {"title": "15 Min Core", "discipline": "strength", "duration": 15, "instructor": "Andy Speer"},
]


class Command(BaseCommand):
    help = 'Seed challenges with random Peloton classes from the local library'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--challenge-id',
            type=int,
            help='Update only a specific challenge ID'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing assignments before seeding'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of seed challenges to create (if creating new)'
        )
        parser.add_argument(
            '--seed-classes',
            action='store_true',
            help='Create test RideDetail classes if library is empty'
        )
        parser.add_argument(
            '--past-challenges',
            action='store_true',
            help='Create some past challenges for testing'
        )
    
    def handle(self, *args, **options):
        challenge_id = options.get('challenge_id')
        clear_existing = options.get('clear', False)
        seed_count = options.get('count', 3)
        seed_classes = options.get('seed_classes', False)
        past_challenges = options.get('past_challenges', False)

        
        # Seed test classes if requested
        if seed_classes:
            self.seed_test_classes()
        
        # Create past challenges if requested
        if past_challenges:
            self.create_past_challenges()
        
        # Get challenges to seed
        if challenge_id:
            challenges = Challenge.objects.filter(id=challenge_id)
            if not challenges.exists():
                self.stdout.write(self.style.ERROR(f'Challenge {challenge_id} not found'))
                return
        else:
            # Get all challenges (active and past)
            challenges = Challenge.objects.all()
        
        if not challenges.exists():
            self.stdout.write(self.style.WARNING('No challenges to seed'))
            return
        
        self.stdout.write(f"Seeding {challenges.count()} challenge(s)...")
        
        for challenge in challenges:
            self.seed_challenge(challenge, clear=clear_existing)
        
        self.stdout.write(self.style.SUCCESS('✓ Challenge seeding complete'))
    
    def seed_challenge(self, challenge, clear=False):
        """Seed a specific challenge with workout assignments."""
        self.stdout.write(f"\nSeeding challenge: {challenge.name}")
        
        # Get templates
        templates = challenge.available_templates.all()
        if not templates.exists():
            self.stdout.write(self.style.WARNING(f'  No templates available for {challenge.name}'))
            return
        
        # Clear existing if requested
        if clear:
            ChallengeWorkoutAssignment.objects.filter(challenge=challenge).delete()
            self.stdout.write('  Cleared existing assignments')
        
        # Check if we need to seed
        existing_count = ChallengeWorkoutAssignment.objects.filter(challenge=challenge).count()
        if existing_count > 0 and not clear:
            self.stdout.write(f'  Already has {existing_count} assignments, skipping')
            return
        
        # Get RideDetail counts by activity type
        ride_count = RideDetail.objects.filter(
            fitness_discipline__in=['cycling', 'ride']
        ).count()
        run_count = RideDetail.objects.filter(
            fitness_discipline__in=['running', 'run']
        ).count()
        yoga_count = RideDetail.objects.filter(
            fitness_discipline__in=['yoga']
        ).count()
        strength_count = RideDetail.objects.filter(
            fitness_discipline__in=['strength']
        ).count()
        
        self.stdout.write(
            f'  Available classes: {ride_count} rides, {run_count} runs, '
            f'{yoga_count} yoga, {strength_count} strength'
        )
        
        if ride_count == 0 and run_count == 0 and yoga_count == 0 and strength_count == 0:
            self.stdout.write(
                self.style.WARNING('  No RideDetail objects found in database. Run sync_missing_rides first.')
            )
            return
        
        # Seed for each template
        total_created = 0
        for template in templates:
            created = self.seed_template(challenge, template, ride_count, run_count, yoga_count, strength_count)
            total_created += created
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {total_created} assignments'))
    
    def seed_template(self, challenge, template, ride_count, run_count, yoga_count, strength_count):
        """Seed assignments for a specific challenge-template combination."""
        num_weeks = challenge.duration_weeks
        created_count = 0
        
        # Get template days
        template_days = {d.day_of_week: d for d in template.days.all()}
        
        # Build lookup for which days need which activities
        day_activities = {}  # day_of_week -> [activity_types]
        for day_num in range(7):
            template_day = template_days.get(day_num)
            if not template_day:
                continue
            
            focus_lower = template_day.peloton_focus.lower()
            activities = []
            
            if 'ride' in focus_lower or 'pz' in focus_lower or 'power zone' in focus_lower:
                activities.append('ride')
            if 'run' in focus_lower:
                activities.append('run')
            if 'yoga' in focus_lower:
                activities.append('yoga')
            if 'strength' in focus_lower:
                activities.append('strength')
            
            if activities:
                day_activities[day_num] = activities
        
        # Get already-seeded days to avoid duplicates
        existing_assignments = ChallengeWorkoutAssignment.objects.filter(
            challenge=challenge,
            template=template
        ).values_list('week_number', 'day_of_week', 'activity_type')
        
        # Seed each week/day/activity
        for week_num in range(1, num_weeks + 1):
            for day_num, activities in day_activities.items():
                for activity_type in activities:
                    # Skip if already assigned
                    if (week_num, day_num, activity_type) in existing_assignments:
                        continue
                    
                    # Get random class of this activity type
                    ride_detail = self.get_random_ride_detail(
                        activity_type,
                        ride_count, run_count, yoga_count, strength_count
                    )
                    
                    if not ride_detail:
                        continue
                    
                    # Create assignment
                    assignment, created = ChallengeWorkoutAssignment.objects.update_or_create(
                        challenge=challenge,
                        template=template,
                        week_number=week_num,
                        day_of_week=day_num,
                        activity_type=activity_type,
                        alternative_group=None,
                        order_in_group=0,
                        defaults={
                            'peloton_url': ride_detail.peloton_class_url,
                            'workout_title': ride_detail.title,
                            'ride_detail': ride_detail,
                            'points': 50,
                        }
                    )
                    if created:
                        created_count += 1
        
        return created_count
    
    def get_random_ride_detail(self, activity_type, ride_count, run_count, yoga_count, strength_count):
        """Get a random RideDetail of the specified activity type."""
        if activity_type == 'ride':
            if ride_count == 0:
                return None
            rides = RideDetail.objects.filter(fitness_discipline__in=['cycling', 'ride'])
            return random.choice(rides) if rides.exists() else None
        
        elif activity_type == 'run':
            if run_count == 0:
                return None
            runs = RideDetail.objects.filter(fitness_discipline__in=['running', 'run'])
            return random.choice(runs) if runs.exists() else None
        
        elif activity_type == 'yoga':
            if yoga_count == 0:
                return None
            yogas = RideDetail.objects.filter(fitness_discipline__in=['yoga'])
            return random.choice(yogas) if yogas.exists() else None
        
        elif activity_type == 'strength':
            if strength_count == 0:
                return None
            strengths = RideDetail.objects.filter(fitness_discipline__in=['strength'])
            return random.choice(strengths) if strengths.exists() else None
        
        return None
    
    def seed_test_classes(self):
        """Create test RideDetail objects if library is empty."""
        ride_count = RideDetail.objects.filter(fitness_discipline__in=['cycling', 'ride']).count()
        run_count = RideDetail.objects.filter(fitness_discipline__in=['running', 'run']).count()
        yoga_count = RideDetail.objects.filter(fitness_discipline__in=['yoga']).count()
        strength_count = RideDetail.objects.filter(fitness_discipline__in=['strength']).count()
        
        total = ride_count + run_count + yoga_count + strength_count
        
        if total > 0:
            self.stdout.write(
                f'Library already has {total} classes. Use --clear if you want to reset.'
            )
            return
        
        self.stdout.write('\nCreating test classes...')
        
        all_samples = [
            (SAMPLE_RIDES, 'cycling', 'Ride'),
            (SAMPLE_RUNS, 'running', 'Run'),
            (SAMPLE_YOGA, 'yoga', 'Yoga'),
            (SAMPLE_STRENGTH, 'strength', 'Strength'),
        ]
        
        created_count = 0
        
        for samples, discipline, workout_type_name in all_samples:
            # Get or create workout type
            workout_type, _ = WorkoutType.objects.get_or_create(
                slug=discipline.lower(),
                defaults={'name': workout_type_name}
            )
            
            for sample in samples:
                # Get or create instructor
                instructor, _ = Instructor.objects.get_or_create(
                    name=sample['instructor'],
                    defaults={'peloton_id': f"test_{sample['instructor'].lower().replace(' ', '_')}"}
                )
                
                # Create test peloton_id
                test_id = f"test_{sample['title'].lower().replace(' ', '_')}"
                
                # Create RideDetail
                ride_detail, created = RideDetail.objects.get_or_create(
                    peloton_id=test_id,
                    defaults={
                        'title': sample['title'],
                        'description': f"Test {sample['discipline']} class",
                        'duration_seconds': sample['duration'] * 60,
                        'fitness_discipline': discipline,
                        'fitness_discipline_display_name': workout_type_name,
                        'workout_type': workout_type,
                        'instructor': instructor,
                        'peloton_class_url': generate_peloton_url(test_id),
                        'created_at_timestamp': timezone.now().timestamp(),
                        'class_type': 'power_zone' if discipline == 'cycling' else 'standard',
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  ✓ {sample["title"]} ({sample["discipline"]})')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {created_count} test classes'))
    
    def create_past_challenges(self):
        """Create past challenges for testing the past challenge flows."""
        from challenges.models import ChallengeInstance
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        self.stdout.write('\nCreating past challenges...')
        
        # Get a default template
        default_template = PlanTemplate.objects.first()
        if not default_template:
            self.stdout.write(self.style.WARNING('  No templates found, skipping past challenges'))
            return
        
        past_challenge_configs = [
            {
                "name": "Winter Warrior Challenge",
                "start_offset_days": 90,  # 90 days ago
                "duration_days": 30,
                "description": "A past challenge testing the Live Challenge badge display.",
            },
            {
                "name": "New Year Reset",
                "start_offset_days": 35,  # 35 days ago
                "duration_days": 28,
                "description": "Another past challenge for testing completed_during_live property.",
            },
            {
                "name": "Spring Sprint",
                "start_offset_days": 7,  # 7 days ago (very recent past)
                "duration_days": 7,
                "description": "Recently completed challenge to test current state transitions.",
            },
        ]
        
        created_count = 0
        
        for config in past_challenge_configs:
            start_date = date.today() - timedelta(days=config["start_offset_days"])
            end_date = start_date + timedelta(days=config["duration_days"])
            
            # Create challenge if it doesn't exist
            challenge, created = Challenge.objects.get_or_create(
                name=config["name"],
                defaults={
                    "description": config["description"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_active": False,  # Past challenges are inactive
                    "is_visible": True,
                    "challenge_type": "team",
                    "categories": "cycling,running",
                }
            )
            
            if created:
                # Add template
                challenge.available_templates.add(default_template)
                challenge.default_template = default_template
                challenge.save()
                created_count += 1
                self.stdout.write(f'  ✓ {config["name"]} ({start_date} to {end_date})')
            else:
                self.stdout.write(f'  ⊘ {config["name"]} (already exists)')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {created_count} past challenges'))
