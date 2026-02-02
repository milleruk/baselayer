from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from plans.models import PlanTemplate
from plans.services import generate_weekly_plan
from .models import WeeklyPlan, DailyPlanItem
from challenges.models import ChallengeInstance
from .forms import DailyPlanItemForm
from core.services import DateRangeService


def sunday_of_current_week(d: date) -> date:
    """Get the Sunday of the current week (week starts on Sunday).
    
    DEPRECATED: Use DateRangeService.sunday_of_current_week() instead.
    This wrapper is kept for backward compatibility.
    """
    return DateRangeService.sunday_of_current_week(d)

@login_required
def weekly_plans(request):
    challenge_instances = ChallengeInstance.objects.filter(user=request.user).select_related("challenge").prefetch_related("weekly_plans")
    
    # Check if user has an active challenge
    # Only show banner for truly active challenges (is_active=True)
    active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
    
    # Check if user already has a plan for the current week
    current_week_start = sunday_of_current_week(date.today())
    existing_current_week_plan = WeeklyPlan.objects.filter(user=request.user, week_start=current_week_start).first()
    
    # Group plans by challenge instance and add week numbers and access info
    plans_by_challenge = []
    for ci in challenge_instances:
        plans = ci.weekly_plans.all().order_by("week_start")
        plans_with_week_numbers = []
        for idx, plan in enumerate(plans, start=1):
            plan.week_number = idx
            
            # Check if this week can be accessed
            plan.can_access_week = True  # Default to True for standalone plans
            plan.locked_reason = None
            
            if ci.challenge:
                # For past challenges (has_ended), all weeks are unlocked
                if ci.challenge.has_ended:
                    plan.can_access_week = True
                    plan.locked_reason = None
                # Check if week is unlocked according to challenge settings
                elif not ci.challenge.is_week_unlocked(idx):
                    plan.can_access_week = False
                    plan.locked_reason = "This week is locked. Please wait for it to be unlocked."
                # For active challenges, also check if previous weeks are completed
                elif ci.challenge.is_active and not ci.challenge.has_ended and idx > 1:
                    # Check if ALL previous weeks are completed
                    previous_plans = plans.filter(week_start__lt=plan.week_start).order_by("week_start")
                    incomplete_weeks = [p for p in previous_plans if not p.is_completed]
                    if incomplete_weeks:
                        plan.can_access_week = False
                        # Store which weeks need to be completed
                        incomplete_week_numbers = []
                        for p in incomplete_weeks:
                            for check_idx, check_p in enumerate(plans, start=1):
                                if check_p.id == p.id:
                                    incomplete_week_numbers.append(check_idx)
                                    break
                        plan.locked_reason = f"Complete Week(s) {', '.join(map(str, incomplete_week_numbers))} first"
            
            plans_with_week_numbers.append(plan)
        
        # Always include active challenge instances, even if they have no plans yet
        # Include inactive instances only if they have plans AND are completed (not just left)
        # For past challenges that are completed, still show them but mark as completed
        if ci.is_active or (plans_with_week_numbers and ci.completed_at):
            # Check if user can leave this challenge
            can_leave, leave_error = ci.can_leave_challenge()
            plans_by_challenge.append({
                "challenge_instance": ci,
                "plans": plans_with_week_numbers,
                "can_leave": can_leave,
                "leave_error": leave_error,
            })
    
    # Also get standalone plans (not part of a challenge)
    standalone_plans = WeeklyPlan.objects.filter(user=request.user, challenge_instance__isnull=True).order_by("-week_start")
    
    return render(request, "tracker/weekly_plans.html", {
        "plans_by_challenge": plans_by_challenge,
        "standalone_plans": standalone_plans,
        "challenge_instances": challenge_instances,
        "active_challenge_instance": active_challenge_instance,
        "existing_current_week_plan": existing_current_week_plan,
    })

@login_required
def generate(request):
    # Check if user has an active challenge instance
    active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
    
    # Check if user already has a plan for the current week
    current_week_start = sunday_of_current_week(date.today())
    existing_plan = WeeklyPlan.objects.filter(user=request.user, week_start=current_week_start).first()
    
    if request.method == "POST":
        template_id = request.POST.get("template_id")
        challenge_id = request.POST.get("challenge_id")
        template = get_object_or_404(PlanTemplate, pk=template_id)
        week_start = sunday_of_current_week(date.today())

        # Check if user already has a plan for this week (unless joining a challenge)
        if not challenge_id and existing_plan:
            messages.error(request, f"You already have a plan for this week (Week of {week_start.strftime('%B %d, %Y')}). Please complete or delete the existing plan first.")
            return redirect("tracker:weekly_plans")

        # Check if user is joining a challenge
        challenge_instance = None
        if challenge_id:
            from challenges.models import Challenge
            challenge = get_object_or_404(Challenge, pk=challenge_id)
            # Get the most recent active instance, or most recent instance if none are active
            challenge_instance = ChallengeInstance.objects.filter(
                user=request.user, 
                challenge=challenge
            ).order_by('-is_active', '-started_at').first()
            
            if challenge_instance:
                # Use user's selected template for this challenge, or challenge default, or provided template
                if challenge_instance.selected_template:
                    template = challenge_instance.selected_template
                elif challenge.default_template:
                    template = challenge.default_template
            else:
                # Create instance with selected template
                challenge_instance = ChallengeInstance.objects.create(
                    user=request.user,
                    challenge=challenge,
                    is_active=True,
                    selected_template=template
                )
                messages.success(request, f"Joined challenge '{challenge.name}'!")
        else:
            # Prevent standalone plan generation if user is in an active challenge
            if active_challenge_instance:
                messages.error(request, f"You are currently in an active challenge '{active_challenge_instance.challenge.name}'. Please complete or exit the challenge before generating standalone plans.")
                return redirect("tracker:weekly_plans")
            
            # Check if there's an active challenge instance
            challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
            if challenge_instance and challenge_instance.selected_template:
                # Use the challenge's selected template
                template = challenge_instance.selected_template
        
        # Calculate week number if part of challenge
        week_number = None
        if challenge_instance:
            all_plans = challenge_instance.weekly_plans.all().order_by("week_start")
            week_number = all_plans.count() + 1
        
        weekly = generate_weekly_plan(
            user=request.user,
            week_start=week_start,
            template=template,
            start_from_today=True,
            challenge_instance=challenge_instance,
            week_number=week_number
        )
        if challenge_instance:
            weekly.challenge_instance = challenge_instance
            weekly.save(update_fields=["challenge_instance"])
        messages.success(request, f"Weekly plan '{template.name}' generated successfully!")
        # Redirect to plan detail
        return redirect("tracker:plan_detail", pk=weekly.pk)
    
    # GET request - show template selection and available challenges
    # Prevent access if user is in an active challenge
    if active_challenge_instance:
        messages.info(request, f"You are currently in an active challenge '{active_challenge_instance.challenge.name}'. Complete or exit the challenge to generate standalone plans.")
        return redirect("tracker:weekly_plans")
    
    # Prevent access if user already has a plan for the current week
    if existing_plan:
        messages.info(request, f"You already have a plan for this week (Week of {current_week_start.strftime('%B %d, %Y')}). Please complete or delete the existing plan first.")
        return redirect("tracker:weekly_plans")
    
    templates = PlanTemplate.objects.all().order_by("name")
    from challenges.models import Challenge
    challenges = Challenge.objects.filter(is_active=True).order_by("-start_date")
    return render(request, "tracker/select_template.html", {
        "templates": templates,
        "challenges": challenges,
    })

@login_required
def delete_plan(request, pk):
    """Delete a weekly plan"""
    plan = get_object_or_404(WeeklyPlan, pk=pk, user=request.user)
    if request.method == "POST":
        plan.delete()
        messages.success(request, "Plan deleted successfully.")
        return redirect("tracker:weekly_plans")
    return redirect("tracker:plan_detail", pk=pk)


@login_required
def plan_detail(request, pk):
    plan = get_object_or_404(
        WeeklyPlan.objects.select_related('challenge_instance__challenge'),
        pk=pk,
        user=request.user
    )

    # Calculate week number if this plan is part of a challenge
    week_number = None
    can_access_week = True  # Default to True for standalone plans
    previous_week_completed = True  # Default to True for standalone plans
    
    if plan.challenge_instance:
        from challenges.models import Challenge
        challenge = plan.challenge_instance.challenge
        all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
        for idx, p in enumerate(all_plans, start=1):
            if p.id == plan.id:
                week_number = idx
                break
        
        # For past challenges (has_ended), all weeks are unlocked
        if challenge.has_ended:
            can_access_week = True
            previous_week_completed = True
        # First check if week is unlocked according to challenge settings
        elif week_number and not challenge.is_week_unlocked(week_number):
            can_access_week = False
            previous_week_completed = False
        # For active challenges (not ended), also check if previous weeks are completed
        elif challenge.is_active and not challenge.has_ended and week_number and week_number > 1:
            # Check if ALL previous weeks exist and are completed
            previous_plans = all_plans.filter(week_start__lt=plan.week_start).order_by("week_start")
            if previous_plans.exists():
                # Check if ALL previous weeks are completed
                incomplete_weeks = [p for p in previous_plans if not p.is_completed]
                can_access_week = len(incomplete_weeks) == 0
                previous_week_completed = can_access_week
            else:
                # Previous weeks don't exist, can't access this week
                can_access_week = False
                previous_week_completed = False

    # items already ordered by day_of_week then id (per Meta ordering)
    all_items = plan.items.select_related("exercise").all()
    
    # Separate bonus workouts (items with "Bonus" in peloton_focus)
    from django.db.models import Q
    bonus_workouts = list(all_items.filter(peloton_focus__icontains="Bonus"))
    items = all_items.exclude(peloton_focus__icontains="Bonus")
    
    # Calculate if bonus is completed (check first bonus workout if exists)
    bonus_completed = False
    if bonus_workouts:
        first_bonus = bonus_workouts[0]
        bonus_completed = first_bonus.ride_done or first_bonus.run_done or first_bonus.yoga_done or first_bonus.strength_done
    
    # Filter out Kegel exercises if user disabled them in challenge (only for regular items)
    if plan.challenge_instance and not plan.challenge_instance.include_kegels:
        # Only show items that have Peloton workouts AND are not kegel exercises
        items = items.filter(
            (Q(peloton_ride_url__isnull=False) |
             Q(peloton_run_url__isnull=False) |
             Q(peloton_yoga_url__isnull=False) |
             Q(peloton_strength_url__isnull=False)) &
            ~Q(exercise__category="kegel")  # Exclude kegel exercises
        )

    # Organize workouts by sequence (Day 1, Day 2, etc.) instead of weekday
    # Get all workout items (items with Peloton URLs), sorted by day_of_week
    # Must exclude empty strings, not just None values
    workout_items = items.filter(
        (Q(peloton_ride_url__isnull=False) & ~Q(peloton_ride_url='')) |
        (Q(peloton_run_url__isnull=False) & ~Q(peloton_run_url='')) |
        (Q(peloton_yoga_url__isnull=False) & ~Q(peloton_yoga_url='')) |
        (Q(peloton_strength_url__isnull=False) & ~Q(peloton_strength_url=''))
    ).order_by('day_of_week', 'id')
    
    # Group workouts by day_of_week, then by activity type for alternatives
    workout_days_dict = {}
    for item in workout_items:
        dow = item.day_of_week
        if dow not in workout_days_dict:
            workout_days_dict[dow] = {}
        
        # Determine activity type for this item (must have non-empty URL)
        activity_type = None
        if item.peloton_ride_url and item.peloton_ride_url.strip():
            activity_type = 'ride'
        elif item.peloton_run_url and item.peloton_run_url.strip():
            activity_type = 'run'
        elif item.peloton_yoga_url and item.peloton_yoga_url.strip():
            activity_type = 'yoga'
        elif item.peloton_strength_url and item.peloton_strength_url.strip():
            activity_type = 'strength'
        
        if activity_type:
            if activity_type not in workout_days_dict[dow]:
                workout_days_dict[dow][activity_type] = []
            workout_days_dict[dow][activity_type].append(item)
    
    # Convert to ordered list of workout days
    workout_days_list = sorted(workout_days_dict.items())
    
    # Get plan type (3 or 4 rides/runs)
    core_count = plan.core_workout_count
    
    # Build workout days structure (Day 1, Day 2, etc.)
    workout_days = []
    for workout_day_num, (dow, activities_dict) in enumerate(workout_days_list, start=1):
        # Calculate points for this workout day
        if core_count == 3:
            day_points = 50  # Each workout = 50 points
        elif core_count == 4:
            if workout_day_num == 1 or workout_day_num == core_count:
                day_points = 50  # First and last = 50
            else:
                day_points = 25  # Middle days = 25
        else:
            day_points = 50  # Default
        
        # Collect all alternatives from all activity types for this day
        # Group by activity type, then combine alternatives
        all_alternatives = []
        day_focus = ""
        
        # Process each activity type
        for activity_type in ['ride', 'run', 'yoga', 'strength']:
            if activity_type in activities_dict:
                activity_items = activities_dict[activity_type]
                if activity_items:
                    if not day_focus:
                        day_focus = activity_items[0].peloton_focus
                    
                    # Add all items of this activity type as alternatives
                    for item in activity_items:
                        # Determine which activity field is done for this item
                        item_done = False
                        if activity_type == 'ride':
                            item_done = item.ride_done
                        elif activity_type == 'run':
                            item_done = item.run_done
                        elif activity_type == 'yoga':
                            item_done = item.yoga_done
                        elif activity_type == 'strength':
                            item_done = item.strength_done
                        
                        # Get the peloton URL for this specific activity type (must be non-empty)
                        peloton_url = None
                        if activity_type == 'ride' and item.peloton_ride_url and item.peloton_ride_url.strip():
                            peloton_url = item.peloton_ride_url
                        elif activity_type == 'run' and item.peloton_run_url and item.peloton_run_url.strip():
                            peloton_url = item.peloton_run_url
                        elif activity_type == 'yoga' and item.peloton_yoga_url and item.peloton_yoga_url.strip():
                            peloton_url = item.peloton_yoga_url
                        elif activity_type == 'strength' and item.peloton_strength_url and item.peloton_strength_url.strip():
                            peloton_url = item.peloton_strength_url
                        
                        # Only add to alternatives if we have a valid peloton_url
                        if peloton_url:
                            all_alternatives.append({
                                'item': item,
                                'peloton_url': peloton_url,
                                'activity_type': activity_type,
                                'done': item_done,
                            })
        
        # Only add workout day if there are alternatives
        if all_alternatives:
            # Check if day is completed (any alternative completed)
            day_completed = any(alt['done'] for alt in all_alternatives)
            
            workout_days.append({
                'day_number': workout_day_num,
                'points': day_points,
                'completed': day_completed,
                'alternatives': all_alternatives if all_alternatives else [],  # Ensure it's always a list
                'focus': day_focus or "Workout",
            })
        else:
            # Debug: Log when alternatives are empty
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Workout day {workout_day_num} (dow={dow}) has no alternatives. Activities dict: {list(activities_dict.keys())}")
    
    # Keep old days structure for now (for template compatibility)
    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    days = []
    current_day = None
    current_focus = ""
    current_items = []
    
    # When include_kegels=False, only show items with Peloton URLs (no exercise-only items)
    show_only_peloton_items = plan.challenge_instance and not plan.challenge_instance.include_kegels

    for item in items:
        if current_day is None:
            current_day = item.day_of_week
            current_focus = item.peloton_focus
            current_items = [item]
            continue

        if item.day_of_week == current_day:
            # Keep the first peloton_focus as the day header focus
            current_items.append(item)
        else:
            # Aggregate activity status for the day (use first item's status)
            first_item = current_items[0] if current_items else None
            focus_lower = current_focus.lower() if current_focus else ""
            
            # Determine which activities are linked/expected for this day type
            has_ride = "pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or "ride" in focus_lower
            has_run = "run" in focus_lower
            has_yoga = "yoga" in focus_lower
            has_strength = "strength" in focus_lower
            
            # Calculate day points (only count exercise points if include_kegels=True)
            if show_only_peloton_items:
                day_exercise_points = 0  # No exercise points when kegels are disabled
            else:
                day_exercise_points = sum(1 for item in current_items if item.is_done) * 10
            day_activity_points = 0
            if first_item:
                # Count each activity type separately (50 points each)
                if first_item.ride_done:
                    day_activity_points += 50
                if first_item.run_done:
                    day_activity_points += 50
                if first_item.yoga_done:
                    day_activity_points += 50
                if first_item.strength_done:
                    day_activity_points += 50
            
            # Check if day is completed (all exercises done and all expected activities done)
            all_exercises_done = all(item.is_done for item in current_items)
            all_activities_done = True
            if has_ride and not first_item.ride_done:
                all_activities_done = False
            if has_run and not first_item.run_done:
                all_activities_done = False
            if has_yoga and not first_item.yoga_done:
                all_activities_done = False
            if has_strength and not first_item.strength_done:
                all_activities_done = False
            
            # Determine Peloton workout info
            peloton_url = None
            peloton_activity_type = None
            peloton_done = False
            if first_item:
                if first_item.peloton_ride_url:
                    peloton_url = first_item.peloton_ride_url
                    peloton_activity_type = "ride"
                    peloton_done = first_item.ride_done
                elif first_item.peloton_run_url:
                    peloton_url = first_item.peloton_run_url
                    peloton_activity_type = "run"
                    peloton_done = first_item.run_done
                elif first_item.peloton_yoga_url:
                    peloton_url = first_item.peloton_yoga_url
                    peloton_activity_type = "yoga"
                    peloton_done = first_item.yoga_done
                elif first_item.peloton_strength_url:
                    peloton_url = first_item.peloton_strength_url
                    peloton_activity_type = "strength"
                    peloton_done = first_item.strength_done
            
            # Filter out exercise-only items (no Peloton URLs) when include_kegels=False
            if show_only_peloton_items:
                from django.db.models import Q
                current_items = [item for item in current_items if (
                    item.peloton_ride_url or item.peloton_run_url or 
                    item.peloton_yoga_url or item.peloton_strength_url
                )]
                # Recalculate first_item after filtering
                first_item = current_items[0] if current_items else None
            
            days.append({
                "dow": current_day,
                "label": day_labels[current_day],
                "focus": current_focus,
                "items": current_items,
                "first_item": first_item,  # For activity toggling
                "ride_done": first_item.ride_done if first_item else False,
                "run_done": first_item.run_done if first_item else False,
                "yoga_done": first_item.yoga_done if first_item else False,
                "strength_done": first_item.strength_done if first_item else False,
                "has_ride": has_ride,  # Linked to this day type
                "has_run": has_run,
                "has_yoga": has_yoga,
                "has_strength": has_strength,
                "peloton_url": peloton_url,
                "peloton_activity_type": peloton_activity_type,
                "peloton_done": peloton_done,
                "day_points": day_activity_points,  # Only Peloton workouts count (exercise_points = 0)
                "is_completed": all_activities_done,  # Only Peloton workouts matter for completion
            })
            current_day = item.day_of_week
            current_focus = item.peloton_focus
            current_items = [item]

    # flush final group
    if current_day is not None:
        first_item = current_items[0] if current_items else None
        focus_lower = current_focus.lower() if current_focus else ""
        
        # Determine which activities are linked/expected for this day type
        has_ride = "pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or "ride" in focus_lower
        has_run = "run" in focus_lower
        has_yoga = "yoga" in focus_lower
        has_strength = "strength" in focus_lower
        
        # Calculate day points - NO exercise points, only Peloton workouts count
        day_exercise_points = 0  # Exercises (kegels) do not generate points
        day_activity_points = 0
        
        # Only count one activity per day (to prevent double-counting alternatives)
        if first_item:
            # Check if any item on this day has the activity done
            from django.db.models import Q
            day_items = plan.items.filter(day_of_week=current_day)
            has_ride = day_items.filter(ride_done=True).exists()
            has_run = day_items.filter(run_done=True).exists()
            has_yoga = day_items.filter(yoga_done=True).exists()
            has_strength = day_items.filter(strength_done=True).exists()
            
            # Calculate points based on plan type
            core_count = plan.core_workout_count
            workout_day_numbers = sorted(set(
                list(plan.items.filter(peloton_ride_url__isnull=False).exclude(peloton_ride_url='').values_list('day_of_week', flat=True)) +
                list(plan.items.filter(peloton_run_url__isnull=False).exclude(peloton_run_url='').values_list('day_of_week', flat=True)) +
                list(plan.items.filter(peloton_yoga_url__isnull=False).exclude(peloton_yoga_url='').values_list('day_of_week', flat=True)) +
                list(plan.items.filter(peloton_strength_url__isnull=False).exclude(peloton_strength_url='').values_list('day_of_week', flat=True))
            ))
            
            if current_day in workout_day_numbers:
                workout_day_num = workout_day_numbers.index(current_day) + 1
                
                if core_count == 3:
                    # 3 rides/runs: Each workout = 50 points
                    if has_ride or has_run or has_yoga or has_strength:
                        day_activity_points = 50
                elif core_count == 4:
                    # 4 rides/runs: Day 1 = 50, Day 2 = 25, Day 3 = 25, Final day = 50
                    if has_ride or has_run or has_yoga or has_strength:
                        if workout_day_num == 1 or workout_day_num == core_count:
                            day_activity_points = 50
                        else:
                            day_activity_points = 25
                else:
                    # Fallback
                    if has_ride or has_run or has_yoga or has_strength:
                        day_activity_points = 50
        
        # Check if day is completed - use the has_* variables we calculated
        # Exercises don't count for completion (only Peloton workouts matter)
        focus_lower = current_focus.lower() if current_focus else ""
        expected_ride = "pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or "ride" in focus_lower
        expected_run = "run" in focus_lower
        expected_yoga = "yoga" in focus_lower
        expected_strength = "strength" in focus_lower
        
        all_activities_done = True
        if expected_ride and not has_ride:
            all_activities_done = False
        if expected_run and not has_run:
            all_activities_done = False
        if expected_yoga and not has_yoga:
            all_activities_done = False
        if expected_strength and not has_strength:
            all_activities_done = False
        
        # Filter out exercise-only items (no Peloton URLs) when include_kegels=False
        if show_only_peloton_items:
            current_items = [item for item in current_items if (
                item.peloton_ride_url or item.peloton_run_url or 
                item.peloton_yoga_url or item.peloton_strength_url
            )]
            # Recalculate first_item after filtering
            first_item = current_items[0] if current_items else None
        
        # Determine Peloton workout info
        peloton_url = None
        peloton_activity_type = None
        peloton_done = False
        if first_item:
            if first_item.peloton_ride_url:
                peloton_url = first_item.peloton_ride_url
                peloton_activity_type = "ride"
                peloton_done = first_item.ride_done
            elif first_item.peloton_run_url:
                peloton_url = first_item.peloton_run_url
                peloton_activity_type = "run"
                peloton_done = first_item.run_done
            elif first_item.peloton_yoga_url:
                peloton_url = first_item.peloton_yoga_url
                peloton_activity_type = "yoga"
                peloton_done = first_item.yoga_done
            elif first_item.peloton_strength_url:
                peloton_url = first_item.peloton_strength_url
                peloton_activity_type = "strength"
                peloton_done = first_item.strength_done
        
        days.append({
            "dow": current_day,
            "label": day_labels[current_day],
            "focus": current_focus,
            "items": current_items,
            "first_item": first_item,  # For activity toggling
            "ride_done": first_item.ride_done if first_item else False,
            "run_done": first_item.run_done if first_item else False,
            "yoga_done": first_item.yoga_done if first_item else False,
            "strength_done": first_item.strength_done if first_item else False,
            "has_ride": has_ride,  # Linked to this day type
            "has_run": has_run,
            "has_yoga": has_yoga,
            "has_strength": has_strength,
            "peloton_url": peloton_url,
            "peloton_activity_type": peloton_activity_type,
            "peloton_done": peloton_done,
            "day_points": day_activity_points,  # Only Peloton workouts count (exercise_points = 0)
            "is_completed": all_activities_done,  # Only Peloton workouts matter for completion
        })

    # Find next week plan and previous week plan for challenges
    next_week_plan = None
    previous_week_plan = None
    total_weeks = None
    challenge = None
    is_challenge_view = False
    challenge_structure = None
    
    if plan.challenge_instance:
        challenge = plan.challenge_instance.challenge
        is_challenge_view = True
        all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
        total_weeks = all_plans.count()
        
        # Get previous week plan
        if week_number and week_number > 1:
            previous_week_start = plan.week_start - timedelta(days=7)
            previous_week_plan = all_plans.filter(week_start=previous_week_start).first()
        
        # Get next week plan
        if plan.challenge_instance.challenge.is_currently_running or plan.challenge_instance.challenge.has_ended:
            next_week_start = plan.week_start + timedelta(days=7)
            next_week_plan = all_plans.filter(week_start=next_week_start).first()
        
        # Get challenge structure text
        if challenge.challenge_type == "individual":
            challenge_structure = "Individual Challenge"
        elif challenge.challenge_type == "team":
            challenge_structure = "Team Challenge"
        else:
            challenge_structure = "Challenge"
    
    # Check if user can leave challenge (if this is a challenge plan)
    can_leave = None
    leave_error = None
    if plan.challenge_instance:
        can_leave, leave_error = plan.challenge_instance.can_leave_challenge()
    
    # Debug: Print workout_days structure
    print(f"DEBUG: workout_days count: {len(workout_days)}")
    print(f"DEBUG: workout_days type: {type(workout_days)}")
    for i, wd in enumerate(workout_days):
        if isinstance(wd, dict):
            print(f"DEBUG: Day {wd.get('day_number', 'N/A')}: {len(wd.get('alternatives', []))} alternatives")
            if wd.get('alternatives'):
                for alt in wd['alternatives']:
                    print(f"  - {alt.get('activity_type')}: {alt.get('peloton_url', 'NO URL')[:50]}")
        else:
            print(f"DEBUG: Item {i} is not a dict, it's {type(wd)}: {wd}")
    
    # Get user profile for FTP and pace target level
    from accounts.models import Profile
    try:
        user_profile = Profile.objects.get(user=request.user)
        user_ftp = user_profile.ftp_score
        user_pace_target = user_profile.pace_target_level
    except Profile.DoesNotExist:
        user_ftp = None
        user_pace_target = None
    
    context = {
        "plan": plan,
        "days": days,  # Keep for backward compatibility
        "workout_days": workout_days,  # New structure: Day 1, Day 2, etc.
        "core_count": core_count,
        "week_number": week_number,
        "can_access_week": can_access_week,
        "previous_week_completed": previous_week_completed,
        "next_week_plan": next_week_plan,
        "previous_week_plan": previous_week_plan,
        "total_weeks": total_weeks,
        "challenge": challenge,
        "is_challenge_view": is_challenge_view,
        "challenge_structure": challenge_structure,
        "can_leave": can_leave,
        "leave_error": leave_error,
        "include_kegels": plan.challenge_instance.include_kegels if plan.challenge_instance else True,
        "bonus_workouts": bonus_workouts,
        "bonus_completed": bonus_completed,
        "user_ftp": user_ftp,
        "user_pace_target": user_pace_target,
    }
    return render(request, "tracker/plan_detail.html", context)

# challenge_detail moved to challenges app

@login_required
def toggle_done(request, pk):
    item = get_object_or_404(DailyPlanItem, pk=pk, weekly_plan__user=request.user)
    plan = item.weekly_plan
    
    # Check if week is locked (for active challenges only, not past challenges)
    if plan.challenge_instance:
        from challenges.models import Challenge
        challenge = plan.challenge_instance.challenge
        # For past challenges, allow all toggling
        if not challenge.has_ended and challenge.is_active:
            all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
            
            # Find current week number
            week_number = None
            for idx, p in enumerate(all_plans, start=1):
                if p.id == plan.id:
                    week_number = idx
                    break
            
            # If not week 1, check if ALL previous weeks are completed
            if week_number and week_number > 1:
                previous_plans = all_plans.filter(week_start__lt=plan.week_start).order_by("week_start")
                # Check if ALL previous weeks are completed
                incomplete_weeks = [p for p in previous_plans if not p.is_completed]
                if incomplete_weeks:
                    incomplete_week_numbers = []
                    for p in incomplete_weeks:
                        for idx, check_p in enumerate(all_plans, start=1):
                            if check_p.id == p.id:
                                incomplete_week_numbers.append(idx)
                                break
                    error_msg = f"Complete Week(s) {', '.join(map(str, incomplete_week_numbers))} before accessing Week {week_number} exercises."
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({"success": False, "error": error_msg})
                    messages.error(request, error_msg)
                    return redirect("tracker:plan_detail", pk=plan.id)
    
    # Check if exercise can be toggled
    can_toggle, error_msg = item.can_toggle
    if not can_toggle:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "error": error_msg or "Cannot toggle this exercise."})
        messages.error(request, error_msg or "Cannot toggle this exercise.")
        return redirect("tracker:plan_detail", pk=item.weekly_plan_id)
    
    # Toggle the done status
    item.is_done = not item.is_done
    if item.is_done:
        item.completed_at = timezone.now()
        success_msg = f"✓ Completed! You earned {item.points_earned} points!"
    else:
        item.completed_at = None
        success_msg = "Exercise unchecked."
    
    item.save(update_fields=["is_done", "completed_at"])
    
    # Refresh plan from DB to get updated stats
    plan.refresh_from_db()
    
    # Check if week is now completed
    week_completed = False
    next_week_unlocked = False
    if plan.completion_rate >= 80 and not plan.completed_at:
        plan.completed_at = timezone.now()
        plan.save(update_fields=["completed_at"])
        week_completed = True
        week_completed_msg = f"🎉 Week completed! Total points: {plan.total_points}"
        
        # For active challenges, auto-generate next week if it doesn't exist
        if plan.challenge_instance and plan.challenge_instance.challenge.is_currently_running:
            next_week_start = plan.week_start + timedelta(days=7)
            # Check if next week is still within challenge dates
            challenge = plan.challenge_instance.challenge
            challenge_end_week_start = sunday_of_current_week(challenge.end_date)
            
            if next_week_start <= challenge_end_week_start:
                # Check if next week plan already exists
                next_week_plan = WeeklyPlan.objects.filter(
                    user=request.user,
                    week_start=next_week_start,
                    challenge_instance=plan.challenge_instance
                ).first()
                
                if not next_week_plan:
                    # Generate next week
                    template = plan.challenge_instance.selected_template or challenge.default_template
                    if template:
                        # Calculate next week number
                        all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
                        next_week_number = all_plans.count() + 1
                        
                        next_weekly = generate_weekly_plan(
                            user=request.user,
                            week_start=next_week_start,
                            template=template,
                            start_from_today=False,  # Generate full week
                            challenge_instance=plan.challenge_instance,
                            week_number=next_week_number
                        )
                        next_weekly.challenge_instance = plan.challenge_instance
                        next_weekly.save(update_fields=["challenge_instance"])
                        next_week_unlocked = True
                        next_week_msg = f"Week {next_week_number} unlocked! You can now start the next week."
    
    # Handle AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {
            "success": True,
            "is_done": item.is_done,
            "points_earned": item.points_earned if item.is_done else 0,
            "message": success_msg,
            "plan_completion_rate": plan.completion_rate,
            "plan_total_points": plan.total_points,
            "plan_max_total_points": plan.max_total_points,
            "plan_is_completed": plan.is_completed,
            "week_completed": week_completed,
        }
        if week_completed:
            response_data["week_completed_msg"] = week_completed_msg
        if next_week_unlocked:
            response_data["next_week_unlocked"] = True
            response_data["next_week_msg"] = next_week_msg
        return JsonResponse(response_data)
    
    # Non-AJAX request - use messages and redirect
    messages.success(request, success_msg)
    if week_completed:
        messages.success(request, week_completed_msg)
    if next_week_unlocked:
        messages.info(request, next_week_msg)
    
    return redirect("tracker:plan_detail", pk=item.weekly_plan_id)

@login_required
def toggle_activity(request, pk, activity):
    """Toggle activity (ride, run, yoga, strength) for a day - updates all items for that day"""
    item = get_object_or_404(DailyPlanItem, pk=pk, weekly_plan__user=request.user)
    plan = item.weekly_plan
    
    # Check if week is locked (for active challenges only, not past challenges)
    if plan.challenge_instance:
        from challenges.models import Challenge
        challenge = plan.challenge_instance.challenge
        # For past challenges, allow all toggling
        if not challenge.has_ended and challenge.is_active:
            all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
            
            # Find current week number
            week_number = None
            for idx, p in enumerate(all_plans, start=1):
                if p.id == plan.id:
                    week_number = idx
                    break
            
            # If not week 1, check if ALL previous weeks are completed
            if week_number and week_number > 1:
                previous_plans = all_plans.filter(week_start__lt=plan.week_start).order_by("week_start")
                # Check if ALL previous weeks are completed
                incomplete_weeks = [p for p in previous_plans if not p.is_completed]
                if incomplete_weeks:
                    incomplete_week_numbers = []
                    for p in incomplete_weeks:
                        for idx, check_p in enumerate(all_plans, start=1):
                            if check_p.id == p.id:
                                incomplete_week_numbers.append(idx)
                                break
                    error_msg = f"Complete Week(s) {', '.join(map(str, incomplete_week_numbers))} before accessing Week {week_number} activities."
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({"success": False, "error": error_msg})
                    messages.error(request, error_msg)
                    return redirect("tracker:plan_detail", pk=plan.id)
    
    # Map activity names to model fields
    activity_map = {
        "ride": "ride_done",
        "run": "run_done",
        "yoga": "yoga_done",
        "strength": "strength_done",
    }
    
    if activity not in activity_map:
        error_msg = "Invalid activity."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "error": error_msg})
        messages.error(request, error_msg)
        return redirect("tracker:plan_detail", pk=item.weekly_plan_id)
    
    field_name = activity_map[activity]
    current_value = getattr(item, field_name)
    new_value = not current_value
    
    # Update the current item
    setattr(item, field_name, new_value)
    item.save(update_fields=[field_name])
    
    # If checking a workout, uncheck all other workout alternatives on the same day
    if new_value:
        plan = item.weekly_plan
        from django.db.models import Q
        
        # Check if this is a bonus workout
        is_bonus = item.peloton_focus and "Bonus" in item.peloton_focus
        
        if is_bonus:
            # For bonus workouts, uncheck all other bonus workouts (only one bonus can be selected)
            other_bonus_items = plan.items.filter(
                peloton_focus__icontains="Bonus"
            ).exclude(
                id=item.id
            )
            
            # Uncheck all activity types for other bonus items
            for other_item in other_bonus_items:
                if other_item.ride_done:
                    other_item.ride_done = False
                if other_item.run_done:
                    other_item.run_done = False
                if other_item.yoga_done:
                    other_item.yoga_done = False
                if other_item.strength_done:
                    other_item.strength_done = False
                other_item.save(update_fields=['ride_done', 'run_done', 'yoga_done', 'strength_done'])
        else:
            # For regular workouts, uncheck all other workout alternatives on the same day (excluding bonus workouts)
            other_day_items = plan.items.filter(
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
            
            # Uncheck all activity types for other items on this day
            for other_item in other_day_items:
                if other_item.ride_done:
                    other_item.ride_done = False
                if other_item.run_done:
                    other_item.run_done = False
                if other_item.yoga_done:
                    other_item.yoga_done = False
                if other_item.strength_done:
                    other_item.strength_done = False
                other_item.save(update_fields=['ride_done', 'run_done', 'yoga_done', 'strength_done'])
    
    activity_name = activity.capitalize()
    plan = item.weekly_plan
    plan.refresh_from_db()  # Refresh to get updated stats
    
    # Calculate points for this specific activity
    # Points depend on plan type and workout day number
    core_count = plan.core_workout_count
    workout_day_numbers = sorted(set(
        list(plan.items.filter(peloton_ride_url__isnull=False).exclude(peloton_ride_url='').values_list('day_of_week', flat=True)) +
        list(plan.items.filter(peloton_run_url__isnull=False).exclude(peloton_run_url='').values_list('day_of_week', flat=True)) +
        list(plan.items.filter(peloton_yoga_url__isnull=False).exclude(peloton_yoga_url='').values_list('day_of_week', flat=True)) +
        list(plan.items.filter(peloton_strength_url__isnull=False).exclude(peloton_strength_url='').values_list('day_of_week', flat=True))
    ))
    
    points_earned = 0
    if item.day_of_week in workout_day_numbers and new_value:
        workout_day_num = workout_day_numbers.index(item.day_of_week) + 1
        if core_count == 3:
            points_earned = 50
        elif core_count == 4:
            if workout_day_num == 1 or workout_day_num == core_count:
                points_earned = 50
            else:
                points_earned = 25
        else:
            points_earned = 50
    
    if new_value:
        success_msg = f"✓ {activity_name} marked as done!"
    else:
        success_msg = f"{activity_name} unchecked."
    
    # Check if week is now completed
    week_completed = False
    next_week_unlocked = False
    if plan.completion_rate >= 80 and not plan.completed_at:
        plan.completed_at = timezone.now()
        plan.save(update_fields=["completed_at"])
        week_completed = True
        week_completed_msg = f"🎉 Week completed! Total points: {plan.total_points}"
        
        # For active challenges, auto-generate next week if it doesn't exist
        if plan.challenge_instance and plan.challenge_instance.challenge.is_currently_running:
            next_week_start = plan.week_start + timedelta(days=7)
            # Check if next week is still within challenge dates
            challenge = plan.challenge_instance.challenge
            challenge_end_week_start = sunday_of_current_week(challenge.end_date)
            
            if next_week_start <= challenge_end_week_start:
                # Check if next week plan already exists
                next_week_plan = WeeklyPlan.objects.filter(
                    user=request.user,
                    week_start=next_week_start,
                    challenge_instance=plan.challenge_instance
                ).first()
                
                if not next_week_plan:
                    # Generate next week
                    template = plan.challenge_instance.selected_template or challenge.default_template
                    if template:
                        # Calculate next week number
                        all_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
                        next_week_number = all_plans.count() + 1
                        
                        next_weekly = generate_weekly_plan(
                            user=request.user,
                            week_start=next_week_start,
                            template=template,
                            start_from_today=False,  # Generate full week
                            challenge_instance=plan.challenge_instance,
                            week_number=next_week_number
                        )
                        next_weekly.challenge_instance = plan.challenge_instance
                        next_weekly.save(update_fields=["challenge_instance"])
                        next_week_unlocked = True
                        next_week_msg = f"Week {next_week_number} unlocked! You can now start the next week."
    
    # Handle AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get updated day stats - NO exercise points, only Peloton workouts count
        day_items = plan.items.filter(day_of_week=item.day_of_week)
        day_points = 0  # Exercise points are 0 - only Peloton workouts count
        
        # Count activity points - only one activity per day counts (to prevent double-counting alternatives)
        # Check if any item on this day has the activity done
        from django.db.models import Q
        has_ride = day_items.filter(ride_done=True).exists()
        has_run = day_items.filter(run_done=True).exists()
        has_yoga = day_items.filter(yoga_done=True).exists()
        has_strength = day_items.filter(strength_done=True).exists()
        
        # Calculate points based on plan type and workout day number
        core_count = plan.core_workout_count
        workout_day_numbers = sorted(set(
            list(plan.items.filter(peloton_ride_url__isnull=False).exclude(peloton_ride_url='').values_list('day_of_week', flat=True)) +
            list(plan.items.filter(peloton_run_url__isnull=False).exclude(peloton_run_url='').values_list('day_of_week', flat=True)) +
            list(plan.items.filter(peloton_yoga_url__isnull=False).exclude(peloton_yoga_url='').values_list('day_of_week', flat=True)) +
            list(plan.items.filter(peloton_strength_url__isnull=False).exclude(peloton_strength_url='').values_list('day_of_week', flat=True))
        ))
        
        if item.day_of_week in workout_day_numbers:
            workout_day_num = workout_day_numbers.index(item.day_of_week) + 1
            
            if core_count == 3:
                # 3 rides/runs: Each workout = 50 points
                if has_ride or has_run or has_yoga or has_strength:
                    day_points = 50
            elif core_count == 4:
                # 4 rides/runs: Day 1 = 50, Day 2 = 25, Day 3 = 25, Final day = 50
                if has_ride or has_run or has_yoga or has_strength:
                    if workout_day_num == 1 or workout_day_num == core_count:
                        day_points = 50
                    else:
                        day_points = 25
            else:
                # Fallback
                if has_ride or has_run or has_yoga or has_strength:
                    day_points = 50
        
        # Get all items for this day to check which alternatives should be disabled
        day_items = plan.items.filter(day_of_week=item.day_of_week)
        other_checked_items = []
        if new_value:
            # If we just checked this item, find other checked items for the same activity
            for other_item in day_items.exclude(id=item.id):
                if getattr(other_item, field_name):
                    other_checked_items.append(other_item.id)
        
        response_data = {
            "success": True,
            "activity_done": new_value,
            "activity_name": activity_name,
            "message": success_msg,
            "day_points": day_points,
            "plan_completion_rate": plan.completion_rate,
            "plan_total_points": plan.total_points,
            "plan_max_total_points": plan.max_total_points,
            "plan_is_completed": plan.is_completed,
            "week_completed": week_completed,
            "other_checked_item_ids": other_checked_items,  # Items that should be unchecked
        }
        if week_completed:
            response_data["week_completed_msg"] = week_completed_msg
        if next_week_unlocked:
            response_data["next_week_unlocked"] = True
            response_data["next_week_msg"] = next_week_msg
        return JsonResponse(response_data)
    
    # Non-AJAX request - use messages and redirect
    messages.success(request, success_msg)
    if week_completed:
        messages.success(request, week_completed_msg)
    if next_week_unlocked:
        messages.info(request, next_week_msg)
    
    return redirect("tracker:plan_detail", pk=item.weekly_plan_id)

@login_required
def edit_item(request, pk):
    item = get_object_or_404(DailyPlanItem, pk=pk, weekly_plan__user=request.user)

    if request.method == "POST":
        form = DailyPlanItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("tracker:plan_detail", pk=item.weekly_plan_id)
    else:
        form = DailyPlanItemForm(instance=item)

    context = {
        "item": item,
        "form": form,
    }
    return render(request, "tracker/edit_item.html", context)