from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from django.http import JsonResponse
from datetime import date
from .models import Challenge, ChallengeInstance, ChallengeWorkoutAssignment, ChallengeWeekUnlock, ChallengeBonusWorkout, Team, TeamMember, TeamLeaderVolunteer
from .utils import extract_class_id
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.services.ride_detail import get_or_check_ride_detail, queue_missing_rides

User = get_user_model()
from plans.models import PlanTemplate

def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_admin, login_url='/')
def admin_challenges_list(request):
    """List all challenges for admin management"""
    challenges = Challenge.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        challenges = challenges.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(categories__icontains=search_query)
        )
    
    # Filter by status if requested
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        challenges = challenges.filter(is_active=True, end_date__gte=date.today())
    elif status_filter == 'upcoming':
        challenges = challenges.filter(is_active=True, start_date__gt=date.today())
    elif status_filter == 'running':
        challenges = challenges.filter(is_active=True, start_date__lte=date.today(), end_date__gte=date.today())
    elif status_filter == 'past':
        challenges = challenges.filter(end_date__lt=date.today())
    elif status_filter == 'inactive':
        challenges = challenges.filter(is_active=False)
    
    # Sort functionality
    sort_by = request.GET.get('sort', 'start_date')
    if sort_by == 'name':
        challenges = challenges.order_by('name')
    elif sort_by == 'created':
        challenges = challenges.order_by('-created_at')
    elif sort_by == 'participants':
        # Annotate with participant count and sort
        challenges = challenges.annotate(participant_count=Count('instances')).order_by('-participant_count')
    else:  # default: start_date
        challenges = challenges.order_by("start_date", "created_at")
    
    # Get participant counts for each challenge
    challenge_data = []
    for challenge in challenges:
        participant_count = ChallengeInstance.objects.filter(challenge=challenge).count()
        active_participants = ChallengeInstance.objects.filter(challenge=challenge, is_active=True).count()
        challenge_data.append({
            'challenge': challenge,
            'participant_count': participant_count,
            'active_participants': active_participants,
        })
    
    # Calculate stats
    total_challenges = Challenge.objects.count()
    active_challenges = Challenge.objects.filter(is_active=True, end_date__gte=date.today()).count()
    running_challenges = Challenge.objects.filter(is_active=True, start_date__lte=date.today(), end_date__gte=date.today()).count()
    total_participants = ChallengeInstance.objects.count()
    
    return render(request, "challenges/admin/challenges_list.html", {
        "challenge_data": challenge_data,
        "status_filter": status_filter,
        "search_query": search_query,
        "sort_by": sort_by,
        "total_challenges": total_challenges,
        "active_challenges": active_challenges,
        "running_challenges": running_challenges,
        "total_participants": total_participants,
    })

@login_required
@user_passes_test(is_admin, login_url='/')
def admin_challenge_create(request):
    """Create a new challenge"""
    templates = PlanTemplate.objects.all().order_by("name")
    
    if request.method == "POST":
        try:
            challenge = Challenge()
            challenge.name = request.POST.get("name")
            challenge.description = request.POST.get("description", "")
            challenge.start_date = request.POST.get("start_date")
            challenge.end_date = request.POST.get("end_date")
            challenge.signup_opens_date = request.POST.get("signup_opens_date") or None
            challenge.signup_deadline = request.POST.get("signup_deadline") or None
            challenge.is_active = request.POST.get("is_active") == "on"
            challenge.is_visible = request.POST.get("is_visible") == "on"
            challenge.team_leaders_can_see_users = request.POST.get("team_leaders_can_see_users") == "on"
            team_leaders_see_users_date_str = request.POST.get("team_leaders_see_users_date", "").strip()
            challenge.team_leaders_see_users_date = None
            if team_leaders_see_users_date_str:
                try:
                    from datetime import datetime
                    challenge.team_leaders_see_users_date = datetime.strptime(team_leaders_see_users_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            challenge.challenge_type = request.POST.get("challenge_type", "mini")
            challenge.categories = request.POST.get("categories", "")
            
            # Validate and save first (needed for ManyToMany)
            challenge.full_clean()
            challenge.save()
            
            # Handle image upload (after initial save)
            if "image" in request.FILES:
                challenge.image = request.FILES["image"]
                challenge.save(update_fields=['image'])
            
            # Set available templates
            template_ids = request.POST.getlist("available_templates")
            if template_ids:
                challenge.available_templates.set(template_ids)
            else:
                # If no templates selected, clear them
                challenge.available_templates.clear()
            
            # Set default template
            default_template_id = request.POST.get("default_template")
            if default_template_id:
                challenge.default_template_id = default_template_id
            else:
                challenge.default_template = None
            challenge.save()
            
            messages.success(request, f"Challenge '{challenge.name}' created successfully! Now assign Peloton workouts.")
            return redirect("challenges:admin_assign_workouts", challenge_id=challenge.id)
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        except Exception as e:
            messages.error(request, f"Error creating challenge: {str(e)}")
    
    return render(request, "challenges/admin/challenge_form.html", {
        "challenge": None,
        "templates": templates,
        "form_action": "create",
    })

@login_required
@user_passes_test(is_admin, login_url='/')
def admin_challenge_edit(request, challenge_id):
    """Edit an existing challenge"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    templates = PlanTemplate.objects.all().order_by("name")
    
    if request.method == "POST":
        try:
            challenge.name = request.POST.get("name")
            challenge.description = request.POST.get("description", "")
            challenge.start_date = request.POST.get("start_date")
            challenge.end_date = request.POST.get("end_date")
            challenge.signup_opens_date = request.POST.get("signup_opens_date") or None
            challenge.signup_deadline = request.POST.get("signup_deadline") or None
            challenge.is_active = request.POST.get("is_active") == "on"
            challenge.is_visible = request.POST.get("is_visible") == "on"
            challenge.team_leaders_can_see_users = request.POST.get("team_leaders_can_see_users") == "on"
            team_leaders_see_users_date_str = request.POST.get("team_leaders_see_users_date", "").strip()
            challenge.team_leaders_see_users_date = None
            if team_leaders_see_users_date_str:
                try:
                    from datetime import datetime
                    challenge.team_leaders_see_users_date = datetime.strptime(team_leaders_see_users_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            challenge.challenge_type = request.POST.get("challenge_type", "mini")
            challenge.categories = request.POST.get("categories", "")
            
            # Validate and save first
            challenge.full_clean()
            challenge.save()
            
            # Handle image upload (after initial save)
            if "image" in request.FILES:
                challenge.image = request.FILES["image"]
                challenge.save(update_fields=['image'])
            
            # Set available templates
            template_ids = request.POST.getlist("available_templates")
            if template_ids:
                challenge.available_templates.set(template_ids)
            else:
                # If no templates selected, clear them
                challenge.available_templates.clear()
            
            # Set default template
            default_template_id = request.POST.get("default_template")
            if default_template_id:
                challenge.default_template_id = default_template_id
            else:
                challenge.default_template = None
            challenge.save()
            
            # Handle week unlocks
            for week_num in challenge.week_range:
                is_unlocked = request.POST.get(f"week_unlocked_{week_num}") == "1"
                unlock_date_str = request.POST.get(f"week_unlock_date_{week_num}", "").strip()
                unlock_date = None
                if unlock_date_str:
                    try:
                        from datetime import datetime
                        unlock_date = datetime.strptime(unlock_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                
                ChallengeWeekUnlock.objects.update_or_create(
                    challenge=challenge,
                    week_number=week_num,
                    defaults={
                        "is_unlocked": is_unlocked,
                        "unlock_date": unlock_date,
                    }
                )
            
            messages.success(request, f"Challenge '{challenge.name}' updated successfully!")
            return redirect("challenges:admin_challenges_list")
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        except Exception as e:
            messages.error(request, f"Error updating challenge: {str(e)}")
    
    # Get week unlock status for each week
    week_unlocks = {}
    for week_num in challenge.week_range:
        try:
            unlock = ChallengeWeekUnlock.objects.get(challenge=challenge, week_number=week_num)
            week_unlocks[week_num] = unlock
        except ChallengeWeekUnlock.DoesNotExist:
            week_unlocks[week_num] = None
    
    return render(request, "challenges/admin/challenge_form.html", {
        "challenge": challenge,
        "templates": templates,
        "form_action": "edit",
        "week_unlocks": week_unlocks,
    })

@login_required
@user_passes_test(is_admin, login_url='/')
def admin_challenge_delete(request, challenge_id):
    """Delete a challenge"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    if request.method == "POST":
        challenge_name = challenge.name
        challenge.delete()
        messages.success(request, f"Challenge '{challenge_name}' deleted successfully!")
        return redirect("challenges:admin_challenges_list")
    
    return render(request, "challenges/admin/challenge_delete.html", {
        "challenge": challenge,
    })

@login_required
@user_passes_test(is_admin, login_url='/')
def admin_assign_workouts(request, challenge_id):
    """Wizard to assign Peloton workouts for challenge templates"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    templates = challenge.available_templates.all()
    num_weeks = challenge.duration_weeks
    
    if not templates.exists():
        messages.warning(request, "No templates available for this challenge. Please add templates first.")
        return redirect("challenges:admin_challenge_edit", challenge_id=challenge_id)
    
    # Build structure: template -> week -> day -> activities
    workout_structure = []
    for template in templates:
        template_data = {
            "template": template,
            "weeks": []
        }
        
        for week_num in range(1, num_weeks + 1):
            week_data = {
                "week_number": week_num,
                "days": []
            }
            
            # Get template days to determine which activities are expected
            template_days = {d.day_of_week: d for d in template.days.all()}
            
            for day_num in range(7):
                template_day = template_days.get(day_num)
                focus_lower = template_day.peloton_focus.lower() if template_day else ""
                
                # Determine which activities are expected for this day
                has_ride = template_day and ("pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or "ride" in focus_lower)
                has_run = template_day and "run" in focus_lower
                has_yoga = template_day and "yoga" in focus_lower
                has_strength = template_day and "strength" in focus_lower
                
                # Get existing assignments (including alternatives)
                assignments = ChallengeWorkoutAssignment.objects.filter(
                    challenge=challenge,
                    template=template,
                    week_number=week_num,
                    day_of_week=day_num
                ).order_by('alternative_group', 'order_in_group')
                
                # Group assignments by activity type and alternative_group
                day_assignments = {
                    "ride": [],
                    "run": [],
                    "yoga": [],
                    "strength": [],
                }
                
                for assignment in assignments:
                    if assignment.activity_type in day_assignments:
                        day_assignments[assignment.activity_type].append(assignment)
                
                # Determine if this day should allow alternatives
                template_name_lower = template.name.lower()
                is_3_plan = "3" in template_name_lower and ("ride" in template_name_lower or "run" in template_name_lower)
                is_4_plan = "4" in template_name_lower and ("ride" in template_name_lower or "run" in template_name_lower)
                is_2r2r_plan = "2 runs 2 rides" in template_name_lower or "2 rides 2 runs" in template_name_lower
                
                # Count workout days to determine which day number this is
                workout_days = []
                for d in range(7):
                    td = template_days.get(d)
                    if td:
                        focus_lower = td.peloton_focus.lower()
                        if ("pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or 
                            "ride" in focus_lower or "run" in focus_lower or 
                            "yoga" in focus_lower or "strength" in focus_lower):
                            workout_days.append(d)
                
                workout_day_number = None
                if day_num in workout_days:
                    workout_day_number = workout_days.index(day_num) + 1
                
                allows_alternatives = False
                if is_3_plan and workout_day_number in [2, 3]:
                    allows_alternatives = True
                elif is_4_plan and workout_day_number in [1, 4, 6]:
                    allows_alternatives = True
                elif is_2r2r_plan and workout_day_number in [2, 4]:
                    allows_alternatives = True
                
                # Use day number if it's a workout day, otherwise use day name
                if workout_day_number:
                    day_label = f"Day {workout_day_number}"
                else:
                    day_name_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                    day_label = day_name_labels[day_num]
                
                week_data["days"].append({
                    "day_of_week": day_num,
                    "day_label": day_label,
                    "peloton_focus": template_day.peloton_focus if template_day else "",
                    "has_ride": has_ride,
                    "has_run": has_run,
                    "has_yoga": has_yoga,
                    "has_strength": has_strength,
                    "assignments": day_assignments,
                    "allows_alternatives": allows_alternatives,
                    "workout_day_number": workout_day_number,
                })
            
            template_data["weeks"].append(week_data)
        
        workout_structure.append(template_data)
    
    # Get bonus workouts for each week
    challenge_name_lower = challenge.name.lower()
    default_bonus_activity = "run" if "3 runs" in challenge_name_lower or ("run" in challenge_name_lower and "3" in challenge_name_lower) else "ride"
    
    bonus_workouts = {}
    for week_num in range(1, num_weeks + 1):
        bonus_workout = ChallengeBonusWorkout.objects.filter(
            challenge=challenge,
            week_number=week_num
        ).first()
        bonus_workouts[week_num] = bonus_workout
    
    if request.method == "POST":
        # Process form submission
        assignments_created = 0
        assignments_updated = 0
        
        for template in templates:
            template_name_lower = template.name.lower()
            is_3_plan = "3" in template_name_lower and ("ride" in template_name_lower or "run" in template_name_lower)
            is_4_plan = "4" in template_name_lower and ("ride" in template_name_lower or "run" in template_name_lower)
            is_2r2r_plan = "2 runs 2 rides" in template_name_lower or "2 rides 2 runs" in template_name_lower
            
            template_days = {d.day_of_week: d for d in template.days.all()}
            workout_days = []
            for d in range(7):
                td = template_days.get(d)
                if td:
                    focus_lower = td.peloton_focus.lower()
                    if ("pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or 
                        "ride" in focus_lower or "run" in focus_lower or 
                        "yoga" in focus_lower or "strength" in focus_lower):
                        workout_days.append(d)
            
            for week_num in range(1, num_weeks + 1):
                for day_num in range(7):
                    workout_day_number = None
                    if day_num in workout_days:
                        workout_day_number = workout_days.index(day_num) + 1
                    
                    allows_alternatives = False
                    if is_3_plan and workout_day_number in [2, 3]:
                        allows_alternatives = True
                    elif is_4_plan and workout_day_number in [1, 4, 6]:
                        allows_alternatives = True
                    elif is_2r2r_plan and workout_day_number in [2, 4]:
                        allows_alternatives = True
                    
                    for activity_type in ["ride", "run", "yoga", "strength"]:
                        # Process primary workout
                        url_key = f"workout_{template.id}_{week_num}_{day_num}_{activity_type}"
                        ride_id_key = f"ride_id_{template.id}_{week_num}_{day_num}_{activity_type}"
                        title_key = f"title_{template.id}_{week_num}_{day_num}_{activity_type}"
                        points_key = f"points_{template.id}_{week_num}_{day_num}_{activity_type}"
                        
                        # Try to get ride_id first (from search), fallback to URL
                        ride_id = request.POST.get(ride_id_key, "").strip()
                        peloton_url = request.POST.get(url_key, "").strip()
                        workout_title = request.POST.get(title_key, "").strip()
                        points_str = request.POST.get(points_key, "50").strip()
                        
                        try:
                            points = int(points_str) if points_str else 50
                        except (ValueError, TypeError):
                            points = 50
                        
                        # Get ride_detail if ride_id is provided
                        ride_detail = None
                        if ride_id:
                            try:
                                from workouts.models import RideDetail
                                ride_detail = RideDetail.objects.get(id=ride_id)
                                # Use ride_detail's URL if no URL provided
                                if not peloton_url and ride_detail.peloton_class_url:
                                    peloton_url = ride_detail.peloton_class_url
                                if not workout_title:
                                    workout_title = ride_detail.title
                            except (RideDetail.DoesNotExist, ValueError):
                                pass
                        
                        if peloton_url or ride_detail:
                            defaults = {
                                "peloton_url": peloton_url,
                                "workout_title": workout_title,
                                "points": points,
                                "ride_detail": ride_detail,
                            }
                            assignment, created = ChallengeWorkoutAssignment.objects.update_or_create(
                                challenge=challenge,
                                template=template,
                                week_number=week_num,
                                day_of_week=day_num,
                                activity_type=activity_type,
                                alternative_group=None,
                                order_in_group=0,
                                defaults=defaults
                            )
                            if created:
                                assignments_created += 1
                            else:
                                assignments_updated += 1
                        else:
                            ChallengeWorkoutAssignment.objects.filter(
                                challenge=challenge,
                                template=template,
                                week_number=week_num,
                                day_of_week=day_num,
                                activity_type=activity_type
                            ).delete()
                        
                        # Process alternatives
                        if allows_alternatives:
                            alternative_index = 1
                            while alternative_index <= 10:
                                url_key = f"workout_{template.id}_{week_num}_{day_num}_{activity_type}_alt{alternative_index}"
                                ride_id_key = f"ride_id_{template.id}_{week_num}_{day_num}_{activity_type}_alt{alternative_index}"
                                title_key = f"title_{template.id}_{week_num}_{day_num}_{activity_type}_alt{alternative_index}"
                                points_key = f"points_{template.id}_{week_num}_{day_num}_{activity_type}_alt{alternative_index}"
                                
                                # Try to get ride_id first (from search), fallback to URL
                                ride_id = request.POST.get(ride_id_key, "").strip()
                                peloton_url = request.POST.get(url_key, "").strip()
                                workout_title = request.POST.get(title_key, "").strip()
                                points_str = request.POST.get(points_key, "50").strip()
                                
                                try:
                                    points = int(points_str) if points_str else 50
                                except (ValueError, TypeError):
                                    points = 50
                                
                                # Get ride_detail if ride_id is provided
                                ride_detail = None
                                if ride_id:
                                    try:
                                        from workouts.models import RideDetail
                                        ride_detail = RideDetail.objects.get(id=ride_id)
                                        # Use ride_detail's URL if no URL provided
                                        if not peloton_url and ride_detail.peloton_class_url:
                                            peloton_url = ride_detail.peloton_class_url
                                        if not workout_title:
                                            workout_title = ride_detail.title
                                    except (RideDetail.DoesNotExist, ValueError):
                                        pass
                                
                                if peloton_url or ride_detail:
                                    defaults = {
                                        "peloton_url": peloton_url,
                                        "workout_title": workout_title,
                                        "points": points,
                                        "ride_detail": ride_detail,
                                    }
                                    assignment, created = ChallengeWorkoutAssignment.objects.update_or_create(
                                        challenge=challenge,
                                        template=template,
                                        week_number=week_num,
                                        day_of_week=day_num,
                                        activity_type=activity_type,
                                        alternative_group=day_num,
                                        order_in_group=alternative_index,
                                        defaults=defaults
                                    )
                                    if created:
                                        assignments_created += 1
                                    else:
                                        assignments_updated += 1
                                else:
                                    ChallengeWorkoutAssignment.objects.filter(
                                        challenge=challenge,
                                        template=template,
                                        week_number=week_num,
                                        day_of_week=day_num,
                                        activity_type=activity_type,
                                        alternative_group=day_num,
                                        order_in_group=alternative_index
                                    ).delete()
                                    break
                                
                                alternative_index += 1
        
        # Handle bonus workouts
        challenge_name_lower = challenge.name.lower()
        default_bonus_activity = "run" if "3 runs" in challenge_name_lower or ("run" in challenge_name_lower and "3" in challenge_name_lower) else "ride"
        
        bonus_created = 0
        bonus_updated = 0
        for week_num in range(1, num_weeks + 1):
            url_key = f"bonus_workout_{week_num}"
            title_key = f"bonus_title_{week_num}"
            points_key = f"bonus_points_{week_num}"
            activity_key = f"bonus_activity_{week_num}"
            
            peloton_url = request.POST.get(url_key, "").strip()
            workout_title = request.POST.get(title_key, "").strip()
            points = request.POST.get(points_key, "10").strip()
            activity_type = request.POST.get(activity_key, default_bonus_activity).strip()
            
            if activity_type not in ["ride", "run", "yoga", "strength"]:
                activity_type = default_bonus_activity
            
            try:
                points = int(points) if points else 10
            except ValueError:
                points = 10
            
            if workout_title or peloton_url:
                bonus_workout, created = ChallengeBonusWorkout.objects.update_or_create(
                    challenge=challenge,
                    week_number=week_num,
                    defaults={
                        "activity_type": activity_type,
                        "peloton_url": peloton_url if peloton_url else "",
                        "workout_title": workout_title if workout_title else f"Week {week_num} Bonus {activity_type.title()}",
                        "points": points,
                    }
                )
                if created:
                    bonus_created += 1
                else:
                    bonus_updated += 1
            else:
                ChallengeBonusWorkout.objects.filter(
                    challenge=challenge,
                    week_number=week_num
                ).delete()
        
        # Validate that all assigned workouts exist in the local library
        # Collect all peloton URLs/IDs from assignments
        all_class_ids = []
        all_assignments = ChallengeWorkoutAssignment.objects.filter(challenge=challenge)
        for assignment in all_assignments:
            if assignment.peloton_url:
                try:
                    class_id = extract_class_id(assignment.peloton_url)
                    all_class_ids.append(class_id)
                except ValueError:
                    # Invalid URL format - will be handled elsewhere
                    pass
        
        # Queue missing rides for sync but allow partial saves
        if all_class_ids:
            validation_result = queue_missing_rides(all_class_ids)
            missing_count = validation_result['missing_count']
            
            if missing_count > 0:
                # Queue the missing rides but allow save to proceed
                queued_count = validation_result['queued_count']
                already_queued_count = validation_result['already_queued_count']
                
                info_msg = (
                    f"Assignments saved! Note: {missing_count} classes were queued for sync "
                    f"({queued_count} newly queued, {already_queued_count} already queued). "
                    f"Full workout details will appear after sync completes."
                )
                messages.info(request, info_msg)
        
        messages.success(request, f"Workout assignments saved! ({assignments_created} created, {assignments_updated} updated, {bonus_created + bonus_updated} bonus workouts)")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'message': f'Workout assignments saved! ({assignments_created} created, {assignments_updated} updated)',
                'created': assignments_created,
                'updated': assignments_updated,
            })
        
        return redirect("challenges:admin_challenges_list")
    
    week_range = list(range(1, num_weeks + 1))
    
    return render(request, "challenges/admin/assign_workouts.html", {
        "challenge": challenge,
        "workout_structure": workout_structure,
        "bonus_workouts": bonus_workouts,
        "default_bonus_activity": default_bonus_activity,
        "num_weeks": num_weeks,
        "week_range": week_range,
    })


@login_required
@user_passes_test(is_admin, login_url='/')
def admin_manage_teams(request, challenge_id):
    """Admin panel to manage team assignments and volunteers"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Get all teams
    all_teams = Team.objects.all().order_by('name')
    
    # Get volunteers for this challenge
    volunteers = TeamLeaderVolunteer.objects.filter(
        challenge=challenge,
        assigned=False
    ).select_related('user', 'challenge_instance').order_by('-volunteered_at')
    
    # Get users without teams for this challenge (only those who have signed up)
    users_with_teams = set()
    for member in TeamMember.objects.filter(challenge_instance__challenge=challenge, challenge_instance__is_active=True):
        users_with_teams.add(member.challenge_instance.user.id)
    
    # Only show users who have actually signed up for this challenge
    users_without_teams = User.objects.filter(
        challenge_instances__challenge=challenge,
        challenge_instances__is_active=True
    ).exclude(id__in=users_with_teams).distinct().order_by('email')
    
    # Get team members for this challenge
    team_members = TeamMember.objects.filter(
        challenge_instance__challenge=challenge,
        challenge_instance__is_active=True
    ).select_related('team', 'challenge_instance__user').order_by('team__name', 'challenge_instance__user__email')
    
    # Group by team
    teams_data = {}
    for member in team_members:
        team = member.team
        if team.id not in teams_data:
            teams_data[team.id] = {
                'team': team,
                'members': []
            }
        teams_data[team.id]['members'].append(member)
    
    # Handle POST requests
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "assign_volunteer":
            volunteer_id = request.POST.get("volunteer_id")
            team_id = request.POST.get("team_id")
            create_new_team = request.POST.get("create_new_team") == "on"
            new_team_name = request.POST.get("new_team_name", "").strip()
            
            try:
                volunteer = TeamLeaderVolunteer.objects.get(pk=volunteer_id, challenge=challenge, assigned=False)
                
                if create_new_team:
                    if not new_team_name:
                        messages.error(request, "Please provide a team name.")
                    else:
                        # Create new team with volunteer as leader
                        team = Team.objects.create(name=new_team_name, leader=volunteer.user)
                        # Assign volunteer to challenge instance
                        if volunteer.challenge_instance:
                            TeamMember.objects.get_or_create(
                                team=team,
                                challenge_instance=volunteer.challenge_instance
                            )
                        volunteer.assigned = True
                        volunteer.assigned_team = team
                        volunteer.assigned_at = timezone.now()
                        volunteer.save()
                        messages.success(request, f"Created team '{team.name}' and assigned {volunteer.user.email} as leader.")
                elif team_id:
                    team = get_object_or_404(Team, pk=team_id)
                    # Check if team can add another leader (max 3)
                    # For now, we only have one leader field, so we'll replace if needed
                    # TODO: When implementing multiple leaders, check if team.team_leaders count < 3
                    if team.leader and team.leader != volunteer.user:
                        # Check if we're at max leaders (for now, just one leader)
                        # In future, check: len(team.team_leaders) >= 3
                        if not team.can_add_leader():
                            messages.error(request, f"Team '{team.name}' already has the maximum number of leaders (3).")
                            return redirect("challenges:admin_manage_teams", challenge_id=challenge_id)
                    
                    # Assign volunteer as leader
                    team.leader = volunteer.user
                    team.save()
                    # Assign volunteer to challenge instance
                    if volunteer.challenge_instance:
                        TeamMember.objects.get_or_create(
                            team=team,
                            challenge_instance=volunteer.challenge_instance
                        )
                    volunteer.assigned = True
                    volunteer.assigned_team = team
                    volunteer.assigned_at = timezone.now()
                    volunteer.save()
                    messages.success(request, f"Assigned {volunteer.user.email} as leader of '{team.name}'.")
                else:
                    messages.error(request, "Please select a team or create a new one.")
            except TeamLeaderVolunteer.DoesNotExist:
                messages.error(request, "Volunteer not found or already assigned.")
        
        elif action == "assign_user_to_team":
            user_id = request.POST.get("user_id")
            team_id = request.POST.get("team_id")
            
            try:
                user = User.objects.get(pk=user_id)
                team = get_object_or_404(Team, pk=team_id)
                # Find user's challenge instance
                instance = ChallengeInstance.objects.filter(
                    user=user,
                    challenge=challenge,
                    is_active=True
                ).first()
                
                if instance:
                    TeamMember.objects.get_or_create(
                        team=team,
                        challenge_instance=instance
                    )
                    messages.success(request, f"Assigned {user.email} to team '{team.name}'.")
                else:
                    messages.error(request, f"User {user.email} is not participating in this challenge.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        
        elif action == "remove_member":
            member_id = request.POST.get("member_id")
            try:
                member = TeamMember.objects.get(pk=member_id, challenge_instance__challenge=challenge)
                user_email = member.challenge_instance.user.email
                team_name = member.team.name
                member.delete()
                messages.success(request, f"Removed {user_email} from team '{team_name}'.")
            except TeamMember.DoesNotExist:
                messages.error(request, "Member not found.")
        
        elif action == "change_team_leader":
            team_id = request.POST.get("team_id")
            new_leader_id = request.POST.get("new_leader_id")
            try:
                team = get_object_or_404(Team, pk=team_id)
                new_leader = User.objects.get(pk=new_leader_id)
                # Check if new leader is a member of the team
                is_member = TeamMember.objects.filter(
                    team=team,
                    challenge_instance__user=new_leader,
                    challenge_instance__challenge=challenge,
                    challenge_instance__is_active=True
                ).exists()
                
                if is_member:
                    # Check if team already has max leaders (3)
                    # For now, we only track one leader, but we can add additional leaders later
                    # Just check if we're replacing the existing leader or if there's no leader
                    if team.leader and team.leader != new_leader:
                        # Check if we can add another leader (max 3)
                        # Since we only have one leader field for now, we'll just replace it
                        # TODO: Implement multiple leaders (up to 3) when needed
                        pass
                    team.leader = new_leader
                    team.save()
                    messages.success(request, f"Changed team leader of '{team.name}' to {new_leader.email}.")
                else:
                    messages.error(request, "New leader must be a member of the team.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        
        elif action == "create_team":
            # Only allow superusers to create teams
            if not request.user.is_superuser:
                messages.error(request, "Only superusers can create teams.")
                return redirect("challenges:admin_manage_teams", challenge_id=challenge_id)
            
            team_name = request.POST.get("team_name", "").strip()
            leader_id = request.POST.get("leader_id") or None
            
            if not team_name:
                messages.error(request, "Please provide a team name.")
                return redirect("challenges:admin_manage_teams", challenge_id=challenge_id)
            
            # Check if team name already exists
            if Team.objects.filter(name=team_name).exists():
                messages.error(request, f"A team with the name '{team_name}' already exists.")
                return redirect("challenges:admin_manage_teams", challenge_id=challenge_id)
            
            try:
                leader = None
                if leader_id:
                    leader = User.objects.get(pk=leader_id)
                
                team = Team.objects.create(name=team_name, leader=leader)
                
                # If leader was specified and they're in this challenge, assign them to the team
                if leader:
                    instance = ChallengeInstance.objects.filter(
                        user=leader,
                        challenge=challenge,
                        is_active=True
                    ).first()
                    if instance:
                        TeamMember.objects.get_or_create(
                            team=team,
                            challenge_instance=instance
                        )
                
                messages.success(request, f"Created team '{team.name}' successfully.")
            except User.DoesNotExist:
                messages.error(request, "Leader user not found.")
            except Exception as e:
                messages.error(request, f"Error creating team: {str(e)}")
        
        return redirect("challenges:admin_manage_teams", challenge_id=challenge_id)
    
    # Get all users in the challenge for team leader selection
    all_challenge_users = User.objects.filter(
        challenge_instances__challenge=challenge,
        challenge_instances__is_active=True
    ).distinct().order_by('email')
    
    return render(request, "challenges/admin/manage_teams.html", {
        "challenge": challenge,
        "all_teams": all_teams,
        "volunteers": volunteers,
        "users_without_teams": users_without_teams,
        "teams_data": teams_data,
        "all_challenge_users": all_challenge_users,
    })


@login_required
@user_passes_test(is_admin, login_url='/')
def admin_assign_teams_dragdrop(request, challenge_id):
    """Drag-and-drop interface for assigning users to teams"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Get all teams
    all_teams = Team.objects.all().order_by('name')
    
    # Get users without teams for this challenge
    users_with_teams = set()
    for member in TeamMember.objects.filter(challenge_instance__challenge=challenge, challenge_instance__is_active=True):
        users_with_teams.add(member.challenge_instance.user.id)
    
    # Get unassigned users with their challenge instances
    unassigned_users = []
    for user in User.objects.filter(
        challenge_instances__challenge=challenge,
        challenge_instances__is_active=True
    ).exclude(id__in=users_with_teams).distinct().order_by('email'):
        instance = ChallengeInstance.objects.filter(
            user=user,
            challenge=challenge,
            is_active=True
        ).first()
        if instance:
            unassigned_users.append({
                'user': user,
                'instance': instance
            })
    
    # Get team members grouped by team
    team_members = TeamMember.objects.filter(
        challenge_instance__challenge=challenge,
        challenge_instance__is_active=True
    ).select_related('team', 'challenge_instance__user').order_by('team__name', 'challenge_instance__user__email')
    
    # Initialize teams_data with all teams (including empty ones)
    teams_data = {}
    for team in all_teams:
        teams_data[team.id] = {
            'team': team,
            'members': []
        }
    
    # Populate members for teams that have them
    for member in team_members:
        team = member.team
        if team.id in teams_data:
            teams_data[team.id]['members'].append(member)
    
    return render(request, "challenges/admin/assign_teams_dragdrop.html", {
        "challenge": challenge,
        "all_teams": all_teams,
        "unassigned_users": unassigned_users,
        "teams_data": teams_data,
    })


@login_required
@user_passes_test(is_admin, login_url='/')
def admin_assign_user_to_team_ajax(request, challenge_id):
    """AJAX endpoint to assign a user to a team via drag-and-drop"""
    if request.method != "POST":
        from django.http import JsonResponse
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    import json
    from django.http import JsonResponse
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        team_id = data.get('team_id')
        
        if not user_id or not team_id:
            return JsonResponse({'success': False, 'error': 'Missing user_id or team_id'}, status=400)
        
        challenge = get_object_or_404(Challenge, pk=challenge_id)
        user = get_object_or_404(User, pk=user_id)
        team = get_object_or_404(Team, pk=team_id)
        
        # Find user's challenge instance
        instance = ChallengeInstance.objects.filter(
            user=user,
            challenge=challenge,
            is_active=True
        ).first()
        
        if not instance:
            return JsonResponse({
                'success': False, 
                'error': f'User {user.email} is not participating in this challenge.'
            }, status=400)
        
        # Check if user is already in a team
        existing_member = TeamMember.objects.filter(challenge_instance=instance).first()
        if existing_member:
            # Remove from old team
            existing_member.delete()
        
        # Assign to new team
        TeamMember.objects.get_or_create(
            team=team,
            challenge_instance=instance
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Assigned {user.email} to team {team.name}',
            'user_email': user.email,
            'team_name': team.name
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin, login_url='/')
def search_ride_classes(request):
    """
    API endpoint to search RideDetail classes in local database.
    Searches by: class ID (exact match), title (partial match)
    Returns JSON with class details including chart/target_metrics availability.
    """
    from workouts.models import RideDetail
    from django.http import JsonResponse
    
    query = request.GET.get('q', '').strip()
    activity_type = request.GET.get('activity', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    # First try exact match on class ID (most specific)
    rides = RideDetail.objects.filter(peloton_ride_id__iexact=query)
    
    # If no exact match, search by title (partial match)
    if not rides.exists():
        rides = RideDetail.objects.filter(title__icontains=query)
    
    # Apply activity type filter if specified
    if activity_type:
        discipline_map = {
            'ride': 'cycling',
            'run': 'running',
            'yoga': 'yoga',
            'strength': 'strength',
        }
        discipline = discipline_map.get(activity_type.lower())
        if discipline:
            rides = rides.filter(fitness_discipline__iexact=discipline)
    
    # Return top 10 results with chart/target availability
    results = []
    for ride in rides[:10]:
        # Check if this class has target metrics (chart/target plan in library)
        # target_metrics_data is a dict - non-empty means it has chart data
        has_chart = bool(ride.target_metrics_data) if ride.target_metrics_data else False
        
        # Generate proper .com Peloton URL format
        peloton_url = ride.peloton_class_url or ''
        if ride.peloton_ride_id:
            peloton_url = f"https://members.onepeloton.com/classes/cycling/{ride.peloton_ride_id}?modal=classDetailsModal&classId={ride.peloton_ride_id}"
        
        results.append({
            'id': ride.id,
            'peloton_id': ride.peloton_ride_id,
            'title': ride.title,
            'discipline': ride.fitness_discipline_display_name or ride.fitness_discipline,
            'instructor': ride.instructor.name if ride.instructor else 'Unknown',
            'duration': ride.duration_minutes,
            'difficulty': ride.difficulty_level or 'N/A',
            'has_chart': has_chart,
            'image_url': ride.image_url or '',
            'peloton_url': peloton_url,
            'target_metrics_data': ride.target_metrics_data or {},
        })
    
    return JsonResponse({'results': results})
