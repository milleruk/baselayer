from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from plans.models import PlanTemplate
from plans.services import generate_weekly_plan
from tracker.models import WeeklyPlan
from .models import Challenge, ChallengeInstance


def sunday_of_current_week(d: date) -> date:
    """Get the Sunday of the current week (week starts on Sunday)"""
    # weekday() returns 0=Monday, 6=Sunday
    # We want Sunday to be day 0, so we adjust
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)


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
    
    return render(request, "challenges/challenges.html", {
        "upcoming_challenges": upcoming_challenges,
        "running_challenges": running_challenges,
        "past_challenges": past_challenges,
        "user_challenge_ids": user_challenge_ids,
        "active_challenge_id": active_challenge_id,
        "user_challenge_instances": user_challenge_instances,
    })


@login_required
def select_challenge_template(request, challenge_id):
    """Select plan template when joining a challenge"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Check if signup is allowed
    if not challenge.can_signup:
        messages.error(request, f"Signup for '{challenge.name}' is no longer available.")
        return redirect("challenges:challenges_list")
    
    # For future challenges: allow signup even if user has other future challenges
    # For active/running challenges: check if user already has an active challenge
    today = date.today()
    if challenge.start_date <= today:
        # Challenge has started - check if user already has an active challenge
        active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
        if active_challenge_instance:
            if active_challenge_instance.challenge.id != challenge.id:
                messages.error(request, f"You are already actively participating in '{active_challenge_instance.challenge.name}'. Please leave or complete that challenge before joining another active challenge.")
                return redirect("challenges:challenges_list")
            else:
                # User is trying to select template for the same challenge they're already in
                messages.info(request, f"You're already participating in '{challenge.name}'")
                return redirect("tracker:weekly_plans")
    else:
        # Future challenge - allow signup even if user has other future challenges
        # But check if they're already signed up for this specific challenge
        existing_instance = ChallengeInstance.objects.filter(
            user=request.user, 
            challenge=challenge,
            is_active=True
        ).first()
        if existing_instance:
            messages.info(request, f"You're already signed up for '{challenge.name}'")
            return redirect("tracker:weekly_plans")
    
    # Check if user has a plan for the current week
    current_week_start = sunday_of_current_week(date.today())
    existing_current_week_plan = WeeklyPlan.objects.filter(user=request.user, week_start=current_week_start).first()
    
    # Filter templates based on challenge categories
    categories = [cat.strip().lower() for cat in challenge.categories.split(",") if cat.strip()]
    all_templates = PlanTemplate.objects.all()
    matching_templates = set()  # Use set to avoid duplicates
    
    # Filter templates based on categories
    for template in all_templates:
        template_name_lower = template.name.lower()
        should_include = False
        
        # Check if template matches any category
        if "cycling" in categories:
            if "ride" in template_name_lower or "2 runs 2 rides" in template_name_lower:
                should_include = True
        if "running" in categories:
            if "run" in template_name_lower or "2 runs 2 rides" in template_name_lower:
                should_include = True
        if "strength" in categories:
            if "strength" in template_name_lower:
                should_include = True
            # Also include "Just Kegels" for strength challenges
            if "just kegels" in template_name_lower:
                should_include = True
        if "yoga" in categories:
            if "yoga" in template_name_lower:
                should_include = True
            # Also include "Just Kegels" for yoga challenges
            if "just kegels" in template_name_lower:
                should_include = True
        
        # Always include the default template if set
        if challenge.default_template and template == challenge.default_template:
            should_include = True
        
        if should_include:
            matching_templates.add(template)
    
    # If no templates matched categories, use available_templates or fallback to all
    if not matching_templates:
        if challenge.available_templates.exists():
            templates = challenge.available_templates.all().order_by("name")
        else:
            # Fallback: show all templates if none are specified (backward compatibility)
            templates = all_templates.order_by("name")
    else:
        templates = list(matching_templates)
    
    # Order templates and prioritize default template
    templates = sorted(templates, key=lambda t: t.name)
    if challenge.default_template and challenge.default_template in templates:
        templates = list(templates)
        templates.remove(challenge.default_template)
        templates.insert(0, challenge.default_template)
    
    return render(request, "challenges/select_challenge_template.html", {
        "challenge": challenge,
        "templates": templates,
        "existing_current_week_plan": existing_current_week_plan,
    })


@login_required
def join_challenge(request, challenge_id):
    """Join a challenge and auto-generate weekly plans"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Check if signup is allowed
    if not challenge.can_signup:
        messages.error(request, f"Signup for '{challenge.name}' is no longer available.")
        return redirect("challenges:challenges_list")
    
    # For future challenges: allow signup even if user has other future challenges
    # For active/running challenges: check if user already has an active challenge
    today = date.today()
    if challenge.start_date <= today:
        # Challenge has started - check if user already has an active challenge
        active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
        if active_challenge_instance:
            if active_challenge_instance.challenge.id != challenge.id:
                messages.error(request, f"You are already actively participating in '{active_challenge_instance.challenge.name}'. Please leave or complete that challenge before joining another active challenge.")
                return redirect("challenges:challenges_list")
            else:
                # User is trying to join the same challenge they're already in
                messages.info(request, f"You're already participating in '{challenge.name}'")
                return redirect("tracker:weekly_plans")
    else:
        # Future challenge - allow signup even if user has other future challenges
        # But check if they're already signed up for this specific challenge
        existing_instance = ChallengeInstance.objects.filter(
            user=request.user, 
            challenge=challenge,
            is_active=True
        ).first()
        if existing_instance:
            messages.info(request, f"You're already signed up for '{challenge.name}'")
            return redirect("tracker:weekly_plans")
    
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
        # Double-check constraints based on challenge start date
        today = date.today()
        if challenge.start_date <= today:
            # Challenge has started - can only join if no other active challenge
            active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
            if active_challenge_instance and active_challenge_instance.challenge.id != challenge.id:
                messages.error(request, f"You are already actively participating in '{active_challenge_instance.challenge.name}'. Please leave or complete that challenge before joining another active challenge.")
                return redirect("challenges:challenges_list")
        else:
            # Future challenge - allow multiple signups, but check if already signed up for this one
            existing_instance = ChallengeInstance.objects.filter(
                user=request.user, 
                challenge=challenge,
                is_active=True
            ).first()
            if existing_instance:
                messages.info(request, f"You're already signed up for '{challenge.name}'")
                return redirect("tracker:weekly_plans")
        
        template_id = request.POST.get("template_id")
        delete_existing_plan = request.POST.get("delete_existing_plan") == "true"
        
        if not template_id:
            messages.error(request, "Please select a plan template.")
            return redirect("challenges:select_challenge_template", challenge_id=challenge_id)
        
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
                return redirect("challenges:select_challenge_template", challenge_id=challenge_id)
        
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
    return redirect("challenges:select_challenge_template", challenge_id=challenge_id)


@login_required
def complete_challenge(request, challenge_instance_id):
    """Mark a challenge instance as completed"""
    challenge_instance = get_object_or_404(ChallengeInstance, pk=challenge_instance_id, user=request.user)
    
    # Only allow completion if user owns this instance
    if challenge_instance.user != request.user:
        messages.error(request, "You don't have permission to complete this challenge.")
        return redirect("tracker:weekly_plans")
    
    # For past challenges, require all weeks to be completed
    if challenge_instance.challenge.has_ended:
        if not challenge_instance.all_weeks_completed:
            messages.warning(request, f"Please complete all weeks of '{challenge_instance.challenge.name}' before marking it as completed.")
            return redirect("tracker:weekly_plans")
    
    if request.method == "POST":
        challenge_instance.is_active = False
        challenge_instance.completed_at = timezone.now()
        challenge_instance.save(update_fields=["is_active", "completed_at"])
        
        completion_rate = challenge_instance.completion_rate
        messages.success(
            request, 
            f"🎉 Challenge '{challenge_instance.challenge.name}' completed! "
            f"Total points: {challenge_instance.total_points} | "
            f"Completion rate: {completion_rate:.1f}%"
        )
        return redirect("tracker:weekly_plans")
    
    # GET request - show confirmation or redirect
    return redirect("tracker:weekly_plans")


@login_required
def retake_challenge(request, challenge_id):
    """Retake a completed challenge - creates a new instance"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Check if user already has an active instance for this challenge
    active_instance = ChallengeInstance.objects.filter(
        user=request.user,
        challenge=challenge,
        is_active=True
    ).first()
    
    if active_instance:
        messages.info(request, f"You're already participating in '{challenge.name}'. Complete or leave the current attempt first.")
        return redirect("tracker:weekly_plans")
    
    # Check if challenge can be retaken (past challenges can always be retaken)
    if not challenge.has_ended and not challenge.can_signup:
        messages.error(request, f"Cannot retake '{challenge.name}' - challenge is currently running and signup is closed.")
        return redirect("challenges:challenges_list")
    
    # Get the most recent completed instance to use as a template
    previous_instances = ChallengeInstance.objects.filter(
        user=request.user,
        challenge=challenge
    ).order_by('-completed_at', '-started_at')
    
    last_completed = previous_instances.filter(completed_at__isnull=False).first()
    last_any = previous_instances.first()  # Get any previous instance (even if not completed)
    
    # If user has a previous instance, use their last template choice
    # Otherwise, redirect to template selection
    template = None
    include_kegels = True
    
    if last_completed and last_completed.selected_template:
        template = last_completed.selected_template
        include_kegels = last_completed.include_kegels
    elif last_any and last_any.selected_template:
        template = last_any.selected_template
        include_kegels = last_any.include_kegels
    elif challenge.default_template:
        template = challenge.default_template
    elif challenge.available_templates.exists():
        template = challenge.available_templates.first()
    
    if template:
        # Create new challenge instance
        new_instance = ChallengeInstance.objects.create(
            user=request.user,
            challenge=challenge,
            selected_template=template,
            include_kegels=include_kegels,
            is_active=True
        )
        
        messages.success(request, f"Retaking '{challenge.name}' with template '{template.name}'. Generating weekly plans...")
        
        # Generate weekly plans (same logic as join_challenge)
        today = date.today()
        challenge_start = challenge.start_date
        challenge_end = challenge.end_date
        
        # For past challenges (retaking), generate all weeks from challenge start
        # For current/upcoming challenges, generate from current week or challenge start
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
            
            # Always generate fresh plans for retake
            weekly = generate_weekly_plan(
                user=request.user,
                week_start=current_week_start,
                template=template,
                start_from_today=(use_start_from_today and current_week_start == sunday_of_current_week(today)),
                challenge_instance=new_instance,
                week_number=week_num
            )
            weekly.challenge_instance = new_instance
            weekly.save(update_fields=["challenge_instance"])
            weeks_generated += 1
            
            current_week_start += timedelta(days=7)
            use_start_from_today = False  # Only for first week
        
        if weeks_generated > 0:
            messages.success(request, f"Retaking '{challenge.name}'! Generated {weeks_generated} week(s).")
        else:
            messages.info(request, f"Retaking '{challenge.name}'!")
        
        return redirect("tracker:weekly_plans")
    else:
        # No template available, redirect to template selection
        return redirect("challenges:select_challenge_template", challenge_id=challenge_id)


@login_required
def hide_completed_challenge(request, challenge_instance_id):
    """Hide a completed challenge from the plan tracker by setting it to inactive without completed_at"""
    challenge_instance = get_object_or_404(ChallengeInstance, pk=challenge_instance_id, user=request.user)
    
    # Only allow hiding completed challenges
    if not challenge_instance.completed_at:
        messages.warning(request, "Only completed challenges can be hidden.")
        return redirect("tracker:weekly_plans")
    
    if request.method == "POST":
        # Clear completed_at to hide it from the plan tracker
        # This way it won't show in the list (since we filter by completed_at)
        challenge_name = challenge_instance.challenge.name
        challenge_instance.completed_at = None
        challenge_instance.is_active = False
        challenge_instance.save(update_fields=["completed_at", "is_active"])
        messages.success(request, f"'{challenge_name}' has been hidden from your plan tracker.")
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
        return redirect("challenges:challenges_list")
    
    if request.method == "POST":
        challenge_name = challenge_instance.challenge.name
        # Set as inactive but don't mark as completed (they're leaving, not completing)
        challenge_instance.is_active = False
        challenge_instance.completed_at = None
        challenge_instance.save(update_fields=["is_active", "completed_at"])
        messages.success(request, f"You have left the challenge '{challenge_name}'. You can join another challenge or generate standalone plans.")
        return redirect("challenges:challenges_list")
    
    # Show confirmation page
    return render(request, "challenges/leave_challenge.html", {
        "challenge_instance": challenge_instance,
        "can_leave": can_leave,
        "error_msg": error_msg,
    })


@login_required
def challenge_detail(request, challenge_id, week_number=None):
    """View challenge plan by challenge ID and optional week number - renders plan_detail template directly"""
    from tracker.models import WeeklyPlan
    from tracker.views import plan_detail as tracker_plan_detail
    
    # Get the challenge
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Get user's challenge instance for this challenge
    challenge_instance = ChallengeInstance.objects.filter(
        user=request.user,
        challenge=challenge
    ).first()
    
    if not challenge_instance:
        messages.error(request, "You are not participating in this challenge.")
        return redirect("challenges:challenges_list")
    
    # Get all weekly plans for this challenge instance, ordered by week_start
    all_plans = challenge_instance.weekly_plans.all().order_by("week_start")
    total_weeks = all_plans.count()
    
    if total_weeks == 0:
        messages.error(request, "No weekly plans found for this challenge.")
        return redirect("challenges:challenges_list")
    
    # Determine which week to show
    if week_number is not None:
        # Get the plan for the specified week number (1-indexed)
        if week_number < 1 or week_number > total_weeks:
            messages.error(request, f"Invalid week number. This challenge has {total_weeks} week(s).")
            return redirect("challenges:challenge_detail", challenge_id=challenge_id)
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
    
    # Instead of redirecting, call the plan_detail view directly with the plan ID
    # This keeps the URL as /challenges/55/week/1/ instead of redirecting to /tracker/17/
    # The plan_detail view accepts pk as a parameter, so we can call it directly
    return tracker_plan_detail(request, pk=plan.id)
