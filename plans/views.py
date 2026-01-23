from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from datetime import date, timedelta
from collections import defaultdict
from .models import Exercise
from tracker.models import ChallengeInstance, WeeklyPlan
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
    ).first()
    
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
        show_recent_plans = recent_plans.exists()
    else:
        # No challenge involvement - set defaults
        all_plans = WeeklyPlan.objects.none()
        total_points = 0
        total_weeks_completed = 0
        total_weeks = 0
        recent_plans = WeeklyPlan.objects.none()
        upcoming_plans = WeeklyPlan.objects.none()
        show_recent_plans = False
    
    context = {
        'active_challenge_instance': active_challenge_instance,
        'current_week_plan': current_week_plan,
        'total_points': total_points,
        'total_weeks_completed': total_weeks_completed,
        'total_weeks': total_weeks,
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
    from accounts.models import WeightEntry
    
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
    }
    
    return render(request, "plans/metrics.html", context)