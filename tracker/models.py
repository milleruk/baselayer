from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from plans.models import Exercise

class WeeklyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    challenge_instance = models.ForeignKey("challenges.ChallengeInstance", on_delete=models.CASCADE, related_name="weekly_plans", null=True, blank=True)
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
