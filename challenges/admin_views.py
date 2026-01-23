from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from datetime import date
from .models import Challenge, ChallengeInstance, ChallengeWorkoutAssignment, ChallengeWeekUnlock, ChallengeBonusWorkout
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
                        title_key = f"title_{template.id}_{week_num}_{day_num}_{activity_type}"
                        points_key = f"points_{template.id}_{week_num}_{day_num}_{activity_type}"
                        
                        peloton_url = request.POST.get(url_key, "").strip()
                        workout_title = request.POST.get(title_key, "").strip()
                        points_str = request.POST.get(points_key, "50").strip()
                        
                        try:
                            points = int(points_str) if points_str else 50
                        except (ValueError, TypeError):
                            points = 50
                        
                        if peloton_url:
                            assignment, created = ChallengeWorkoutAssignment.objects.update_or_create(
                                challenge=challenge,
                                template=template,
                                week_number=week_num,
                                day_of_week=day_num,
                                activity_type=activity_type,
                                alternative_group=None,
                                order_in_group=0,
                                defaults={
                                    "peloton_url": peloton_url,
                                    "workout_title": workout_title,
                                    "points": points,
                                }
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
                                title_key = f"title_{template.id}_{week_num}_{day_num}_{activity_type}_alt{alternative_index}"
                                points_key = f"points_{template.id}_{week_num}_{day_num}_{activity_type}_alt{alternative_index}"
                                
                                peloton_url = request.POST.get(url_key, "").strip()
                                workout_title = request.POST.get(title_key, "").strip()
                                points_str = request.POST.get(points_key, "50").strip()
                                
                                try:
                                    points = int(points_str) if points_str else 50
                                except (ValueError, TypeError):
                                    points = 50
                                
                                if peloton_url:
                                    assignment, created = ChallengeWorkoutAssignment.objects.update_or_create(
                                        challenge=challenge,
                                        template=template,
                                        week_number=week_num,
                                        day_of_week=day_num,
                                        activity_type=activity_type,
                                        alternative_group=day_num,
                                        order_in_group=alternative_index,
                                        defaults={
                                            "peloton_url": peloton_url,
                                            "workout_title": workout_title,
                                            "points": points,
                                        }
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
