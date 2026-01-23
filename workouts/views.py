from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from datetime import date

from .models import Workout, WorkoutType, Instructor, PelotonConnection


@login_required
def workout_history(request):
    """Display user's workout history with filtering and pagination"""
    # Get user's workouts
    workouts = Workout.objects.filter(user=request.user).select_related(
        'workout_type', 'instructor', 'metrics'
    ).prefetch_related('performance_data')
    
    # Get Peloton connection status
    try:
        peloton_connection = request.user.peloton_connection
    except PelotonConnection.DoesNotExist:
        peloton_connection = None
    
    # Search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        workouts = workouts.filter(
            Q(title__icontains=search_query) |
            Q(instructor__name__icontains=search_query)
        )
    
    # Filter by workout type
    workout_type_filter = request.GET.get('type', '')
    if workout_type_filter:
        workouts = workouts.filter(workout_type__slug=workout_type_filter)
    
    # Filter by instructor
    instructor_filter = request.GET.get('instructor', '')
    if instructor_filter:
        workouts = workouts.filter(instructor_id=instructor_filter)
    
    # Filter by duration
    duration_filter = request.GET.get('duration', '')
    if duration_filter:
        try:
            duration_min = int(duration_filter)
            workouts = workouts.filter(duration_minutes=duration_min)
        except ValueError:
            pass
    
    # Ordering
    order_by = request.GET.get('order_by', '-completed_date')
    if order_by in ['completed_date', '-completed_date', 'recorded_date', '-recorded_date', 'title', '-title']:
        workouts = workouts.order_by(order_by)
    else:
        workouts = workouts.order_by('-completed_date')
    
    # Pagination
    paginator = Paginator(workouts, 12)  # 12 workouts per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    workout_types = WorkoutType.objects.all().order_by('name')
    instructors = Instructor.objects.filter(
        workouts__user=request.user
    ).distinct().order_by('name')
    
    # Get unique durations for filter
    durations = Workout.objects.filter(user=request.user).values_list(
        'duration_minutes', flat=True
    ).distinct().order_by('duration_minutes')
    
    context = {
        'workouts': page_obj,
        'workout_types': workout_types,
        'instructors': instructors,
        'durations': durations,
        'peloton_connection': peloton_connection,
        'search_query': search_query,
        'workout_type_filter': workout_type_filter,
        'instructor_filter': instructor_filter,
        'duration_filter': duration_filter,
        'order_by': order_by,
        'total_workouts': paginator.count,
    }
    
    return render(request, 'workouts/history.html', context)


@login_required
def workout_detail(request, pk):
    """Display detailed view of a single workout"""
    workout = get_object_or_404(
        Workout.objects.select_related('workout_type', 'instructor', 'metrics')
        .prefetch_related('performance_data'),
        pk=pk,
        user=request.user
    )
    
    # Get performance data ordered by timestamp
    performance_data = workout.performance_data.all().order_by('timestamp')
    
    context = {
        'workout': workout,
        'performance_data': performance_data,
    }
    
    return render(request, 'workouts/detail.html', context)


@login_required
def connect(request):
    """Connect Peloton account"""
    # This will be implemented when Peloton API integration is added
    # For now, just a placeholder
    messages.info(request, "Peloton account connection will be available when Peloton API integration is complete.")
    return redirect('workouts:history')


@login_required
def sync_workouts(request):
    """Trigger manual sync of workouts from Peloton API"""
    # This will be implemented when Peloton API integration is added
    # For now, just a placeholder
    
    if request.method == 'POST':
        # TODO: Implement Peloton API sync
        messages.info(request, "Workout sync functionality will be available when Peloton API integration is complete.")
        return redirect('workouts:history')
    
    return redirect('workouts:history')
