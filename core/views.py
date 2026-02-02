from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import date, timedelta, datetime
from collections import defaultdict
import json
from tracker.models import WeeklyPlan
from challenges.models import ChallengeInstance
from core.services import DateRangeService, ZoneCalculatorService
from plans.services import get_dashboard_period, get_dashboard_challenge_context
from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS
from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS
from accounts.rowing_pace_levels_data import DEFAULT_ROWING_PACE_LEVELS

@login_required
def dashboard(request):
    # Get time period from request (default to 7d)
    period = request.GET.get('period', '7d')

    today = timezone.now().date()
    period_context = get_dashboard_period(period, today=today)
    start_date = period_context['start_date']
    period_label = period_context['period_label']
    period_description = period_context['period_description']
    comparison_label = period_context['comparison_label']
    comparison_start = period_context['comparison_start']
    comparison_end = period_context['comparison_end']
    
    current_week_start = DateRangeService.sunday_of_current_week(date.today())
    challenge_context = get_dashboard_challenge_context(
        user=request.user,
        current_week_start=current_week_start,
    )
    active_challenge_instance = challenge_context['active_challenge_instance']
    team_info = challenge_context['team_info']
    current_week_plan = challenge_context['current_week_plan']
    completed_challenges_count = challenge_context['completed_challenges_count']
    has_challenge_involvement = challenge_context['has_challenge_involvement']
    all_plans = challenge_context['all_plans']
    total_points = challenge_context['total_points']
    total_weeks_completed = challenge_context['total_weeks_completed']
    total_weeks = challenge_context['total_weeks']
    recent_plans = challenge_context['recent_plans']
    upcoming_plans = challenge_context['upcoming_plans']
    show_recent_plans = challenge_context['show_recent_plans']
    avg_completion_rate = challenge_context['avg_completion_rate']
    
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
    
    # Workouts over time (based on selected period, grouped by week)
    if start_date:
        period_workouts = all_workouts.filter(completed_date__gte=start_date)
    else:
        period_workouts = all_workouts  # All time
    
    # Group workouts by week for chart
    workouts_by_week = {}
    for workout in period_workouts:
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
    
    # Helper functions
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
    
    # Period workouts stats
    if start_date:
        period_workouts_filtered = all_workouts.filter(completed_date__gte=start_date)
    else:
        period_workouts_filtered = all_workouts
    
    period_count = period_workouts_filtered.count()
    period_output = sum(safe_get_output(w) for w in period_workouts_filtered) or 0
    
    # Comparison period stats
    if comparison_start and comparison_end:
        comparison_workouts = all_workouts.filter(completed_date__gte=comparison_start, completed_date__lt=comparison_end)
        comparison_count = comparison_workouts.count()
        comparison_output = sum(safe_get_output(w) for w in comparison_workouts) or 0
    else:
        comparison_count = 0
        comparison_output = 0
    
    period_diff = period_count - comparison_count
    
    # This week's workouts (for static card)
    week_start = today - timedelta(days=today.weekday())
    this_week_workouts = all_workouts.filter(
        completed_date__gte=week_start
    )
    this_week_count = this_week_workouts.count()
    this_week_output = sum(safe_get_output(w) for w in this_week_workouts) or 0
    this_week_calories = sum(safe_get_calories(w) for w in this_week_workouts) or 0
    
    # Last 7 days workouts (for backward compatibility)
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

    # Discipline KPIs (Running/Walking + Cycling) for selected period
    def _pace_str_from_mph(mph):
        try:
            mph = float(mph)
            if mph <= 0:
                return None
            pace_min_per_mile = 60.0 / mph
            minutes = int(pace_min_per_mile)
            seconds = int(round((pace_min_per_mile - minutes) * 60.0))
            if seconds == 60:
                minutes += 1
                seconds = 0
            return f"{minutes}:{seconds:02d}/mi"
        except Exception:
            return None

    cycling_period = period_workouts_filtered.filter(ride_detail__fitness_discipline__iexact='cycling')
    running_period = period_workouts_filtered.filter(ride_detail__fitness_discipline__iexact='running')
    walking_period = period_workouts_filtered.filter(ride_detail__fitness_discipline__iexact='walking')

    cycling_kpis_raw = cycling_period.aggregate(
        count=Count('id'),
        distance=Sum('details__distance'),
        total_output=Sum('details__total_output'),
        avg_output=Avg('details__avg_output'),
        tss=Sum('details__tss'),
        avg_cadence=Avg('details__avg_cadence'),
        avg_resistance=Avg('details__avg_resistance'),
        calories=Sum('details__total_calories'),
    )
    running_kpis_raw = running_period.aggregate(
        count=Count('id'),
        distance=Sum('details__distance'),
        avg_speed=Avg('details__avg_speed'),
        avg_heart_rate=Avg('details__avg_heart_rate'),
        calories=Sum('details__total_calories'),
    )
    walking_kpis_raw = walking_period.aggregate(
        count=Count('id'),
        distance=Sum('details__distance'),
        avg_speed=Avg('details__avg_speed'),
        avg_heart_rate=Avg('details__avg_heart_rate'),
        calories=Sum('details__total_calories'),
    )

    cycling_kpis = {
        'count': cycling_kpis_raw.get('count') or 0,
        'distance': cycling_kpis_raw.get('distance'),
        'total_output': cycling_kpis_raw.get('total_output'),
        'avg_output': cycling_kpis_raw.get('avg_output'),
        'tss': cycling_kpis_raw.get('tss'),
        'avg_cadence': cycling_kpis_raw.get('avg_cadence'),
        'avg_resistance': cycling_kpis_raw.get('avg_resistance'),
        'calories': cycling_kpis_raw.get('calories'),
    }

    avg_speed = running_kpis_raw.get('avg_speed')
    if not avg_speed:
        # Fallback: derive avg speed from time-series performance data if details.avg_speed is missing.
        try:
            from workouts.models import WorkoutPerformanceData
            avg_speed = WorkoutPerformanceData.objects.filter(
                workout__in=running_period,
                speed__isnull=False,
            ).aggregate(avg_speed=Avg('speed')).get('avg_speed')
        except Exception:
            avg_speed = None
    running_kpis = {
        'count': running_kpis_raw.get('count') or 0,
        'distance': running_kpis_raw.get('distance'),
        'avg_speed': avg_speed,
        'avg_pace_str': _pace_str_from_mph(avg_speed) if avg_speed else None,
        'avg_heart_rate': running_kpis_raw.get('avg_heart_rate'),
        'calories': running_kpis_raw.get('calories'),
    }

    avg_walk_speed = walking_kpis_raw.get('avg_speed')
    if not avg_walk_speed:
        try:
            from workouts.models import WorkoutPerformanceData
            avg_walk_speed = WorkoutPerformanceData.objects.filter(
                workout__in=walking_period,
                speed__isnull=False,
            ).aggregate(avg_speed=Avg('speed')).get('avg_speed')
        except Exception:
            avg_walk_speed = None
    walking_kpis = {
        'count': walking_kpis_raw.get('count') or 0,
        'distance': walking_kpis_raw.get('distance'),
        'avg_speed': avg_walk_speed,
        'avg_pace_str': _pace_str_from_mph(avg_walk_speed) if avg_walk_speed else None,
        'avg_heart_rate': walking_kpis_raw.get('avg_heart_rate'),
        'calories': walking_kpis_raw.get('calories'),
    }
    
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
        # Time period filter data
        'selected_period': period,
        'period_label': period_label,
        'period_description': period_description,
        'period_count': period_count,
        'period_output': period_output,
        'period_diff': period_diff,
        'comparison_label': comparison_label,
        'comparison_count': comparison_count,
        # Discipline KPI cards
        'cycling_kpis': cycling_kpis,
        'running_kpis': running_kpis,
        'walking_kpis': walking_kpis,
    }
    
    # If HTMX request, return only dashboard content partial
    if request.headers.get('HX-Request'):
        return render(request, 'plans/partials/dashboard_content.html', context)
    
    return render(request, "plans/dashboard.html", context)
