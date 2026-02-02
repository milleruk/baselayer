"""Activity Toggle Service - Manages toggling of workout activities"""


class ActivityToggleService:
    """Service for handling activity toggle logic across the application.
    
    Responsible for:
    - Validating activity types
    - Toggling activity completion status
    - Managing activity exclusivity (bonus vs regular, alternatives on same day)
    - Calculating points earned for activities
    - Handling week lock status checks
    
    Examples:
        # Validate activity type
        if not ActivityToggleService.is_valid_activity('ride'):
            return error
        
        # Get activity field mapping
        field = ActivityToggleService.get_activity_field('run')  # returns 'run_done'
        
        # Get conflicting items to uncheck
        items_to_uncheck = ActivityToggleService.get_items_to_uncheck_for_bonus(item)
        
        # Calculate points earned
        points = ActivityToggleService.calculate_activity_points(item, new_value, plan)
        
        # Check week lock status
        can_edit, message = ActivityToggleService.check_week_lock_status(item)
    """
    
    # Activity to model field mapping
    ACTIVITY_MAP = {
        "ride": "ride_done",
        "run": "run_done",
        "yoga": "yoga_done",
        "strength": "strength_done",
    }
    
    @staticmethod
    def is_valid_activity(activity):
        """Check if activity type is valid.
        
        Args:
            activity (str): Activity type ('ride', 'run', 'yoga', 'strength')
            
        Returns:
            bool: True if activity is valid
        """
        return activity in ActivityToggleService.ACTIVITY_MAP
    
    @staticmethod
    def get_activity_field(activity):
        """Get the model field name for an activity.
        
        Args:
            activity (str): Activity type
            
        Returns:
            str: Field name (e.g., 'ride_done') or None if invalid
        """
        return ActivityToggleService.ACTIVITY_MAP.get(activity)
    
    @staticmethod
    def check_week_lock_status(item):
        """Check if week is locked based on challenge status.
        
        For active challenges, prevents editing of weeks before the current week
        unless all previous weeks are completed.
        
        Args:
            item: DailyPlanItem instance
            
        Returns:
            tuple: (can_edit: bool, error_message: str or None)
            
        Example:
            can_edit, message = ActivityToggleService.check_week_lock_status(item)
            if not can_edit:
                return JsonResponse({"error": message})
        """
        plan = item.weekly_plan
        
        # If not part of a challenge, no lock
        if not plan.challenge_instance:
            return True, None
        
        # Import here to avoid circular dependencies
        from challenges.models import Challenge
        
        challenge = plan.challenge_instance.challenge
        
        # Past challenges are never locked
        if challenge.has_ended or not challenge.is_active:
            return True, None
        
        # Find current week number for this challenge instance
        all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
        week_number = None
        for idx, p in enumerate(all_plans, start=1):
            if p.id == plan.id:
                week_number = idx
                break
        
        # Week 1 is always available
        if not week_number or week_number == 1:
            return True, None
        
        # Check if all previous weeks are completed
        previous_plans = all_plans.filter(week_start__lt=plan.week_start).order_by("week_start")
        incomplete_weeks = [p for p in previous_plans if not p.is_completed]
        
        if incomplete_weeks:
            # Build list of incomplete week numbers
            incomplete_week_numbers = []
            for p in incomplete_weeks:
                for idx, check_p in enumerate(all_plans, start=1):
                    if check_p.id == p.id:
                        incomplete_week_numbers.append(idx)
                        break
            
            error_msg = f"Complete Week(s) {', '.join(map(str, incomplete_week_numbers))} before accessing Week {week_number} activities."
            return False, error_msg
        
        return True, None
    
    @staticmethod
    def get_items_to_uncheck_for_bonus(item):
        """Get all bonus items to uncheck when checking a bonus item.
        
        Only one bonus workout can be selected at a time. When checking a bonus,
        all other bonus items should be unchecked.
        
        Args:
            item: DailyPlanItem instance (must be a bonus item)
            
        Returns:
            QuerySet: Other bonus DailyPlanItems to uncheck
            
        Example:
            items_to_uncheck = ActivityToggleService.get_items_to_uncheck_for_bonus(item)
            for other_item in items_to_uncheck:
                other_item.ride_done = False
                other_item.run_done = False
                # ... etc
        """
        plan = item.weekly_plan
        return plan.items.filter(
            peloton_focus__icontains="Bonus"
        ).exclude(
            id=item.id
        )
    
    @staticmethod
    def get_items_to_uncheck_for_regular(item):
        """Get all regular workout alternatives to uncheck when checking a regular workout.
        
        Only one regular workout can be selected per day. When checking a workout,
        all other alternatives on the same day (excluding bonus) should be unchecked.
        
        Args:
            item: DailyPlanItem instance (must be a regular, non-bonus item)
            
        Returns:
            QuerySet: Other DailyPlanItems on the same day to uncheck
            
        Example:
            items_to_uncheck = ActivityToggleService.get_items_to_uncheck_for_regular(item)
            for other_item in items_to_uncheck:
                other_item.ride_done = False
                other_item.run_done = False
                # ... etc
        """
        from django.db.models import Q
        
        plan = item.weekly_plan
        return plan.items.filter(
            day_of_week=item.day_of_week
        ).exclude(
            id=item.id
        ).exclude(
            peloton_focus__icontains="Bonus"
        ).filter(
            (Q(peloton_ride_url__isnull=False) & ~Q(peloton_ride_url='')) |
            (Q(peloton_run_url__isnull=False) & ~Q(peloton_run_url='')) |
            (Q(peloton_yoga_url__isnull=False) & ~Q(peloton_yoga_url='')) |
            (Q(peloton_strength_url__isnull=False) & ~Q(peloton_strength_url=''))
        )
    
    @staticmethod
    def uncheck_all_activities(item):
        """Uncheck all activity flags for an item.
        
        Args:
            item: DailyPlanItem instance
            
        Returns:
            bool: True if any changes were made
        """
        changed = False
        for activity, field_name in ActivityToggleService.ACTIVITY_MAP.items():
            if getattr(item, field_name):
                setattr(item, field_name, False)
                changed = True
        
        if changed:
            item.save(update_fields=list(ActivityToggleService.ACTIVITY_MAP.values()))
        
        return changed
    
    @staticmethod
    def get_activity_name(activity):
        """Get display name for an activity.
        
        Args:
            activity (str): Activity type
            
        Returns:
            str: Capitalized activity name (e.g., 'Ride')
        """
        return activity.capitalize() if activity else None
    
    @staticmethod
    def get_workout_day_numbers(plan):
        """Get sorted list of day-of-week numbers that have workouts in a plan.
        
        Args:
            plan: WeeklyPlan instance
            
        Returns:
            list: Sorted list of day_of_week integers (e.g., [1, 3, 5])
            
        Example:
            workout_days = ActivityToggleService.get_workout_day_numbers(plan)
            # Returns [1, 3, 5] for a Mon/Wed/Fri plan
        """
        return sorted(set(
            list(plan.items.filter(peloton_ride_url__isnull=False).exclude(peloton_ride_url='').values_list('day_of_week', flat=True)) +
            list(plan.items.filter(peloton_run_url__isnull=False).exclude(peloton_run_url='').values_list('day_of_week', flat=True)) +
            list(plan.items.filter(peloton_yoga_url__isnull=False).exclude(peloton_yoga_url='').values_list('day_of_week', flat=True)) +
            list(plan.items.filter(peloton_strength_url__isnull=False).exclude(peloton_strength_url='').values_list('day_of_week', flat=True))
        ))
    
    @staticmethod
    def calculate_activity_points(item, is_being_checked, plan):
        """Calculate points earned when an activity is toggled.
        
        Points are based on:
        - Plan type (3-core, 4-core, etc.)
        - Workout day number
        - Activity is being checked (unchecking doesn't award points)
        
        Args:
            item: DailyPlanItem instance
            is_being_checked (bool): True if item is being checked, False if unchecked
            plan: WeeklyPlan instance
            
        Returns:
            int: Points earned (0 if unchecking or not a workout day)
            
        Example:
            points = ActivityToggleService.calculate_activity_points(item, True, plan)
            # Returns 50 for a 3-core plan, or 50/25 for a 4-core plan depending on day
        """
        # No points when unchecking
        if not is_being_checked:
            return 0
        
        # No points if not on a workout day
        core_count = plan.core_workout_count
        workout_day_numbers = ActivityToggleService.get_workout_day_numbers(plan)
        
        if item.day_of_week not in workout_day_numbers:
            return 0
        
        # Get workout day position (1-indexed)
        workout_day_num = workout_day_numbers.index(item.day_of_week) + 1
        
        # Calculate points based on core count
        if core_count == 3:
            # 3 core workouts: Each = 50 points
            return 50
        elif core_count == 4:
            # 4 core workouts: Day 1 = 50, Days 2-3 = 25, Final day = 50
            if workout_day_num == 1 or workout_day_num == core_count:
                return 50
            else:
                return 25
        else:
            # Fallback for other core counts
            return 50
    
    @staticmethod
    def get_day_activity_status(plan, day_of_week):
        """Get activity completion status for all items on a specific day.
        
        Returns which activities are marked as done for any item on that day.
        Since alternatives exist, we check if ANY item on the day has the activity done.
        
        Args:
            plan: WeeklyPlan instance
            day_of_week (int): Day of week (1-7)
            
        Returns:
            dict: Activity status e.g. {'ride': True, 'run': False, 'yoga': True, 'strength': False}
            
        Example:
            status = ActivityToggleService.get_day_activity_status(plan, 1)
            if status['ride']:
                print("Ride is marked as done for this day")
        """
        day_items = plan.items.filter(day_of_week=day_of_week)
        
        return {
            'ride': day_items.filter(ride_done=True).exists(),
            'run': day_items.filter(run_done=True).exists(),
            'yoga': day_items.filter(yoga_done=True).exists(),
            'strength': day_items.filter(strength_done=True).exists(),
        }
    
    @staticmethod
    def calculate_day_points(plan, day_of_week):
        """Calculate total points earned for a specific day's activities.
        
        Only one activity type counts per day (to prevent double-counting alternatives).
        Points are only awarded if any activity is done on that day.
        
        Args:
            plan: WeeklyPlan instance
            day_of_week (int): Day of week (1-7)
            
        Returns:
            int: Points for this day
            
        Example:
            day_points = ActivityToggleService.calculate_day_points(plan, 1)
            print(f"Monday earned {day_points} points")
        """
        # Check if any activity is done on this day
        activity_status = ActivityToggleService.get_day_activity_status(plan, day_of_week)
        
        if not any(activity_status.values()):
            return 0
        
        # Get core count and workout day numbers
        core_count = plan.core_workout_count
        workout_day_numbers = ActivityToggleService.get_workout_day_numbers(plan)
        
        # If this day is not a workout day, no points
        if day_of_week not in workout_day_numbers:
            return 0
        
        # Get workout day position (1-indexed)
        workout_day_num = workout_day_numbers.index(day_of_week) + 1
        
        # Calculate points based on core count
        if core_count == 3:
            return 50
        elif core_count == 4:
            if workout_day_num == 1 or workout_day_num == core_count:
                return 50
            else:
                return 25
        else:
            return 50
