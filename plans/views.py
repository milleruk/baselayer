from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import date, timedelta, datetime
from collections import defaultdict
import json
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
    ).select_related('challenge').prefetch_related('weekly_plans', 'team_membership__team').first()
    
    # Get team information if user is in a team for this challenge
    team_info = None
    if active_challenge_instance:
        try:
            from challenges.models import TeamMember
            team_membership = active_challenge_instance.team_membership
            team_info = {
                'name': team_membership.team.name,
                'id': team_membership.team.id,
            }
        except (TeamMember.DoesNotExist, AttributeError):
            team_info = None
    
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
    
    # Get recent workouts from Peloton
    # All class data comes from ride_detail via SQL joins
    from workouts.models import Workout, WorkoutDetails
    from django.db.models import Sum, Avg, Count, Q
    from django.core.exceptions import ObjectDoesNotExist
    
    recent_workouts = Workout.objects.filter(
        user=request.user
    ).select_related('ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details').order_by('-completed_date')[:5]
    
    # Get Peloton statistics from user's profile
    profile = request.user.profile
    peloton_stats = {
        'total_workouts': profile.peloton_total_workouts or 0,
        'total_output': profile.peloton_total_output or 0,
        'total_distance': profile.peloton_total_distance or 0,
        'total_calories': profile.peloton_total_calories or 0,
        'current_weekly_streak': profile.peloton_current_weekly_streak or 0,
        'best_weekly_streak': profile.peloton_best_weekly_streak or 0,
        'current_daily_streak': profile.peloton_current_daily_streak or 0,
        'total_achievements': profile.peloton_total_achievements or 0,
        'workout_counts': profile.peloton_workout_counts or {},
    }
    
    # Calculate workout statistics from database (more accurate than profile)
    all_workouts = Workout.objects.filter(user=request.user).select_related('ride_detail', 'details')
    
    # Total workouts count
    total_workouts_count = all_workouts.count()
    
    # Calculate totals from workout details (sum all workouts)
    workout_stats = all_workouts.aggregate(
        total_output_sum=Sum('details__total_output'),
        total_distance_sum=Sum('details__distance'),
        total_calories_sum=Sum('details__total_calories'),
        avg_output=Avg('details__avg_output'),
        avg_heart_rate=Avg('details__avg_heart_rate'),
    )
    
    # Workouts by type breakdown
    workouts_by_type = {}
    for workout in all_workouts.select_related('ride_detail__workout_type'):
        if workout.ride_detail and workout.ride_detail.workout_type:
            type_name = workout.ride_detail.workout_type.name
            workouts_by_type[type_name] = workouts_by_type.get(type_name, 0) + 1
    
    # Workouts over time (last 30 days, grouped by week)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    recent_workouts_30d = all_workouts.filter(completed_date__gte=thirty_days_ago)
    
    # Group workouts by week for chart
    workouts_by_week = {}
    for workout in recent_workouts_30d:
        week_start = workout.completed_date - timedelta(days=workout.completed_date.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        if week_key not in workouts_by_week:
            workouts_by_week[week_key] = {
                'date': week_start,
                'count': 0,
                'total_output': 0,
                'total_calories': 0,
            }
        workouts_by_week[week_key]['count'] += 1
        try:
            details = workout.details
            if details and details.total_output:
                workouts_by_week[week_key]['total_output'] += details.total_output
            if details and details.total_calories:
                workouts_by_week[week_key]['total_calories'] += details.total_calories
        except (WorkoutDetails.DoesNotExist, AttributeError):
            pass
    
    # Sort by date
    workouts_by_week_list = sorted(workouts_by_week.values(), key=lambda x: x['date'])
    
    # This week's workouts
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    this_week_workouts = all_workouts.filter(
        completed_date__gte=week_start
    )
    this_week_count = this_week_workouts.count()
    def safe_get_output(workout):
        try:
            return workout.details.total_output if workout.details and workout.details.total_output else 0
        except (WorkoutDetails.DoesNotExist, AttributeError):
            return 0
    
    def safe_get_calories(workout):
        try:
            return workout.details.total_calories if workout.details and workout.details.total_calories else 0
        except (WorkoutDetails.DoesNotExist, AttributeError):
            return 0
    
    this_week_output = sum(safe_get_output(w) for w in this_week_workouts) or 0
    this_week_calories = sum(safe_get_calories(w) for w in this_week_workouts) or 0
    
    # Last 7 days workouts
    seven_days_ago = today - timedelta(days=7)
    last_7_days_workouts = all_workouts.filter(completed_date__gte=seven_days_ago)
    last_7_days_count = last_7_days_workouts.count()
    last_7_days_output = sum(safe_get_output(w) for w in last_7_days_workouts) or 0
    
    # Previous 7 days (for comparison)
    fourteen_days_ago = today - timedelta(days=14)
    previous_7_days_workouts = all_workouts.filter(completed_date__gte=fourteen_days_ago, completed_date__lt=seven_days_ago)
    previous_7_days_count = previous_7_days_workouts.count()
    previous_7_days_output = sum(safe_get_output(w) for w in previous_7_days_workouts) or 0
    
    # Monthly totals (this month)
    month_start = today.replace(day=1)
    this_month_workouts = all_workouts.filter(completed_date__gte=month_start)
    this_month_count = this_month_workouts.count()
    this_month_output = sum(safe_get_output(w) for w in this_month_workouts) or 0
    this_month_calories = sum(safe_get_calories(w) for w in this_month_workouts) or 0
    
    # Previous month (for comparison)
    if month_start.month == 1:
        previous_month_start = date(month_start.year - 1, 12, 1)
    else:
        previous_month_start = date(month_start.year, month_start.month - 1, 1)
    
    # Calculate end of previous month
    if previous_month_start.month == 12:
        previous_month_end = date(previous_month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        previous_month_end = date(previous_month_start.year, previous_month_start.month + 1, 1) - timedelta(days=1)
    
    previous_month_workouts = all_workouts.filter(completed_date__gte=previous_month_start, completed_date__lte=previous_month_end)
    previous_month_count = previous_month_workouts.count()
    previous_month_output = sum(safe_get_output(w) for w in previous_month_workouts) or 0
    
    # Calculate differences for comparison display
    last_7_days_diff = last_7_days_count - previous_7_days_count
    this_month_diff = this_month_count - previous_month_count
    
    # Convert data to JSON for JavaScript charts
    workouts_by_week_json = mark_safe(json.dumps([
        {
            'date': w['date'].strftime('%Y-%m-%d'),
            'count': w['count'],
            'total_output': w['total_output'],
            'total_calories': w['total_calories']
        }
        for w in workouts_by_week_list
    ]))
    workouts_by_type_json = mark_safe(json.dumps(workouts_by_type))
    
    context = {
        'active_challenge_instance': active_challenge_instance,
        'team_info': team_info,
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
        'recent_workouts': recent_workouts,
        # Peloton stats
        'peloton_stats': peloton_stats,
        'total_workouts_count': total_workouts_count,
        'workout_stats': workout_stats,
        'workouts_by_type': workouts_by_type_json,
        'workouts_by_week': workouts_by_week_json,
        'this_week_count': this_week_count,
        'this_week_output': this_week_output,
        'this_week_calories': this_week_calories,
        'last_7_days_count': last_7_days_count,
        'last_7_days_output': last_7_days_output,
        'previous_7_days_count': previous_7_days_count,
        'previous_7_days_output': previous_7_days_output,
        'this_month_count': this_month_count,
        'this_month_output': this_month_output,
        'this_month_calories': this_month_calories,
        'previous_month_count': previous_month_count,
        'previous_month_output': previous_month_output,
        'last_7_days_diff': last_7_days_diff,
        'this_month_diff': this_month_diff,
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

def privacy_policy(request):
    return render(request, "plans/privacy_policy.html")

def terms_and_conditions(request):
    return render(request, "plans/terms_and_conditions.html")

def features(request):
    return render(request, "plans/features.html")

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
    
    # Get Peloton workout data for Personal Records and monthly stats
    from workouts.models import Workout, WorkoutDetails, WorkoutPerformanceData
    from django.db.models import Max, Sum, Avg, Q
    from django.core.exceptions import ObjectDoesNotExist
    
    all_workouts = Workout.objects.filter(user=request.user).select_related('ride_detail', 'details', 'ride_detail__workout_type')
    
    # Helper function to safely get workout details
    def safe_get_details_value(workout, field_name, default=0):
        """Safely get a value from workout.details, returning default if details don't exist"""
        try:
            details = workout.details
            if details:
                value = getattr(details, field_name, None)
                return value if value is not None else default
        except (WorkoutDetails.DoesNotExist, AttributeError, ObjectDoesNotExist):
            pass
        return default
    
    # Calculate Personal Records (1 min, 3 min, 5 min, 10 min, 20 min power)
    # These are calculated from time-series performance data
    def calculate_power_records(workouts, months=3):
        """Calculate max power for different time intervals"""
        cutoff_date = timezone.now().date() - timedelta(days=30 * months)
        cycling_workouts = workouts.filter(
            completed_date__gte=cutoff_date,
            ride_detail__fitness_discipline__in=['cycling', 'ride']
        ).prefetch_related('performance_data')
        
        records = {
            '1min': 0,
            '3min': 0,
            '5min': 0,
            '10min': 0,
            '20min': 0,
        }
        
        for workout in cycling_workouts:
            try:
                if not hasattr(workout, 'details') or not workout.details or not workout.details.total_output:
                    continue
            except (WorkoutDetails.DoesNotExist, AttributeError, ObjectDoesNotExist):
                continue
            
            # Get time-series performance data
            perf_data = list(workout.performance_data.filter(output__isnull=False).order_by('timestamp'))
            if not perf_data:
                continue
            
            # Convert to list of (timestamp, output) tuples
            data_points = [(p.timestamp, p.output) for p in perf_data if p.output]
            
            if not data_points:
                continue
            
            # Calculate rolling averages for different intervals
            intervals = [60, 180, 300, 600, 1200]  # 1min, 3min, 5min, 10min, 20min in seconds
            interval_keys = ['1min', '3min', '5min', '10min', '20min']
            
            for idx, interval_seconds in enumerate(intervals):
                max_avg = 0
                # Calculate rolling average for this interval
                # Assuming 5-second intervals, we need interval_seconds // 5 data points
                window_size = interval_seconds // 5
                for i in range(len(data_points) - window_size + 1):
                    window = data_points[i:i + window_size]
                    if len(window) == window_size:
                        avg_output = sum(p[1] for p in window) / len(window)
                        max_avg = max(max_avg, avg_output)
                
                if max_avg > records[interval_keys[idx]]:
                    records[interval_keys[idx]] = int(max_avg)
        
        return records
    
    # Calculate Personal Records for 1, 2, 3 months
    personal_records_1m = calculate_power_records(all_workouts, months=1)
    personal_records_2m = calculate_power_records(all_workouts, months=2)
    personal_records_3m = calculate_power_records(all_workouts, months=3)
    
    # Calculate monthly stats (this month)
    today = timezone.now().date()
    month_start = today.replace(day=1)
    this_month_workouts = all_workouts.filter(completed_date__gte=month_start)
    
    # This month stats by discipline
    this_month_cycling = this_month_workouts.filter(ride_detail__fitness_discipline__in=['cycling', 'ride'])
    this_month_running = this_month_workouts.filter(ride_detail__fitness_discipline__in=['running', 'run', 'walking'])
    
    # Cycling stats
    cycling_monthly_distance = sum(
        safe_get_details_value(w, 'distance') for w in this_month_cycling
    ) or 0
    cycling_monthly_output = sum(
        safe_get_details_value(w, 'total_output') for w in this_month_cycling
    ) or 0
    cycling_monthly_tss = sum(
        safe_get_details_value(w, 'tss') for w in this_month_cycling
    ) or 0
    
    # Running stats
    running_monthly_distance = sum(
        safe_get_details_value(w, 'distance') for w in this_month_running
    ) or 0
    running_monthly_output = sum(
        safe_get_details_value(w, 'total_output') for w in this_month_running
    ) or 0
    running_monthly_tss = sum(
        safe_get_details_value(w, 'tss') for w in this_month_running
    ) or 0
    
    # Yearly stats (all time)
    cycling_yearly_workouts = all_workouts.filter(ride_detail__fitness_discipline__in=['cycling', 'ride'])
    cycling_yearly_distance = sum(
        safe_get_details_value(w, 'distance') for w in cycling_yearly_workouts
    ) or 0
    cycling_yearly_output = sum(
        safe_get_details_value(w, 'total_output') for w in cycling_yearly_workouts
    ) or 0
    cycling_yearly_tss = sum(
        safe_get_details_value(w, 'tss') for w in cycling_yearly_workouts
    ) or 0
    
    running_yearly_workouts = all_workouts.filter(ride_detail__fitness_discipline__in=['running', 'run', 'walking'])
    running_yearly_distance = sum(
        safe_get_details_value(w, 'distance') for w in running_yearly_workouts
    ) or 0
    running_yearly_output = sum(
        safe_get_details_value(w, 'total_output') for w in running_yearly_workouts
    ) or 0
    running_yearly_tss = sum(
        safe_get_details_value(w, 'tss') for w in running_yearly_workouts
    ) or 0
    
    # Calculate average heart rate by workout type and overall
    def calculate_heart_rate_by_type(workouts, months=None):
        """Calculate average heart rate by workout type"""
        if months:
            cutoff_date = timezone.now().date() - timedelta(days=30 * months)
            workouts = workouts.filter(completed_date__gte=cutoff_date)
        
        # Get workouts with heart rate data
        heart_rate_workouts = workouts.filter(details__avg_heart_rate__isnull=False).select_related('ride_detail', 'ride_detail__workout_type', 'details')
        
        # Group by workout type
        hr_by_type = {}
        total_hr_sum = 0
        total_hr_count = 0
        
        for workout in heart_rate_workouts:
            try:
                hr = safe_get_details_value(workout, 'avg_heart_rate')
                if hr > 0:
                    # Determine workout type category
                    if workout.ride_detail:
                        fitness_discipline = workout.ride_detail.fitness_discipline or ''
                        workout_type_name = workout.ride_detail.workout_type.name if workout.ride_detail.workout_type else ''
                        
                        # Map to display categories
                        if fitness_discipline.lower() in ['cycling', 'ride'] or 'cycling' in workout_type_name.lower():
                            category = 'Cycling'
                        elif fitness_discipline.lower() in ['running', 'run', 'walking'] or 'running' in workout_type_name.lower() or 'tread' in workout_type_name.lower():
                            category = 'Tread'
                        else:
                            # Skip other types for now (can add more later)
                            continue
                    else:
                        continue
                    
                    if category not in hr_by_type:
                        hr_by_type[category] = {'sum': 0, 'count': 0}
                    
                    hr_by_type[category]['sum'] += hr
                    hr_by_type[category]['count'] += 1
                    total_hr_sum += hr
                    total_hr_count += 1
            except (WorkoutDetails.DoesNotExist, AttributeError, ObjectDoesNotExist):
                continue
        
        # Calculate averages
        result = {}
        for category, data in hr_by_type.items():
            result[category] = int(data['sum'] / data['count']) if data['count'] > 0 else 0
        
        # Overall average
        result['overall'] = int(total_hr_sum / total_hr_count) if total_hr_count > 0 else 0
        
        return result
    
    # Calculate heart rate for different time periods
    hr_this_month = calculate_heart_rate_by_type(all_workouts, months=None)  # This month
    hr_1m = calculate_heart_rate_by_type(all_workouts, months=1)
    hr_2m = calculate_heart_rate_by_type(all_workouts, months=2)
    hr_3m = calculate_heart_rate_by_type(all_workouts, months=3)
    
    # Legacy support - overall average
    avg_heart_rate = hr_this_month.get('overall')
    
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
        # Personal Records
        'personal_records_1m': personal_records_1m,
        'personal_records_2m': personal_records_2m,
        'personal_records_3m': personal_records_3m,
        # Monthly stats
        'cycling_monthly_distance': cycling_monthly_distance,
        'cycling_monthly_output': cycling_monthly_output,
        'cycling_monthly_tss': cycling_monthly_tss,
        'cycling_yearly_distance': cycling_yearly_distance,
        'cycling_yearly_output': cycling_yearly_output,
        'cycling_yearly_tss': cycling_yearly_tss,
        'running_monthly_distance': running_monthly_distance,
        'running_monthly_output': running_monthly_output,
        'running_monthly_tss': running_monthly_tss,
        'running_yearly_distance': running_yearly_distance,
        'running_yearly_output': running_yearly_output,
        'running_yearly_tss': running_yearly_tss,
        # Heart rate
        'avg_heart_rate': avg_heart_rate,
        'hr_this_month': hr_this_month,
        'hr_1m': hr_1m,
        'hr_2m': hr_2m,
        'hr_3m': hr_3m,
    }
    
    # Convert Personal Records to JSON for JavaScript
    context['personal_records_1m'] = mark_safe(json.dumps(personal_records_1m))
    context['personal_records_2m'] = mark_safe(json.dumps(personal_records_2m))
    context['personal_records_3m'] = mark_safe(json.dumps(personal_records_3m))
    
    # Convert Heart Rate data to JSON for JavaScript
    context['hr_this_month'] = mark_safe(json.dumps(hr_this_month))
    context['hr_1m'] = mark_safe(json.dumps(hr_1m))
    context['hr_2m'] = mark_safe(json.dumps(hr_2m))
    context['hr_3m'] = mark_safe(json.dumps(hr_3m))
    
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
            next_milestone = None
            progress_percentage = 0
            
            # Check which milestones are achieved and find next uncompleted milestone
            for i, threshold in enumerate(milestone_thresholds):
                if count >= threshold:
                    achieved.append(threshold)
                else:
                    # This is the next uncompleted milestone
                    if next_milestone is None:
                        next_milestone = threshold
                        # Calculate progress: how far from previous milestone (or 0) to next milestone
                        previous_threshold = milestone_thresholds[i - 1] if i > 0 else 0
                        if next_milestone > previous_threshold:
                            progress = (count - previous_threshold) / (next_milestone - previous_threshold)
                            progress_percentage = min(100, max(0, int(progress * 100)))
                    break
            
            peloton_milestones.append({
                'name': category_info['name'],
                'icon': category_info['icon'],
                'count': count,
                'achieved': achieved,
                'thresholds': milestone_thresholds,
                'next_milestone': next_milestone,
                'progress_percentage': progress_percentage,
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
                'next_milestone': 10,  # First milestone
                'progress_percentage': 0,
            })
    
    context['peloton_milestones'] = peloton_milestones
    
    return render(request, "plans/metrics.html", context)