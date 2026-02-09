from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q

from .models import RideDetail, ClassType, Instructor, WorkoutType
from peloton.models import PelotonConnection
from .tasks import store_ride_detail_from_api
from classes.services.filters import ClassLibraryFilter


ORDERING_CHOICES = [
    ('-original_air_time', 'Newest first'),
    ('original_air_time', 'Oldest first'),
    ('title', 'Title A → Z'),
    ('-title', 'Title Z → A'),
    ('duration_seconds', 'Shortest duration'),
    ('-duration_seconds', 'Longest duration'),
]


@staff_member_required
def admin_library(request):
    """Admin view for managing the RideDetail library.

    Supports filters: search (title), class_type, power_zone flag, missing targets.
    Actions (POST): repull, set_class_type, mark_power_zone
    """
    base_queryset = (
        RideDetail.objects.exclude(peloton_ride_id__startswith='manual_')
        .select_related('instructor', 'workout_type')
    )
    qs = base_queryset.order_by('-original_air_time')
    is_hx = bool(request.headers.get('HX-Request'))
    request_params = request.POST if request.method == 'POST' else request.GET

    # Filters
    search = request_params.get('search', '').strip()
    workout_type = request_params.get('type', '').strip()
    instructor = request_params.get('instructor', '').strip()
    duration = request_params.get('duration', '').strip()
    year = request_params.get('year', '').strip()
    month = request_params.get('month', '').strip()
    order_by = request_params.get('order_by', '-original_air_time')
    power_zone = request_params.get('power_zone', '')
    missing_targets = request_params.get('missing_targets', '')

    # Apply class-library style filters via ClassLibraryFilter helper for consistency
    class_filter = ClassLibraryFilter(qs)
    class_filter.apply_search(search)
    class_filter.apply_instructor_filter(instructor)
    class_filter.apply_duration_filter(duration)
    class_filter.apply_year_filter(year)
    class_filter.apply_month_filter(year, month)
    class_filter.apply_ordering(order_by)
    qs = class_filter.get_queryset()
    filters = class_filter.get_filters()

    # Workout type filter should allow all slugs for admin view
    if workout_type:
        qs = qs.filter(workout_type__slug=workout_type)
        filters['workout_type'] = workout_type

    if power_zone == '1':
        qs = qs.filter(Q(class_type='power_zone') | Q(is_power_zone_class=True))
    if missing_targets == '1':
        qs = qs.filter(Q(target_metrics_data={}) | Q(target_metrics_data__isnull=True))

    # Handle actions
    if request.method == 'POST':
        action = request.POST.get('action')
        ride_id = request.POST.get('ride_id')
        if not ride_id:
            messages.error(request, 'No ride specified for action')
            return redirect('classes:admin')

        rd = get_object_or_404(RideDetail, peloton_ride_id=ride_id)

        if action == 'repull':
            conn = PelotonConnection.objects.filter(is_active=True).first()
            if not conn:
                messages.error(request, 'No active Peloton connection available to repull')
            else:
                client = conn.get_client()
                res = store_ride_detail_from_api(client, rd.peloton_ride_id)
                if res.get('status') == 'success':
                    messages.success(request, f'Repulled {rd.peloton_ride_id}')
                else:
                    messages.error(request, f"Repull failed: {res.get('message')}")

        elif action == 'set_class_type':
            new_type = request.POST.get('new_class_type')
            if new_type:
                rd.class_type = new_type
                rd.save()
                messages.success(request, f"Set class_type for {rd.peloton_ride_id} to {new_type}")
            else:
                messages.error(request, 'No class type provided')

        elif action == 'mark_power_zone':
            rd.class_type = 'power_zone'
            rd.is_power_zone_class = True
            rd.save()
            messages.success(request, f"Marked {rd.peloton_ride_id} as Power Zone")

        elif action == 'mark_pace_target':
            rd.class_type = 'pace_target'
            rd.save()
            messages.success(request, f"Marked {rd.peloton_ride_id} as Pace Target")

        if not is_hx:
            return redirect('classes:admin')

    # Show full list (no pagination) as requested
    all_rides = qs

    # Class type options (from ClassType table and choices)
    class_types = list(ClassType.objects.filter(is_active=True).order_by('fitness_discipline', 'name'))

    # Instructors and durations matching class library options
    instructors = (
        Instructor.objects.filter(ride_details__in=base_queryset)
        .distinct()
        .order_by('name')
    )
    durations = ClassLibraryFilter.get_available_durations(base_queryset)
    workout_types = (
        WorkoutType.objects.filter(ride_details__in=base_queryset)
        .distinct()
        .order_by('name')
    )

    available_years = ClassLibraryFilter.get_available_years(base_queryset)
    year_filter = filters.get('year', year)
    month_filter = filters.get('month', month)
    available_months = ClassLibraryFilter.get_available_months(base_queryset, year_filter) if year_filter else []

    search = filters.get('search', search)
    instructor_filter = filters.get('instructor', instructor)
    duration_filter = filters.get('duration', duration)
    order_by = filters.get('order_by', order_by)
    workout_type_filter = filters.get('workout_type', workout_type)

    ride_count = all_rides.count()
    total_ride_count = base_queryset.count()

    context = {
        'rides': all_rides,
        'ride_count': ride_count,
        'total_ride_count': total_ride_count,
        'search': search,
        'workout_type_filter': workout_type_filter,
        'instructor_filter': instructor_filter,
        'duration_filter': duration_filter,
        'power_zone_filter': power_zone,
        'missing_targets': missing_targets,
        'class_types': class_types,
        'instructors': instructors,
        'durations': durations,
        'workout_types': workout_types,
        'available_years': available_years,
        'available_months': available_months,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'order_by': order_by,
        'ordering_choices': ORDERING_CHOICES,
    }

    if is_hx:
        return render(request, 'workouts/partials/admin_class_list.html', context)
    return render(request, 'workouts/admin_library.html', context)
