from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import date, datetime, timezone as dt_timezone
# Use datetime.timezone.utc (recommended for Django 4.2+, required for Django 5.0+)
UTC = dt_timezone.utc
import json
import re

# Timezone handling for date conversion (for converting workout dates to match Peloton's timezone)
try:
    from zoneinfo import ZoneInfo
    pytz = None
except ImportError:
    # Fallback for Python < 3.9
    ZoneInfo = None
    try:
        import pytz
    except ImportError:
        pytz = None

from .models import Workout, WorkoutType, Instructor, RideDetail, WorkoutDetails, Playlist
from .services.class_filter import ClassLibraryFilter
from .services.metrics import MetricsCalculator
from .services.chart_builder import ChartBuilder
from peloton.models import PelotonConnection
from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS, ZONE_COLORS
from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS, WALKING_ZONE_COLORS
from accounts.rowing_pace_levels_data import DEFAULT_ROWING_PACE_LEVELS, ROWING_ZONE_COLORS

# Import shared utilities from core.utils
from core.utils.pace_converter import (
    pace_zone_to_level,
    pace_str_from_mph,
    mph_from_pace_value,
    pace_zone_level_from_speed,
    scaled_pace_zone_value_from_speed,
    pace_zone_label_from_level,
    resolve_pace_context,
    PACE_ZONE_LEVEL_TO_KEY,
    PACE_ZONE_KEY_TO_LEVEL,
    PACE_ZONE_LEVEL_ORDER,
    PACE_ZONE_LEVEL_LABELS,
    PACE_ZONE_LEVEL_DISPLAY,
    PACE_ZONE_COLORS,
)
from core.utils.chart_helpers import (
    downsample_points,
    downsample_series,
    normalize_series_to_svg_points,
    scaled_zone_value_from_output,
)
from core.utils.workout_targets import (
    target_value_at_time,
    target_value_at_time_with_shift,
    target_segment_at_time_with_shift,
    extract_spin_up_intervals,
    calculate_target_line_from_segments,
    calculate_pace_target_line_from_segments,
    calculate_power_zone_target_line,
)

import logging

logger = logging.getLogger(__name__)

# Initialize service instances (stateless services)
metrics_calculator = MetricsCalculator()
chart_builder = ChartBuilder()


# Create wrapper functions with underscore prefix for backward compatibility
def _pace_zone_to_level(zone):
    """Wrapper for pace_zone_to_level from core.utils.pace_converter."""
    return pace_zone_to_level(zone)


def _pace_str_from_mph(mph):
    """Wrapper for pace_str_from_mph from core.utils.pace_converter."""
    return pace_str_from_mph(mph)


def _mph_from_pace_value(pace_value):
    """Wrapper for mph_from_pace_value from core.utils.pace_converter."""
    return mph_from_pace_value(pace_value)


def _pace_zone_level_from_speed(speed_mph, pace_ranges):
    """Wrapper for pace_zone_level_from_speed from core.utils.pace_converter."""
    return pace_zone_level_from_speed(speed_mph, pace_ranges)


def _scaled_pace_zone_value_from_speed(speed_mph, pace_ranges):
    """Wrapper for scaled_pace_zone_value_from_speed from core.utils.pace_converter."""
    return scaled_pace_zone_value_from_speed(speed_mph, pace_ranges)


def _pace_zone_label_from_level(level, uppercase=True):
    """Wrapper for pace_zone_label_from_level from core.utils.pace_converter."""
    return pace_zone_label_from_level(level, uppercase)


def _resolve_pace_context(user_profile, workout_date, discipline):
    """Wrapper for resolve_pace_context from core.utils.pace_converter."""
    return resolve_pace_context(user_profile, workout_date, discipline)


def _downsample_points(values, max_points=48):
    """Wrapper for downsample_points from core.utils.chart_helpers."""
    return downsample_points(values, max_points)


def _downsample_series(series, max_points=48):
    """Wrapper for downsample_series from core.utils.chart_helpers."""
    return downsample_series(series, max_points)


def _normalize_series_to_svg_points(
    series,
    width=360,
    height=120,
    left_pad=34,
    right_pad=10,
    top_pad=8,
    bottom_pad=8,
    *,
    preserve_full_series=False,
    max_points=120,
    scaled_min=None,
    scaled_max=None,
):
    """Wrapper for normalize_series_to_svg_points from core.utils.chart_helpers."""
    return normalize_series_to_svg_points(
        series, width, height, left_pad, right_pad, top_pad, bottom_pad,
        preserve_full_series=preserve_full_series, max_points=max_points,
        scaled_min=scaled_min, scaled_max=scaled_max
    )


def _scaled_zone_value_from_output(output_watts, zone_ranges):
    """Wrapper for scaled_zone_value_from_output from core.utils.chart_helpers."""
    return scaled_zone_value_from_output(output_watts, zone_ranges)


def _target_value_at_time(segments, t_seconds):
    """Wrapper for target_value_at_time from core.utils.workout_targets."""
    return target_value_at_time(segments, t_seconds)


def _target_value_at_time_with_shift(segments, t_seconds, shift_seconds=0):
    """Wrapper for target_value_at_time_with_shift from core.utils.workout_targets."""
    return target_value_at_time_with_shift(segments, t_seconds, shift_seconds)


def _target_segment_at_time_with_shift(segments, t_seconds, shift_seconds=0):
    """Wrapper for target_segment_at_time_with_shift from core.utils.workout_targets."""
    return target_segment_at_time_with_shift(segments, t_seconds, shift_seconds)


def _extract_spin_up_intervals(ride_detail):
    """Wrapper for extract_spin_up_intervals from core.utils.workout_targets."""
    return extract_spin_up_intervals(ride_detail)


def _calculate_target_line_from_segments(segments, zone_ranges, seconds_array, user_ftp=None, spin_up_intervals=None):
    """Wrapper for calculate_target_line_from_segments from core.utils.workout_targets."""
    # Pass zone_power_percentages from MetricsCalculator
    return calculate_target_line_from_segments(
        segments, zone_ranges, seconds_array, user_ftp, spin_up_intervals,
        zone_power_percentages=metrics_calculator.ZONE_POWER_PERCENTAGES
    )


def _calculate_pace_target_line_from_segments(segments, seconds_array):
    """Wrapper for calculate_pace_target_line_from_segments from core.utils.workout_targets."""
    return calculate_pace_target_line_from_segments(segments, seconds_array)


def _calculate_power_zone_target_line(target_metrics_list, user_ftp, seconds_array):
    """Wrapper for calculate_power_zone_target_line from core.utils.workout_targets."""
    # Pass zone_power_percentages from MetricsCalculator
    return calculate_power_zone_target_line(
        target_metrics_list, user_ftp, seconds_array,
        zone_power_percentages=metrics_calculator.ZONE_POWER_PERCENTAGES
    )


def detect_class_type(ride_data, ride_details=None):
    """
    Detect class type from Peloton API data.
    Checks multiple sources: is_power_zone, pace_target_type, title keywords, segment types.
    
    Args:
        ride_data: Data from ride API response
        ride_details: Optional full ride details response (for target_metrics_data)
    
    Returns:
        str: Class type key (e.g., 'power_zone', 'pace_target', 'climb', etc.) or None
    """
    # Priority 1: Check explicit flags
    if ride_data.get('is_power_zone_class') or ride_data.get('is_power_zone'):
        return 'power_zone'
    
    # Priority 2: Check pace_target_type for running/walking


@login_required
def workout_history(request):
    """Display user's workout history with filtering and pagination"""
    # Get user's workouts - all class data comes from ride_detail via SQL joins
    workouts = Workout.objects.filter(user=request.user).select_related(
        'ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details'
    )
    
    # Get Peloton connection status (from peloton app)
    try:
        peloton_connection = PelotonConnection.objects.get(user=request.user)
    except PelotonConnection.DoesNotExist:
        peloton_connection = None
    
    # Search query - all data comes from ride_detail via SQL joins
    search_query = request.GET.get('search', '').strip()
    if search_query:
        workouts = workouts.filter(
            Q(ride_detail__title__icontains=search_query) |
            Q(ride_detail__instructor__name__icontains=search_query)
        )
    
    # Filter by workout type - via ride_detail
    workout_type_filter = request.GET.get('type', '')
    if workout_type_filter:
        workouts = workouts.filter(ride_detail__workout_type__slug=workout_type_filter)
    
    # Filter by instructor - via ride_detail
    instructor_filter = request.GET.get('instructor', '')
    if instructor_filter:
        workouts = workouts.filter(ride_detail__instructor_id=instructor_filter)
    
    # Filter by duration - via ride_detail
    duration_filter = request.GET.get('duration', '')
    if duration_filter:
        try:
            duration_min = int(duration_filter)
            workouts = workouts.filter(
                Q(ride_detail__duration_seconds__gte=duration_min * 60 - 30) &
                Q(ride_detail__duration_seconds__lte=duration_min * 60 + 30)
            )
        except ValueError:
            pass
    
    # Filter by TSS (Training Stress Score) - via details
    tss_filter = request.GET.get('tss', '')
    if tss_filter:
        try:
            tss_value = float(tss_filter)
            workouts = workouts.filter(details__tss__gte=tss_value)
        except (ValueError, TypeError):
            pass

    # Filter by Peloton class type (from RideDetail.class_type_ids via ClassType model)
    # We support both:
    # - class_type=<peloton_id> (legacy/backward-compatible)
    # - class_type_name=<human name> (preferred; de-duplicates labels)
    class_type_filter = (request.GET.get('class_type', '') or '').strip()
    class_type_name_filter = (request.GET.get('class_type_name', '') or '').strip()
    class_type_label = None
    class_type_ids = []
    try:
        from workouts.models import ClassType
        if class_type_name_filter:
            class_type_label = class_type_name_filter
            class_type_ids = list(
                ClassType.objects.filter(is_active=True, name__iexact=class_type_name_filter)
                .values_list('peloton_id', flat=True)
            )
        elif class_type_filter:
            class_type_label = class_type_filter
            class_type_ids = [class_type_filter]
    except Exception:
        class_type_ids = [class_type_filter] if class_type_filter else []

    if class_type_ids:
        try:
            from django.db import connection
            vendor = getattr(connection, 'vendor', '')
            q_obj = Q()
            for ct_id in class_type_ids:
                if not ct_id:
                    continue
                if vendor in ['postgresql', 'mysql']:
                    q_obj |= Q(ride_detail__class_type_ids__contains=[ct_id])
                else:
                    token = f"\\\"{ct_id}\\\""
                    q_obj |= Q(ride_detail__class_type_ids__icontains=token)
            if q_obj:
                workouts = workouts.filter(q_obj)
        except Exception:
            # Fallback: OR across raw substring matches
            q_obj = Q()
            for ct_id in class_type_ids:
                if ct_id:
                    q_obj |= Q(ride_detail__class_type_ids__icontains=ct_id)
            if q_obj:
                workouts = workouts.filter(q_obj)

    # Filter: only workouts with performance charts (time-series data exists)
    has_charts_raw = (request.GET.get('has_charts', '') or '').strip().lower()
    has_charts_filter = has_charts_raw in ['1', 'true', 'yes', 'on']
    if has_charts_filter:
        try:
            from django.db.models import Exists, OuterRef
            from workouts.models import WorkoutPerformanceData

            workouts = workouts.annotate(
                has_charts=Exists(
                    # Only count as "charted" if we have usable series for our cards
                    # (stretches often only have HR, which we don't chart on cards)
                    WorkoutPerformanceData.objects.filter(workout_id=OuterRef('pk')).filter(
                        Q(output__isnull=False) | Q(speed__isnull=False)
                    )
                )
            ).filter(has_charts=True)
        except Exception:
            # Fallback: may create duplicates; keep stable ordering via distinct()
            workouts = workouts.filter(
                Q(performance_data__output__isnull=False) | Q(performance_data__speed__isnull=False)
            ).distinct()
    
    # Ordering - title ordering uses ride_detail__title via SQL join
    order_by = request.GET.get('order_by', '-completed_date')
    if order_by in ['completed_date', '-completed_date', 'recorded_date', '-recorded_date']:
        # Stable tie-breakers for same-day workouts.
        #
        # Workout IDs reflect sync insert order. Since the Peloton API list is typically newest-first,
        # the *smaller* ID can represent the more recent activity within the same completed_date.
        # Tie-break accordingly so "most recent activity on the day" comes first.
        tie_breaker = 'id' if order_by.startswith('-') else '-id'
        workouts = workouts.order_by(order_by, tie_breaker)
    elif order_by in ['title', '-title']:
        # Order by ride_detail title via SQL join
        workouts = workouts.order_by('ride_detail__title' if order_by == 'title' else '-ride_detail__title', '-id')
    else:
        workouts = workouts.order_by('-completed_date', 'id')
    
    # Pagination
    paginator = Paginator(workouts, 12)  # 12 workouts per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Prefetch time-series performance data ONLY for the current page (critical for performance)
    # and attach lightweight mini-chart data to each workout for rendering in cards.
    try:
        from django.db.models import Prefetch
        from workouts.models import WorkoutPerformanceData

        page_obj.object_list = page_obj.object_list.prefetch_related(
            Prefetch(
                'performance_data',
                queryset=WorkoutPerformanceData.objects.only(
                    'workout_id',
                    'timestamp',
                    'output',
                    'speed',
                    'power_zone',
                    'intensity_zone',
                ).order_by('timestamp'),
            )
        )
    except Exception:
        # If prefetch fails for any reason, continue without card charts.
        pass
    
    # Add pagination flag for template
    is_paginated = page_obj.has_other_pages()
    
    # Get filter options - all data comes from ride_detail via SQL joins
    workout_types = WorkoutType.objects.all().order_by('name')
    # Get instructors from ride_details (all workouts use ride_detail now)
    instructors = Instructor.objects.filter(
        ride_details__workouts__user=request.user
    ).distinct().order_by('name')
    
    # Get unique durations for filter (from ride_detail) - standard durations
    standard_durations = [5, 10, 15, 20, 30, 45, 60, 75, 90, 120]
    # Also get actual durations from user's workouts
    actual_durations = Workout.objects.filter(
        user=request.user,
        ride_detail__isnull=False
    ).values_list('ride_detail__duration_seconds', flat=True).distinct()
    # Convert to minutes and combine with standard durations
    actual_durations_min = sorted(set(int(d / 60) for d in actual_durations if d))
    # Combine and deduplicate, keeping standard durations first
    all_durations = sorted(set(standard_durations + actual_durations_min))
    
    # Get fitness disciplines for tabs (cycling, running, rowing, etc.)
    fitness_disciplines = Workout.objects.filter(
        user=request.user,
        ride_detail__isnull=False
    ).values_list('ride_detail__fitness_discipline', flat=True).distinct()
    fitness_disciplines = [d for d in fitness_disciplines if d]  # Remove empty values
    
    # Calculate sync status for template
    sync_in_progress = False
    sync_cooldown_until = None
    cooldown_remaining_minutes = None
    can_sync = True
    
    if peloton_connection:
        sync_in_progress = peloton_connection.sync_in_progress
        if peloton_connection.sync_cooldown_until and timezone.now() < peloton_connection.sync_cooldown_until:
            sync_cooldown_until = peloton_connection.sync_cooldown_until
            cooldown_remaining_minutes = int((peloton_connection.sync_cooldown_until - timezone.now()).total_seconds() / 60)
            can_sync = False
        if sync_in_progress:
            can_sync = False
    
    context = {
        'workouts': page_obj,
        'workout_types': workout_types,
        'instructors': instructors,
        'durations': all_durations,
        'fitness_disciplines': fitness_disciplines,
        'peloton_connection': peloton_connection,
        'sync_in_progress': sync_in_progress,
        'sync_cooldown_until': sync_cooldown_until,
        'cooldown_remaining_minutes': cooldown_remaining_minutes,
        'can_sync': can_sync,
        'search_query': search_query,
        'workout_type_filter': workout_type_filter,
        'instructor_filter': instructor_filter,
        'duration_filter': duration_filter,
        'tss_filter': tss_filter,
        'has_charts_filter': has_charts_filter,
        'class_type_filter': class_type_filter,
        'class_type_name_filter': class_type_name_filter,
        'class_type_label': class_type_label,
        'order_by': order_by,
        'total_workouts': paginator.count,
        'is_paginated': is_paginated,
        # Query strings for building links while preserving filters
        'qs_without_page': None,
        'qs_without_type_and_page': None,
        'qs_remove': {},
        'class_types_by_discipline': {},
    }

    # Class types for dropdown (grouped)
    try:
        from workouts.models import ClassType
        class_types = ClassType.objects.filter(is_active=True).order_by('fitness_discipline', 'name', 'peloton_id')
        grouped = {}
        seen = set()
        for ct in class_types:
            key = (ct.fitness_discipline or 'other').strip() or 'other'
            # De-dupe within a discipline by display name (Peloton can have multiple IDs with same name)
            sig = (key, (ct.name or '').strip().lower())
            if sig in seen:
                continue
            seen.add(sig)
            grouped.setdefault(key, []).append(ct)
        context['class_types_by_discipline'] = grouped
    except Exception:
        context['class_types_by_discipline'] = {}

    # Pre-compute querystrings for templates (preserve multi-filter combinations)
    try:
        qs = request.GET.copy()
        qs.pop('page', None)
        qs.pop('infinite', None)
        context['qs_without_page'] = qs.urlencode()

        qs2 = request.GET.copy()
        qs2.pop('page', None)
        qs2.pop('infinite', None)
        qs2.pop('type', None)
        context['qs_without_type_and_page'] = qs2.urlencode()

        # Query strings for removing a single filter while preserving others
        qs_remove = {}
        for key in ['search', 'instructor', 'duration', 'tss', 'has_charts', 'class_type', 'class_type_name', 'type', 'order_by']:
            q = request.GET.copy()
            q.pop('page', None)
            q.pop('infinite', None)
            q.pop(key, None)
            qs_remove[key] = q.urlencode()
        context['qs_remove'] = qs_remove
    except Exception:
        context['qs_without_page'] = ''
        context['qs_without_type_and_page'] = ''
        context['qs_remove'] = {}

    # Build per-card mini chart data (SVG sparkline + optional zone bands)
    try:
        user_profile = getattr(request.user, "profile", None)
        for w in page_obj.object_list:
            # Derived metrics for cards (avoid blanks when Peloton didn't send metrics)
            w.derived_tss = _estimate_workout_tss(w, user_profile=user_profile)
            w.derived_avg_speed = _estimate_workout_avg_speed_mph(w)
            w.card_chart = _build_workout_card_chart(w, user_profile=user_profile)
    except Exception:
        # Keep page usable even if chart derivation fails for an edge case.
        pass
    
    # Otherwise return full page
    return render(request, 'workouts/history.html', context)


@login_required
def workout_history_suggest(request):
    """
    Lightweight JSON suggestions for the workout history search box.
    Returns titles and instructor names matching the query.
    """
    from django.http import JsonResponse
    from django.db.models import Q

    q = (request.GET.get('q', '') or '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    # Guard against expensive regex / huge inputs
    if len(q) > 64:
        q = q[:64]

    # Build a safe "fuzzy" regex: characters in order, allowing gaps.
    # Example: "pzr" -> "p.*z.*r"
    import re
    q_compact = re.sub(r"\s+", "", q)
    # Keep alphanumerics only for the regex pattern to avoid special chars
    q_alnum = re.sub(r"[^0-9A-Za-z]+", "", q_compact)
    fuzzy_regex = None
    if len(q_alnum) >= 2 and len(q_alnum) <= 32:
        fuzzy_regex = ".*".join(re.escape(ch) for ch in q_alnum)

    base = Workout.objects.filter(user=request.user, ride_detail__isnull=False).select_related(
        'ride_detail', 'ride_detail__instructor'
    )
    base = base.filter(
        Q(ride_detail__title__icontains=q) |
        Q(ride_detail__instructor__name__icontains=q) |
        (
            Q(ride_detail__title__iregex=fuzzy_regex) |
            Q(ride_detail__instructor__name__iregex=fuzzy_regex)
        if fuzzy_regex else Q()
        )
    )

    titles = list(
        base.order_by('ride_detail__title')
        .values_list('ride_detail__title', flat=True)
        .distinct()[:7]
    )
    instructors = list(
        base.exclude(ride_detail__instructor__name__isnull=True)
        .order_by('ride_detail__instructor__name')
        .values_list('ride_detail__instructor__name', flat=True)
        .distinct()[:5]
    )

    results = [{'label': t, 'value': t, 'kind': 'title'} for t in titles if t]
    results.extend([{'label': f'Instructor: {n}', 'value': n, 'kind': 'instructor'} for n in instructors if n])

    return JsonResponse({'results': results})




def _estimate_workout_avg_speed_mph(workout):
    """Estimate avg speed (mph) from details or time-series speed."""
    try:
        details = getattr(workout, "details", None)
        if details and getattr(details, "avg_speed", None) is not None:
            return float(details.avg_speed)
    except Exception:
        pass

    try:
        perf = list(workout.performance_data.all())
    except Exception:
        perf = []
    speeds = []
    for p in perf:
        v = getattr(p, "speed", None)
        if isinstance(v, (int, float)):
            speeds.append(float(v))
    if not speeds:
        return None
    return sum(speeds) / float(len(speeds))




def _estimate_workout_if_from_tss(workout):
    """
    Estimate IF from stored TSS + duration when available.
    
    Delegates to MetricsCalculator service.
    """
    try:
        details = getattr(workout, "details", None)
        tss = getattr(details, "tss", None) if details else None
        if tss is None:
            return None
        ride = getattr(workout, "ride_detail", None)
        duration_seconds = getattr(ride, "duration_seconds", None) if ride else None
        if not isinstance(duration_seconds, int) or duration_seconds <= 0:
            return None
        
        return metrics_calculator.calculate_intensity_factor(
            tss=tss,
            duration_seconds=duration_seconds
        )
    except Exception:
        return None


def _estimate_workout_tss(workout, user_profile=None):
    """
    Estimate cycling TSS when Peloton didn't provide it.

    Uses a common approximation:
      IF ≈ avg_power / FTP
      TSS ≈ hours * IF^2 * 100
    
    Delegates to MetricsCalculator service.
    """
    ride = getattr(workout, "ride_detail", None)
    if not ride:
        return None

    discipline = (getattr(ride, "fitness_discipline", "") or "").lower()
    if discipline not in ["cycling", "ride", "bike", "bike_bootcamp", "circuit"]:
        return None

    # Prefer stored avg_output if available
    avg_power = None
    try:
        details = getattr(workout, "details", None)
        if details and getattr(details, "avg_output", None) is not None:
            avg_power = float(details.avg_output)
        if details and getattr(details, "tss", None) is not None:
            return float(details.tss)
    except Exception:
        pass

    try:
        perf = list(workout.performance_data.all())
    except Exception:
        perf = []
    outputs = []
    max_t = None
    for p in perf:
        t = getattr(p, "timestamp", None)
        if isinstance(t, int):
            max_t = t if max_t is None else max(max_t, t)
        v = getattr(p, "output", None)
        if isinstance(v, (int, float)):
            outputs.append(float(v))

    if avg_power is None:
        if not outputs:
            return None
        avg_power = sum(outputs) / float(len(outputs))

    # Duration: prefer class duration; fallback to last timestamp
    duration_seconds = getattr(ride, "duration_seconds", None)
    if not isinstance(duration_seconds, int) or duration_seconds <= 0:
        duration_seconds = (max_t + 1) if isinstance(max_t, int) else None
    if not duration_seconds or duration_seconds <= 0:
        return None

    # FTP at workout date
    ftp = None
    workout_date = getattr(workout, "completed_date", None) or getattr(workout, "recorded_date", None)
    if user_profile and workout_date and hasattr(user_profile, "get_ftp_at_date"):
        try:
            ftp = user_profile.get_ftp_at_date(workout_date)
        except Exception:
            ftp = None
    if not ftp and user_profile and hasattr(user_profile, "get_current_ftp"):
        try:
            ftp = user_profile.get_current_ftp()
        except Exception:
            ftp = None
    
    # Use MetricsCalculator for TSS calculation
    return metrics_calculator.calculate_tss(
        avg_power=avg_power,
        duration_seconds=duration_seconds,
        ftp=ftp
    )






def _zone_ranges_for_ftp(ftp):
    """
    Return power zone ranges dict from FTP.
    
    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_power_zone_ranges(ftp)


def _power_zone_for_output(output_watts, zone_ranges):
    """
    Return zone number 1-7 for an output value given zone_ranges.
    
    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_power_zone_for_output(output_watts, zone_ranges)




def _pace_zone_targets_for_level(pace_level):
    """
    Build pace zone targets (min/mile) from a pace level (1-10),
    matching Profile.get_pace_zone_targets().
    
    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_pace_zone_targets(pace_level)


def _target_watts_for_zone(zone_ranges, zone_num):
    """
    Get target watts (midpoint) for a power zone.
    
    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_target_watts_for_zone(zone_num, zone_ranges)


















def _build_workout_card_chart(workout, user_profile=None):
    """
    Build lightweight mini-chart data for workout cards.
    Output is a dict that templates can render as an inline SVG.
    """
    ride = getattr(workout, 'ride_detail', None)
    if not ride:
        return None

    perf = list(getattr(workout, 'performance_data', []).all() if hasattr(workout, 'performance_data') else [])
    if not perf:
        return None

    discipline = (getattr(ride, 'fitness_discipline', '') or '').lower()
    class_type = (getattr(ride, 'class_type', '') or '').lower()
    is_power_zone = bool(getattr(ride, 'is_power_zone_class', False) or class_type == 'power_zone')
    is_pace = class_type == 'pace_target' or discipline in ['running', 'run', 'walking', 'walk']
    is_cycling = discipline in ['cycling', 'ride', 'bike']
    workout_date = getattr(workout, 'completed_date', None) or getattr(workout, 'recorded_date', None)
    user_ftp = None
    if user_profile and workout_date and hasattr(user_profile, "get_ftp_at_date"):
        try:
            user_ftp = user_profile.get_ftp_at_date(workout_date)
        except Exception:
            user_ftp = None
    zone_ranges = _zone_ranges_for_ftp(user_ftp) if user_ftp else None
    pace_context = None
    pace_ranges = None
    pace_zone_thresholds = None
    pace_level_value = None
    activity_type = None
    if is_pace:
        pace_context = _resolve_pace_context(user_profile, workout_date, discipline)
        if isinstance(pace_context, dict):
            activity_type = pace_context.get('activity_type')
            pace_ranges = pace_context.get('pace_ranges') or None
            pace_zone_thresholds = pace_context.get('pace_zone_thresholds') or None
            pace_level_value = pace_context.get('pace_level')

    # Decide which series to chart
    metric_key = None
    chart_kind = None
    if is_pace:
        metric_key = 'speed'
        chart_kind = 'pace'
        line_color = "rgba(253, 224, 71, 0.95)"  # yellow-300
    elif is_cycling:
        metric_key = 'output'
        chart_kind = 'power_zone' if is_power_zone else 'cycling_output_zones'
        line_color = "rgba(253, 224, 71, 0.95)"  # yellow-300
    else:
        return None

    series = []
    for p in perf:
        t = getattr(p, 'timestamp', None)
        v = getattr(p, metric_key, None)
        if not isinstance(t, int):
            continue
        if not isinstance(v, (int, float)):
            continue
        point = {'t': int(t), 'v': float(v)}
        if chart_kind == 'power_zone':
            z = getattr(p, 'power_zone', None)
            if isinstance(z, int):
                point['z'] = z
            else:
                # Fallback: compute from FTP if power_zone field missing
                zc = _power_zone_for_output(point['v'], zone_ranges)
                if isinstance(zc, int):
                    point['z'] = zc
        elif chart_kind == 'pace':
            z = getattr(p, 'intensity_zone', None)
            if isinstance(z, str) and z:
                point['z'] = z
                lvl = _pace_zone_to_level(z)
                if isinstance(lvl, int):
                    point['sv'] = float(lvl)
            if pace_ranges:
                sv = _scaled_pace_zone_value_from_speed(point['v'], pace_ranges)
                if sv is not None:
                    point['sv'] = sv
                if not point.get('z'):
                    lvl = _pace_zone_level_from_speed(point['v'], pace_ranges)
                    label = _pace_zone_label_from_level(lvl) if lvl else None
                    if label:
                        point['z'] = label
        elif chart_kind == 'cycling_output_zones':
            # Non–PZ cycling should follow power zones (not pace/intensity bands)
            zc = _power_zone_for_output(point['v'], zone_ranges)
            if isinstance(zc, int):
                point['z'] = zc
        if chart_kind in ['power_zone', 'cycling_output_zones']:
            scaled_sv = _scaled_zone_value_from_output(point['v'], zone_ranges)
            if scaled_sv is not None:
                point['sv'] = scaled_sv
            elif isinstance(point.get('z'), int):
                point['sv'] = float(point['z'])
        series.append(point)

    scaled_min = None
    scaled_max = None
    display_max_zone = 7
    if chart_kind in ['power_zone', 'cycling_output_zones', 'pace']:
        scaled_min = 0.5
        scaled_max = display_max_zone + 0.5

    # Build target segments (optional)
    target_segments = None
    TARGET_TIME_SHIFT_SECONDS = -60  # intro is within target metrics; shift targets earlier
    try:
        if chart_kind == 'power_zone' and user_ftp and hasattr(ride, 'get_power_zone_segments'):
            pz_segments = ride.get_power_zone_segments(user_ftp=user_ftp)
            target_segments = []
            for seg in (pz_segments or []):
                z = seg.get('zone')
                try:
                    z = int(z)
                except Exception:
                    z = None
                tv = _target_watts_for_zone(zone_ranges, z) if z else None
                target_segments.append({
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'target': tv,
                    'zone': z,
                })
        elif chart_kind == 'pace' and hasattr(ride, 'get_pace_segments'):
            pace_zones = pace_zone_thresholds
            if not pace_zones:
                fallback_level = pace_level_value or 5
                pace_zones = _pace_zone_targets_for_level(fallback_level)
            pace_segments = ride.get_pace_segments(user_pace_zones=pace_zones)
            target_segments = []
            for seg in (pace_segments or []):
                raw_zone = seg.get('zone') or seg.get('zone_name') or seg.get('pace_level')
                zone_level = _pace_zone_to_level(raw_zone)
                tv = None
                for key in ('target_speed_mph', 'target_mph'):
                    value = seg.get(key)
                    if isinstance(value, (int, float)):
                        tv = float(value)
                        break
                if tv is None:
                    tv = _mph_from_pace_value(seg.get('pace_range') or seg.get('pace_target'))
                if tv is None and pace_ranges and isinstance(zone_level, int):
                    zone_meta = pace_ranges.get(zone_level)
                    if zone_meta:
                        tv = zone_meta.get('mid_mph')
                target_segments.append({
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'target': tv,
                    'zone': seg.get('zone'),
                    'zone_name': seg.get('zone_name'),
                    'zone_level': zone_level,
                })
    except Exception:
        target_segments = None

    # Attach target values to points (so scaling includes them and tooltip can show them)
    if target_segments:
        for pt in series:
            t = pt.get('t')
            if isinstance(t, int):
                seg = _target_segment_at_time_with_shift(target_segments, t, shift_seconds=TARGET_TIME_SHIFT_SECONDS)
                if not isinstance(seg, dict):
                    continue

                tv = seg.get('target')
                if isinstance(tv, (int, float)):
                    pt['tv'] = float(tv)

                # Scaled target for zone-space plotting
                if chart_kind in ['power_zone', 'cycling_output_zones']:
                    stv = _scaled_zone_value_from_output(tv, zone_ranges) if isinstance(tv, (int, float)) else None
                    if stv is None:
                        zt = seg.get('zone')
                        try:
                            zt = int(zt) if zt is not None else None
                        except Exception:
                            zt = None
                        if isinstance(zt, int) and 1 <= zt <= 7:
                            stv = float(zt)
                    if isinstance(stv, (int, float)):
                        pt['stv'] = stv
                elif chart_kind == 'pace':
                    stv = None
                    if isinstance(tv, (int, float)) and pace_ranges:
                        stv = _scaled_pace_zone_value_from_speed(tv, pace_ranges)
                    if stv is None:
                        lvl = seg.get('zone_level') or _pace_zone_to_level(seg.get('zone') or seg.get('zone_name'))
                        if isinstance(lvl, int):
                            stv = float(lvl)
                    if isinstance(stv, (int, float)):
                        pt['stv'] = stv

    if chart_kind in ['power_zone', 'cycling_output_zones', 'pace']:
        zone_cap = 7
        max_zone_hit = 0

        def _apply_zone_candidate(candidate):
            nonlocal max_zone_hit
            if candidate is None:
                return
            if chart_kind == 'pace' and not isinstance(candidate, (int, float)):
                lvl = _pace_zone_to_level(candidate)
            else:
                try:
                    lvl = int(round(float(candidate)))
                except Exception:
                    lvl = None
            if isinstance(lvl, int) and 1 <= lvl <= zone_cap:
                max_zone_hit = max(max_zone_hit, lvl)

        for pt in series:
            if isinstance(pt.get('sv'), (int, float)):
                _apply_zone_candidate(pt.get('sv'))
            else:
                _apply_zone_candidate(pt.get('z'))

        if target_segments:
            for seg in target_segments or []:
                candidate = None
                if isinstance(seg, dict):
                    candidate = seg.get('zone_level')
                    if candidate is None:
                        candidate = seg.get('zone') or seg.get('zone_name')
                _apply_zone_candidate(candidate)

        if max_zone_hit > 0:
            display_max_zone = min(zone_cap, max_zone_hit + 2)
        scaled_min = 0.5
        scaled_max = display_max_zone + 0.5

    width = 420
    height = 150
    preserve_full_series = chart_kind in ['power_zone', 'cycling_output_zones', 'pace']
    points_str, plot_box, points_list, vmin, vmax = _normalize_series_to_svg_points(
        series,
        width=width,
        height=height,
        left_pad=0,
        right_pad=0,
        top_pad=6,
        bottom_pad=8,
        preserve_full_series=preserve_full_series,
        max_points=120,
        scaled_min=scaled_min,
        scaled_max=scaled_max,
    )
    if not points_str:
        return None

    plot_x0, plot_y0, plot_x1, plot_y1 = plot_box
    plot_w = plot_x1 - plot_x0
    plot_h = plot_y1 - plot_y0
    plot_h = plot_y1 - plot_y0

    bands = []
    labels = []

    if is_pace:
        zone_levels = list(range(display_max_zone, 0, -1)) or list(reversed(PACE_ZONE_LEVEL_ORDER))
        band_h = plot_h / float(len(zone_levels)) if zone_levels else plot_h
        for idx, level in enumerate(zone_levels):
            bands.append({
                'y': plot_y0 + idx * band_h,
                'h': band_h,
                'fill': PACE_ZONE_COLORS.get(level, "rgba(59, 130, 246, 0.55)"),
                'label': _pace_zone_label_from_level(level) or f"Zone {level}",
                'label_y': plot_y0 + idx * band_h + band_h / 2.0,
            })

    elif chart_kind in ['power_zone', 'cycling_output_zones']:
        zone_colors = {
            7: "rgba(239, 68, 68, 0.45)",   # red-500
            6: "rgba(249, 115, 22, 0.45)",  # orange-500
            5: "rgba(245, 158, 11, 0.45)",  # amber-500
            4: "rgba(34, 197, 94, 0.45)",   # green-500
            3: "rgba(20, 184, 166, 0.45)",  # teal-500
            2: "rgba(59, 130, 246, 0.45)",  # blue-500
            1: "rgba(124, 58, 237, 0.45)",  # violet-600
        }
        top_zone = display_max_zone or 7
        top_zone = max(1, min(7, top_zone))
        zone_range = list(range(top_zone, 0, -1))
        band_h = plot_h / float(len(zone_range))
        for idx, zone in enumerate(zone_range):
            bands.append({
                'y': plot_y0 + idx * band_h,
                'h': band_h,
                'fill': zone_colors.get(zone, zone_colors[1]),
                'label': f"Zone {zone}",
                'label_y': plot_y0 + idx * band_h + band_h / 2.0,
            })

    # Safe JSON for inline script blocks in templates
    try:
        from django.utils.safestring import mark_safe
        series_json = mark_safe(json.dumps(points_list))
    except Exception:
        series_json = "[]"

    # Build target polyline string if targets exist (stepped line for 90-degree angles)
    target_points = None
    if points_list and any(isinstance(p.get('tv'), (int, float)) for p in points_list):
        try:
            plot_x0, plot_y0, plot_x1, plot_y1 = plot_box
            if vmax == vmin:
                vmax = (vmin or 0) + 1.0

            def y_for(v):
                norm = (float(v) - float(vmin)) / float(float(vmax) - float(vmin))
                return float(plot_y1) - norm * (float(plot_y1) - float(plot_y0))

            # Build stepped line points: for each segment, add horizontal then vertical point
            target_pts = []
            prev_x = None
            prev_y = None
            prev_tv = None
            prev_stv = None
            
            for i, p in enumerate(points_list):
                tv = p.get('tv')
                stv = p.get('stv')
                curr_y = y_for(stv) if isinstance(stv, (int, float)) else y_for(tv) if isinstance(tv, (int, float)) else None
                curr_x = float(p['x'])
                
                if curr_y is None:
                    # Missing target - break the line
                    prev_x = None
                    prev_y = None
                    prev_tv = None
                    prev_stv = None
                    continue
                
                if prev_x is not None and prev_y is not None:
                    # Add intermediate point for stepped line: horizontal from prev, then vertical to curr
                    # This creates 90-degree angles like Chart.js stepped: 'before'
                    target_pts.append(f"{curr_x},{prev_y:.1f}")
                
                target_pts.append(f"{curr_x},{curr_y:.1f}")
                
                prev_x = curr_x
                prev_y = curr_y
                prev_tv = tv
                prev_stv = stv
            
            # Filter out any empty strings and join
            joined = " ".join([s for s in target_pts if s])
            target_points = joined if joined else None
        except Exception:
            target_points = None

    return {
        'width': width,
        'height': height,
        'plot_x0': plot_x0,
        'plot_x1': plot_x1,
        'plot_y0': plot_y0,
        'plot_y1': plot_y1,
        'plot_w': plot_w,
        'plot_h': plot_h,
        'bands': bands,
        'points': points_str,
        'target_points': target_points,
        'series_json': series_json,
        'kind': chart_kind,
        'vmin': vmin,
        'vmax': vmax,
        'line_color': line_color,
    }


@login_required
def workout_detail(request, pk):
    """Display detailed view of a single workout"""
    workout = get_object_or_404(
        Workout.objects.select_related(
            'ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details', 'user', 'ride_detail__playlist'
        ).prefetch_related('performance_data'),
        pk=pk,
        user=request.user
    )
    
    # Get performance data ordered by timestamp
    performance_data = workout.performance_data.all().order_by('timestamp')
    
    # Get user profile for target metrics calculations
    user_profile = request.user.profile

    # Determine workout date and FTP snapshot (reused across templates)
    workout_date = workout.completed_date or workout.recorded_date
    user_ftp = None
    if user_profile:
        try:
            if workout_date and hasattr(user_profile, 'get_ftp_at_date'):
                user_ftp = user_profile.get_ftp_at_date(workout_date)
        except Exception:
            user_ftp = None

        if not user_ftp and hasattr(user_profile, 'get_current_ftp'):
            try:
                user_ftp = user_profile.get_current_ftp()
            except Exception:
                user_ftp = None
    
    # Prepare target metrics data based on class type
    target_metrics = None
    target_metrics_json = None
    target_line_data = None  # For power zone graph target line
    is_pace_target = False  # Initialize flag early
    spin_up_intervals = _extract_spin_up_intervals(workout.ride_detail)
    
    if workout.ride_detail:
        ride_detail = workout.ride_detail
        
        if ride_detail.is_power_zone_class or ride_detail.class_type == 'power_zone':
            # Power Zone class - get user's FTP at workout date for zone calculations
            # Calculate zone ranges using FTP at workout date (not current FTP)
            zone_ranges = metrics_calculator.get_power_zone_ranges(user_ftp) if user_ftp else None
            
            segments = ride_detail.get_power_zone_segments(user_ftp=user_ftp)
            # Always set target_metrics for power zone classes, even if segments are empty
            # This ensures the template detects it as a power zone class
            # Convert zone_ranges tuples to lists for JSON serialization
            zone_ranges_json = None
            if zone_ranges:
                zone_ranges_json = {str(k): [v[0] if v[0] is not None else None, v[1] if v[1] is not None else None] for k, v in zone_ranges.items()}
            
            target_metrics = {
                'type': 'power_zone',
                'segments': segments or [],  # Ensure it's always a list
                'zone_ranges': zone_ranges_json  # Use JSON-serializable format
            }
            
            logger.info(f"Power zone workout {workout.id}: segments={len(segments)}, user_ftp={user_ftp}, zone_ranges={'set' if zone_ranges else 'none'}")
            
            # Calculate target line from class plan segments (preferred method)
            # Use segments from ride_detail.get_power_zone_segments() which has the class plan
            target_line_data = None
            
            if user_ftp and performance_data.exists():
                performance_timestamps = list(performance_data.values_list('timestamp', flat=True))
                
                if segments and len(segments) > 0:
                    # Method 1: Use segments from class plan
                    target_line_data = _calculate_target_line_from_segments(
                        segments,
                        zone_ranges,
                        performance_timestamps,
                        user_ftp,
                        spin_up_intervals=spin_up_intervals,
                    )
                    logger.info(f"Calculated target line from {len(segments)} segments for workout {workout.id}")
                else:
                    logger.warning(f"No segments found for power zone workout {workout.id}, trying API fallback")
                
                # Fallback: Try to fetch from performance graph API if segments not available
                if not target_line_data and workout.peloton_workout_id:
                    try:
                        from peloton.models import PelotonConnection
                        from peloton.services.peloton import PelotonClient, PelotonAPIError
                        
                        connection = PelotonConnection.objects.filter(
                            user=request.user, 
                            is_active=True
                        ).first()
                        
                        if connection:
                            client = connection.get_client()
                            performance_graph = client.fetch_performance_graph(workout.peloton_workout_id, every_n=5)
                            
                            # Extract target_metrics_performance_data
                            target_metrics_perf = performance_graph.get('target_metrics_performance_data', {})
                            target_metrics_list = target_metrics_perf.get('target_metrics', [])
                            
                            if target_metrics_list and user_ftp:
                                # Get timestamps from performance_data (database) to align target line
                                # If no performance_data yet, use seconds_since_pedaling_start from graph
                                if performance_data.exists():
                                    performance_timestamps = list(performance_data.values_list('timestamp', flat=True))
                                else:
                                    performance_timestamps = performance_graph.get('seconds_since_pedaling_start', [])
                                
                                # Calculate target line data points aligned with performance data timestamps
                                target_line_data = _calculate_power_zone_target_line(
                                    target_metrics_list, 
                                    user_ftp,
                                    performance_timestamps
                                )
                                logger.info(f"Calculated target line from API for workout {workout.id}")
                    except Exception as e:
                        logger.warning(f"Could not fetch performance graph for workout {workout.id}: {e}")
            else:
                if not user_ftp:
                    logger.warning(f"No FTP found for power zone workout {workout.id}")
                if not performance_data.exists():
                    logger.warning(f"No performance data found for workout {workout.id}")
        elif ride_detail.fitness_discipline in ['running', 'walking']:
            # Running/Walking class - get user's pace zones based on activity type
            activity_type = 'running' if ride_detail.fitness_discipline in ['running', 'run'] else 'walking'
            # Get the pace level that was active at the workout date
            workout_date = workout.completed_date or workout.recorded_date
            current_pace_level = user_profile.get_pace_at_date(workout_date, activity_type=activity_type) if user_profile and workout_date else None
            # Fallback to pace_target_level if no PaceEntry exists
            if current_pace_level is None and user_profile:
                current_pace_level = user_profile.pace_target_level
            
            # Get full pace range data from the pace levels definitions
            from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS
            from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS
            
            pace_zones = None
            pace_ranges = None  # Full range data (min/max mph for each zone)
            
            if current_pace_level:
                if activity_type == 'running':
                    pace_level_data = DEFAULT_RUNNING_PACE_LEVELS.get(current_pace_level)
                else:
                    pace_level_data = DEFAULT_WALKING_PACE_LEVELS.get(current_pace_level)
                
                if pace_level_data:
                    # pace_level_data format: {zone_name: (min_mph, max_mph, min_pace, max_pace, description)}
                    pace_zones = {}
                    pace_ranges = {}
                    for zone_name, (min_mph, max_mph, min_pace, max_pace, desc) in pace_level_data.items():
                        # Use middle of mph range for target
                        middle_mph = (min_mph + max_mph) / 2
                        pace_zones[zone_name] = int(min_pace * 60)  # Keep old format for compatibility
                        pace_ranges[zone_name] = {
                            'min_mph': min_mph,
                            'max_mph': max_mph,
                            'middle_mph': middle_mph,  # This is what we'll use for target line
                            'min_pace': min_pace,
                            'max_pace': max_pace
                        }
            
            segments = ride_detail.get_pace_segments(user_pace_zones=pace_zones)
            target_metrics = {
                'type': 'pace',
                'segments': segments,
                'pace_zones': pace_zones,
                'pace_ranges': pace_ranges  # Add full range data for target line
            }
            # Set is_pace_target flag for running/walking classes
            is_pace_target = True
        else:
            # Standard cycling class - cadence/resistance ranges
            segments = ride_detail.get_cadence_resistance_segments()
            target_metrics = {
                'type': 'cadence_resistance',
                'segments': segments
            }
        
        # Convert to JSON for template
        if target_metrics:
            target_metrics_json = mark_safe(json.dumps(target_metrics))
    
    # Ensure is_pace_target is set correctly (check class_type or fitness_discipline if not already set)
    if workout.ride_detail and not is_pace_target:
        if (workout.ride_detail.class_type == 'pace_target' or 
            workout.ride_detail.fitness_discipline in ['running', 'walking']):
            is_pace_target = True
    
    # Get playlist if available
    playlist = None
    if workout.ride_detail:
        try:
            playlist = workout.ride_detail.playlist
        except:
            pass
    
    # Serialize target_line_data to JSON
    target_line_data_json = None
    if target_line_data:
        target_line_data_json = mark_safe(json.dumps(target_line_data))
    
    # Calculate power profile (5s, 1m, 5m, 20m peak power) - matching example code approach
    power_profile = None
    if performance_data and workout.ride_detail and (workout.ride_detail.is_power_zone_class or workout.ride_detail.class_type == 'power_zone'):
        # Calculate segment_length from performance data timestamps (default 5 seconds)
        segment_length = 5  # Default Peloton sampling interval
        perf_list = list(performance_data.order_by('timestamp'))
        if len(perf_list) > 1:
            # Calculate average interval between data points
            intervals = []
            for i in range(1, min(10, len(perf_list))):  # Check first 10 intervals
                interval = perf_list[i].timestamp - perf_list[i-1].timestamp
                if interval > 0:
                    intervals.append(interval)
            if intervals:
                segment_length = int(sum(intervals) / len(intervals))
        
        # Extract output values as list
        output_values = [p.output for p in performance_data if p.output is not None]
        if output_values and len(output_values) > 0:
            power_profile = {}
            intervals = [
                (5, '5_second'),
                (60, '1_minute'),
                (300, '5_minute'),
                (1200, '20_minute')
            ]
            
            for interval_seconds, key in intervals:
                # Calculate number of samples needed for this interval
                num_samples = max(1, int(interval_seconds / segment_length))
                
                if num_samples > len(output_values):
                    continue
                
                peak_power = 0
                # Calculate rolling average power for the duration
                for i in range(len(output_values) - num_samples + 1):
                    window = output_values[i:i + num_samples]
                    avg_power = sum(window) / len(window) if window else 0
                    peak_power = max(peak_power, avg_power)
                
                if interval_seconds == 5:
                    power_profile["5_second"] = round(peak_power)
                elif interval_seconds == 60:
                    power_profile["1_minute"] = round(peak_power)
                elif interval_seconds == 300:
                    power_profile["5_minute"] = round(peak_power)
                elif interval_seconds == 1200:
                    power_profile["20_minute"] = round(peak_power)
    
    # Calculate zone targets and progress for power zone classes - matching example code approach
    zone_targets = None
    class_notes = None
    if target_metrics and target_metrics.get('type') == 'power_zone' and target_metrics.get('segments'):
        segments = target_metrics.get('segments', [])
        
        # Calculate segment_length from performance data timestamps (default 5 seconds)
        segment_length = 5  # Default Peloton sampling interval
        if performance_data:
            perf_list = list(performance_data.order_by('timestamp'))
            if len(perf_list) > 1:
                # Calculate average interval between data points
                intervals = []
                for i in range(1, min(10, len(perf_list))):  # Check first 10 intervals
                    interval = perf_list[i].timestamp - perf_list[i-1].timestamp
                    if interval > 0:
                        intervals.append(interval)
                if intervals:
                    segment_length = int(sum(intervals) / len(intervals))
        
        # Calculate time in each zone from target segments
        zone_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        zone_blocks = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        previous_zone = None
        
        for segment in segments:
            zone = segment.get('zone')
            # Get duration from segment - segments from get_power_zone_segments() have 'start' and 'end' keys
            # But they might also have 'offsets' dict with 'start' and 'end' inside
            if 'start' in segment and 'end' in segment:
                start = segment.get('start', 0)
                end = segment.get('end', start)
                duration = max(end - start, 0)
            else:
                # Try offsets structure
                offsets = segment.get('offsets', {})
                start = offsets.get('start', 0)
                end = offsets.get('end', start)
                duration = max(end - start, segment.get('duration', 0))
            
            if zone and duration > 0:
                zone_times[zone] = zone_times.get(zone, 0) + duration
                # Count blocks - consecutive segments in same zone = 1 block
                if zone != previous_zone:
                    # Zone changed, this is a new block
                    zone_blocks[zone] = zone_blocks.get(zone, 0) + 1
                # If same zone as previous, it's a continuation of the same block, don't increment
                previous_zone = zone
        
        # Calculate actual time in zones from performance data
        zone_actual_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        if performance_data and user_ftp:
            # Use segment_length to determine time duration per data point
            for perf in performance_data:
                if perf.output and perf.output > 0:
                    percentage = perf.output / user_ftp
                    
                    # Map watts to power zone based on FTP (matching example code)
                    if percentage < 0.55:
                        zone_actual_times[1] += segment_length
                    elif percentage < 0.75:
                        zone_actual_times[2] += segment_length
                    elif percentage < 0.90:
                        zone_actual_times[3] += segment_length
                    elif percentage < 1.05:
                        zone_actual_times[4] += segment_length
                    elif percentage < 1.20:
                        zone_actual_times[5] += segment_length
                    elif percentage < 1.50:
                        zone_actual_times[6] += segment_length
                    else:
                        zone_actual_times[7] += segment_length
        
        # Build zone targets with progress
        zone_targets_list = []
        total_target_time = 0
        total_actual_time = 0
        
        zone_names = {
            1: "Z1 • Active Recovery",
            2: "Z2 • Endurance",
            3: "Z3 • Tempo",
            4: "Z4 • Threshold",
            5: "Z5 • VO2 Max",
            6: "Z6 • Anaerobic",
            7: "Z7 • Neuromuscular"
        }
        
        # Process zones in reverse order (Z7 to Z1) for display
        for zone in range(7, 0, -1):
            target_time = zone_times.get(zone, 0)
            actual_time = zone_actual_times.get(zone, 0)
            blocks = zone_blocks.get(zone, 0)
            
            if target_time > 0:
                total_target_time += target_time
                # Only count actual time up to target (matching example code)
                total_actual_time += min(actual_time, target_time)
                
                percentage = min(100, (actual_time / target_time * 100)) if target_time > 0 else 0
                
                def format_duration(seconds):
                    mins = seconds // 60
                    secs = seconds % 60
                    return f"{mins}:{secs:02d}"
                
                zone_targets_list.append({
                    'zone': zone,
                    'name': zone_names[zone],
                    'target_time': target_time,
                    'target_time_str': format_duration(target_time),
                    'actual_time': actual_time,
                    'actual_time_str': format_duration(actual_time),
                    'percentage': percentage,
                    'blocks': blocks
                })
        
        # Calculate overall progress (matching example code - only count up to target)
        overall_percentage = 0
        if total_target_time > 0:
            overall_percentage = (total_actual_time / total_target_time) * 100
        
        # Only create zone_targets if we have zones with targets
        if zone_targets_list:
            zone_targets = {
                'overall_percentage': round(overall_percentage, 2),
                'zones': zone_targets_list
            }
        else:
            zone_targets = None
        
        # Build class notes (zone breakdown) - reuse zone_names from above
        class_notes_list = []
        for zone in range(7, 0, -1):
            target_time = zone_times.get(zone, 0)
            blocks = zone_blocks.get(zone, 0)
            if target_time > 0:
                def format_duration(seconds):
                    mins = seconds // 60
                    secs = seconds % 60
                    return f"{mins}:{secs:02d}"
                
                # Get zone name (format: "Z1 • Active Recovery" -> "Active Recovery")
                full_name = zone_names.get(zone, f"Zone {zone}")
                zone_name = full_name.split(' • ')[1] if ' • ' in full_name else full_name
                
                class_notes_list.append({
                    'zone': zone,
                    'zone_label': f"Z{zone}",
                    'name': zone_name,
                    'total_time': target_time,
                    'total_time_str': format_duration(target_time),
                    'blocks': blocks
                })
        
        class_notes = class_notes_list if class_notes_list else None
    
    # Calculate pace target distribution and summary for pace target classes
    pace_targets = None
    pace_class_notes = None
    # is_pace_target should already be set above, but ensure it's set if we have pace target_metrics
    if not is_pace_target and target_metrics and target_metrics.get('type') == 'pace':
        is_pace_target = True
    
    # Calculate pace targets if this is a pace target class (even if segments is empty, we still want to show the cards)
    if is_pace_target and target_metrics and target_metrics.get('type') == 'pace':
        segments = target_metrics.get('segments', [])
        
        # Calculate segment_length from performance data timestamps (default 5 seconds)
        segment_length = 5  # Default Peloton sampling interval
        if performance_data:
            perf_list = list(performance_data.order_by('timestamp'))
            if len(perf_list) > 1:
                intervals = []
                for i in range(1, min(10, len(perf_list))):
                    interval = perf_list[i].timestamp - perf_list[i-1].timestamp
                    if interval > 0:
                        intervals.append(interval)
                if intervals:
                    segment_length = int(sum(intervals) / len(intervals))
        
        # Calculate time in each pace level from target segments
        # Pace zones: recovery=1, easy=2, moderate=3, challenging=4, hard=5, very_hard=6, max=7
        pace_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        pace_blocks = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        previous_pace = None
        
        # If no segments from get_pace_segments, try to get from target_metrics_data
        if not segments and workout.ride_detail and workout.ride_detail.target_metrics_data:
            # Try to extract segments from target_metrics_data
            target_metrics_data = workout.ride_detail.target_metrics_data
            target_metrics_list = target_metrics_data.get('target_metrics', [])
            if target_metrics_list:
                for tm in target_metrics_list:
                    offsets = tm.get('offsets', {})
                    start = offsets.get('start', 0)
                    end = offsets.get('end', start)
                    duration = max(end - start, 0)
                    
                    # Find pace_intensity in metrics
                    pace_zone = None
                    for metric in tm.get('metrics', []):
                        if metric.get('name') == 'pace_intensity':
                            # pace_intensity is 0-6, map to 1-7 (recovery=1, easy=2, etc.)
                            pace_intensity = metric.get('lower') or metric.get('upper')
                            if pace_intensity is not None:
                                pace_zone = int(pace_intensity) + 1  # Convert 0-6 to 1-7
                                break
                    
                    if pace_zone and duration > 0:
                        segments.append({
                            'start': start,
                            'end': end,
                            'zone': pace_zone,
                            'duration': duration
                        })
        
        for segment in segments:
            pace_zone = segment.get('zone')  # 1-7 from get_pace_segments
            if 'start' in segment and 'end' in segment:
                start = segment.get('start', 0)
                end = segment.get('end', start)
                duration = max(end - start, 0)
            else:
                offsets = segment.get('offsets', {})
                start = offsets.get('start', 0)
                end = offsets.get('end', start)
                duration = max(end - start, segment.get('duration', 0))
            
            if pace_zone and duration > 0:
                pace_times[pace_zone] = pace_times.get(pace_zone, 0) + duration
                if pace_zone != previous_pace:
                    pace_blocks[pace_zone] = pace_blocks.get(pace_zone, 0) + 1
                previous_pace = pace_zone
        
        # Calculate actual time in pace levels from performance data (speed-based)
        pace_actual_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        if performance_data and target_metrics and target_metrics.get('pace_zones'):
            pace_zones = target_metrics.get('pace_zones')
            # Get user's pace zones for comparison
            for perf in performance_data:
                if perf.speed and perf.speed > 0:
                    # Convert speed (mph) to pace (seconds/mile) because pace_zones thresholds are in seconds
                    pace_sec_per_mile = (3600.0 / perf.speed) if perf.speed > 0 else None
                    
                    if pace_sec_per_mile:
                        # Map pace to zone based on user's pace zones (higher seconds = slower)
                        if pace_sec_per_mile >= pace_zones.get('recovery', 1200.0):  # 20:00/mi
                            pace_actual_times[1] += segment_length
                        elif pace_sec_per_mile >= pace_zones.get('easy', 900.0):     # 15:00/mi
                            pace_actual_times[2] += segment_length
                        elif pace_sec_per_mile >= pace_zones.get('moderate', 720.0): # 12:00/mi
                            pace_actual_times[3] += segment_length
                        elif pace_sec_per_mile >= pace_zones.get('challenging', 600.0): # 10:00/mi
                            pace_actual_times[4] += segment_length
                        elif pace_sec_per_mile >= pace_zones.get('hard', 510.0):    # 8:30/mi
                            pace_actual_times[5] += segment_length
                        elif pace_sec_per_mile >= pace_zones.get('very_hard', 450.0): # 7:30/mi
                            pace_actual_times[6] += segment_length
                        else:
                            pace_actual_times[7] += segment_length
        
        # Build pace targets with progress
        pace_targets_list = []
        total_target_time = 0
        total_actual_time = 0
        
        pace_names = {
            1: "Recovery",
            2: "Easy",
            3: "Moderate",
            4: "Challenging",
            5: "Hard",
            6: "Very Hard",
            7: "Max"
        }
        
        # Process pace levels in reverse order (Max to Recovery) for display
        for pace_level in range(7, 0, -1):
            target_time = pace_times.get(pace_level, 0)
            actual_time = pace_actual_times.get(pace_level, 0)
            blocks = pace_blocks.get(pace_level, 0)
            
            if target_time > 0:
                total_target_time += target_time
                total_actual_time += min(actual_time, target_time)
                
                percentage = min(100, (actual_time / target_time * 100)) if target_time > 0 else 0
                
                def format_duration(seconds):
                    mins = seconds // 60
                    secs = seconds % 60
                    return f"{mins}:{secs:02d}"
                
                pace_targets_list.append({
                    'zone': pace_level,
                    'name': pace_names[pace_level],
                    'target_time': target_time,
                    'target_time_str': format_duration(target_time),
                    'actual_time': actual_time,
                    'actual_time_str': format_duration(actual_time),
                    'percentage': percentage,
                    'blocks': blocks
                })
        
        # Calculate overall progress
        overall_percentage = 0
        if total_target_time > 0:
            overall_percentage = (total_actual_time / total_target_time) * 100
        
        if pace_targets_list:
            pace_targets = {
                'overall_percentage': round(overall_percentage, 2),
                'zones': pace_targets_list
            }
        else:
            pace_targets = None
        
        # Build pace class notes
        pace_class_notes_list = []
        for pace_level in range(7, 0, -1):
            target_time = pace_times.get(pace_level, 0)
            blocks = pace_blocks.get(pace_level, 0)
            if target_time > 0:
                def format_duration(seconds):
                    mins = seconds // 60
                    secs = seconds % 60
                    return f"{mins}:{secs:02d}"
                
                pace_class_notes_list.append({
                    'zone': pace_level,
                    'zone_label': pace_names[pace_level],
                    'name': pace_names[pace_level],
                    'total_time': target_time,
                    'total_time_str': format_duration(target_time),
                    'blocks': blocks
                })
        
        pace_class_notes = pace_class_notes_list if pace_class_notes_list else None
    
    # Get user pace level for pace target classes - use correct level based on activity type and workout date
    user_pace_level = None
    if is_pace_target and user_profile and workout.ride_detail:
        activity_type = 'running' if workout.ride_detail.fitness_discipline in ['running', 'run'] else 'walking'
        # Get the pace level that was active at the workout date
        workout_date = workout.completed_date or workout.recorded_date
        if workout_date:
            user_pace_level = user_profile.get_pace_at_date(workout_date, activity_type=activity_type)
        else:
            # Fallback to current pace if no workout date
            user_pace_level = user_profile.get_current_pace(activity_type=activity_type)
        # Fallback to pace_target_level if no PaceEntry exists
        if user_pace_level is None:
            user_pace_level = user_profile.pace_target_level or 5  # Default to level 5
    
    # Build class_sections from ride_detail if available
    class_sections = {}
    if workout.ride_detail and hasattr(workout.ride_detail, 'target_metrics_data') and workout.ride_detail.target_metrics_data:
        # Get segments from ride detail
        if is_pace_target and user_profile:
            activity_type = 'running' if workout.ride_detail.fitness_discipline in ['running', 'run'] else 'walking'
            pace_zones = user_profile.get_pace_zone_targets(activity_type=activity_type) if hasattr(user_profile, 'get_pace_zone_targets') else None
            pace_segs = workout.ride_detail.get_pace_segments(user_pace_zones=pace_zones)
            
            # Organize into sections
            section_templates = {
                'warm_up': {'name': 'Warm Up', 'icon': '🔥', 'description': 'Gradually increase your effort to prepare for the main workout.'},
                'main': {'name': 'Running', 'icon': 'X', 'description': 'Main run workout segment.'},
                'cool_down': {'name': 'Cool Down', 'icon': '❄️', 'description': 'Gradually decrease your effort to recover from the workout.'}
            }
            
            for key, template in section_templates.items():
                class_sections[key] = {
                    'name': template['name'],
                    'icon': template['icon'],
                    'description': template['description'],
                    'segments': [],
                    'duration': 0
                }
            
            total_duration = workout.ride_detail.duration_seconds
            if total_duration > 0:
                warm_up_cutoff = total_duration * 0.15
                cool_down_start = total_duration * 0.90
                
                pace_name_map = {
                    'recovery': 'Recovery', 'easy': 'Easy', 'moderate': 'Moderate',
                    'challenging': 'Challenging', 'hard': 'Hard', 'very_hard': 'Very Hard', 'max': 'Max'
                }
                
                for pace_seg in pace_segs:
                    seg_start = pace_seg['start']
                    seg_end = pace_seg['end']
                    seg_duration = seg_end - seg_start
                    
                    if seg_start < warm_up_cutoff:
                        section_key = 'warm_up'
                    elif seg_start >= cool_down_start:
                        section_key = 'cool_down'
                    else:
                        section_key = 'main'
                    
                    zone_name = pace_seg.get('zone_name', '')
                    if not zone_name:
                        zone_num = pace_seg.get('zone', 1)
                        zone_map = {1: 'recovery', 2: 'easy', 3: 'moderate', 4: 'challenging', 
                                   5: 'hard', 6: 'very_hard', 7: 'max'}
                        zone_name = zone_map.get(zone_num, 'moderate')
                    
                    pace_name = pace_name_map.get(zone_name.lower(), zone_name.replace('_', ' ').title())
                    
                    class_sections[section_key]['segments'].append({
                        'name': pace_name,
                        'start': seg_start,
                        'end': seg_end,
                        'duration': seg_duration,
                        'duration_str': f"{seg_duration // 60}:{(seg_duration % 60):02d}"
                    })
                    class_sections[section_key]['duration'] += seg_duration
            
            # Remove empty sections
            for section_key in list(class_sections.keys()):
                if not class_sections[section_key]['segments']:
                    del class_sections[section_key]
    
    # Workout summary metrics (for UI cards)
    workout_summary = {}
    details = getattr(workout, 'details', None)
    if details:
        def _pace_str_from_mph(mph):
            try:
                mph = float(mph)
            except (TypeError, ValueError):
                return None
            if mph <= 0:
                return None
            total_seconds = int(round(3600.0 / mph))
            mins = total_seconds // 60
            secs = total_seconds % 60
            return f"{mins}:{secs:02d}"

        workout_summary = {
            'distance_mi': details.distance,
            'total_calories': details.total_calories,
            'avg_output_w': details.avg_output,
            'total_output_kj': details.total_output,
            'avg_speed_mph': details.avg_speed,
            'max_speed_mph': details.max_speed,
            'avg_pace_str': _pace_str_from_mph(details.avg_speed),
            'avg_heart_rate': details.avg_heart_rate,
            'max_heart_rate': details.max_heart_rate,
            'tss': details.tss,
        }
    else:
        # If we don't have WorkoutDetails, still allow pace from performance data if present
        def _pace_str_from_mph(mph):
            try:
                mph = float(mph)
            except (TypeError, ValueError):
                return None
            if mph <= 0:
                return None
            total_seconds = int(round(3600.0 / mph))
            mins = total_seconds // 60
            secs = total_seconds % 60
            return f"{mins}:{secs:02d}"

    # Fallback: derive avg speed/pace from stored performance_data (no API call)
    if (not workout_summary.get('avg_speed_mph')) and performance_data.exists():
        speeds = list(performance_data.values_list('speed', flat=True))
        speeds = [s for s in speeds if isinstance(s, (int, float)) and s and s > 0]
        if speeds:
            avg_speed = sum(speeds) / len(speeds)
            workout_summary['avg_speed_mph'] = avg_speed
            if not workout_summary.get('avg_pace_str'):
                workout_summary['avg_pace_str'] = _pace_str_from_mph(avg_speed)

    # Fallback: fetch elevation (and missing summaries) from Peloton performance graph if available
    # Only do this if we have a Peloton workout id and no elevation yet.
    if workout.peloton_workout_id and workout_summary.get('elevation_ft') is None:
        try:
            connection = PelotonConnection.objects.filter(user=request.user, is_active=True).first()
            if connection:
                client = connection.get_client()
                # Larger every_n reduces payload; summaries are unaffected.
                performance_graph = client.fetch_performance_graph(workout.peloton_workout_id, every_n=30)
                summaries_array = performance_graph.get('summaries', []) or []
                for summary in summaries_array:
                    if not isinstance(summary, dict):
                        continue
                    if summary.get('slug') == 'elevation' and summary.get('value') is not None:
                        workout_summary['elevation_ft'] = summary.get('value')
                        break

                # Fill distance / total output / calories if missing in WorkoutDetails
                if summaries_array:
                    if workout_summary.get('distance_mi') is None:
                        for s in summaries_array:
                            if isinstance(s, dict) and s.get('slug') == 'distance' and s.get('value') is not None:
                                workout_summary['distance_mi'] = s.get('value')
                                break
                    if workout_summary.get('total_output_kj') is None:
                        for s in summaries_array:
                            if isinstance(s, dict) and s.get('slug') == 'total_output' and s.get('value') is not None:
                                workout_summary['total_output_kj'] = s.get('value')
                                break
                    if workout_summary.get('total_calories') is None:
                        for s in summaries_array:
                            if isinstance(s, dict) and s.get('slug') in ('total_calories', 'calories') and s.get('value') is not None:
                                workout_summary['total_calories'] = s.get('value')
                                break

                # Fill avg_speed from average_summaries if missing (and thus avg pace)
                if workout_summary.get('avg_speed_mph') is None:
                    avg_summaries = performance_graph.get('average_summaries', []) or []
                    for s in avg_summaries:
                        if isinstance(s, dict) and s.get('slug') == 'avg_speed' and s.get('value') is not None:
                            workout_summary['avg_speed_mph'] = s.get('value')
                            break
                    if workout_summary.get('avg_speed_mph') is None:
                        # Some graphs use metrics[].slug == 'speed' with average_value
                        metrics = performance_graph.get('metrics', []) or []
                        for m in metrics:
                            if isinstance(m, dict) and m.get('slug') == 'speed' and m.get('average_value') is not None:
                                workout_summary['avg_speed_mph'] = m.get('average_value')
                                break
                if workout_summary.get('avg_speed_mph') is not None and not workout_summary.get('avg_pace_str'):
                    workout_summary['avg_pace_str'] = _pace_str_from_mph(workout_summary.get('avg_speed_mph'))
        except Exception:
            # Keep page resilient even if Peloton API fails
            pass

    # Generate chart data using ChartBuilder service
    performance_graph_data = None
    zone_distribution_data = None
    summary_stats_data = None
    
    if performance_data.exists() and workout.ride_detail:
        # Convert performance_data queryset to list of dicts for ChartBuilder
        perf_list = list(performance_data.values('timestamp', 'output'))
        
        # Generate performance graph
        if workout.ride_detail.is_power_zone_class or workout.ride_detail.class_type == 'power_zone':
            performance_graph_data = chart_builder.generate_performance_graph(
                performance_data=perf_list,
                workout_type='power_zone',
                ftp=user_ftp or 200.0
            )
            
            # Generate zone distribution from performance data
            if user_ftp and perf_list:
                # Calculate zone distribution directly from performance data
                zone_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
                zone_samples = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []}
                
                # Calculate average interval for time tracking
                segment_length = 5  # Default Peloton sampling interval
                perf_obj_list = list(performance_data)
                if len(perf_obj_list) > 1:
                    intervals = []
                    for i in range(1, min(10, len(perf_obj_list))):
                        interval = perf_obj_list[i].timestamp - perf_obj_list[i-1].timestamp
                        if interval > 0:
                            intervals.append(interval)
                    if intervals:
                        segment_length = int(sum(intervals) / len(intervals))
                
                # Categorize each performance point into zones
                for point in perf_obj_list:
                    if point.output and point.output > 0:
                        percentage = point.output / user_ftp
                        
                        # Determine zone from percentage
                        if percentage < 0.55:
                            zone = 1
                        elif percentage < 0.75:
                            zone = 2
                        elif percentage < 0.90:
                            zone = 3
                        elif percentage < 1.05:
                            zone = 4
                        elif percentage < 1.20:
                            zone = 5
                        elif percentage < 1.50:
                            zone = 6
                        else:
                            zone = 7
                        
                        zone_times[zone] += segment_length
                        zone_samples[zone].append(point.output)
                
                # Build zone_data_dict for ChartBuilder (only include zones with data)
                zone_data_dict = {}
                for zone in range(1, 8):
                    if zone_times[zone] > 0:
                        zone_data_dict[zone] = {
                            'output': zone_samples[zone][:10] if zone_samples[zone] else [0],
                            'time_sec': zone_times[zone]
                        }
                
                if zone_data_dict:  # Only pass if we have data
                    # Convert dict to list format expected by ChartBuilder
                    zone_data_list = []
                    for zone, data in zone_data_dict.items():
                        zone_data_list.append({
                            'zone': zone,
                            'time_sec': data['time_sec']
                        })
                    
                    zone_distribution_data = chart_builder.generate_zone_distribution(
                        zone_data=zone_data_list,
                        workout_type='power_zone',
                        total_duration_seconds=workout.ride_detail.duration_seconds
                    )
        
        elif workout.ride_detail.fitness_discipline in ['running', 'walking']:
            performance_graph_data = chart_builder.generate_performance_graph(
                performance_data=perf_list,
                workout_type='pace_target',
                pace_level=user_pace_level
            )
        
        # Generate summary stats for any workout type with performance data
        if details:
            summary_stats_data = chart_builder.generate_summary_stats(
                performance_data=perf_list,
                zone_distribution=None,
                duration_seconds=workout.ride_detail.duration_seconds if workout.ride_detail else None,
                avg_power=details.avg_output if hasattr(details, 'avg_output') else None,
                ftp=user_ftp or 200.0,
                calories=details.total_calories if hasattr(details, 'total_calories') else None
            )
    
    context = {
        'workout': workout,
        'performance_data': performance_data,
        'target_metrics': target_metrics,
        'target_metrics_json': target_metrics_json,
        'target_line_data': target_line_data_json,
        'user_profile': user_profile,
        'user_ftp': user_ftp,  # Pass FTP explicitly for template
        'user_pace_level': user_pace_level,  # Pass pace level for pace target classes
        'workout_summary': workout_summary,
        'playlist': playlist,
        'power_profile': power_profile,
        'zone_targets': zone_targets,
        'class_notes': class_notes,
        'pace_targets': pace_targets,  # Pace target distribution
        'pace_class_notes': pace_class_notes,  # Pace class notes
        'class_sections': class_sections,  # Class sections for collapsible details
        'spin_up_intervals': spin_up_intervals,
        'is_pace_target': is_pace_target,  # Flag to identify pace target classes
        'performance_graph_data': performance_graph_data,  # ChartBuilder: Performance graph
        'zone_distribution_data': zone_distribution_data,  # ChartBuilder: Zone distribution
        'summary_stats_data': summary_stats_data,  # ChartBuilder: Summary statistics
    }
    
    # Determine which template to use based on workout type
    template_name = 'workouts/detail_general.html'  # Default template
    
    if workout.ride_detail:
        ride_detail = workout.ride_detail
        
        # Power Zone classes
        if ride_detail.is_power_zone_class or ride_detail.class_type == 'power_zone':
            template_name = 'workouts/detail_power_zone.html'
        
        # Pace Target classes (Running/Walking)
        elif ride_detail.fitness_discipline in ['running', 'walking', 'run', 'walk'] or ride_detail.class_type == 'pace_target':
            template_name = 'workouts/detail_pace_target.html'
        
        # Non–Power Zone cycling workouts (dedicated template)
        elif ride_detail.fitness_discipline in ['cycling', 'ride']:
            template_name = 'workouts/detail_cycling.html'
    
    return render(request, template_name, context)








@login_required
def connect(request):
    """Redirect to Peloton connection page"""
    return redirect('peloton:connect')


def _store_playlist_from_data(playlist_data, ride_detail, logger, workout_num=None, workout_id=None):
    """
    Helper function to store playlist data for a ride.
    playlist_data should come from ride_details response (data['playlist']).
    Returns True if playlist was stored successfully, False otherwise.
    """
    if not playlist_data:
        return False
    
    try:
        # Extract playlist information
        peloton_playlist_id = playlist_data.get('id')
        songs = playlist_data.get('songs', [])
        top_artists = playlist_data.get('top_artists', [])
        top_albums = playlist_data.get('top_albums', [])
        stream_id = playlist_data.get('stream_id')
        stream_url = playlist_data.get('stream_url')
        
        # Create or update playlist
        playlist, playlist_created = Playlist.objects.update_or_create(
            ride_detail=ride_detail,
            defaults={
                'peloton_playlist_id': peloton_playlist_id,
                'songs': songs,
                'top_artists': top_artists,
                'top_albums': top_albums,
                'stream_id': stream_id,
                'stream_url': stream_url,
                'is_top_artists_shown': playlist_data.get('is_top_artists_shown', False),
                'is_playlist_shown': playlist_data.get('is_playlist_shown', False),
                'is_in_class_music_shown': playlist_data.get('is_in_class_music_shown', False),
            }
        )
        log_prefix = f"Workout {workout_num} ({workout_id})" if workout_num and workout_id else "Playlist"
        if playlist_created:
            logger.info(f"{log_prefix}: ✓ Created Playlist with {len(songs)} songs")
        else:
            logger.debug(f"{log_prefix}: ↻ Updated Playlist")
        return True
    except Exception as e:
        # Playlist storage is optional - don't fail the whole sync if it fails
        log_prefix = f"Workout {workout_num} ({workout_id})" if workout_num and workout_id else "Playlist"
        logger.debug(f"{log_prefix}: Could not store playlist: {e}")
    return False


@login_required
def sync_workouts(request):
    """Trigger manual sync of workouts from Peloton API"""
    if request.method != 'POST':
        return redirect('workouts:history')
    
    try:
        connection = PelotonConnection.objects.get(user=request.user)
    except PelotonConnection.DoesNotExist:
        messages.error(request, 'No Peloton connection found. Please connect your Peloton account first.')
        return redirect('workouts:history')
    
    # Check if sync is already in progress
    if connection.sync_in_progress:
        messages.warning(request, 'A sync is already in progress. Please wait for it to complete.')
        # If HTMX request, return partial
        if request.headers.get('HX-Request'):
            context = {
                'peloton_connection': connection,
                'sync_in_progress': True,
                'sync_cooldown_until': None,
                'cooldown_remaining_minutes': None,
                'can_sync': False,
            }
            return render(request, 'workouts/partials/sync_status.html', context)
        return redirect('workouts:history')
    
    # Check if sync is in cooldown period (60 minutes)
    from datetime import timedelta
    if connection.sync_cooldown_until and timezone.now() < connection.sync_cooldown_until:
        remaining_minutes = int((connection.sync_cooldown_until - timezone.now()).total_seconds() / 60)
        messages.warning(request, f'Sync is on cooldown. Please wait {remaining_minutes} more minute(s) before syncing again.')
        # If HTMX request, return partial
        if request.headers.get('HX-Request'):
            context = {
                'peloton_connection': connection,
                'sync_in_progress': False,
                'sync_cooldown_until': connection.sync_cooldown_until,
                'cooldown_remaining_minutes': remaining_minutes,
                'can_sync': False,
            }
            return render(request, 'workouts/partials/sync_status.html', context)
        return redirect('workouts:history')
    
    # Mark sync as in progress
    connection.sync_in_progress = True
    connection.sync_started_at = timezone.now()
    connection.save()
    
    try:
        from peloton.services.peloton import PelotonAPIError
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get client
        client = connection.get_client()
        
        # Get user ID
        if not connection.peloton_user_id:
            user_data = client.fetch_current_user()
            peloton_user_id = user_data.get('id')
            if peloton_user_id:
                connection.peloton_user_id = str(peloton_user_id)
                connection.save()
            else:
                messages.error(request, 'Could not determine Peloton user ID.')
                return redirect('workouts:history')
        else:
            peloton_user_id = connection.peloton_user_id
        
        # Determine sync type: full or incremental
        is_full_sync = connection.last_sync_at is None
        sync_cutoff_timestamp = None
        
        if is_full_sync:
            logger.info(f"Starting FULL sync for user {request.user.email}, Peloton ID: {peloton_user_id} (no previous sync found)")
        else:
            # Convert last_sync_at to Unix timestamp for comparison
            # Ensure timezone-aware: last_sync_at is already UTC (Django stores in UTC when USE_TZ=True)
            # But make it explicitly UTC-aware for safety
            if connection.last_sync_at.tzinfo is None:
                # If somehow timezone-naive, assume UTC
                last_sync_utc = timezone.make_aware(connection.last_sync_at, UTC)
            else:
                last_sync_utc = connection.last_sync_at.astimezone(UTC)
            
            sync_cutoff_timestamp = last_sync_utc.timestamp()
            logger.info(f"Starting INCREMENTAL sync for user {request.user.email}, Peloton ID: {peloton_user_id}")
            logger.info(f"  - Last sync (UTC): {last_sync_utc}")
            logger.info(f"  - Last sync timestamp: {sync_cutoff_timestamp}")
            logger.info(f"  - Only syncing workouts after: {last_sync_utc}")
        
        workouts_synced = 0
        workouts_updated = 0
        workouts_skipped = 0
        total_processed = 0
        workouts_older_than_sync = 0
        
        # Iterate through workouts (newest first)
        logger.info(f"Fetching workouts from Peloton API...")
        for workout_data in client.iter_user_workouts(peloton_user_id):
            total_processed += 1
            
            # Log progress every 50 workouts
            if total_processed % 50 == 0:
                logger.info(f"Progress: {total_processed} workouts processed ({workouts_synced} new, {workouts_updated} updated, {workouts_skipped} skipped)")
            try:
                peloton_workout_id = workout_data.get('id')
                if not peloton_workout_id:
                    workouts_skipped += 1
                    logger.warning(f"Workout {total_processed}: Skipping workout with no ID")
                    continue
                
                logger.info(f"Workout {total_processed}: Processing workout ID {peloton_workout_id}")
                
                # Log initial workout data structure for debugging
                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Initial workout_data keys: {list(workout_data.keys())}")
                if 'ride' in workout_data and workout_data.get('ride'):
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): ride keys: {list(workout_data.get('ride', {}).keys())}")
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): ride data: {str(workout_data.get('ride', {}))[:200]}")
                
                # Try to extract title and duration from workout_data first (might already be there)
                initial_title = None
                initial_duration_seconds = None
                ride_data = workout_data.get('ride', {})
                if ride_data:
                    initial_title = ride_data.get('title') or ride_data.get('name') or ride_data.get('class_title')
                    initial_duration_seconds = ride_data.get('duration') or ride_data.get('length')
                    if initial_title:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found title in initial workout_data: '{initial_title}'")
                    if initial_duration_seconds:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found duration in initial workout_data: {initial_duration_seconds}s")
                
                # Get or create workout type
                workout_type_slug = workout_data.get('fitness_discipline', '').lower()
                if not workout_type_slug:
                    workout_type_slug = 'other'
                
                # Map Peloton workout types to our workout types
                type_mapping = {
                    'cycling': 'cycling',
                    'running': 'running',
                    'walking': 'walking',
                    'yoga': 'yoga',
                    'strength': 'strength',
                    'stretching': 'stretching',
                    'meditation': 'meditation',
                    'cardio': 'cardio',
                }
                workout_type_slug = type_mapping.get(workout_type_slug, 'other')
                
                workout_type, _ = WorkoutType.objects.get_or_create(
                    slug=workout_type_slug,
                    defaults={'name': workout_type_slug.title()}
                )
                
                # Get or create instructor
                instructor = None
                instructor_data = workout_data.get('instructor', {})
                if instructor_data:
                    peloton_instructor_id = instructor_data.get('id')
                    instructor_name = instructor_data.get('name', 'Unknown')
                    if peloton_instructor_id:
                        instructor, _ = Instructor.objects.get_or_create(
                            peloton_id=peloton_instructor_id,
                            defaults={'name': instructor_name}
                        )
                        if instructor.image_url != instructor_data.get('image_url'):
                            instructor.image_url = instructor_data.get('image_url', '')
                            instructor.save()
                
                # Parse dates - use created_at if available (more reliable for sync cutoff), otherwise start_time
                # created_at is when Peloton created the workout record, start_time is when user completed it
                # IMPORTANT: All Peloton timestamps are in UTC (Unix timestamps or ISO strings with Z)
                workout_timestamp = None
                created_at = workout_data.get('created_at')
                start_time = workout_data.get('start_time')
                
                # Prefer created_at for sync cutoff comparison (more reliable)
                # But use start_time for completed_date (what user sees)
                if created_at:
                    if isinstance(created_at, (int, float)):
                        # Unix timestamp (seconds) - already UTC
                        workout_timestamp = created_at
                    else:
                        # ISO string - parse and ensure UTC
                        try:
                            # Handle ISO format strings (e.g., "2024-01-01T12:00:00Z" or "2024-01-01T12:00:00+00:00")
                            dt_str = str(created_at).replace('Z', '+00:00')
                            dt = datetime.fromisoformat(dt_str)
                            # If timezone-naive, assume UTC
                            if dt.tzinfo is None:
                                dt = timezone.make_aware(dt, UTC)
                            else:
                                dt = dt.astimezone(UTC)
                            workout_timestamp = dt.timestamp()
                        except Exception as e:
                            logger.debug(f"Could not parse created_at '{created_at}': {e}")
                            pass
                
                # Fallback to start_time if created_at not available
                if not workout_timestamp and start_time:
                    if isinstance(start_time, (int, float)):
                        # Unix timestamp (seconds) - already UTC
                        workout_timestamp = start_time
                    else:
                        # ISO string - parse and ensure UTC
                        try:
                            dt_str = str(start_time).replace('Z', '+00:00')
                            dt = datetime.fromisoformat(dt_str)
                            # If timezone-naive, assume UTC
                            if dt.tzinfo is None:
                                dt = timezone.make_aware(dt, UTC)
                            else:
                                dt = dt.astimezone(UTC)
                            workout_timestamp = dt.timestamp()
                        except Exception as e:
                            logger.debug(f"Could not parse start_time '{start_time}': {e}")
                            pass
                
                # Parse completed_date from start_time
                # IMPORTANT: Convert to US Eastern Time (Peloton's timezone) before extracting date
                # This ensures streaks match Peloton's calculation (they use local date, not UTC date)
                # Example: Workout at 11 PM PST = 2 AM ET next day, but Peloton counts it as same day in PST
                # So we use ET to match Peloton's behavior
                try:
                    if ZoneInfo:
                        ET = ZoneInfo("America/New_York")  # US Eastern Time (handles DST automatically)
                    elif pytz:
                        ET = pytz.timezone("America/New_York")
                    else:
                        # No timezone library available, fallback to UTC
                        ET = UTC
                        logger.warning("No timezone library available, using UTC for completed_date (streaks may not match Peloton)")
                except Exception as e:
                    # Fallback to UTC if timezone conversion fails
                    ET = UTC
                    logger.warning(f"Failed to set ET timezone: {e}, using UTC for completed_date")
                
                if start_time:
                    if isinstance(start_time, (int, float)):
                        # Unix timestamp - convert to UTC datetime, then to ET, then extract date
                        dt_utc = datetime.fromtimestamp(start_time, tz=UTC)
                        dt_et = dt_utc.astimezone(ET) if ET != UTC else dt_utc
                        completed_date = dt_et.date()
                        # Log timezone conversion for debugging
                        if dt_utc.date() != completed_date:
                            logger.debug(f"Timezone conversion: UTC date {dt_utc.date()} -> ET date {completed_date} (offset: {dt_et.utcoffset()})")
                    else:
                        try:
                            dt_str = str(start_time).replace('Z', '+00:00')
                            dt = datetime.fromisoformat(dt_str)
                            if dt.tzinfo is None:
                                dt = timezone.make_aware(dt, UTC)
                            else:
                                dt = dt.astimezone(UTC)
                            # Convert to ET before extracting date
                            dt_et = dt.astimezone(ET) if ET != UTC else dt
                            completed_date = dt_et.date()
                            # Log timezone conversion for debugging
                            if dt.date() != completed_date:
                                logger.debug(f"Timezone conversion: UTC date {dt.date()} -> ET date {completed_date} (offset: {dt_et.utcoffset()})")
                        except Exception as e:
                            logger.debug(f"Error parsing start_time for completed_date: {e}")
                            # Fallback: use UTC date if conversion fails
                            try:
                                dt_utc = datetime.fromtimestamp(start_time, tz=UTC) if isinstance(start_time, (int, float)) else timezone.now()
                                dt_et = dt_utc.astimezone(ET) if ET != UTC else dt_utc
                                completed_date = dt_et.date()
                            except Exception:
                                completed_date = timezone.now().date()
                else:
                    # No start_time, use current date in ET
                    try:
                        dt_et = timezone.now().astimezone(ET) if ET != UTC else timezone.now()
                        completed_date = dt_et.date()
                    except Exception:
                        completed_date = timezone.now().date()
                
                # If we still don't have a timestamp, use current time in UTC (shouldn't happen, but be safe)
                if not workout_timestamp:
                    workout_timestamp = timezone.now().timestamp()
                
                # For incremental sync: check if this workout is older than last sync
                # Since workouts are sorted newest first, we can stop early
                # Both timestamps are now in UTC, so comparison is safe regardless of server/user timezone
                if not is_full_sync and sync_cutoff_timestamp and workout_timestamp:
                    # Add small buffer (5 seconds) to account for potential clock skew or rounding differences
                    # This ensures we don't miss workouts that were created at the exact same second
                    buffer_seconds = 5
                    if workout_timestamp <= (sync_cutoff_timestamp + buffer_seconds):
                        workouts_older_than_sync += 1
                        # If we've seen several older workouts in a row, we've likely passed the cutoff
                        # (allowing for some clock skew or edge cases where timestamps might be slightly off)
                        if workouts_older_than_sync >= 5:
                            cutoff_dt = datetime.fromtimestamp(sync_cutoff_timestamp, tz=UTC)
                            logger.info(f"Reached workouts older than last sync ({cutoff_dt} UTC). Stopping sync early.")
                            logger.info(f"  - Processed {total_processed} workouts before cutoff")
                            logger.info(f"  - Cutoff timestamp: {sync_cutoff_timestamp} (UTC)")
                            break
                        # Skip this workout but continue checking (in case of minor timestamp discrepancies)
                        continue
                    else:
                        # Reset counter when we find a newer workout
                        workouts_older_than_sync = 0
                
                # Step 1: Get ride_id from workout data
                ride_id = None
                if 'ride' in workout_data and workout_data.get('ride'):
                    ride_id = workout_data.get('ride', {}).get('id')
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found ride_id in workout_data: {ride_id}")
                
                # Step 2: Check if RideDetail already exists, if not fetch it FIRST
                ride_detail = None
                if ride_id:
                    # Check if we already have this ride detail
                    try:
                        ride_detail = RideDetail.objects.get(peloton_ride_id=ride_id)
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found existing RideDetail for ride_id {ride_id}: '{ride_detail.title}'")
                        # Fetch playlist for existing RideDetail if not already present
                        try:
                            ride_detail.playlist
                        except:
                            # Playlist doesn't exist, fetch ride details to get playlist
                            try:
                                ride_details = client.fetch_ride_details(ride_id)
                                playlist_data = ride_details.get('playlist')
                                if playlist_data:
                                    _store_playlist_from_data(playlist_data, ride_detail, logger, total_processed, peloton_workout_id)
                            except Exception as e:
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch ride details for playlist: {e}")
                    except RideDetail.DoesNotExist:
                        # RideDetail doesn't exist, fetch it now BEFORE creating workout
                        logger.info(f"Workout {total_processed} ({peloton_workout_id}): RideDetail not found for ride_id {ride_id}, fetching ride details first...")
                        try:
                            ride_details = client.fetch_ride_details(ride_id)
                            ride_data = ride_details.get('ride', {})
                            if ride_data:
                                # We'll create RideDetail below after we have all the data
                                logger.info(f"Workout {total_processed} ({peloton_workout_id}): Successfully fetched ride details for ride_id {ride_id}")
                            else:
                                logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Ride details response missing 'ride' data for ride_id {ride_id}")
                                ride_details = None
                        except Exception as e:
                            logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch ride details for ride_id {ride_id}: {e}")
                            ride_details = None
                else:
                    # No ride_id yet, try to get it from detailed workout
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No ride_id in workout_data, fetching detailed workout to get ride_id...")
                    try:
                        detailed_workout = client.fetch_workout(peloton_workout_id)
                        ride_id = detailed_workout.get('ride', {}).get('id') or detailed_workout.get('ride_id')
                        if ride_id:
                            logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found ride_id in detailed_workout: {ride_id}")
                            # Check if RideDetail exists
                            try:
                                ride_detail = RideDetail.objects.get(peloton_ride_id=ride_id)
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found existing RideDetail for ride_id {ride_id}")
                                # Fetch playlist for existing RideDetail if not already present
                                try:
                                    ride_detail.playlist
                                except:
                                    # Playlist doesn't exist, fetch ride details to get playlist
                                    try:
                                        ride_details = client.fetch_ride_details(ride_id)
                                        playlist_data = ride_details.get('playlist')
                                        if playlist_data:
                                            _store_playlist_from_data(playlist_data, ride_detail, logger, total_processed, peloton_workout_id)
                                    except Exception as e:
                                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch ride details for playlist: {e}")
                            except RideDetail.DoesNotExist:
                                # Fetch ride details
                                logger.info(f"Workout {total_processed} ({peloton_workout_id}): Fetching ride details for ride_id {ride_id}...")
                                try:
                                    ride_details = client.fetch_ride_details(ride_id)
                                    ride_data = ride_details.get('ride', {})
                                    if not ride_data:
                                        ride_details = None
                                except Exception as e:
                                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch ride details: {e}")
                                    ride_details = None
                        else:
                            logger.warning(f"Workout {total_processed} ({peloton_workout_id}): No ride_id found in detailed workout")
                            detailed_workout = None
                            ride_details = None
                    except Exception as e:
                        logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch detailed workout: {e}")
                        detailed_workout = None
                        ride_details = None
                
                # Step 3: Create or update RideDetail if we have ride_details and it doesn't exist yet
                if ride_id and not ride_detail and 'ride_details' in locals() and ride_details:
                    ride_data = ride_details.get('ride', {})
                    if ride_data:
                        logger.info(f"Workout {total_processed} ({peloton_workout_id}): Creating RideDetail for ride_id {ride_id}...")
                        
                        # Extract instructor from ride_details (more reliable than workout_data)
                        # ride_details has: ride_data['instructor_id'] and ride_data['instructor'] object
                        ride_instructor = None
                        instructor_id_from_ride = ride_data.get('instructor_id')
                        instructor_obj_from_ride = ride_data.get('instructor', {})
                        
                        if instructor_id_from_ride:
                            # Try to get instructor by peloton_id
                            try:
                                ride_instructor = Instructor.objects.get(peloton_id=instructor_id_from_ride)
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found existing instructor: {ride_instructor.name}")
                            except Instructor.DoesNotExist:
                                # Create instructor from ride_details instructor object
                                if instructor_obj_from_ride:
                                    instructor_name = instructor_obj_from_ride.get('name') or instructor_obj_from_ride.get('full_name') or 'Unknown Instructor'
                                    instructor_image = instructor_obj_from_ride.get('image_url') or ''
                                    ride_instructor, created = Instructor.objects.get_or_create(
                                        peloton_id=instructor_id_from_ride,
                                        defaults={
                                            'name': instructor_name,
                                            'image_url': instructor_image,
                                        }
                                    )
                                    if created:
                                        logger.info(f"Workout {total_processed} ({peloton_workout_id}): Created new instructor: {ride_instructor.name}")
                                    else:
                                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found instructor after creation: {ride_instructor.name}")
                                else:
                                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): instructor_id {instructor_id_from_ride} found but no instructor object in ride_details")
                        
                        # Fallback to instructor from workout_data if not found in ride_details
                        if not ride_instructor:
                            ride_instructor = instructor
                            if ride_instructor:
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Using instructor from workout_data: {ride_instructor.name}")
                        
                        # Extract equipment tags
                        equipment_tags = ride_data.get('equipment_tags', [])
                        if not isinstance(equipment_tags, list):
                            equipment_tags = []
                        
                        # Extract class type IDs
                        class_type_ids = ride_data.get('class_type_ids', [])
                        if not isinstance(class_type_ids, list):
                            class_type_ids = []
                        
                        # Detect class type from various sources
                        detected_class_type = detect_class_type(ride_data, ride_details)
                        
                        # Extract equipment IDs
                        equipment_ids = ride_data.get('equipment_ids', [])
                        if not isinstance(equipment_ids, list):
                            equipment_ids = []
                        
                        # Generate class URL
                        peloton_class_url = f"https://members.onepeloton.com/classes/cycling/{ride_id}" if ride_id else ''
                        # Try to determine discipline from ride_data
                        fitness_discipline = ride_data.get('fitness_discipline', '')
                        if fitness_discipline:
                            # Map discipline to URL path
                            discipline_paths = {
                                'cycling': 'cycling',
                                'running': 'treadmill',
                                'walking': 'walking',
                                'yoga': 'yoga',
                                'strength': 'strength',
                                'stretching': 'stretching',
                                'meditation': 'meditation',
                                'cardio': 'cardio',
                            }
                            path = discipline_paths.get(fitness_discipline, 'cycling')
                            peloton_class_url = f"https://members.onepeloton.com/classes/{path}/{ride_id}"
                        
                        ride_detail, ride_detail_created = RideDetail.objects.update_or_create(
                            peloton_ride_id=ride_id,
                            defaults={
                                'title': ride_data.get('title', ''),
                                'description': ride_data.get('description', ''),
                                'duration_seconds': ride_data.get('duration', 0),
                                'workout_type': workout_type,
                                'instructor': ride_instructor,  # Use instructor from ride_details
                                'fitness_discipline': ride_data.get('fitness_discipline', ''),
                                'fitness_discipline_display_name': ride_data.get('fitness_discipline_display_name', ''),
                                'difficulty_rating_avg': ride_data.get('difficulty_rating_avg'),
                                'difficulty_rating_count': ride_data.get('difficulty_rating_count', 0),
                                'difficulty_level': ride_data.get('difficulty_level') or None,
                                'overall_estimate': ride_data.get('overall_estimate'),
                                'difficulty_estimate': ride_data.get('difficulty_estimate'),
                                'image_url': ride_data.get('image_url', ''),
                                'home_peloton_id': ride_data.get('home_peloton_id') or '',
                                'original_air_time': ride_data.get('original_air_time'),
                                'scheduled_start_time': ride_data.get('scheduled_start_time'),
                                'created_at_timestamp': ride_data.get('created_at'),
                                'class_type_ids': class_type_ids,
                                'equipment_ids': equipment_ids,
                                'equipment_tags': equipment_tags,
                                'content_format': ride_data.get('content_format', ''),
                                'content_provider': ride_data.get('content_provider', ''),
                                'has_closed_captions': ride_data.get('has_closed_captions', False),
                                'is_archived': ride_data.get('is_archived', False),
                                'is_power_zone_class': ride_data.get('is_power_zone_class', False),
                                'class_type': detected_class_type,  # Store detected class type
                                'peloton_class_url': peloton_class_url,
                                # Store target metrics from ride_details (not ride_data)
                                'target_metrics_data': ride_details.get('target_metrics_data', {}),
                                'target_class_metrics': ride_details.get('target_class_metrics', {}),
                                'pace_target_type': ride_details.get('pace_target_type'),
                                # Store segments structure (contains segment_list with Warm Up, Main, Cool Down)
                                'segments_data': ride_details.get('segments', {}),
                            }
                        )
                        if ride_detail_created:
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): ✓ Created RideDetail: '{ride_detail.title}'")
                        else:
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): ↻ Updated RideDetail: '{ride_detail.title}'")
                        
                        # Step 4: Store playlist from ride_details if available (playlist is included in ride_details response)
                        playlist_data = ride_details.get('playlist') if 'ride_details' in locals() else None
                        if playlist_data:
                            _store_playlist_from_data(playlist_data, ride_detail, logger, total_processed, peloton_workout_id)
                
                # Step 4: Now fetch detailed workout for metrics (if we haven't already)
                if 'detailed_workout' not in locals():
                    try:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Fetching detailed workout for metrics...")
                        detailed_workout = client.fetch_workout(peloton_workout_id)
                    except Exception as e:
                        logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch detailed workout: {e}")
                        detailed_workout = None
                
                # Step 5: Extract title, duration, etc. from ride_detail if available, otherwise from other sources
                if ride_detail:
                    # Use data from RideDetail (most reliable)
                    title = ride_detail.title
                    duration_seconds = ride_detail.duration_seconds
                    duration_minutes = ride_detail.duration_minutes
                    description = ride_detail.description
                    difficulty_rating = ride_detail.difficulty_rating_avg
                    total_ratings = ride_detail.difficulty_rating_count
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Using data from RideDetail: '{title}' ({duration_minutes}min)")
                else:
                    # Fallback: extract from ride_details or detailed_workout
                    if 'ride_details' in locals() and ride_details:
                        ride_data = ride_details.get('ride', {})
                        title = ride_data.get('title') or ride_details.get('title') or workout_data.get('name', f"{workout_type.name} Workout")
                        duration_seconds = ride_data.get('duration') or ride_data.get('length') or 0
                        duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                        description = ride_data.get('description', '')
                        difficulty_rating = ride_data.get('difficulty_rating_avg')
                        total_ratings = ride_data.get('difficulty_rating_count', 0)
                    elif 'detailed_workout' in locals() and detailed_workout:
                        ride_data = detailed_workout.get('ride', {})
                        title = ride_data.get('title') or detailed_workout.get('name') or workout_data.get('name', f"{workout_type.name} Workout")
                        duration_seconds = ride_data.get('duration') or ride_data.get('length') or 0
                        duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                        description = detailed_workout.get('description', '')
                        difficulty_rating = None
                        total_ratings = 0
                    else:
                        # Last resort: use workout_data
                        title = initial_title or workout_data.get('name') or workout_data.get('title') or f"{workout_type.name} Workout"
                        duration_seconds = initial_duration_seconds or workout_data.get('duration') or 0
                        duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                        description = ''
                        difficulty_rating = None
                        total_ratings = 0
                    
                    logger.info(f"Workout {total_processed} ({peloton_workout_id}): Using fallback data - title: '{title}', duration: {duration_minutes}min")
                
                # Get Peloton workout URL - use workout ID format (profile/workouts/{id})
                peloton_url = None
                if peloton_workout_id:
                    # The workout URL format is: /profile/workouts/{workout_id}
                    peloton_url = f"https://members.onepeloton.com/profile/workouts/{peloton_workout_id}"
                
                # Create or update workout
                # NOTE: ride_detail is REQUIRED for new workouts - all class data comes from there via SQL joins
                # We don't store duplicate data (title, duration, instructor, etc.) in Workout model
                if not ride_detail:
                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Cannot create workout without ride_detail. Skipping.")
                    workouts_skipped += 1
                    continue
                
                workout, created = Workout.objects.update_or_create(
                    peloton_workout_id=peloton_workout_id,
                    user=request.user,
                    defaults={
                        'ride_detail': ride_detail,  # REQUIRED - all class data comes from here
                        'peloton_url': peloton_url,
                        'recorded_date': completed_date,
                        'completed_date': completed_date,
                        # No duplicate storage - title, duration, instructor, etc. come from ride_detail via joins
                    }
                )
                
                if created:
                    workouts_synced += 1
                    logger.info(f"Workout {total_processed} ({peloton_workout_id}): ✓ Created - '{ride_detail.title}' ({ride_detail.duration_minutes}min, {ride_detail.workout_type.name})")
                else:
                    workouts_updated += 1
                    logger.info(f"Workout {total_processed} ({peloton_workout_id}): ↻ Updated - '{ride_detail.title}' ({ride_detail.duration_minutes}min, {ride_detail.workout_type.name})")
                
                # Fetch performance graph to get detailed metrics (TSS, cadence, resistance, etc.)
                # This endpoint contains the actual workout metrics
                try:
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Fetching performance graph for metrics (every_n=5)...")
                    performance_graph = client.fetch_performance_graph(peloton_workout_id, every_n=5)
                    
                    # Extract metrics from performance graph
                    # The performance graph has a 'summaries' array with summary metrics (total_output, etc.)
                    # and a 'metrics' array with time-series data (for avg/max calculations)
                    summaries_array = performance_graph.get('summaries', [])
                    metrics_array = performance_graph.get('metrics', [])
                    metrics_dict = {}
                    
                    # Extract from summaries array (has slug and value)
                    for summary in summaries_array:
                        if isinstance(summary, dict):
                            slug = summary.get('slug')
                            value = summary.get('value')
                            
                            if slug and value is not None:
                                metrics_dict[slug] = value
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found summary metric {slug} = {value}")
                    
                    # Extract avg/max from metrics array (time-series data with average_value and max_value)
                    for metric in metrics_array:
                        if isinstance(metric, dict):
                            slug = metric.get('slug')
                            avg_value = metric.get('average_value')
                            max_value = metric.get('max_value')
                            
                            if slug:
                                # Map slug to our field names
                                if avg_value is not None:
                                    # Map common slugs to our field names
                                    avg_field_map = {
                                        'output': 'avg_output',
                                        'cadence': 'avg_cadence',
                                        'resistance': 'avg_resistance',
                                        'speed': 'avg_speed',
                                        'heart_rate': 'avg_heart_rate',
                                    }
                                    field_name = avg_field_map.get(slug, f'avg_{slug}')
                                    metrics_dict[field_name] = avg_value
                                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found avg metric {slug} -> {field_name} = {avg_value}")
                                
                                if max_value is not None:
                                    max_field_map = {
                                        'output': 'max_output',
                                        'cadence': 'max_cadence',
                                        'resistance': 'max_resistance',
                                        'speed': 'max_speed',
                                        'heart_rate': 'max_heart_rate',
                                    }
                                    field_name = max_field_map.get(slug, f'max_{slug}')
                                    metrics_dict[field_name] = max_value
                                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found max metric {slug} -> {field_name} = {max_value}")
                    
                    # Also check for average_summaries (if present)
                    average_summaries = performance_graph.get('average_summaries', [])
                    for summary in average_summaries:
                        if isinstance(summary, dict):
                            slug = summary.get('slug')
                            value = summary.get('value')
                            if slug and value is not None:
                                # These are typically averages
                                avg_field_map = {
                                    'output': 'avg_output',
                                    'cadence': 'avg_cadence',
                                    'resistance': 'avg_resistance',
                                    'speed': 'avg_speed',
                                    'heart_rate': 'avg_heart_rate',
                                }
                                field_name = avg_field_map.get(slug, f'avg_{slug}')
                                if field_name not in metrics_dict:  # Don't overwrite if already set
                                    metrics_dict[field_name] = value
                                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found average_summary {slug} -> {field_name} = {value}")
                    
                    # Also check detailed_workout for any metrics that might be there (fallback)
                    if 'detailed_workout' in locals() and detailed_workout:
                        top_level_metrics = ['total_output', 'avg_output', 'max_output', 'distance', 'total_calories', 
                                            'avg_heart_rate', 'max_heart_rate', 'avg_cadence', 'max_cadence', 
                                            'avg_resistance', 'max_resistance', 'avg_speed', 'max_speed', 'tss', 'tss_target']
                        for key in top_level_metrics:
                            if key in detailed_workout and key not in metrics_dict:
                                metrics_dict[key] = detailed_workout[key]
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found metric in detailed_workout {key} = {detailed_workout[key]}")
                    
                    # Update workout details with extracted metrics
                    if metrics_dict:
                        details, details_created = WorkoutDetails.objects.get_or_create(workout=workout)
                        details_updated = False
                        
                        # TSS (might be in detailed_workout, not performance graph)
                        if 'tss' in metrics_dict:
                            try:
                                details.tss = float(metrics_dict['tss'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'tss_target' in metrics_dict:
                            try:
                                details.tss_target = float(metrics_dict['tss_target'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Output metrics
                        if 'total_output' in metrics_dict:
                            try:
                                details.total_output = float(metrics_dict['total_output'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'avg_output' in metrics_dict:
                            try:
                                details.avg_output = float(metrics_dict['avg_output'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_output' in metrics_dict:
                            try:
                                details.max_output = float(metrics_dict['max_output'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Speed metrics
                        if 'avg_speed' in metrics_dict:
                            try:
                                details.avg_speed = float(metrics_dict['avg_speed'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_speed' in metrics_dict:
                            try:
                                details.max_speed = float(metrics_dict['max_speed'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Distance
                        if 'distance' in metrics_dict:
                            try:
                                details.distance = float(metrics_dict['distance'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Heart rate (might be in metrics array as 'heart_rate')
                        if 'avg_heart_rate' in metrics_dict:
                            try:
                                details.avg_heart_rate = int(float(metrics_dict['avg_heart_rate']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_heart_rate' in metrics_dict:
                            try:
                                details.max_heart_rate = int(float(metrics_dict['max_heart_rate']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Cadence
                        if 'avg_cadence' in metrics_dict:
                            try:
                                details.avg_cadence = int(float(metrics_dict['avg_cadence']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_cadence' in metrics_dict:
                            try:
                                details.max_cadence = int(float(metrics_dict['max_cadence']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Resistance
                        if 'avg_resistance' in metrics_dict:
                            try:
                                details.avg_resistance = float(metrics_dict['avg_resistance'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_resistance' in metrics_dict:
                            try:
                                details.max_resistance = float(metrics_dict['max_resistance'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Calories (from summaries, slug is 'calories')
                        if 'calories' in metrics_dict or 'total_calories' in metrics_dict:
                            try:
                                calories_value = metrics_dict.get('calories') or metrics_dict.get('total_calories')
                                details.total_calories = int(float(calories_value))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        if details_updated:
                            details.save()
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): WorkoutDetails {'created' if details_created else 'updated'} with {len(metrics_dict)} metrics")
                        else:
                            logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No metrics to update")
                    
                    # Store time-series performance data in WorkoutPerformanceData
                    # The performance graph has 'seconds_since_pedaling_start' and 'metrics' with 'values' arrays
                    seconds_array = performance_graph.get('seconds_since_pedaling_start', [])
                    if seconds_array and metrics_array:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Storing time-series performance data...")
                        
                        # Delete existing performance data for this workout
                        from .models import WorkoutPerformanceData
                        WorkoutPerformanceData.objects.filter(workout=workout).delete()
                        
                        # Build a dict of metric values by slug for easier access
                        metric_values_by_slug = {}
                        for metric in metrics_array:
                            slug = metric.get('slug')
                            values = metric.get('values', [])
                            if slug and values:
                                metric_values_by_slug[slug] = values
                            
                            # For running classes, speed might be in the 'pace' metric's alternatives array
                            if slug == 'pace':
                                alternatives = metric.get('alternatives', [])
                                for alt in alternatives:
                                    alt_slug = alt.get('slug')
                                    alt_values = alt.get('values', [])
                                    if alt_slug == 'speed' and alt_values:
                                        # Use speed from alternatives if not already found
                                        if 'speed' not in metric_values_by_slug:
                                            metric_values_by_slug['speed'] = alt_values
                                            logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found speed in pace metric alternatives ({len(alt_values)} values)")
                        
                        # Create performance data entries for each timestamp
                        performance_data_entries = []
                        for idx, timestamp in enumerate(seconds_array):
                            if not isinstance(timestamp, (int, float)):
                                continue
                            
                            # Extract values for this timestamp from each metric
                            perf_data = WorkoutPerformanceData(
                                workout=workout,
                                timestamp=int(timestamp),
                                output=metric_values_by_slug.get('output', [None])[idx] if idx < len(metric_values_by_slug.get('output', [])) else None,
                                cadence=int(metric_values_by_slug.get('cadence', [None])[idx]) if idx < len(metric_values_by_slug.get('cadence', [])) and metric_values_by_slug.get('cadence', [None])[idx] is not None else None,
                                resistance=metric_values_by_slug.get('resistance', [None])[idx] if idx < len(metric_values_by_slug.get('resistance', [])) else None,
                                speed=metric_values_by_slug.get('speed', [None])[idx] if idx < len(metric_values_by_slug.get('speed', [])) else None,
                                heart_rate=int(metric_values_by_slug.get('heart_rate', [None])[idx]) if idx < len(metric_values_by_slug.get('heart_rate', [])) and metric_values_by_slug.get('heart_rate', [None])[idx] is not None else None,
                            )
                            performance_data_entries.append(perf_data)
                        
                        # Bulk create performance data
                        if performance_data_entries:
                            WorkoutPerformanceData.objects.bulk_create(performance_data_entries, ignore_conflicts=True)
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): Stored {len(performance_data_entries)} time-series data points")
                        else:
                            logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No time-series data to store")
                        
                        # Log target_metrics_performance_data availability for power zone classes
                        target_metrics_perf = performance_graph.get('target_metrics_performance_data', {})
                        target_metrics_list = target_metrics_perf.get('target_metrics', [])
                        if target_metrics_list:
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): Found {len(target_metrics_list)} target metric segments (will be fetched on-demand for graph)")
                        elif ride_detail and ride_detail.is_power_zone_class:
                            logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Power zone class but no target_metrics_performance_data found in API response")
                    else:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No time-series data available (seconds_array: {len(seconds_array) if seconds_array else 0}, metrics_array: {len(metrics_array) if metrics_array else 0})")
                        
                except Exception as e:
                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch performance graph for metrics: {e}")
                    # Continue without metrics - workout is still created
                
            except Exception as e:
                workouts_skipped += 1
                logger.error(f"Workout {total_processed} ({workout_data.get('id', 'unknown')}): ✗ Error syncing workout: {e}", exc_info=True)
                continue
        
        # Update connection last sync time
        sync_completed_at = timezone.now()
        connection.last_sync_at = sync_completed_at
        
        # Clear sync in progress and set cooldown period (60 minutes)
        connection.sync_in_progress = False
        connection.sync_started_at = None
        connection.sync_cooldown_until = sync_completed_at + timedelta(minutes=60)
        connection.save()
        
        # Also update profile sync time
        if hasattr(request.user, 'profile'):
            request.user.profile.peloton_last_synced_at = sync_completed_at
            request.user.profile.save()
        
        # Build success message
        sync_type_str = "full" if is_full_sync else "incremental"
        if workouts_synced > 0 or workouts_updated > 0:
            success_message = f'Successfully synced {workouts_synced} new workouts and updated {workouts_updated} existing workouts ({sync_type_str} sync)!'
        else:
            success_message = f'No new workouts to sync ({sync_type_str} sync).'
        
        messages.success(request, success_message)
        logger.info(f"Workout sync completed for user {request.user.email} ({sync_type_str} sync):")
        logger.info(f"  - Sync type: {sync_type_str}")
        logger.info(f"  - Total processed: {total_processed}")
        logger.info(f"  - New workouts: {workouts_synced}")
        logger.info(f"  - Updated workouts: {workouts_updated}")
        logger.info(f"  - Skipped/errors: {workouts_skipped}")
        if not is_full_sync:
            logger.info(f"  - Workouts older than last sync (skipped): {workouts_older_than_sync}")
        logger.info(f"  - Success rate: {((workouts_synced + workouts_updated) / total_processed * 100) if total_processed > 0 else 0:.1f}%")
        logger.info(f"  - Next sync will be incremental (after {sync_completed_at})")
        
        # If HTMX request, return partial
        if request.headers.get('HX-Request'):
            context = {
                'peloton_connection': connection,
                'sync_in_progress': False,
                'sync_cooldown_until': connection.sync_cooldown_until,
                'cooldown_remaining_minutes': 60,  # Just started cooldown
                'can_sync': False,
            }
            return render(request, 'workouts/partials/sync_status.html', context)
        
        # If AJAX request, return JSON (backwards compatibility)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'sync_type': sync_type_str,
                'message': success_message,
                'workouts_synced': workouts_synced,
                'workouts_updated': workouts_updated,
            })
        
    except PelotonAPIError as e:
        logger.error(f"Peloton API error during sync: {e}", exc_info=True)
        error_message = f'Peloton API error: {str(e)}'
        
        # Clear sync status on error
        connection.sync_in_progress = False
        connection.sync_started_at = None
        connection.save()
        
        messages.error(request, error_message)
        
        # If AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_message,
            }, status=400)
    except Exception as e:
        logger.error(f"Error syncing workouts: {e}", exc_info=True)
        error_message = f'Error syncing workouts: {str(e)}'
        
        # Clear sync status on error
        connection.sync_in_progress = False
        connection.sync_started_at = None
        connection.save()
        
        messages.error(request, error_message)
        
        # If AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_message,
            }, status=500)
    
    return redirect('workouts:history')


@login_required
@require_http_methods(["GET"])
def sync_status(request):
    """Return sync status for AJAX/HTMX polling"""
    try:
        peloton_connection = PelotonConnection.objects.get(user=request.user)
        
        # Check if sync is in progress or cooldown
        sync_in_progress = peloton_connection.sync_in_progress
        sync_cooldown_until = None
        cooldown_remaining_minutes = None
        can_sync = True
        
        if peloton_connection.sync_cooldown_until and timezone.now() < peloton_connection.sync_cooldown_until:
            sync_cooldown_until = peloton_connection.sync_cooldown_until
            cooldown_remaining_minutes = int((peloton_connection.sync_cooldown_until - timezone.now()).total_seconds() / 60)
            can_sync = False
        
        if sync_in_progress:
            can_sync = False
        
        # If HTMX request, return HTML partial
        if request.headers.get('HX-Request'):
            context = {
                'peloton_connection': peloton_connection,
                'sync_in_progress': sync_in_progress,
                'sync_cooldown_until': sync_cooldown_until,
                'cooldown_remaining_minutes': cooldown_remaining_minutes,
                'can_sync': can_sync,
            }
            return render(request, 'workouts/partials/sync_status.html', context)
        
        # Otherwise return JSON (for backwards compatibility)
        status = {
            'connected': True,
            'last_sync_at': peloton_connection.last_sync_at.isoformat() if peloton_connection.last_sync_at else None,
            'sync_in_progress': sync_in_progress,
            'sync_cooldown_until': sync_cooldown_until.isoformat() if sync_cooldown_until else None,
            'cooldown_remaining_minutes': cooldown_remaining_minutes,
            'workout_count': Workout.objects.filter(user=request.user).count(),
        }
    except PelotonConnection.DoesNotExist:
        # If HTMX request, return HTML partial
        if request.headers.get('HX-Request'):
            context = {
                'peloton_connection': None,
                'sync_in_progress': False,
                'sync_cooldown_until': None,
                'cooldown_remaining_minutes': None,
                'can_sync': False,
            }
            return render(request, 'workouts/partials/sync_status.html', context)
        
        # Otherwise return JSON
        status = {
            'connected': False,
            'last_sync_at': None,
            'sync_in_progress': False,
            'sync_cooldown_until': None,
            'cooldown_remaining_minutes': None,
            'workout_count': 0,
        }
    
    return JsonResponse(status)
