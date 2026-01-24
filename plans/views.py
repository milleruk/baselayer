from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from datetime import date, timedelta, datetime
from collections import defaultdict
from .models import Exercise
from tracker.models import WeeklyPlan
from challenges.models import ChallengeInstance
from tracker.views import sunday_of_current_week

@login_required
def dashboard(request):
    # Get active challenge instance (only truly active ones)
    active_challenge_instance = ChallengeInstance.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('challenge').prefetch_related('weekly_plans').first()
    
    # Get current week plan
    current_week_start = sunday_of_current_week(date.today())
    current_week_plan = WeeklyPlan.objects.filter(
        user=request.user,
        week_start=current_week_start
    ).select_related('challenge_instance__challenge').first()
    
    # Calculate week number if current plan is part of a challenge
    if current_week_plan and current_week_plan.challenge_instance:
        all_ci_plans = current_week_plan.challenge_instance.weekly_plans.all().order_by("week_start")
        for idx, p in enumerate(all_ci_plans, start=1):
            if p.id == current_week_plan.id:
                current_week_plan.week_number = idx
                break
    
    # Get completed challenges count (all weeks completed)
    all_challenge_instances = ChallengeInstance.objects.filter(
        user=request.user
    ).prefetch_related('weekly_plans')
    completed_challenges_count = sum(
        1 for ci in all_challenge_instances
        if ci.all_weeks_completed
    )
    
    # Check if user has any challenge involvement (active or completed)
    has_challenge_involvement = active_challenge_instance is not None or completed_challenges_count > 0
    
    # Get all plans for stats (only challenge-related plans for accurate stats)
    # Only calculate stats if user has challenge involvement
    if has_challenge_involvement:
        all_plans = WeeklyPlan.objects.filter(
            user=request.user,
            challenge_instance__isnull=False
        ).select_related('challenge_instance')
        
        # Calculate stats
        total_points = sum(plan.total_points for plan in all_plans)
        total_weeks_completed = sum(1 for plan in all_plans if plan.is_completed)
        total_weeks = all_plans.count()
        
        # Get recent plans (last 3) and calculate week numbers
        recent_plans = list(all_plans.order_by('-week_start')[:3])
        for plan in recent_plans:
            if plan.challenge_instance:
                all_ci_plans = plan.challenge_instance.weekly_plans.all().order_by("week_start")
                for idx, p in enumerate(all_ci_plans, start=1):
                    if p.id == plan.id:
                        plan.week_number = idx
                        break
        
        # Get upcoming plans (next 2 weeks)
        next_week_start = current_week_start + timedelta(days=7)
        upcoming_plans = WeeklyPlan.objects.filter(
            user=request.user,
            challenge_instance__isnull=False,
            week_start__gte=next_week_start
        ).order_by('week_start')[:2]
        
        # Only show recent plans if user has challenge involvement
        show_recent_plans = len(recent_plans) > 0
        # Calculate average completion rate
        avg_completion_rate = (total_weeks_completed / total_weeks * 100) if total_weeks > 0 else 0
    else:
        # No challenge involvement - set defaults
        all_plans = WeeklyPlan.objects.none()
        total_points = 0
        total_weeks_completed = 0
        total_weeks = 0
        recent_plans = WeeklyPlan.objects.none()
        upcoming_plans = WeeklyPlan.objects.none()
        show_recent_plans = False
        avg_completion_rate = 0
    
    context = {
        'active_challenge_instance': active_challenge_instance,
        'current_week_plan': current_week_plan,
        'total_points': total_points,
        'total_weeks_completed': total_weeks_completed,
        'total_weeks': total_weeks,
        'avg_completion_rate': avg_completion_rate,
        'recent_plans': recent_plans if show_recent_plans else [],
        'upcoming_plans': upcoming_plans,
        'completed_challenges_count': completed_challenges_count,
        'show_recent_plans': show_recent_plans,
        'has_challenge_involvement': has_challenge_involvement,
    }
    
    return render(request, "plans/dashboard.html", context)

@login_required
def exercise_list(request):
    exercises = Exercise.objects.all().order_by("category", "name")
    return render(request, "plans/exercises.html", {"exercises": exercises})

def landing(request):
    return render(request, "plans/landing.html")

def guide(request):
    return render(request, "plans/guide.html")

@login_required
def metrics(request):
    from collections import defaultdict
    from accounts.models import WeightEntry, FTPEntry, PaceEntry
    
    # Get all challenge instances for this user
    all_challenge_instances = ChallengeInstance.objects.filter(
        user=request.user
    ).select_related('challenge').prefetch_related('weekly_plans').order_by('-started_at')
    
    # Group by challenge and count attempts
    challenge_groups = defaultdict(list)
    
    for ci in all_challenge_instances:
        challenge_groups[ci.challenge.id].append(ci)
    
    # Separate into fully completed and partially completed, showing only latest attempt per challenge
    fully_completed_challenges = []
    partially_completed_challenges = []
    
    for challenge_id, instances in challenge_groups.items():
        # Sort by started_at descending to get the latest attempt
        latest_instance = max(instances, key=lambda x: x.started_at)
        attempt_count = len(instances)
        
        # Add attempt count to the instance
        latest_instance.attempt_count = attempt_count
        
        if latest_instance.all_weeks_completed:
            fully_completed_challenges.append(latest_instance)
        elif latest_instance.weekly_plans.exists() and latest_instance.completion_rate > 0:
            # Has some progress but not all weeks completed
            partially_completed_challenges.append(latest_instance)
    
    # Get weight entries for power-to-weight calculations
    weight_entries = WeightEntry.objects.filter(user=request.user).order_by('-recorded_date', '-created_at')
    current_weight = weight_entries.first() if weight_entries.exists() else None
    
    # Get all plans for stats
    all_plans = WeeklyPlan.objects.filter(user=request.user)
    total_points = sum(plan.total_points for plan in all_plans)
    
    # Get FTP entries for progression chart (all entries, ordered by date)
    ftp_entries = FTPEntry.objects.filter(user=request.user).order_by('recorded_date')
    
    # Get Pace entries for progression chart (all entries, ordered by date)
    # Separate by activity type for the chart
    running_pace_entries = PaceEntry.objects.filter(user=request.user, activity_type='running').order_by('recorded_date')
    walking_pace_entries = PaceEntry.objects.filter(user=request.user, activity_type='walking').order_by('recorded_date')
    
    # Calculate Power-to-Weight ratios
    # Get current FTP
    current_ftp = ftp_entries.filter(is_active=True).order_by('-recorded_date').first()
    if not current_ftp:
        current_ftp = ftp_entries.order_by('-recorded_date').first()
    
    # Calculate current power-to-weight ratios
    current_cycling_pw = None
    current_tread_pw = None
    
    if current_weight and current_ftp:
        # Convert weight from lbs to kg (1 lb = 0.453592 kg)
        weight_kg = float(current_weight.weight) * 0.453592
        if weight_kg > 0:
            current_cycling_pw = round(float(current_ftp.ftp_value) / weight_kg, 2)
            # Tread P/W will be None until we have tread-specific FTP data
            current_tread_pw = None
    
    # Build historical power-to-weight data
    # Combine FTP and weight entries by date (month/year)
    pw_history = []
    
    # Create a dictionary of weight by month/year (keep most recent entry per month)
    weight_by_month = {}
    for weight_entry in weight_entries.order_by('recorded_date'):
        # Use first day of month as key for grouping
        month_start = weight_entry.recorded_date.replace(day=1)
        month_key = month_start.strftime('%b %Y')
        # Keep the most recent weight for each month
        if month_key not in weight_by_month:
            weight_by_month[month_key] = {
                'weight': weight_entry.weight,
                'date': month_start
            }
        else:
            # Update if this entry is more recent
            if weight_entry.recorded_date > weight_by_month[month_key]['date']:
                weight_by_month[month_key] = {
                    'weight': weight_entry.weight,
                    'date': month_start
                }
    
    # Create a dictionary of FTP by month/year (keep most recent entry per month)
    ftp_by_month = {}
    for ftp_entry in ftp_entries.order_by('recorded_date'):
        # Use first day of month as key for grouping
        month_start = ftp_entry.recorded_date.replace(day=1)
        month_key = month_start.strftime('%b %Y')
        # Keep the most recent FTP for each month
        if month_key not in ftp_by_month:
            ftp_by_month[month_key] = {
                'ftp': ftp_entry.ftp_value,
                'date': month_start
            }
        else:
            # Update if this entry is more recent
            if ftp_entry.recorded_date > ftp_by_month[month_key]['date']:
                ftp_by_month[month_key] = {
                    'ftp': ftp_entry.ftp_value,
                    'date': month_start
                }
    
    # Combine all unique months
    all_months = set(list(weight_by_month.keys()) + list(ftp_by_month.keys()))
    
    # Build history entries for cycling
    cycling_history_entries = []
    
    for month_key in all_months:
        weight_data = weight_by_month.get(month_key, {})
        ftp_data = ftp_by_month.get(month_key, {})
        
        weight = weight_data.get('weight') if weight_data else None
        ftp = ftp_data.get('ftp') if ftp_data else None
        
        # Use the date from either weight or ftp entry for sorting
        sort_date = weight_data.get('date') if weight_data else ftp_data.get('date')
        
        # Cycling P/W calculation
        cycling_pw_ratio = None
        if weight and ftp:
            weight_kg = float(weight) * 0.453592
            if weight_kg > 0:
                cycling_pw_ratio = round(float(ftp) / weight_kg, 2)
        
        cycling_history_entries.append({
            'date': month_key,
            'ftp': ftp,
            'weight': weight,
            'pw_ratio': cycling_pw_ratio,
            'sort_date': sort_date
        })
    
    # Sort by date descending (most recent first)
    pw_history_cycling = sorted(cycling_history_entries, key=lambda x: x['sort_date'] if x['sort_date'] else datetime(1900, 1, 1), reverse=True)
    
    # Tread history - empty until we have tread-specific FTP data
    # For now, we don't have tread FTP entries, so tread history will be empty
    pw_history_tread = []
    
    # Calculate monthly stats (placeholder - will be replaced with Peloton data)
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    context = {
        'fully_completed_challenges': fully_completed_challenges,
        'partially_completed_challenges': partially_completed_challenges,
        'current_weight': current_weight,
        'weight_entries': weight_entries,
        'total_points': total_points,
        'current_month': current_month,
        'current_year': current_year,
        'ftp_entries': ftp_entries,
        'running_pace_entries': running_pace_entries,
        'walking_pace_entries': walking_pace_entries,
        'current_ftp': current_ftp,
        'current_cycling_pw': current_cycling_pw,
        'current_tread_pw': current_tread_pw,
        'pw_history_cycling': pw_history_cycling,
        'pw_history_tread': pw_history_tread,
    }
    
    # Calculate Peloton milestones
    peloton_milestones = []
    if hasattr(request.user, 'profile') and request.user.profile.peloton_workout_counts:
        workout_counts = request.user.profile.peloton_workout_counts
        
        # Map milestone categories to Peloton workout slugs
        categories = [
            {'name': 'Yoga', 'slug': 'yoga', 'icon': '🧘'},
            {'name': 'Bike', 'slug': 'cycling', 'icon': '🚴'},
            {'name': 'Tread', 'slug': 'running', 'icon': '🏃'},
            {'name': 'Stretching', 'slug': 'stretching', 'icon': '🤸'},
            {'name': 'Strength', 'slug': 'strength', 'icon': '💪'},
        ]
        
        # Milestone thresholds
        milestone_thresholds = [10, 50, 100, 500, 1000]
        
        for category_info in categories:
            count = workout_counts.get(category_info['slug'], 0)
            achieved = []
            
            # Check which milestones are achieved
            for threshold in milestone_thresholds:
                if count >= threshold:
                    achieved.append(threshold)
            
            peloton_milestones.append({
                'name': category_info['name'],
                'icon': category_info['icon'],
                'count': count,
                'achieved': achieved,
                'thresholds': milestone_thresholds,
            })
    else:
        # Default structure if no Peloton data
        categories = [
            {'name': 'Yoga', 'icon': '🧘'},
            {'name': 'Bike', 'icon': '🚴'},
            {'name': 'Tread', 'icon': '🏃'},
            {'name': 'Stretching', 'icon': '🤸'},
            {'name': 'Strength', 'icon': '💪'},
        ]
        for category_info in categories:
            peloton_milestones.append({
                'name': category_info['name'],
                'icon': category_info['icon'],
                'count': 0,
                'achieved': [],
                'thresholds': [10, 50, 100, 500, 1000],
            })
    
    context['peloton_milestones'] = peloton_milestones
    
    return render(request, "plans/metrics.html", context)