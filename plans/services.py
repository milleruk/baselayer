from datetime import date, timedelta
from plans.models import Exercise, PlanTemplateDay
from tracker.models import WeeklyPlan, DailyPlanItem
from challenges.models import ChallengeWorkoutAssignment, ChallengeBonusWorkout

def generate_weekly_plan(*, user, week_start, template, start_from_today=False, challenge_instance=None, week_number=None):
    """
    Generates a plan from a PlanTemplate into tracker models.
    Idempotent per (user, week_start) due to unique constraint.
    
    Args:
        start_from_today: If True, only generate exercises for today and future days in the week
    """
    weekly, _created = WeeklyPlan.objects.get_or_create(
        user=user,
        week_start=week_start,
        defaults={"template_name": template.name},
    )

    # Clear existing items if regenerating
    weekly.items.all().delete()

    # Pull exercises (you can tune these later)
    def ex(name):
        return Exercise.objects.get(name=name)

    # Core set (based on what you've been using)
    basic = ex("Basic Kegel")
    pulse = ex("Pulse Kegels")
    elevator = ex("Elevator Kegels")
    longhold = ex("Long-Hold Kegel")
    reverse = ex("Reverse Kegels")
    tilts = ex("Pelvic Tilts")
    happy = ex("Happy Baby Release")
    clocks = ex("Pelvic Clocks")

    day_map = {d.day_of_week: d for d in template.days.all()}
    
    # If generating mid-week, determine which days to skip
    today = date.today()
    start_day = 0  # Sunday = 0
    if start_from_today:
        # Calculate which day of week today is (0=Sunday, 6=Saturday)
        days_since_sunday = (today.weekday() + 1) % 7
        start_day = days_since_sunday

    for dow in range(start_day, 7):
        td = day_map.get(dow)
        if td is None:
            continue

        focus = td.peloton_focus

        # Assign exercise blocks by focus keyword (simple + effective starter)
        focus_lower = focus.lower()

        if "pze" in focus_lower:
            picks = [elevator, reverse, tilts]
        elif "power zone" in focus_lower or "pz" in focus_lower or "threshold" in focus_lower:
            picks = [longhold, reverse]
        elif "run" in focus_lower:
            picks = [pulse, longhold]
        elif "yoga" in focus_lower or "recovery" in focus_lower:
            picks = [reverse, clocks, happy]
        else:
            picks = [basic, reverse]

        # Get Peloton workout assignments if this is part of a challenge
        # Group assignments by activity type, handling alternatives
        peloton_assignments = {}
        if challenge_instance and week_number:
            challenge = challenge_instance.challenge
            assignments = ChallengeWorkoutAssignment.objects.filter(
                challenge=challenge,
                template=template,
                week_number=week_number,
                day_of_week=dow
            ).order_by('alternative_group', 'order_in_group')
            
            for assignment in assignments:
                activity_type = assignment.activity_type
                if activity_type not in peloton_assignments:
                    peloton_assignments[activity_type] = []
                peloton_assignments[activity_type].append(assignment)
        
        # For backward compatibility, also create peloton_urls dict (first assignment only)
        peloton_urls = {}
        for activity_type, assignment_list in peloton_assignments.items():
            if assignment_list:
                first_assignment = assignment_list[0]
                if activity_type == "ride":
                    peloton_urls["ride"] = first_assignment.peloton_url
                elif activity_type == "run":
                    peloton_urls["run"] = first_assignment.peloton_url
                elif activity_type == "yoga":
                    peloton_urls["yoga"] = first_assignment.peloton_url
                elif activity_type == "strength":
                    peloton_urls["strength"] = first_assignment.peloton_url
        
        # Check if user wants Kegels (only for challenge instances)
        include_kegels = True  # Default to True for standalone plans
        if challenge_instance:
            include_kegels = challenge_instance.include_kegels
        
        # Create items for Peloton workouts (including alternatives)
        # When there are alternatives, create one item per alternative
        if peloton_assignments:
            # Always provide an exercise (required by model)
            # When Kegels are disabled, use a non-kegel exercise (tilts) as placeholder
            if include_kegels and picks:
                exercise_to_use = picks[0]
            else:
                # Use a non-kegel mobility exercise when kegels are disabled
                exercise_to_use = tilts
            
            # Create items for each activity type and its alternatives
            for activity_type, assignment_list in peloton_assignments.items():
                for assignment in assignment_list:
                    # Build peloton_urls for this specific assignment
                    item_peloton_urls = {}
                    if assignment.activity_type == "ride":
                        item_peloton_urls["ride"] = assignment.peloton_url
                    elif assignment.activity_type == "run":
                        item_peloton_urls["run"] = assignment.peloton_url
                    elif assignment.activity_type == "yoga":
                        item_peloton_urls["yoga"] = assignment.peloton_url
                    elif assignment.activity_type == "strength":
                        item_peloton_urls["strength"] = assignment.peloton_url
                    
                    DailyPlanItem.objects.create(
                        weekly_plan=weekly,
                        day_of_week=dow,
                        peloton_focus=focus,
                        exercise=exercise_to_use,
                        ride_done=False,
                        run_done=False,
                        yoga_done=False,
                        strength_done=False,
                        peloton_ride_url=item_peloton_urls.get("ride"),
                        peloton_run_url=item_peloton_urls.get("run"),
                        peloton_yoga_url=item_peloton_urls.get("yoga"),
                        peloton_strength_url=item_peloton_urls.get("strength"),
                        workout_points=assignment.points,  # Copy points from assignment
                    )
        elif peloton_urls:
            # Fallback for backward compatibility (single workout per activity)
            if include_kegels and picks:
                exercise_to_use = picks[0]
            else:
                exercise_to_use = tilts
            
            DailyPlanItem.objects.create(
                weekly_plan=weekly,
                day_of_week=dow,
                peloton_focus=focus,
                exercise=exercise_to_use,
                ride_done=False,
                run_done=False,
                yoga_done=False,
                strength_done=False,
                peloton_ride_url=peloton_urls.get("ride"),
                peloton_run_url=peloton_urls.get("run"),
                peloton_yoga_url=peloton_urls.get("yoga"),
                peloton_strength_url=peloton_urls.get("strength"),
            )
        
        # If Kegels are enabled, also create Kegel exercise items
        if include_kegels:
            for e in picks:
                # Skip if we already created an item for this day (when Peloton workout exists)
                if not peloton_urls:
                    DailyPlanItem.objects.create(
                        weekly_plan=weekly,
                        day_of_week=dow,
                        peloton_focus=focus,
                        exercise=e,
                        ride_done=False,
                        run_done=False,
                        yoga_done=False,
                        strength_done=False,
                    )
    
    # Add bonus workouts for this week (same for all templates)
    if challenge_instance and week_number:
        challenge = challenge_instance.challenge
        bonus_workouts = ChallengeBonusWorkout.objects.filter(
            challenge=challenge,
            week_number=week_number
        )
        
        for bonus in bonus_workouts:
            # Use tilts as placeholder exercise (non-kegel)
            exercise_to_use = tilts
            
            # Create bonus workout item - use Saturday (day 6) as the day, or we could add a special day
            # For now, add it as a separate item that can be displayed separately
            DailyPlanItem.objects.create(
                weekly_plan=weekly,
                day_of_week=6,  # Saturday - bonus workouts
                peloton_focus=f"Bonus {bonus.get_activity_type_display()}",
                exercise=exercise_to_use,
                ride_done=False,
                run_done=False,
                yoga_done=False,
                strength_done=False,
                peloton_ride_url=bonus.peloton_url if bonus.activity_type == "ride" else None,
                peloton_run_url=bonus.peloton_url if bonus.activity_type == "run" else None,
                peloton_yoga_url=bonus.peloton_url if bonus.activity_type == "yoga" else None,
                peloton_strength_url=bonus.peloton_url if bonus.activity_type == "strength" else None,
                points_earned=bonus.points,  # Use bonus workout points
            )

    return weekly
