from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, date
from challenges.models import Challenge, ChallengeInstance
from tracker.models import WeeklyPlan, DailyPlanItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed a completed challenge for a user (for testing badges/completion display)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--userid',
            type=int,
            required=True,
            help='User ID to complete the challenge for'
        )
        parser.add_argument(
            '--challengeid',
            type=int,
            required=False,
            help='Challenge ID to mark as completed'
        )
        parser.add_argument(
            '--changeid',
            type=int,
            required=False,
            help='Challenge ID to mark as completed (alias for --challengeid)'
        )
        parser.add_argument(
            '--completion-rate',
            type=float,
            default=100.0,
            help='Completion rate percentage (default: 100.0)'
        )

    def handle(self, *args, **options):
        user_id = options['userid']
        challenge_id = options.get('challengeid') or options.get('changeid')
        completion_rate = options['completion_rate']
        
        if not challenge_id:
            self.stdout.write(self.style.ERROR('Challenge ID is required. Use --challengeid or --changeid'))
            return
        
        # Validate user exists
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with ID {user_id} does not exist.'))
            return
        
        # Validate challenge exists
        try:
            challenge = Challenge.objects.get(pk=challenge_id)
        except Challenge.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Challenge with ID {challenge_id} does not exist.'))
            return
        
        self.stdout.write(f'Seeding completed challenge for user: {user.username} ({user_id})')
        self.stdout.write(f'Challenge: {challenge.name} ({challenge_id})')
        self.stdout.write(f'Target completion rate: {completion_rate}%')
        
        # Get or create challenge instance
        challenge_instance, created = ChallengeInstance.objects.get_or_create(
            user=user,
            challenge=challenge,
            defaults={
                'is_active': True,
                'include_kegels': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.WARNING(f'Created new ChallengeInstance (no template selected yet)'))
            # Try to set a default template if available
            if challenge.default_template:
                challenge_instance.selected_template = challenge.default_template
                challenge_instance.save(update_fields=['selected_template'])
                self.stdout.write(f'  Set default template: {challenge.default_template.name}')
            elif challenge.available_templates.exists():
                template = challenge.available_templates.first()
                challenge_instance.selected_template = template
                challenge_instance.save(update_fields=['selected_template'])
                self.stdout.write(f'  Set first available template: {template.name}')
        else:
            self.stdout.write(f'Using existing ChallengeInstance')
        
        # Get all weekly plans for this challenge instance
        weekly_plans = WeeklyPlan.objects.filter(
            challenge_instance=challenge_instance
        ).order_by('week_start')
        
        if not weekly_plans.exists():
            self.stdout.write(self.style.WARNING(
                f'No weekly plans found for this challenge instance. '
                f'You may need to join the challenge first or run regenerate_challenge_plans.'
            ))
            # Still mark as completed even without plans
            challenge_instance.completed_at = timezone.now()
            challenge_instance.is_active = False
            challenge_instance.save(update_fields=['completed_at', 'is_active'])
            self.stdout.write(self.style.SUCCESS(
                f'✓ Marked challenge as completed (no weekly plans to complete)'
            ))
            return
        
        self.stdout.write(f'Found {weekly_plans.count()} weekly plan(s)')
        
        # Calculate how many items need to be completed to achieve target completion rate
        total_plans = weekly_plans.count()
        plans_to_complete = int((completion_rate / 100.0) * total_plans)
        
        self.stdout.write(f'Completing {plans_to_complete} out of {total_plans} weekly plan(s)')
        
        # Complete weekly plans
        completed_count = 0
        for i, plan in enumerate(weekly_plans):
            if i < plans_to_complete:
                # Mark plan as completed
                plan.completed_at = timezone.now()
                plan.save(update_fields=['completed_at'])
                
                # Mark all items in the plan as done
                items = plan.items.all()
                items_updated = 0
                for item in items:
                    # Mark exercise as done
                    if not item.is_done:
                        item.is_done = True
                        item.completed_at = timezone.now()
                        items_updated += 1
                    
                    # Mark all Peloton activities as done
                    if item.peloton_ride_url and not item.ride_done:
                        item.ride_done = True
                        items_updated += 1
                    if item.peloton_run_url and not item.run_done:
                        item.run_done = True
                        items_updated += 1
                    if item.peloton_yoga_url and not item.yoga_done:
                        item.yoga_done = True
                        items_updated += 1
                    if item.peloton_strength_url and not item.strength_done:
                        item.strength_done = True
                        items_updated += 1
                    
                    if items_updated > 0:
                        item.save()
                
                # Mark bonus workout as done if it exists
                if plan.bonus_workout_done is False:
                    plan.bonus_workout_done = True
                    plan.save(update_fields=['bonus_workout_done'])
                
                completed_count += 1
                self.stdout.write(f'  ✓ Completed week {i+1} (Week of {plan.week_start})')
        
        # Mark challenge instance as completed
        challenge_instance.completed_at = timezone.now()
        challenge_instance.is_active = False
        challenge_instance.save(update_fields=['completed_at', 'is_active'])
        
        # Calculate actual completion rate
        actual_completion_rate = challenge_instance.completion_rate
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Successfully seeded completed challenge!'
        ))
        self.stdout.write(f'  - Completed {completed_count} weekly plan(s)')
        self.stdout.write(f'  - Actual completion rate: {actual_completion_rate:.1f}%')
        self.stdout.write(f'  - Total points: {challenge_instance.total_points}')
        self.stdout.write(f'  - Challenge marked as completed at: {challenge_instance.completed_at}')
