from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, date
from plans.models import Exercise, PlanTemplate

class Challenge(models.Model):
    """Admin-defined challenge with time periods and workout configuration"""
    CHALLENGE_TYPE_CHOICES = [
        ("team", "Team Challenge"),
        ("mini", "Mini Challenge"),
        ("individual", "Individual Challenge"),
    ]
    
    CATEGORY_CHOICES = [
        ("cycling", "CYCLING"),
        ("running", "RUNNING"),
        ("strength", "STRENGTH"),
        ("yoga", "YOGA"),
    ]
    
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    start_date = models.DateField(help_text="Challenge start date")
    end_date = models.DateField(help_text="Challenge end date")
    signup_opens_date = models.DateField(null=True, blank=True, help_text="Date when signup opens for this challenge (optional, defaults to challenge start date)")
    signup_deadline = models.DateField(null=True, blank=True, help_text="Last date users can sign up (optional)")
    is_active = models.BooleanField(default=True, help_text="Whether this challenge is currently active")
    is_visible = models.BooleanField(default=True, help_text="Whether this challenge is visible for signup")
    challenge_type = models.CharField(max_length=20, choices=CHALLENGE_TYPE_CHOICES, default="mini")
    categories = models.CharField(max_length=200, blank=True, default="", help_text="Comma-separated categories (cycling,running,strength,yoga)")
    image = models.ImageField(upload_to="challenges/", blank=True, null=True, help_text="Challenge logo/image")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Workout configuration - which templates are available for this challenge
    available_templates = models.ManyToManyField(
        PlanTemplate,
        related_name="challenges",
        help_text="Plan templates available for this challenge. Users can choose from these when joining."
    )
    # Default/recommended template (should be one of the available templates)
    default_template = models.ForeignKey(PlanTemplate, on_delete=models.SET_NULL, null=True, blank=True, 
                                         help_text="Recommended template (should be one of the available templates)")
    
    def get_categories_list(self):
        """Return categories as a list"""
        if not self.categories:
            return []
        return [cat.strip().upper() for cat in self.categories.split(",")]
    
    class Meta:
        ordering = ["start_date", "created_at"]  # Earliest first
    
    def __str__(self):
        return self.name
    
    @property
    def is_currently_running(self):
        """Check if challenge is currently running"""
        today = date.today()
        return self.start_date <= today <= self.end_date
    
    @property
    def has_ended(self):
        """Check if challenge has ended"""
        return date.today() > self.end_date
    
    @property
    def can_signup(self):
        """Check if users can still sign up - based on signup_opens_date, signup_deadline, and challenge status"""
        if not self.is_visible:
            return False
        
        today = date.today()
        
        # Can always retake past challenges (after they've ended)
        if self.has_ended:
            return True
        
        # Cannot join once challenge has started (but hasn't ended yet)
        if today >= self.start_date:
            return False
        
        # Check if signup has opened yet
        signup_opens = self.signup_opens_date if self.signup_opens_date else self.start_date
        if today < signup_opens:
            return False  # Signup hasn't opened yet
        
        # Check signup deadline if set
        if self.signup_deadline:
            return today <= self.signup_deadline
        
        # If no deadline, can signup after signup opens and before challenge starts
        return True
    
    @property
    def duration_weeks(self):
        """Calculate duration in weeks"""
        if not self.start_date or not self.end_date:
            return 0
        delta = self.end_date - self.start_date
        return max(1, (delta.days // 7) + 1)
    
    @property
    def week_range(self):
        """Return a range of week numbers for this challenge"""
        return range(1, self.duration_weeks + 1)
    
    def is_week_unlocked(self, week_number):
        """Check if a specific week is unlocked/live"""
        # If challenge has ended, all weeks are unlocked (for retaking past challenges)
        if self.has_ended:
            return True
        
        # For active/upcoming challenges, check unlock status
        try:
            unlock = self.week_unlocks.get(week_number=week_number)
            # Check if manually unlocked
            if unlock.is_unlocked:
                return True
            # Check if auto-unlock date has passed
            if unlock.unlock_date and date.today() >= unlock.unlock_date:
                # Auto-unlock it
                unlock.is_unlocked = True
                unlock.save()
                return True
            return False
        except ChallengeWeekUnlock.DoesNotExist:
            # If no unlock record exists, check if challenge has started
            # If challenge hasn't started yet, lock all weeks
            if date.today() < self.start_date:
                return False
            # If challenge has started but no unlock record, unlock week 1 by default
            # Other weeks need explicit unlock
            return week_number == 1
    
    def get_unlocked_weeks(self):
        """Get list of unlocked week numbers"""
        unlocked = []
        for week_num in self.week_range:
            if self.is_week_unlocked(week_num):
                unlocked.append(week_num)
        return unlocked
    
    def get_scoring_participants(self):
        """Get challenge instances that are contributing to team scores"""
        if self.challenge_type != "team":
            return self.instances.all()
        
        # For team challenges, filter to only scoring participants
        return [instance for instance in self.instances.all() if instance.is_scoring]
    
    def get_team_total_points(self):
        """Get total points from all scoring participants (for team challenges)"""
        if self.challenge_type != "team":
            return None
        
        scoring_instances = self.get_scoring_participants()
        return sum(instance.total_points for instance in scoring_instances)
    
    def clean(self):
        """Validate that challenge dates don't overlap with other active challenges"""
        from django.db.models import Q
        
        # Validate that end_date is after start_date
        if self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End date must be after start date.'
            })
        
        # Validate that signup_deadline is before start_date if set
        if self.signup_deadline and self.signup_deadline >= self.start_date:
            raise ValidationError({
                'signup_deadline': 'Signup deadline must be before the challenge start date.'
            })
        
        # Only check for overlaps if this challenge is active
        # Inactive challenges can overlap (they're not "real" challenges)
        if self.is_active:
            # Check for overlapping dates with other active challenges
            # Two date ranges overlap if: start1 <= end2 AND end1 >= start2
            overlapping = Challenge.objects.filter(
                is_active=True
            ).exclude(
                pk=self.pk  # Exclude self when updating
            ).filter(
                Q(start_date__lte=self.end_date) & Q(end_date__gte=self.start_date)
            )
            
            if overlapping.exists():
                overlapping_challenges = [str(c) for c in overlapping]
                raise ValidationError({
                    'start_date': f'This challenge overlaps with existing active challenge(s): {", ".join(overlapping_challenges)}. '
                                f'Active challenges cannot have overlapping dates.',
                    'end_date': f'This challenge overlaps with existing active challenge(s): {", ".join(overlapping_challenges)}. '
                               f'Active challenges cannot have overlapping dates.',
                })
    
    def save(self, *args, **kwargs):
        """Override save to call clean() validation"""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # After saving, validate that default_template is in available_templates
        # This needs to happen after save because ManyToMany fields need the object to be saved first
        if self.default_template and self.available_templates.exists():
            if self.default_template not in self.available_templates.all():
                # Clear default_template if it's not in available_templates
                self.default_template = None
                super().save(update_fields=['default_template'])


class ChallengeInstance(models.Model):
    """User's participation in a challenge"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenge_instances")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="instances")
    selected_template = models.ForeignKey(PlanTemplate, on_delete=models.SET_NULL, null=True, blank=True,
                                         help_text="User's chosen plan template for this challenge")
    include_kegels = models.BooleanField(default=True, help_text="Whether user wants to include Kegel exercises in their plan")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        # Removed unique_together to allow multiple attempts per challenge
        ordering = ["-started_at"]
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.name}"
    
    @property
    def total_points(self):
        return sum(plan.total_points for plan in self.weekly_plans.all())
    
    @property
    def completion_rate(self):
        plans = self.weekly_plans.all()
        if not plans:
            return 0
        completed = sum(1 for plan in plans if plan.is_completed)
        return (completed / len(plans)) * 100
    
    @property
    def all_weeks_completed(self):
        """Check if all weeks in this challenge are completed"""
        plans = self.weekly_plans.all()
        if not plans:
            return False
        return all(plan.is_completed for plan in plans)
    
    def can_leave_challenge(self):
        """
        Check if user can leave this challenge.
        - Past challenges: Always can leave
        - Live challenges: Can only leave if they haven't completed anything in the previous week
        """
        # Past challenges: always can leave
        if self.challenge.has_ended:
            return True, None
        
        # Live challenges: check previous week completion
        if self.challenge.is_currently_running:
            plans = self.weekly_plans.all().order_by("week_start")
            if not plans.exists():
                # No plans yet, can leave
                return True, None
            
            # Find current week number based on today's date
            from datetime import date, timedelta
            today = date.today()
            challenge_start = self.challenge.start_date
            
            # Calculate which week we're currently in
            days_since_start = (today - challenge_start).days
            current_week_num = (days_since_start // 7) + 1
            
            # If we're in week 1, can always leave (no previous week)
            if current_week_num <= 1:
                return True, None
            
            # Check previous week (current_week_num - 1)
            previous_week_num = current_week_num - 1
            
            # Find the plan for the previous week
            previous_week_start = challenge_start + timedelta(days=(previous_week_num - 1) * 7)
            previous_plan = plans.filter(week_start=previous_week_start).first()
            
            if not previous_plan:
                # Previous week plan doesn't exist, can leave
                return True, None
            
            # Check if user has completed ANY activities in the previous week
            # Check for completed exercises
            has_completed_exercises = previous_plan.items.filter(is_done=True).exists()
            
            # Check for completed Peloton activities
            has_completed_activities = (
                previous_plan.items.filter(ride_done=True).exists() or
                previous_plan.items.filter(run_done=True).exists() or
                previous_plan.items.filter(yoga_done=True).exists() or
                previous_plan.items.filter(strength_done=True).exists()
            )
            
            # Check for completed bonus workout
            has_completed_bonus = previous_plan.bonus_workout_done
            
            # If they've completed anything in previous week, can't leave
            if has_completed_exercises or has_completed_activities or has_completed_bonus:
                return False, f"You cannot leave this challenge because you've completed activities in Week {previous_week_num}. You can leave if you don't complete anything in Week {current_week_num}."
            
            # No completions in previous week, can leave
            return True, None
        
        # Upcoming challenges: can leave
        return True, None
    
    @property
    def is_scoring(self):
        """
        Check if this user is contributing to team scores.
        For active challenges, users must be completing activities to score.
        For past challenges, all participants score.
        """
        # If challenge has ended, user always scores (for historical purposes)
        if self.challenge.has_ended:
            return True
        
        # If challenge hasn't started yet, user scores (they're signed up)
        if date.today() < self.challenge.start_date:
            return True
        
        # For active challenges, check if user is completing activities
        if self.challenge.is_currently_running:
            # Get all plans for this challenge instance
            plans = self.weekly_plans.all().order_by("week_start")
            if not plans.exists():
                # No plans yet, but challenge is running - don't score until they start
                return False
            
            # Check if user has completed any activities in the last 2 weeks
            # This ensures they're actively participating
            today = date.today()
            two_weeks_ago = today - timedelta(days=14)
            
            # Get plans from the last 2 weeks
            recent_plans = plans.filter(week_start__gte=two_weeks_ago)
            
            if recent_plans.exists():
                # Check if any recent plan has completed activities
                for plan in recent_plans:
                    # Check if plan has any completed exercises or activities
                    items = plan.items.all()
                    for item in items:
                        # Check if any exercise is done (kegel exercises)
                        if item.is_done:
                            return True
                        # Check if any Peloton activity is done
                        if (item.peloton_ride_url and item.ride_done) or \
                           (item.peloton_run_url and item.run_done) or \
                           (item.peloton_yoga_url and item.yoga_done) or \
                           (item.peloton_strength_url and item.strength_done):
                            return True
                
                # No activities completed in recent weeks - not scoring
                return False
            else:
                # No recent plans, but challenge is running - check if they have any plans at all
                # If they have plans but none are recent, they might have joined early
                # Check if they've completed anything ever
                for plan in plans:
                    items = plan.items.all()
                    for item in items:
                        if item.is_done or item.ride_done or item.run_done or item.yoga_done or item.strength_done:
                            return True
                return False
        
        # For upcoming challenges, user scores (they're signed up)
        return True
    
    @property
    def contributes_to_team_score(self):
        """Alias for is_scoring - for team challenge compatibility"""
        return self.is_scoring

class WeeklyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    challenge_instance = models.ForeignKey("ChallengeInstance", on_delete=models.CASCADE, related_name="weekly_plans", null=True, blank=True)
    week_start = models.DateField()
    template_name = models.CharField(max_length=120)
    bonus_workout_done = models.BooleanField(default=False, help_text="Whether the bonus workout (additional ride) is completed")
    bonus_workout_url = models.URLField(blank=True, null=True, help_text="URL for the bonus workout (any 30 min Peloton class)")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "week_start")
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.user.username} - {self.week_start}"
    
    @property
    def week_end(self):
        return self.week_start + timedelta(days=6)
    
    @property
    def is_past(self):
        return self.week_end < timezone.now().date()
    
    @property
    def is_current_week(self):
        today = timezone.now().date()
        return self.week_start <= today <= self.week_end
    
    @property
    def total_exercises(self):
        return self.items.count()
    
    @property
    def completed_exercises(self):
        return self.items.filter(is_done=True).count()
    
    @property
    def max_core_points(self):
        """Maximum possible points from core workouts only (excluding bonus) - sum of all workout_points"""
        from django.db.models import Q
        
        # Get all workout items (items with Peloton URLs, excluding bonus)
        workout_items = self.items.filter(
            (Q(peloton_ride_url__isnull=False) & ~Q(peloton_ride_url='')) |
            (Q(peloton_run_url__isnull=False) & ~Q(peloton_run_url='')) |
            (Q(peloton_yoga_url__isnull=False) & ~Q(peloton_yoga_url='')) |
            (Q(peloton_strength_url__isnull=False) & ~Q(peloton_strength_url=''))
        ).exclude(peloton_focus__icontains="Bonus")
        
        # Group by day_of_week - sum max points per day (only one workout per day counts)
        total_max = 0
        days_seen = set()
        
        for item in workout_items.order_by('day_of_week', 'id'):
            if item.day_of_week in days_seen:
                continue  # Already counted max points for this day
            
            # Use stored workout_points, fallback to 50 for backward compatibility
            points = item.workout_points if item.workout_points > 0 else 50
            total_max += points
            days_seen.add(item.day_of_week)
        
        return total_max if total_max > 0 else 150  # Fallback to 150 if no points set
    
    @property
    def completion_rate(self):
        """Completion rate based on total points out of max core (150) for medal calculation"""
        max_core = self.max_core_points
        if max_core == 0:
            return 0
        # Use max_core (150) as denominator, not max_total_points (160)
        # This allows 160/150 = 106.67% for Platinum medal
        return (self.total_points / max_core) * 100
    
    @property
    def exercise_points(self):
        """Points from completed kegel exercises - NOW WORTH 0 POINTS"""
        # Kegels no longer contribute to points
        return 0
    
    @property
    def core_workout_count(self):
        """Count total number of core workouts (rides/runs/yoga/strength) in this week"""
        # Count distinct days with any core workout assigned
        all_days = set()
        all_days.update(self.items.filter(peloton_ride_url__isnull=False).exclude(peloton_ride_url='').values_list('day_of_week', flat=True))
        all_days.update(self.items.filter(peloton_run_url__isnull=False).exclude(peloton_run_url='').values_list('day_of_week', flat=True))
        all_days.update(self.items.filter(peloton_yoga_url__isnull=False).exclude(peloton_yoga_url='').values_list('day_of_week', flat=True))
        all_days.update(self.items.filter(peloton_strength_url__isnull=False).exclude(peloton_strength_url='').values_list('day_of_week', flat=True))
        
        return len(all_days)
    
    @property
    def completed_core_workouts(self):
        """Count completed core workouts"""
        # Count distinct days with completed core workouts
        all_days = set()
        all_days.update(self.items.filter(ride_done=True).values_list('day_of_week', flat=True))
        all_days.update(self.items.filter(run_done=True).values_list('day_of_week', flat=True))
        all_days.update(self.items.filter(yoga_done=True).values_list('day_of_week', flat=True))
        all_days.update(self.items.filter(strength_done=True).values_list('day_of_week', flat=True))
        
        return len(all_days)
    
    @property
    def activity_points(self):
        """Points from completed core workouts - simplified to use stored workout_points"""
        from django.db.models import Q
        
        # Get all workout items (items with Peloton URLs, excluding bonus)
        workout_items = self.items.filter(
            (Q(peloton_ride_url__isnull=False) & ~Q(peloton_ride_url='')) |
            (Q(peloton_run_url__isnull=False) & ~Q(peloton_run_url='')) |
            (Q(peloton_yoga_url__isnull=False) & ~Q(peloton_yoga_url='')) |
            (Q(peloton_strength_url__isnull=False) & ~Q(peloton_strength_url=''))
        ).exclude(peloton_focus__icontains="Bonus")
        
        # Group by day_of_week - only count one completed workout per day (to handle alternatives)
        total_points = 0
        completed_days = set()
        
        for item in workout_items.order_by('day_of_week', 'id'):
            if item.day_of_week in completed_days:
                continue  # Already counted a workout for this day
            
            # Check if this workout is completed
            if item.ride_done or item.run_done or item.yoga_done or item.strength_done:
                # Use stored workout_points, fallback to 50 for backward compatibility
                points = item.workout_points if item.workout_points > 0 else 50
                total_points += points
                completed_days.add(item.day_of_week)
        
        return total_points
    
    @property
    def bonus_points(self):
        """Points from bonus workouts - 10 points each, but only if all core workouts are completed"""
        from django.db.models import Q
        
        # First check if all core workouts are completed
        core_count = self.core_workout_count
        completed_core_count = self.completed_core_workouts
        
        # Only award bonus points if all core workouts are done
        if core_count == 0 or completed_core_count < core_count:
            return 0
        
        # Count completed bonus workouts (items with "Bonus" in peloton_focus)
        bonus_items = self.items.filter(peloton_focus__icontains="Bonus")
        completed_bonus = bonus_items.filter(
            Q(ride_done=True) | Q(run_done=True) | Q(yoga_done=True) | Q(strength_done=True)
        ).count()
        return completed_bonus * 10
    
    @property
    def total_points(self):
        """Total points from core workouts and bonus workout"""
        return self.activity_points + self.bonus_points
    
    @property
    def max_total_points(self):
        """Maximum possible points based on actual workout_points stored in items"""
        # Use max_core_points which correctly sums up the actual workout_points from items
        # This ensures the calculation matches the actual points assigned to each workout
        max_core = self.max_core_points
        return max_core + 10  # +10 for bonus
    
    @property
    def max_exercise_points(self):
        """Maximum possible points from exercises (10 per exercise)"""
        return self.total_exercises * 10
    
    @property
    def max_activity_points(self):
        """Maximum possible points from activities (50 per activity)"""
        # Count each activity type separately (a day can have multiple activities)
        # Count distinct days with ride activities
        days_with_ride = set()
        # Count distinct days with run activities
        days_with_run = set()
        # Count distinct days with yoga activities
        days_with_yoga = set()
        # Count distinct days with strength activities
        days_with_strength = set()
        
        for item in self.items.all():
            focus_lower = item.peloton_focus.lower()
            if "pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or "ride" in focus_lower:
                days_with_ride.add(item.day_of_week)
            if "run" in focus_lower:
                days_with_run.add(item.day_of_week)
            if "yoga" in focus_lower:
                days_with_yoga.add(item.day_of_week)
            if "strength" in focus_lower:
                days_with_strength.add(item.day_of_week)
        
        # Each activity type counts as 50 points per day it's available
        max_activities = len(days_with_ride) + len(days_with_run) + len(days_with_yoga) + len(days_with_strength)
        return max_activities * 50
    
    # Removed duplicate max_total_points - using the one above that calculates based on core_count
    
    @property
    def is_completed(self):
        return self.completed_at is not None or (self.is_past and self.completion_rate >= 80)
    
    def can_toggle_exercise(self, day_of_week):
        """Check if exercise can be toggled based on date"""
        today = timezone.now().date()
        exercise_date = self.week_start + timedelta(days=day_of_week)
        
        # For past challenges, allow toggling all exercises
        if self.challenge_instance and self.challenge_instance.challenge.has_ended:
            # Can't toggle if week is completed
            if self.is_completed:
                return False, "This week is already completed."
            return True, None
        
        # Can toggle if it's today or in the future (within the week)
        if exercise_date > today:
            return True, None
        # Can toggle if it's today
        if exercise_date == today:
            return True, None
        # Can't toggle if it's in the past (for active challenges)
        if exercise_date < today:
            return False, "This exercise is in the past and cannot be marked as done."
        # Can't toggle if week is completed
        if self.is_completed:
            return False, "This week is already completed."
        return True, None


class DailyPlanItem(models.Model):
    DAY_CHOICES = [(0,"Sun"),(1,"Mon"),(2,"Tue"),(3,"Wed"),(4,"Thu"),(5,"Fri"),(6,"Sat")]
    weekly_plan = models.ForeignKey(WeeklyPlan, on_delete=models.CASCADE, related_name="items")
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    peloton_focus = models.CharField(max_length=120)
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    is_done = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    points_earned = models.IntegerField(default=10)  # Points per exercise
    # Activity tracking
    ride_done = models.BooleanField(default=False)
    run_done = models.BooleanField(default=False)
    yoga_done = models.BooleanField(default=False)
    strength_done = models.BooleanField(default=False)
    # Peloton workout URLs
    peloton_ride_url = models.URLField(blank=True, null=True, help_text="Peloton ride workout URL")
    peloton_run_url = models.URLField(blank=True, null=True, help_text="Peloton run workout URL")
    peloton_yoga_url = models.URLField(blank=True, null=True, help_text="Peloton yoga workout URL")
    peloton_strength_url = models.URLField(blank=True, null=True, help_text="Peloton strength workout URL")
    workout_points = models.IntegerField(default=0, help_text="Points awarded for completing this workout (set from challenge assignment)")
    notes = models.CharField(max_length=240, blank=True)
    progression = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["day_of_week", "id"]
    
    @property
    def exercise_date(self):
        return self.weekly_plan.week_start + timedelta(days=self.day_of_week)
    
    @property
    def can_toggle(self):
        return self.weekly_plan.can_toggle_exercise(self.day_of_week)


class ChallengeWorkoutAssignment(models.Model):
    """Stores Peloton workout assignments for challenge templates"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="workout_assignments")
    template = models.ForeignKey(PlanTemplate, on_delete=models.CASCADE, related_name="workout_assignments")
    week_number = models.IntegerField(help_text="Week number (1-based)")
    day_of_week = models.IntegerField(choices=DailyPlanItem.DAY_CHOICES, help_text="Day of week")
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ("ride", "Ride"),
            ("run", "Run"),
            ("yoga", "Yoga"),
            ("strength", "Strength"),
        ],
        help_text="Type of activity"
    )
    peloton_url = models.URLField(help_text="Peloton workout URL")
    workout_title = models.CharField(max_length=200, blank=True, help_text="Optional: Workout title/description")
    points = models.IntegerField(default=50, help_text="Points awarded for completing this workout")
    alternative_group = models.IntegerField(null=True, blank=True, help_text="Group ID for alternative workouts (same group = user chooses one)")
    order_in_group = models.IntegerField(default=0, help_text="Order within alternative group")
    
    class Meta:
        unique_together = ("challenge", "template", "week_number", "day_of_week", "activity_type", "alternative_group", "order_in_group")
        ordering = ["challenge", "template", "week_number", "day_of_week", "activity_type", "alternative_group", "order_in_group"]
    
    def __str__(self):
        return f"{self.challenge.name} - {self.template.name} - Week {self.week_number} - {self.get_day_of_week_display()} - {self.get_activity_type_display()}"


class ChallengeBonusWorkout(models.Model):
    """Stores bonus workout assignments for challenges (same for all templates)"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="bonus_workouts")
    week_number = models.IntegerField(help_text="Week number (1-based)")
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ("ride", "Ride"),
            ("run", "Run"),
            ("yoga", "Yoga"),
            ("strength", "Strength"),
        ],
        help_text="Type of activity"
    )
    peloton_url = models.URLField(blank=True, help_text="Peloton workout URL (leave empty for 'Any 30 min+ Peloton Workout')")
    workout_title = models.CharField(max_length=200, blank=True, help_text="Optional: Workout title/description")
    points = models.IntegerField(default=10, help_text="Points awarded for completing this bonus workout")
    
    class Meta:
        unique_together = ("challenge", "week_number")
        ordering = ["challenge", "week_number"]
    
    def __str__(self):
        return f"{self.challenge.name} - Week {self.week_number} - {self.get_activity_type_display()} (Bonus)"


class ChallengeWeekUnlock(models.Model):
    """Tracks which weeks are unlocked/live for a challenge"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="week_unlocks")
    week_number = models.IntegerField(help_text="Week number (1-based)")
    is_unlocked = models.BooleanField(default=False, help_text="Whether this week is currently unlocked/live")
    unlock_date = models.DateField(null=True, blank=True, help_text="Optional: Date when this week should automatically unlock")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("challenge", "week_number")
        ordering = ["challenge", "week_number"]
    
    def __str__(self):
        status = "Unlocked" if self.is_unlocked else "Locked"
        return f"{self.challenge.name} - Week {self.week_number} ({status})"