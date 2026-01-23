from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from tracker.models import WeeklyPlan
from challenges.models import ChallengeInstance
from tracker.views import sunday_of_current_week
from plans.services import generate_weekly_plan


class Command(BaseCommand):
    help = "Regenerate weekly plans for challenge instances that don't have plans"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="Username to regenerate plans for (optional, if not provided regenerates for all users)",
        )
        parser.add_argument(
            "--challenge",
            type=int,
            help="Challenge ID to regenerate plans for (optional)",
        )

    def handle(self, *args, **options):
        username = options.get("user")
        challenge_id = options.get("challenge")

        # Get challenge instances
        challenge_instances = ChallengeInstance.objects.all()
        
        if username:
            challenge_instances = challenge_instances.filter(user__username=username)
        
        if challenge_id:
            challenge_instances = challenge_instances.filter(challenge_id=challenge_id)
        
        if not challenge_instances.exists():
            self.stdout.write(self.style.WARNING("No challenge instances found."))
            return
        
        total_regenerated = 0
        
        for ci in challenge_instances:
            challenge = ci.challenge
            template = ci.selected_template or challenge.default_template
            
            if not template:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping {ci.user.username} - {challenge.name}: No template selected"
                    )
                )
                continue
            
            # Check if plans already exist
            existing_plans_count = ci.weekly_plans.count()
            
            if existing_plans_count > 0:
                self.stdout.write(
                    f"Skipping {ci.user.username} - {challenge.name}: Already has {existing_plans_count} plan(s)"
                )
                continue
            
            # Generate plans
            today = date.today()
            challenge_start = challenge.start_date
            challenge_end = challenge.end_date
            
            # For past challenges, generate all weeks from challenge start
            # For current/upcoming challenges, generate from current week or challenge start
            if challenge.has_ended:
                start_week = sunday_of_current_week(challenge_start)
                use_start_from_today = False
            else:
                challenge_week_start = sunday_of_current_week(challenge_start)
                start_week = max(sunday_of_current_week(today), challenge_week_start)
                use_start_from_today = (start_week == sunday_of_current_week(today))
            
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
                
                # Check if plan already exists for this week
                existing_plan = WeeklyPlan.objects.filter(
                    user=ci.user,
                    week_start=current_week_start,
                    challenge_instance=ci
                ).first()
                
                if not existing_plan:
                    weekly = generate_weekly_plan(
                        user=ci.user,
                        week_start=current_week_start,
                        template=template,
                        start_from_today=(use_start_from_today and current_week_start == sunday_of_current_week(today)),
                        challenge_instance=ci,
                        week_number=week_num
                    )
                    weekly.challenge_instance = ci
                    weekly.save(update_fields=["challenge_instance"])
                    weeks_generated += 1
                
                current_week_start += timedelta(days=7)
            
            if weeks_generated > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {ci.user.username} - {challenge.name}: Generated {weeks_generated} week(s)"
                    )
                )
                total_regenerated += weeks_generated
            else:
                self.stdout.write(
                    f"  {ci.user.username} - {challenge.name}: No weeks to generate"
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Regenerated {total_regenerated} week(s) across {challenge_instances.count()} challenge instance(s)."
            )
        )
