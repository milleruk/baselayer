from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from plans.models import PlanTemplate
from plans.services import generate_weekly_plan
from tracker.models import WeeklyPlan
from .models import Challenge, ChallengeInstance, Team, TeamMember, TeamLeaderboard, TeamLeaderVolunteer
from core.services import DateRangeService

User = get_user_model()


def sunday_of_current_week(d: date) -> date:
    """Get the Sunday of the current week (week starts on Sunday).
    
    DEPRECATED: Use DateRangeService.sunday_of_current_week() instead.
    This wrapper is kept for backward compatibility.
    """
    return DateRangeService.sunday_of_current_week(d)


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
    
    # If POST, save template selection and redirect to team selection
    if request.method == "POST":
        template_id = request.POST.get("template_id")
        if not template_id:
            messages.error(request, "Please select a plan template.")
            return render(request, "challenges/select_challenge_template.html", {
                "challenge": challenge,
                "templates": templates,
                "existing_current_week_plan": existing_current_week_plan,
            })
        
        # Store template selection in session
        request.session[f'challenge_{challenge_id}_template_id'] = template_id
        request.session[f'challenge_{challenge_id}_include_kegels'] = request.POST.get("include_kegels") == "on"
        request.session[f'challenge_{challenge_id}_delete_existing_plan'] = request.POST.get("delete_existing_plan") == "true"
        
        # For team challenges, redirect to team selection; otherwise go directly to join
        if challenge.challenge_type == "team":
            return redirect("challenges:select_team", challenge_id=challenge_id)
        else:
            # For non-team challenges, skip team selection and go directly to join
            request.session[f'challenge_{challenge_id}_team_option'] = None
            return redirect("challenges:join_challenge", challenge_id=challenge_id)
    
    return render(request, "challenges/select_challenge_template.html", {
        "challenge": challenge,
        "templates": templates,
        "existing_current_week_plan": existing_current_week_plan,
    })


@login_required
def select_team(request, challenge_id):
    """Select team when joining a challenge"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Check if signup is allowed
    if not challenge.can_signup:
        messages.error(request, f"Signup for '{challenge.name}' is no longer available.")
        return redirect("challenges:challenges_list")
    
    # Check if template was selected (should be in session)
    template_id = request.session.get(f'challenge_{challenge_id}_template_id')
    if not template_id:
        messages.error(request, "Please select a plan template first.")
        return redirect("challenges:select_challenge_template", challenge_id=challenge_id)
    
    # Get all teams with member counts for this challenge
    teams = Team.objects.annotate(
        member_count=Count('members', filter=Q(members__challenge_instance__challenge=challenge, members__challenge_instance__is_active=True))
    ).order_by('name')
    
    # Get user's previous team (if they were in a team for a previous challenge)
    previous_team = None
    previous_team_membership = TeamMember.objects.filter(
        challenge_instance__user=request.user
    ).exclude(
        challenge_instance__challenge=challenge
    ).select_related('team', 'challenge_instance__challenge').order_by('-joined_at').first()
    
    if previous_team_membership:
        previous_team = previous_team_membership.team
    
    # Handle POST - team selection
    if request.method == "POST":
        team_option = request.POST.get("team_option")
        team_id = request.POST.get("team_id")
        team_name = request.POST.get("team_name", "").strip()
        
        if not team_option:
            messages.error(request, "Please select a team option.")
            return render(request, "challenges/select_team.html", {
                "challenge": challenge,
                "teams": teams,
                "previous_team": previous_team,
            })
        
        # Store team selection in session
        request.session[f'challenge_{challenge_id}_team_option'] = team_option
        request.session[f'challenge_{challenge_id}_team_id'] = team_id
        request.session[f'challenge_{challenge_id}_team_name'] = team_name
        request.session[f'challenge_{challenge_id}_volunteer_team_lead'] = request.POST.get("volunteer_team_lead") == "on"
        
        # Redirect to join_challenge to process everything
        return redirect("challenges:join_challenge", challenge_id=challenge_id)
    
    return render(request, "challenges/select_team.html", {
        "challenge": challenge,
        "teams": teams,
        "previous_team": previous_team,
    })


@login_required
def join_challenge(request, challenge_id):
    """Join a challenge and auto-generate weekly plans"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Check if signup is allowed
    if not challenge.can_signup:
        messages.error(request, f"Signup for '{challenge.name}' is no longer available.")
        return redirect("challenges:challenges_list")
    
    # Get template and team info from session
    template_id = request.session.get(f'challenge_{challenge_id}_template_id')
    include_kegels = request.session.get(f'challenge_{challenge_id}_include_kegels', True)
    delete_existing_plan = request.session.get(f'challenge_{challenge_id}_delete_existing_plan', False)
    team_option = request.session.get(f'challenge_{challenge_id}_team_option')
    team_id = request.session.get(f'challenge_{challenge_id}_team_id')
    team_name = request.session.get(f'challenge_{challenge_id}_team_name', '')
    volunteer_team_lead = request.session.get(f'challenge_{challenge_id}_volunteer_team_lead', False)
    
    # If POST or if we have session data, create challenge instance with selected template and team
    # For team challenges, require team_option; for others, only require template_id
    has_required_data = template_id and (challenge.challenge_type != "team" or team_option)
    if request.method == "POST" or has_required_data:
        # Double-check constraints based on challenge start date
        today = date.today()
        if challenge.start_date <= today:
            # Challenge has started - can only join if no other active challenge
            active_challenge_instance = ChallengeInstance.objects.filter(user=request.user, is_active=True).first()
            if active_challenge_instance and active_challenge_instance.challenge.id != challenge.id:
                messages.error(request, f"You are already actively participating in '{active_challenge_instance.challenge.name}'. Please leave or complete that challenge before joining another active challenge.")
                # Clear session
                for key in list(request.session.keys()):
                    if key.startswith(f'challenge_{challenge_id}_'):
                        del request.session[key]
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
                # Clear session
                for key in list(request.session.keys()):
                    if key.startswith(f'challenge_{challenge_id}_'):
                        del request.session[key]
                return redirect("tracker:weekly_plans")
        
        if not template_id:
            messages.error(request, "Please select a plan template.")
            # Clear session
            for key in list(request.session.keys()):
                if key.startswith(f'challenge_{challenge_id}_'):
                    del request.session[key]
            return redirect("challenges:select_challenge_template", challenge_id=challenge_id)
        
        # Only require team selection for team challenges
        if challenge.challenge_type == "team" and not team_option:
            messages.error(request, "Please select a team option.")
            # Clear session
            for key in list(request.session.keys()):
                if key.startswith(f'challenge_{challenge_id}_'):
                    del request.session[key]
            return redirect("challenges:select_team", challenge_id=challenge_id)
        
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
        
        # Handle team assignment
        team = None
        if team_option == "join_existing":
            if team_id:
                team = get_object_or_404(Team, pk=team_id)
            elif team_name:
                # Try to find team by name
                team = Team.objects.filter(name__iexact=team_name).first()
                if not team:
                    messages.error(request, f"Team '{team_name}' not found. Please select from the list or create a new team.")
                    # Clear session
                    for key in list(request.session.keys()):
                        if key.startswith(f'challenge_{challenge_id}_'):
                            del request.session[key]
                    return redirect("challenges:select_team", challenge_id=challenge_id)
            
        elif team_option == "random":
            # For random assignment, don't assign team yet - admin will do it
            # If user volunteered to be team lead, create volunteer record
            if volunteer_team_lead:
                # Store volunteer info - will be processed after challenge instance is created
                pass
            # Don't assign team yet - admin will handle assignment
            team = None
            messages.info(request, "You'll be assigned to a team by an admin. You can start the challenge now!")
        elif team_option == "previous_team":
            # Get user's previous team
            previous_team_membership = TeamMember.objects.filter(
                challenge_instance__user=request.user
            ).exclude(
                challenge_instance__challenge=challenge
            ).select_related('team').order_by('-joined_at').first()
            
            if previous_team_membership:
                team = previous_team_membership.team
            else:
                # No previous team - treat as random assignment
                team = None
                messages.info(request, "No previous team found. You'll be assigned to a team by an admin.")
        
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
        
        # Assign user to team (if team was selected)
        if team:
            TeamMember.objects.get_or_create(
                team=team,
                challenge_instance=challenge_instance
            )
        
        # Handle volunteer team lead
        if volunteer_team_lead and team_option == "random":
            TeamLeaderVolunteer.objects.get_or_create(
                user=request.user,
                challenge=challenge,
                defaults={
                    'challenge_instance': challenge_instance,
                    'assigned': False
                }
            )
            messages.info(request, "Thank you for volunteering to be a team leader! An admin will assign you to a team soon.")
        
        # Clear session data
        for key in list(request.session.keys()):
            if key.startswith(f'challenge_{challenge_id}_'):
                del request.session[key]
        
        if weeks_generated > 0:
            messages.success(request, f"Joined challenge '{challenge.name}'! Generated {weeks_generated} week(s).")
        else:
            messages.info(request, f"You're already participating in '{challenge.name}'!")
        
        return redirect("tracker:weekly_plans")
    
    # GET request - check if we have session data, otherwise redirect to template selection
    if template_id and team_option:
        # We have session data, process it (will be handled by POST logic above)
        pass
    else:
        # No session data, redirect to template selection
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


@login_required
def team_admin(request, team_id):
    """Team admin page for team leaders to manage their team"""
    team = get_object_or_404(Team, pk=team_id)
    
    # Check if user is the team leader
    if team.leader != request.user and not request.user.is_superuser:
        messages.error(request, "You don't have permission to manage this team.")
        return redirect("challenges:challenges_list")
    
    # Get all active challenge instances for team members
    team_members = TeamMember.objects.filter(team=team, challenge_instance__is_active=True).select_related(
        'challenge_instance__user', 'challenge_instance__challenge'
    ).order_by('challenge_instance__challenge__start_date', 'challenge_instance__user__email')
    
    # Group by challenge
    challenges_data = {}
    for member in team_members:
        challenge = member.challenge_instance.challenge
        if challenge.id not in challenges_data:
            challenges_data[challenge.id] = {
                'challenge': challenge,
                'members': []
            }
        challenges_data[challenge.id]['members'].append({
            'user': member.challenge_instance.user,
            'instance': member.challenge_instance,
            'team_member': member,  # Store the TeamMember instance
            'joined_at': member.joined_at
        })
    
    # Handle POST requests (remove member, change leader, etc.)
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "remove_member":
            member_id = request.POST.get("member_id")
            try:
                member = TeamMember.objects.get(pk=member_id, team=team)
                user_email = member.challenge_instance.user.email
                member.delete()
                messages.success(request, f"Removed {user_email} from the team.")
            except TeamMember.DoesNotExist:
                messages.error(request, "Member not found.")
        
        elif action == "change_leader":
            new_leader_id = request.POST.get("new_leader_id")
            try:
                new_leader = User.objects.get(pk=new_leader_id)
                # Check if new leader is a member of the team
                is_member = TeamMember.objects.filter(
                    team=team,
                    challenge_instance__user=new_leader,
                    challenge_instance__is_active=True
                ).exists()
                
                if is_member:
                    team.leader = new_leader
                    team.save(update_fields=['leader'])
                    messages.success(request, f"Changed team leader to {new_leader.email}.")
                else:
                    messages.error(request, "New leader must be a member of the team.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        
        return redirect("challenges:team_admin", team_id=team_id)
    
    return render(request, "challenges/team_admin.html", {
        "team": team,
        "challenges_data": challenges_data,
        "is_leader": team.leader == request.user,
    })


@login_required
def team_admin_all_users(request):
    """Super user view to see all users across all teams"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this page.")
        return redirect("challenges:challenges_list")
    
    # Get all teams with their members
    teams = Team.objects.annotate(
        total_members=Count('members', filter=Q(members__challenge_instance__is_active=True))
    ).prefetch_related('members__challenge_instance__user', 'members__challenge_instance__challenge').order_by('name')
    
    # Get all users not in any team (for current active challenges)
    active_challenges = Challenge.objects.filter(is_active=True, is_visible=True)
    users_in_teams = set()
    for team in teams:
        for member in team.members.filter(challenge_instance__is_active=True):
            users_in_teams.add(member.challenge_instance.user.id)
    
    users_not_in_teams = User.objects.exclude(id__in=users_in_teams).order_by('email')
    
    return render(request, "challenges/team_admin_all_users.html", {
        "teams": teams,
        "users_not_in_teams": users_not_in_teams,
    })


@login_required
def team_leader_overview(request):
    """Team leader overview page with challenge filter and leaderboard"""
    # Get user's teams where they are leader
    user_teams = Team.objects.filter(leader=request.user)
    
    if not user_teams.exists():
        messages.error(request, "You are not a team leader.")
        return redirect("challenges:challenges_list")
    
    # For now, use the first team (can be extended to support multiple teams)
    team = user_teams.first()
    
    # Get currently running team challenges where team leaders can see user list
    today = date.today()
    from django.db.models import Q
    
    # Get all team challenges with visibility enabled
    all_team_challenges = Challenge.objects.filter(
        challenge_type="team",
        is_active=True,
        team_leaders_can_see_users=True
    ).order_by("-start_date")
    
    # Filter to show challenges that are currently running AND team leaders can see user list
    # The team_leaders_can_see_user_list() method checks if visibility date has passed
    visible_challenges = []
    for challenge in all_team_challenges:
        # Challenge must be currently running (started and not ended)
        # OR if visibility date is set and has passed, show it even if challenge hasn't started
        can_show = False
        if challenge.is_currently_running:
            can_show = True
        elif challenge.team_leaders_see_users_date and today >= challenge.team_leaders_see_users_date:
            # Visibility date has passed, but challenge hasn't started yet - still show it
            can_show = True
        
        if can_show and challenge.team_leaders_can_see_user_list():
            visible_challenges.append(challenge)
    
    active_challenges = visible_challenges
    
    # Get selected challenge from query params
    challenge_id = request.GET.get("challenge_id")
    selected_challenge = None
    if challenge_id:
        # Allow selecting any challenge that matches the ID, even if not in filtered list
        # (in case admin changed settings after page load)
        try:
            challenge = Challenge.objects.get(pk=challenge_id, challenge_type="team", is_active=True)
            if challenge.team_leaders_can_see_user_list() and challenge.is_currently_running:
                selected_challenge = challenge
        except Challenge.DoesNotExist:
            pass
    
    # If no challenge selected, use the most recent running challenge
    if not selected_challenge and active_challenges:
        selected_challenge = active_challenges[0] if active_challenges else None
    
    # Get week number from query params (required - default to week 1 if not provided)
    week_number = request.GET.get("week")
    if week_number:
        try:
            week_number = int(week_number)
        except ValueError:
            week_number = None
    
    # If no week selected and challenge exists, default to week 1
    if selected_challenge and not week_number:
        week_number = 1
    
    # Get leaderboard data
    leaderboard_data = None
    team_members_data = []
    total_member_count = 0
    team_rank = None
    team_score = 0
    
    if selected_challenge:
        # Get all teams participating in this challenge
        participating_teams = Team.objects.filter(
            members__challenge_instance__challenge=selected_challenge,
            members__challenge_instance__is_active=True
        ).distinct()
        
        # Calculate or get leaderboard scores
        leaderboard_entries = []
        for t in participating_teams:
            entry = t.get_leaderboard_entry(selected_challenge, week_number)
            # Recalculate score (in case it's not up to date)
            score = t.calculate_team_score(selected_challenge, week_number)
            entry.total_points = score
            entry.save()
            leaderboard_entries.append({
                'team': t,
                'score': score,
                'entry': entry
            })
        
        # Sort by score descending
        leaderboard_entries.sort(key=lambda x: x['score'], reverse=True)
        
        # Find team's rank
        for idx, entry in enumerate(leaderboard_entries, 1):
            if entry['team'].id == team.id:
                team_rank = idx
                team_score = entry['score']
                break
        
        leaderboard_data = leaderboard_entries
        
        # Get team members for this challenge
        team_members = team.get_members_for_challenge(selected_challenge).select_related(
            'challenge_instance__user',
            'challenge_instance__selected_template'
        )
        
        # Group members by plan template
        members_by_plan = {}
        from tracker.models import WeeklyPlan
        from datetime import timedelta
        from django.utils import timezone
        
        # Calculate week dates (weeks start on Sunday, matching how plans are created)
        challenge_start = selected_challenge.start_date
        challenge_end = selected_challenge.end_date
        # First week starts on the Sunday of the week containing challenge_start
        first_week_start = sunday_of_current_week(challenge_start)
        today = timezone.now().date()
        
        # Get all weeks for this challenge
        total_weeks = selected_challenge.duration_weeks
        all_weeks_data = []
        for week_num in range(1, total_weeks + 1):
            week_start = first_week_start + timedelta(days=(week_num - 1) * 7)
            week_end = week_start + timedelta(days=6)
            if week_start <= challenge_end:  # Only include weeks within challenge period
                all_weeks_data.append({
                    'week_number': week_num,
                    'week_start': week_start,
                    'week_end': week_end
                })
        
        for member in team_members:
            instance = member.challenge_instance
            # Get all weekly plans for this member, ordered by week_start
            all_member_plans = instance.weekly_plans.filter(
                week_start__gte=first_week_start,
                week_start__lte=challenge_end
            ).order_by('week_start')
            
            # Create a dict for quick lookup
            plans_by_week_start = {plan.week_start: plan for plan in all_member_plans}
            
            # Get data for each week
            weeks_status = []
            total_points = 0
            missed_weeks = 0
            
            for week_info in all_weeks_data:
                week_plan = plans_by_week_start.get(week_info['week_start'])
                week_start = week_info['week_start']
                week_end = week_info['week_end']
                
                # Check if week is completed
                # A week is completed if all days with assigned workouts have at least one completed activity
                # (not counting total activities, but days - some days can have 2 activities but only need 1)
                is_completed = False
                if week_plan:
                    # Check if all days with workouts have at least one completed activity
                    core_count = week_plan.core_workout_count  # Days with workouts assigned
                    completed_core_count = week_plan.completed_core_workouts  # Days with at least one completed workout
                    # Week is completed if all days with workouts are completed, or if completed_at is set
                    is_completed = (core_count > 0 and completed_core_count >= core_count) or bool(week_plan.completed_at)
                    total_points += week_plan.total_points
                else:
                    missed_weeks += 1
                
                # Check bonus workout status (only for weeks that have started)
                bonus_done = False
                week_has_started = week_start <= today
                if week_plan and week_has_started:
                    bonus_done = week_plan.bonus_workout_done or (week_plan.bonus_points > 0)
                
                # Calculate remaining days for current/upcoming weeks
                days_remaining = 0
                if week_end < today:
                    days_remaining = 0  # Week is over
                elif week_start > today:
                    days_remaining = 7  # Week hasn't started
                else:
                    days_remaining = max(0, (week_end - today).days + 1)  # Current week
                
                weeks_status.append({
                    'week_number': week_info['week_number'],
                    'is_completed': is_completed,
                    'bonus_done': bonus_done,
                    'days_remaining': days_remaining,
                    'week_plan': week_plan,
                    'points': week_plan.total_points if week_plan else 0,
                    'week_has_started': week_has_started
                })
            
            # Get plan template name (or "No Plan" if None)
            plan_name = instance.selected_template.name if instance.selected_template else "No Plan"
            
            if plan_name not in members_by_plan:
                members_by_plan[plan_name] = {
                    'plan': instance.selected_template,
                    'members': [],
                    'subtotal': 0
                }
            
            # Count missed items for the selected week only (week not completed + bonus not done)
            missed_items = 0
            for week in weeks_status:
                if week['week_number'] == week_number and week['week_has_started']:
                    if not week['is_completed']:
                        missed_items += 1
                    if not week['bonus_done']:
                        missed_items += 1
            
            member_data = {
                'user': instance.user,
                'instance': instance,
                'total_score': total_points,
                'is_scoring': instance.is_scoring,
                'weeks_status': weeks_status,
                'missed_weeks': missed_weeks,
                'missed_items': missed_items
            }
            members_by_plan[plan_name]['members'].append(member_data)
            members_by_plan[plan_name]['subtotal'] += total_points
        
        # Sort members within each plan by score, then sort plans by subtotal
        for plan_name in members_by_plan:
            members_by_plan[plan_name]['members'].sort(key=lambda x: x['total_score'], reverse=True)
        
        # Convert to list of groups, sorted by subtotal (descending)
        team_members_data = sorted(
            members_by_plan.items(),
            key=lambda x: x[1]['subtotal'],
            reverse=True
        )
        
        # Calculate total member count
        total_member_count = sum(len(plan_data['members']) for _, plan_data in team_members_data)
    
    # Check if team leaders can see user list (must be enabled and challenge must have started)
    can_see_users = False
    all_users_data = []
    if selected_challenge and selected_challenge.team_leaders_can_see_users and selected_challenge.team_leaders_can_see_user_list():
        can_see_users = True
        # Get all users participating in this challenge (for team leaders to see)
        all_instances = ChallengeInstance.objects.filter(
            challenge=selected_challenge,
            is_active=True
        ).select_related('user').order_by('user__email')
        
        for instance in all_instances:
            # Get user's team if they have one (OneToOneField returns object directly, not queryset)
            # OneToOneField raises RelatedObjectDoesNotExist if not found, which we catch
            try:
                team_membership = instance.team_membership
                team_name = team_membership.team.name
            except TeamMember.DoesNotExist:
                team_name = "No team"
            
            if week_number:
                # Get score for specific week
                from tracker.models import WeeklyPlan
                from datetime import timedelta
                challenge_start = selected_challenge.start_date
                week_start = challenge_start + timedelta(days=(week_number - 1) * 7)
                week_plan = instance.weekly_plans.filter(week_start=week_start).first()
                user_score = week_plan.total_points if week_plan else 0
            else:
                user_score = instance.total_points
            
            all_users_data.append({
                'user': instance.user,
                'instance': instance,
                'team_name': team_name,
                'score': user_score,
                'is_scoring': instance.is_scoring
            })
        
        # Sort by score
        all_users_data.sort(key=lambda x: x['score'], reverse=True)
    
    return render(request, "challenges/team_leader_overview.html", {
        "team": team,
        "active_challenges": active_challenges,
        "selected_challenge": selected_challenge,
        "week_number": week_number,
        "leaderboard_data": leaderboard_data,
        "team_members_data": team_members_data,
        "total_member_count": total_member_count if selected_challenge else 0,
        "team_rank": team_rank,
        "team_score": team_score,
        "can_see_users": can_see_users,
        "all_users_data": all_users_data,
    })
