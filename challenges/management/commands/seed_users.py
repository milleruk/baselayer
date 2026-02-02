from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random
import string

from challenges.models import Challenge, ChallengeInstance, Team, TeamMember
from plans.services import generate_weekly_plan
from core.services import DateRangeService

User = get_user_model()


def generate_random_email():
    """Generate a random email address"""
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    domains = ['example.com', 'test.com', 'demo.com', 'fake.com']
    return f"{username}@{random.choice(domains)}"


def generate_random_password():
    """Generate a random password"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


class Command(BaseCommand):
    help = "Seeds random users for testing. Optionally signs them up for a challenge and assigns a random plan."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of users to create (default: 10)'
        )
        parser.add_argument(
            '--challengeid',
            type=int,
            help='Challenge ID to sign users up for. If provided, users will be randomly assigned a plan from this challenge.'
        )
        parser.add_argument(
            '--challangeid',  # Support typo variant
            type=int,
            help='Challenge ID to sign users up for (alias for --challengeid).'
        )
        parser.add_argument(
            '--teamid',
            type=int,
            help='Team ID to assign users to. Requires --challengeid to be set.'
        )

    def handle(self, *args, **options):
        count = options['count']
        # Support both correct spelling and typo variant
        challenge_id = options.get('challengeid') or options.get('challangeid')
        team_id = options.get('teamid')
        
        # Validate team_id is only used with challenge_id
        if team_id and not challenge_id:
            self.stdout.write(
                self.style.ERROR(
                    "--teamid requires --challengeid to be set. "
                    "Users can only be assigned to teams when they join a challenge."
                )
            )
            return
        
        challenge = None
        available_templates = []
        team = None
        
        # Validate and get team if provided
        if team_id:
            try:
                team = Team.objects.get(pk=team_id)
                self.stdout.write(
                    self.style.SUCCESS(f"Found team: {team.name}")
                )
            except Team.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Team with ID {team_id} does not exist.")
                )
                return
        
        if challenge_id:
            try:
                challenge = Challenge.objects.get(pk=challenge_id)
                available_templates = list(challenge.available_templates.all())
                
                if not available_templates:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Challenge '{challenge.name}' has no available templates. "
                            "Please add templates to the challenge first."
                        )
                    )
                    return
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Found challenge: {challenge.name} with {len(available_templates)} template(s)"
                    )
                )
            except Challenge.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Challenge with ID {challenge_id} does not exist.")
                )
                return
        
        created_users = []
        signed_up_count = 0
        
        for i in range(count):
            # Generate unique email
            email = generate_random_email()
            # Ensure email is unique
            while User.objects.filter(email=email).exists():
                email = generate_random_email()
            
            # Create user
            password = generate_random_password()
            user = User.objects.create_user(
                email=email,
                password=password
            )
            created_users.append((user, password))
            
            self.stdout.write(
                self.style.SUCCESS(f"Created user: {user.email} (password: {password})")
            )
            
            # Sign up for challenge if provided
            if challenge and available_templates:
                # Randomly select a template
                template = random.choice(available_templates)
                
                # Randomly decide if user wants kegels (80% chance)
                include_kegels = random.random() < 0.8
                
                # Create challenge instance
                challenge_instance = ChallengeInstance.objects.create(
                    user=user,
                    challenge=challenge,
                    is_active=True,
                    selected_template=template,
                    include_kegels=include_kegels
                )
                
                # Generate weekly plans for the challenge duration
                today = date.today()
                challenge_start = challenge.start_date
                challenge_end = challenge.end_date
                
                # For past challenges (retaking), generate all weeks from challenge start
                # For current/upcoming challenges, generate from current week or challenge start (whichever is later)
                if challenge.has_ended:
                    # Past challenge - generate all weeks from challenge start
                    start_week = DateRangeService.sunday_of_current_week(challenge_start)
                    use_start_from_today = False
                else:
                    # Current or upcoming challenge - start from current week or challenge start
                    challenge_week_start = DateRangeService.sunday_of_current_week(challenge_start)
                    start_week = max(DateRangeService.sunday_of_current_week(today), challenge_week_start)
                    use_start_from_today = (start_week == DateRangeService.sunday_of_current_week(today))
                
                # Generate plans for each week of the challenge
                current_week_start = start_week
                week_num = 1
                weeks_generated = 0
                
                while current_week_start <= challenge_end:
                    # Calculate week number based on challenge start
                    if current_week_start >= challenge_start:
                        week_num = ((current_week_start - challenge_start).days // 7) + 1
                    else:
                        week_num = 1
                    
                    # Generate weekly plan
                    weekly = generate_weekly_plan(
                        user=user,
                        week_start=current_week_start,
                        template=template,
                        start_from_today=(use_start_from_today and current_week_start == DateRangeService.sunday_of_current_week(today)),
                        challenge_instance=challenge_instance,
                        week_number=week_num
                    )
                    weekly.challenge_instance = challenge_instance
                    weekly.save(update_fields=["challenge_instance"])
                    weeks_generated += 1
                    
                    current_week_start += timedelta(days=7)
                
                # Assign user to team if provided
                if team:
                    TeamMember.objects.get_or_create(
                        team=team,
                        challenge_instance=challenge_instance
                    )
                    self.stdout.write(
                        f"  → Signed up for challenge '{challenge.name}' with template '{template.name}' "
                        f"(kegels: {include_kegels}, {weeks_generated} weeks generated, team: {team.name})"
                    )
                else:
                    self.stdout.write(
                        f"  → Signed up for challenge '{challenge.name}' with template '{template.name}' "
                        f"(kegels: {include_kegels}, {weeks_generated} weeks generated)"
                    )
                
                signed_up_count += 1
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Created {len(created_users)} user(s)"
            )
        )
        
        if challenge:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Signed up {signed_up_count} user(s) for challenge '{challenge.name}'"
                )
            )
        
        if team:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Assigned {signed_up_count} user(s) to team '{team.name}'"
                )
            )
        
        # Print credentials for easy testing
        if created_users:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.WARNING("User Credentials (for testing):"))
            self.stdout.write("=" * 60)
            for user, password in created_users:
                self.stdout.write(f"Email: {user.email}")
                self.stdout.write(f"Password: {password}")
                self.stdout.write("-" * 60)
