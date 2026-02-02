"""
Service for plan processing operations - validation, week calculations, and plan management.

Extracts plan-related business logic from tracker/views.py for reusability.
"""
from typing import Optional, Tuple, Dict, Any


class PlanProcessorService:
    """Service for weekly plan validation, week calculations, and plan status checks."""
    
    @staticmethod
    def can_user_generate_plan(user, week_start, active_challenge_instance=None) -> Tuple[bool, Optional[str]]:
        """
        Check if user can generate a new plan for the given week.
        
        Args:
            user: User object
            week_start: Date object for the week start (Sunday)
            active_challenge_instance: Optional ChallengeInstance if user is in a challenge
            
        Returns:
            Tuple of (can_generate: bool, error_message: str or None)
            
        Example:
            >>> can_gen, error = PlanProcessorService.can_user_generate_plan(user, week_start)
            >>> if not can_gen:
            ...     print(error)
        """
        # Lazy import to prevent circular dependencies
        from tracker.models import WeeklyPlan
        
        # Check if user already has a plan for this week
        existing_plan = WeeklyPlan.objects.filter(user=user, week_start=week_start).first()
        if existing_plan:
            return False, f"You already have a plan for this week (Week of {week_start.strftime('%B %d, %Y')}). Please complete or delete the existing plan first."
        
        # Check if user is in an active challenge (for standalone plan generation)
        if active_challenge_instance:
            return False, f"You are currently in an active challenge '{active_challenge_instance.challenge.name}'. Complete or exit the challenge to generate standalone plans."
        
        return True, None
    
    @staticmethod
    def calculate_week_number(plan) -> Optional[int]:
        """
        Calculate the week number for a plan within its challenge.
        
        Args:
            plan: WeeklyPlan object
            
        Returns:
            Week number (1-indexed) or None if not part of a challenge
            
        Example:
            >>> week_num = PlanProcessorService.calculate_week_number(plan)
            >>> print(f"This is week {week_num} of the challenge")
        """
        if not plan.challenge_instance:
            return None
        
        all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
        for idx, p in enumerate(all_plans, start=1):
            if p.id == plan.id:
                return idx
        
        return None
    
    @staticmethod
    def check_week_access(plan, week_number: Optional[int] = None) -> Tuple[bool, bool]:
        """
        Check if user can access a specific week in a challenge.
        
        Args:
            plan: WeeklyPlan object
            week_number: Optional week number (will calculate if not provided)
            
        Returns:
            Tuple of (can_access_week: bool, previous_week_completed: bool)
            
        Example:
            >>> can_access, prev_complete = PlanProcessorService.check_week_access(plan)
            >>> if not can_access:
            ...     print("This week is locked")
        """
        # Default to True for standalone plans
        if not plan.challenge_instance:
            return True, True
        
        challenge = plan.challenge_instance.challenge
        
        # Calculate week number if not provided
        if week_number is None:
            week_number = PlanProcessorService.calculate_week_number(plan)
        
        # For past challenges (has_ended), all weeks are unlocked
        if challenge.has_ended:
            return True, True
        
        # Check if week is unlocked according to challenge settings
        if week_number and not challenge.is_week_unlocked(week_number):
            return False, False
        
        # For active challenges (not ended), also check if previous weeks are completed
        if challenge.is_active and not challenge.has_ended and week_number and week_number > 1:
            all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
            previous_plans = all_plans.filter(week_start__lt=plan.week_start).order_by("week_start")
            
            if previous_plans.exists():
                # Check if ALL previous weeks are completed
                incomplete_weeks = [p for p in previous_plans if not p.is_completed]
                can_access = len(incomplete_weeks) == 0
                return can_access, can_access
            else:
                # Previous weeks don't exist, can't access this week
                return False, False
        
        return True, True
    
    @staticmethod
    def calculate_day_points(core_count: int, workout_day_num: int) -> int:
        """
        Calculate points for a workout day based on core count and day number.
        
        Args:
            core_count: Number of core workouts (3 or 4)
            workout_day_num: Day number within the workout sequence (1-indexed)
            
        Returns:
            Points for this workout day
            
        Example:
            >>> points = PlanProcessorService.calculate_day_points(core_count=4, workout_day_num=2)
            >>> print(points)  # 25 (middle day)
        """
        if core_count == 3:
            return 50  # Each workout = 50 points
        elif core_count == 4:
            if workout_day_num == 1 or workout_day_num == core_count:
                return 50  # First and last = 50
            else:
                return 25  # Middle days = 25
        else:
            return 50  # Default
    
    @staticmethod
    def is_bonus_completed(bonus_workouts: list) -> bool:
        """
        Check if bonus workout is completed.
        
        Args:
            bonus_workouts: List of DailyPlanItem objects that are bonus workouts
            
        Returns:
            True if first bonus workout is completed, False otherwise
            
        Example:
            >>> completed = PlanProcessorService.is_bonus_completed(bonus_items)
        """
        if not bonus_workouts:
            return False
        
        first_bonus = bonus_workouts[0]
        return (first_bonus.ride_done or first_bonus.run_done or 
                first_bonus.yoga_done or first_bonus.strength_done)
    
    @staticmethod
    def get_activity_type_for_item(item) -> Optional[str]:
        """
        Determine the activity type for a DailyPlanItem based on its URLs.
        
        Args:
            item: DailyPlanItem object
            
        Returns:
            Activity type ('ride', 'run', 'yoga', 'strength') or None
            
        Example:
            >>> activity = PlanProcessorService.get_activity_type_for_item(item)
            >>> print(activity)  # 'ride'
        """
        # Must have non-empty URL
        if item.peloton_ride_url and item.peloton_ride_url.strip():
            return 'ride'
        elif item.peloton_run_url and item.peloton_run_url.strip():
            return 'run'
        elif item.peloton_yoga_url and item.peloton_yoga_url.strip():
            return 'yoga'
        elif item.peloton_strength_url and item.peloton_strength_url.strip():
            return 'strength'
        
        return None
    
    @staticmethod
    def is_item_done(item, activity_type: str) -> bool:
        """
        Check if a specific activity is done for an item.
        
        Args:
            item: DailyPlanItem object
            activity_type: Activity type ('ride', 'run', 'yoga', 'strength')
            
        Returns:
            True if activity is done, False otherwise
            
        Example:
            >>> done = PlanProcessorService.is_item_done(item, 'ride')
        """
        if activity_type == 'ride':
            return item.ride_done
        elif activity_type == 'run':
            return item.run_done
        elif activity_type == 'yoga':
            return item.yoga_done
        elif activity_type == 'strength':
            return item.strength_done
        
        return False
    
    @staticmethod
    def organize_workout_days(workout_items) -> Dict[int, Dict[str, list]]:
        """
        Organize workout items by day_of_week and activity type.
        
        Args:
            workout_items: QuerySet or list of DailyPlanItem objects with workouts
            
        Returns:
            Dict mapping day_of_week to dict of activity_type to list of items
            
        Example:
            >>> days = PlanProcessorService.organize_workout_days(items)
            >>> print(days[0]['ride'])  # List of ride items for Sunday
        """
        workout_days_dict = {}
        
        for item in workout_items:
            dow = item.day_of_week
            if dow not in workout_days_dict:
                workout_days_dict[dow] = {}
            
            activity_type = PlanProcessorService.get_activity_type_for_item(item)
            
            if activity_type:
                if activity_type not in workout_days_dict[dow]:
                    workout_days_dict[dow][activity_type] = []
                workout_days_dict[dow][activity_type].append(item)
        
        return workout_days_dict
    
    @staticmethod
    def filter_items_by_kegel_preference(items, challenge_instance, include_bonus: bool = False):
        """
        Filter plan items based on Kegel preference in challenge settings.
        
        Args:
            items: QuerySet of DailyPlanItem objects
            challenge_instance: ChallengeInstance object or None
            include_bonus: Whether to include bonus workouts in filtering
            
        Returns:
            Filtered QuerySet
            
        Example:
            >>> filtered = PlanProcessorService.filter_items_by_kegel_preference(
            ...     all_items, challenge_instance
            ... )
        """
        # If no challenge or kegels are included, return all items
        if not challenge_instance or challenge_instance.include_kegels:
            return items
        
        # Lazy import to prevent circular dependencies
        from django.db.models import Q
        
        # Only show items that have Peloton workouts AND are not kegel exercises
        return items.filter(
            (Q(peloton_ride_url__isnull=False) |
             Q(peloton_run_url__isnull=False) |
             Q(peloton_yoga_url__isnull=False) |
             Q(peloton_strength_url__isnull=False)) &
            ~Q(exercise__category="kegel")  # Exclude kegel exercises
        )
    
    @staticmethod
    def get_workout_items_queryset(items):
        """
        Filter items to only those with Peloton workout URLs (non-empty).
        
        Args:
            items: QuerySet of DailyPlanItem objects
            
        Returns:
            Filtered QuerySet containing only workout items
            
        Example:
            >>> workouts = PlanProcessorService.get_workout_items_queryset(all_items)
        """
        # Lazy import to prevent circular dependencies
        from django.db.models import Q
        
        # Must exclude empty strings, not just None values
        return items.filter(
            (Q(peloton_ride_url__isnull=False) & ~Q(peloton_ride_url='')) |
            (Q(peloton_run_url__isnull=False) & ~Q(peloton_run_url='')) |
            (Q(peloton_yoga_url__isnull=False) & ~Q(peloton_yoga_url='')) |
            (Q(peloton_strength_url__isnull=False) & ~Q(peloton_strength_url=''))
        ).order_by('day_of_week', 'id')
    
    @staticmethod
    def separate_bonus_workouts(all_items):
        """
        Separate bonus workouts from regular items.
        
        Args:
            all_items: QuerySet of DailyPlanItem objects
            
        Returns:
            Tuple of (bonus_workouts: list, regular_items: QuerySet)
            
        Example:
            >>> bonus, regular = PlanProcessorService.separate_bonus_workouts(all_items)
        """
        # Lazy import to prevent circular dependencies
        from django.db.models import Q
        
        bonus_workouts = list(all_items.filter(peloton_focus__icontains="Bonus"))
        items = all_items.exclude(peloton_focus__icontains="Bonus")
        
        return bonus_workouts, items
