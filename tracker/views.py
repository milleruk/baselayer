from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from plans.models import PlanTemplate
from plans.services import generate_weekly_plan
from .models import WeeklyPlan, DailyPlanItem, Challenge, ChallengeInstance
from .forms import DailyPlanItemForm


def sunday_of_current_week(d: date) -> date:
    """Get the Sunday of the current week (week starts on Sunday)"""
    # weekday() returns 0=Monday, 6=Sunday
    # We want Sunday to be day 0, so we adjust
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)

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
        # Redirect to challenge detail if part of challenge, otherwise plan detail
        if challenge_instance:
            return redirect("tracker:challenge_detail", challenge_id=challenge_instance.challenge.id)
        else:
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
def complete_challenge(request, challenge_instance_id):
    """Mark a challenge instance as completed"""
    challenge_instance = get_object_or_404(ChallengeInstance, pk=challenge_instance_id, user=request.user)
    if request.method == "POST":
        challenge_instance.is_active = False
        challenge_instance.completed_at = timezone.now()
        challenge_instance.save(update_fields=["is_active", "completed_at"])
        messages.success(request, f"Challenge completed! Total points: {challenge_instance.total_points}")
        return redirect("tracker:weekly_plans")
    return redirect("tracker:weekly_plans")

@login_required
def leave_challenge(request, challenge_instance_id):
    """Leave a challenge instance"""
    challenge_instance = get_object_or_404(ChallengeInstance, pk=challenge_instance_id, user=request.user)
    
    # Check if user can leave
    can_leave, error_msg = challenge_instance.can_leave_challenge()
    
    if not can_leave:
        messages.error(request, error_msg or "You cannot leave this challenge at this time.")
        return redirect("tracker:challenges_list")
    
    if request.method == "POST":
        challenge_name = challenge_instance.challenge.name
        # Set as inactive but don't mark as completed (they're leaving, not completing)
        challenge_instance.is_active = False
        challenge_instance.completed_at = None
        challenge_instance.save(update_fields=["is_active", "completed_at"])
        messages.success(request, f"You have left the challenge '{challenge_name}'. You can join another challenge or generate standalone plans.")
        return redirect("tracker:challenges_list")
    
    # Show confirmation page
    return render(request, "tracker/leave_challenge.html", {
        "challenge_instance": challenge_instance,
        "can_leave": can_leave,
        "error_msg": error_msg,
    })

@login_required
def join_challenge(request, challenge_id):
    """Join a challenge and auto-generate weekly plans"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Check if user already has an active challenge (can only be in one at a time)
    active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
    if active_challenge_instance:
        if active_challenge_instance.challenge.id != challenge.id:
            messages.error(request, f"You are already participating in '{active_challenge_instance.challenge.name}'. Please leave or complete that challenge before joining another one.")
            return redirect("tracker:challenges_list")
        else:
            # User is trying to join the same challenge they're already in
            messages.info(request, f"You're already participating in '{challenge.name}'")
            return redirect("tracker:weekly_plans")
    
    # Check if signup is allowed
    if not challenge.can_signup:
        messages.error(request, f"Signup for '{challenge.name}' is no longer available.")
        return redirect("tracker:challenges_list")
    
    # Check if user is already participating (for retaking completed challenges)
    # Get the most recent instance (prefer active ones)
    challenge_instance = ChallengeInstance.objects.filter(
        user=request.user, 
        challenge=challenge
    ).order_by('-is_active', '-started_at').first()
    
    if challenge_instance:
        if challenge_instance.is_active:
            # This shouldn't happen due to check above, but handle it anyway
            messages.info(request, f"You're already participating in '{challenge.name}'")
            return redirect("tracker:weekly_plans")
        else:
            # Rejoin a completed challenge - allow retaking
            # Don't redirect to template selection, let them proceed to join flow
            pass
    
    # If POST, create challenge instance with selected template and generate weeks
    if request.method == "POST":
        # Double-check if user already has an active challenge (prevent race conditions)
        active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
        if active_challenge_instance:
            if active_challenge_instance.challenge.id != challenge.id:
                messages.error(request, f"You are already participating in '{active_challenge_instance.challenge.name}'. Please leave or complete that challenge before joining another one.")
                return redirect("tracker:challenges_list")
            else:
                messages.info(request, f"You're already participating in '{challenge.name}'")
                return redirect("tracker:weekly_plans")
        
        template_id = request.POST.get("template_id")
        delete_existing_plan = request.POST.get("delete_existing_plan") == "true"
        
        if not template_id:
            messages.error(request, "Please select a plan template.")
            return redirect("tracker:select_challenge_template", challenge_id=challenge_id)
        
        # Check if user has a plan for the current week and handle deletion
        current_week_start = sunday_of_current_week(date.today())
        existing_current_week_plan = WeeklyPlan.objects.filter(user=request.user, week_start=current_week_start).first()
        
        if existing_current_week_plan:
            if delete_existing_plan:
                # Delete the existing plan
                existing_current_week_plan.delete()
                messages.info(request, "Deleted existing weekly plan for this week.")
            else:
                # User didn't confirm deletion, redirect back
                messages.error(request, "You have an existing plan for this week. Please delete it first or confirm deletion when joining the challenge.")
                return redirect("tracker:select_challenge_template", challenge_id=challenge_id)
        
        template = get_object_or_404(PlanTemplate, pk=template_id)
        include_kegels = request.POST.get("include_kegels") == "on"
        
        # Check if user has an active instance for this challenge
        active_instance = ChallengeInstance.objects.filter(
            user=request.user,
            challenge=challenge,
            is_active=True
        ).first()
        
        if active_instance:
            # User already has an active instance - delete old plans and reset
            active_instance.weekly_plans.all().delete()
            challenge_instance = active_instance
            challenge_instance.selected_template = template
            challenge_instance.is_active = True  # Ensure it stays active
            challenge_instance.completed_at = None
            challenge_instance.include_kegels = include_kegels
            challenge_instance.started_at = timezone.now()  # Update start time for new attempt
            challenge_instance.save(update_fields=["selected_template", "is_active", "completed_at", "include_kegels", "started_at"])
        else:
            # Create new instance (fresh attempt)
            challenge_instance = ChallengeInstance.objects.create(
                user=request.user,
                challenge=challenge,
                is_active=True,
                selected_template=template,
                include_kegels=include_kegels
            )
        
        # Auto-generate weekly plans for the challenge duration
        today = date.today()
        challenge_start = challenge.start_date
        challenge_end = challenge.end_date
        
        # For past challenges (retaking), generate all weeks from challenge start
        # For current/upcoming challenges, generate from current week or challenge start (whichever is later)
        if challenge.has_ended:
            # Past challenge - generate all weeks from challenge start
            start_week = sunday_of_current_week(challenge_start)
            use_start_from_today = False
        else:
            # Current or upcoming challenge - start from current week or challenge start
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
            
            # Always generate fresh plans (old ones were deleted above if rejoining)
            weekly = generate_weekly_plan(
                user=request.user,
                week_start=current_week_start,
                template=template,
                start_from_today=(use_start_from_today and current_week_start == sunday_of_current_week(today)),
                challenge_instance=challenge_instance,
                week_number=week_num
            )
            weekly.challenge_instance = challenge_instance
            weekly.save(update_fields=["challenge_instance"])
            weeks_generated += 1
            
            current_week_start += timedelta(days=7)
        
        if weeks_generated > 0:
            messages.success(request, f"Joined challenge '{challenge.name}'! Generated {weeks_generated} week(s).")
        else:
            messages.info(request, f"You're already participating in '{challenge.name}'!")
        
        return redirect("tracker:weekly_plans")
    
    # GET request - redirect to template selection
    return redirect("tracker:select_challenge_template", challenge_id=challenge_id)

@login_required
def select_challenge_template(request, challenge_id):
    """Select plan template when joining a challenge"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Check if user already has an active challenge (can only be in one at a time)
    active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
    if active_challenge_instance:
        if active_challenge_instance.challenge.id != challenge.id:
            messages.error(request, f"You are already participating in '{active_challenge_instance.challenge.name}'. Please leave or complete that challenge before joining another one.")
            return redirect("tracker:challenges_list")
        else:
            # User is trying to select template for the same challenge they're already in
            messages.info(request, f"You're already participating in '{challenge.name}'")
            return redirect("tracker:weekly_plans")
    
    # Check if signup is allowed
    if not challenge.can_signup:
        messages.error(request, f"Signup for '{challenge.name}' is no longer available.")
        return redirect("tracker:challenges_list")
    
    # Check if user has a plan for the current week
    current_week_start = sunday_of_current_week(date.today())
    existing_current_week_plan = WeeklyPlan.objects.filter(user=request.user, week_start=current_week_start).first()
    
    # Get available templates for this challenge
    if challenge.available_templates.exists():
        # Only show templates that are available for this challenge
        templates = challenge.available_templates.all().order_by("name")
    else:
        # Fallback: show all templates if none are specified (backward compatibility)
        templates = PlanTemplate.objects.all().order_by("name")
    
    # If challenge has a default template, prioritize it
    if challenge.default_template:
        templates = list(templates)
        if challenge.default_template in templates:
            templates.remove(challenge.default_template)
            templates.insert(0, challenge.default_template)
    
    return render(request, "tracker/select_challenge_template.html", {
        "challenge": challenge,
        "templates": templates,
        "existing_current_week_plan": existing_current_week_plan,
    })

@login_required
def challenges_list(request):
    """List all available challenges"""
    today = date.today()
    # Only show visible challenges that haven't started yet (for signup)
    upcoming_challenges = Challenge.objects.filter(
        is_active=True,
        is_visible=True,
        start_date__gt=today  # Only show challenges that haven't started
    ).order_by("start_date")  # Earliest first
    
    # Currently running challenges (for users already participating)
    running_challenges = Challenge.objects.filter(
        is_active=True,
        is_visible=True,
        start_date__lte=today,
        end_date__gte=today
    ).order_by("start_date")  # Earliest first
    
    # Past challenges (ended) - can be retaken
    past_challenges = Challenge.objects.filter(
        is_active=True,
        is_visible=True,
        end_date__lt=today
    ).order_by("start_date")  # Earliest first
    
    user_challenges = ChallengeInstance.objects.filter(user=request.user).select_related("challenge")
    user_challenge_ids = set(user_challenges.values_list("challenge_id", flat=True))
    
    # Get active challenge instance for leave button
    active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
    active_challenge_id = active_challenge_instance.challenge.id if active_challenge_instance else None
    
    # Get user's challenge instances mapped by challenge ID (include all, not just active)
    # This allows us to distinguish between completed (completed_at is set) and left (completed_at is None)
    # Also calculate can_leave for each active instance
    user_challenge_instances = {}
    for ci in user_challenges:
        user_challenge_instances[ci.challenge.id] = ci
        # Add can_leave info for active instances
        if ci.is_active:
            ci.can_leave, ci.leave_error = ci.can_leave_challenge()
    
    return render(request, "tracker/challenges.html", {
        "upcoming_challenges": upcoming_challenges,
        "running_challenges": running_challenges,
        "past_challenges": past_challenges,
        "user_challenge_ids": user_challenge_ids,
        "active_challenge_id": active_challenge_id,
        "user_challenge_instances": user_challenge_instances,
    })

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

    # Find next week plan for active challenges
    next_week_plan = None
    if plan.challenge_instance and plan.challenge_instance.challenge.is_currently_running:
        next_week_start = plan.week_start + timedelta(days=7)
        next_week_plan = plan.challenge_instance.weekly_plans.filter(week_start=next_week_start).first()
    
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
    
    context = {
        "plan": plan,
        "days": days,  # Keep for backward compatibility
        "workout_days": workout_days,  # New structure: Day 1, Day 2, etc.
        "core_count": core_count,
        "week_number": week_number,
        "can_access_week": can_access_week,
        "previous_week_completed": previous_week_completed,
        "next_week_plan": next_week_plan,
        "can_leave": can_leave,
        "leave_error": leave_error,
        "include_kegels": plan.challenge_instance.include_kegels if plan.challenge_instance else True,
        "bonus_workouts": bonus_workouts,
        "bonus_completed": bonus_completed,
    }
    return render(request, "tracker/plan_detail.html", context)

@login_required
def challenge_detail(request, challenge_id, week_number=None):
    """View challenge plan by challenge ID and optional week number"""
    # Get the challenge
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Get user's challenge instance for this challenge
    challenge_instance = ChallengeInstance.objects.filter(
        user=request.user,
        challenge=challenge
    ).first()
    
    if not challenge_instance:
        messages.error(request, "You are not participating in this challenge.")
        return redirect("tracker:challenges_list")
    
    # Get all weekly plans for this challenge instance, ordered by week_start
    all_plans = challenge_instance.weekly_plans.all().order_by("week_start")
    total_weeks = all_plans.count()
    
    if total_weeks == 0:
        messages.error(request, "No weekly plans found for this challenge.")
        return redirect("tracker:challenges_list")
    
    # Determine which week to show
    if week_number is not None:
        # Get the plan for the specified week number (1-indexed)
        if week_number < 1 or week_number > total_weeks:
            messages.error(request, f"Invalid week number. This challenge has {total_weeks} week(s).")
            return redirect("tracker:challenge_detail", challenge_id=challenge_id)
        plan = all_plans[week_number - 1]
    else:
        # Show current week or first week
        current_week_start = sunday_of_current_week(date.today())
        current_plan = all_plans.filter(week_start=current_week_start).first()
        if current_plan:
            plan = current_plan
        else:
            # Show the first week
            plan = all_plans.first()
    
    # Calculate actual week number for the selected plan
    actual_week_number = None
    for idx, p in enumerate(all_plans, start=1):
        if p.id == plan.id:
            actual_week_number = idx
            break
    
    # Get previous and next week plans
    previous_week_plan = None
    next_week_plan = None
    if actual_week_number:
        if actual_week_number > 1:
            previous_week_plan = all_plans[actual_week_number - 2]
        if actual_week_number < total_weeks:
            next_week_plan = all_plans[actual_week_number]
    
    # Check access permissions (reuse logic from plan_detail)
    can_access_week = True
    previous_week_completed = True
    
    if challenge.has_ended:
        can_access_week = True
        previous_week_completed = True
    elif actual_week_number and not challenge.is_week_unlocked(actual_week_number):
        can_access_week = False
        previous_week_completed = False
    elif challenge.is_active and not challenge.has_ended and actual_week_number and actual_week_number > 1:
        previous_plans = all_plans.filter(week_start__lt=plan.week_start).order_by("week_start")
        if previous_plans.exists():
            incomplete_weeks = [p for p in previous_plans if not p.is_completed]
            can_access_week = len(incomplete_weeks) == 0
            previous_week_completed = can_access_week
        else:
            can_access_week = False
            previous_week_completed = False
    
    # Get challenge structure description (e.g., "2 Ride & 2 Run per week")
    structure_parts = []
    if challenge.categories:
        categories = challenge.get_categories_list()
        # Count workout types from template or default
        # For now, use a simple description based on categories
        if "CYCLING" in categories and "RUNNING" in categories:
            structure_parts.append("2 Ride & 2 Run")
        elif "CYCLING" in categories:
            structure_parts.append("Cycling")
        elif "RUNNING" in categories:
            structure_parts.append("Running")
        else:
            structure_parts.append("Workouts")
    else:
        structure_parts.append("Workouts")
    
    challenge_structure = " & ".join(structure_parts) + " per week"
    
    # Now reuse the plan_detail logic by calling it with the plan
    # But we need to add challenge navigation context
    # Let's get the plan and build context similar to plan_detail
    
    # Reuse all the plan_detail logic for building workout days, etc.
    # We'll call the same logic but add challenge navigation context
    
    # Get the plan with all relationships
    plan = WeeklyPlan.objects.select_related('challenge_instance__challenge').get(pk=plan.id)
    
    # Build context similar to plan_detail
    all_items = plan.items.select_related("exercise").all()
    
    from django.db.models import Q
    bonus_workouts = list(all_items.filter(peloton_focus__icontains="Bonus"))
    items = all_items.exclude(peloton_focus__icontains="Bonus")
    
    bonus_completed = False
    if bonus_workouts:
        first_bonus = bonus_workouts[0]
        bonus_completed = first_bonus.ride_done or first_bonus.run_done or first_bonus.yoga_done or first_bonus.strength_done
    
    if plan.challenge_instance and not plan.challenge_instance.include_kegels:
        items = items.filter(
            (Q(peloton_ride_url__isnull=False) |
             Q(peloton_run_url__isnull=False) |
             Q(peloton_yoga_url__isnull=False) |
             Q(peloton_strength_url__isnull=False)) &
            ~Q(exercise__category="kegel")
        )
    
    workout_items = items.filter(
        (Q(peloton_ride_url__isnull=False) & ~Q(peloton_ride_url='')) |
        (Q(peloton_run_url__isnull=False) & ~Q(peloton_run_url='')) |
        (Q(peloton_yoga_url__isnull=False) & ~Q(peloton_yoga_url='')) |
        (Q(peloton_strength_url__isnull=False) & ~Q(peloton_strength_url=''))
    ).order_by('day_of_week', 'id')
    
    workout_days_dict = {}
    for item in workout_items:
        dow = item.day_of_week
        if dow not in workout_days_dict:
            workout_days_dict[dow] = {}
        
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
    
    workout_days_list = sorted(workout_days_dict.items())
    core_count = plan.core_workout_count
    
    workout_days = []
    for workout_day_num, (dow, activities_dict) in enumerate(workout_days_list, start=1):
        if core_count == 3:
            day_points = 50
        elif core_count == 4:
            if workout_day_num == 1 or workout_day_num == core_count:
                day_points = 50
            else:
                day_points = 25
        else:
            day_points = 50
        
        all_alternatives = []
        day_focus = ""
        
        for activity_type in ['ride', 'run', 'yoga', 'strength']:
            if activity_type in activities_dict:
                activity_items = activities_dict[activity_type]
                if activity_items:
                    if not day_focus:
                        day_focus = activity_items[0].peloton_focus
                    
                    for item in activity_items:
                        item_done = False
                        if activity_type == 'ride':
                            item_done = item.ride_done
                        elif activity_type == 'run':
                            item_done = item.run_done
                        elif activity_type == 'yoga':
                            item_done = item.yoga_done
                        elif activity_type == 'strength':
                            item_done = item.strength_done
                        
                        peloton_url = None
                        if activity_type == 'ride' and item.peloton_ride_url and item.peloton_ride_url.strip():
                            peloton_url = item.peloton_ride_url
                        elif activity_type == 'run' and item.peloton_run_url and item.peloton_run_url.strip():
                            peloton_url = item.peloton_run_url
                        elif activity_type == 'yoga' and item.peloton_yoga_url and item.peloton_yoga_url.strip():
                            peloton_url = item.peloton_yoga_url
                        elif activity_type == 'strength' and item.peloton_strength_url and item.peloton_strength_url.strip():
                            peloton_url = item.peloton_strength_url
                        
                        if peloton_url:
                            all_alternatives.append({
                                'item': item,
                                'peloton_url': peloton_url,
                                'activity_type': activity_type,
                                'done': item_done,
                            })
        
        if all_alternatives:
            day_completed = any(alt['done'] for alt in all_alternatives)
            workout_days.append({
                'day_number': workout_day_num,
                'points': day_points,
                'completed': day_completed,
                'alternatives': all_alternatives,
                'focus': day_focus or "Workout",
            })
    
    # Build days structure (for backward compatibility)
    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    days = []
    current_day = None
    current_focus = ""
    current_items = []
    
    show_only_peloton_items = plan.challenge_instance and not plan.challenge_instance.include_kegels
    
    for item in items:
        if current_day is None:
            current_day = item.day_of_week
            current_focus = item.peloton_focus
            current_items = [item]
            continue
        
        if item.day_of_week == current_day:
            current_items.append(item)
        else:
            first_item = current_items[0] if current_items else None
            focus_lower = current_focus.lower() if current_focus else ""
            
            has_ride = "pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or "ride" in focus_lower
            has_run = "run" in focus_lower
            has_yoga = "yoga" in focus_lower
            has_strength = "strength" in focus_lower
            
            if show_only_peloton_items:
                day_exercise_points = 0
            else:
                day_exercise_points = sum(1 for item in current_items if item.is_done) * 10
            day_activity_points = 0
            if first_item:
                if first_item.ride_done:
                    day_activity_points += 50
                if first_item.run_done:
                    day_activity_points += 50
                if first_item.yoga_done:
                    day_activity_points += 50
                if first_item.strength_done:
                    day_activity_points += 50
            
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
            
            if show_only_peloton_items:
                current_items = [item for item in current_items if (
                    item.peloton_ride_url or item.peloton_run_url or 
                    item.peloton_yoga_url or item.peloton_strength_url
                )]
                first_item = current_items[0] if current_items else None
            
            days.append({
                "dow": current_day,
                "label": day_labels[current_day],
                "focus": current_focus,
                "items": current_items,
                "first_item": first_item,
                "ride_done": first_item.ride_done if first_item else False,
                "run_done": first_item.run_done if first_item else False,
                "yoga_done": first_item.yoga_done if first_item else False,
                "strength_done": first_item.strength_done if first_item else False,
                "has_ride": has_ride,
                "has_run": has_run,
                "has_yoga": has_yoga,
                "has_strength": has_strength,
                "peloton_url": peloton_url,
                "peloton_activity_type": peloton_activity_type,
                "peloton_done": peloton_done,
                "day_points": day_activity_points,
                "is_completed": all_activities_done,
            })
            current_day = item.day_of_week
            current_focus = item.peloton_focus
            current_items = [item]
    
    if current_day is not None:
        first_item = current_items[0] if current_items else None
        focus_lower = current_focus.lower() if current_focus else ""
        
        has_ride = "pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or "ride" in focus_lower
        has_run = "run" in focus_lower
        has_yoga = "yoga" in focus_lower
        has_strength = "strength" in focus_lower
        
        day_exercise_points = 0
        day_activity_points = 0
        
        if first_item:
            day_items = plan.items.filter(day_of_week=current_day)
            has_ride = day_items.filter(ride_done=True).exists()
            has_run = day_items.filter(run_done=True).exists()
            has_yoga = day_items.filter(yoga_done=True).exists()
            has_strength = day_items.filter(strength_done=True).exists()
            
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
                    if has_ride or has_run or has_yoga or has_strength:
                        day_activity_points = 50
                elif core_count == 4:
                    if has_ride or has_run or has_yoga or has_strength:
                        if workout_day_num == 1 or workout_day_num == core_count:
                            day_activity_points = 50
                        else:
                            day_activity_points = 25
                else:
                    if has_ride or has_run or has_yoga or has_strength:
                        day_activity_points = 50
        
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
        
        if show_only_peloton_items:
            current_items = [item for item in current_items if (
                item.peloton_ride_url or item.peloton_run_url or 
                item.peloton_yoga_url or item.peloton_strength_url
            )]
            first_item = current_items[0] if current_items else None
        
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
            "first_item": first_item,
            "ride_done": first_item.ride_done if first_item else False,
            "run_done": first_item.run_done if first_item else False,
            "yoga_done": first_item.yoga_done if first_item else False,
            "strength_done": first_item.strength_done if first_item else False,
            "has_ride": has_ride,
            "has_run": has_run,
            "has_yoga": has_yoga,
            "has_strength": has_strength,
            "peloton_url": peloton_url,
            "peloton_activity_type": peloton_activity_type,
            "peloton_done": peloton_done,
            "day_points": day_activity_points,
            "is_completed": all_activities_done,
        })
    
    # Check if user can leave challenge
    can_leave = None
    leave_error = None
    if plan.challenge_instance:
        can_leave, leave_error = plan.challenge_instance.can_leave_challenge()
    
    context = {
        "plan": plan,
        "days": days,
        "workout_days": workout_days,
        "core_count": core_count,
        "week_number": actual_week_number,
        "total_weeks": total_weeks,
        "can_access_week": can_access_week,
        "previous_week_completed": previous_week_completed,
        "next_week_plan": next_week_plan,
        "previous_week_plan": previous_week_plan,
        "can_leave": can_leave,
        "leave_error": leave_error,
        "include_kegels": plan.challenge_instance.include_kegels if plan.challenge_instance else True,
        "bonus_workouts": bonus_workouts,
        "bonus_completed": bonus_completed,
        "challenge": challenge,
        "challenge_structure": challenge_structure,
        "is_challenge_view": True,  # Flag to indicate this is challenge-based view
    }
    return render(request, "tracker/plan_detail.html", context)

@login_required
def toggle_done(request, pk):
    item = get_object_or_404(DailyPlanItem, pk=pk, weekly_plan__user=request.user)
    plan = item.weekly_plan
    
    # Check if week is locked (for active challenges only, not past challenges)
    if plan.challenge_instance:
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
        # Get all other workout items on the same day (excluding bonus workouts)
        from django.db.models import Q
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