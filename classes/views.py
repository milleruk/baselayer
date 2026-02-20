from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.http import JsonResponse
import json
import re

from workouts.models import Workout, WorkoutType, Instructor, RideDetail
from workouts.services.metrics import MetricsCalculator
from .services.filters import ClassLibraryFilter
from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS
from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS
from datetime import datetime

from core.utils.pace_converter import pace_str_from_mph
from core.utils.workout_targets import (
    extract_spin_up_intervals,
    calculate_target_line_from_segments,
    calculate_pace_target_line_from_segments,
    calculate_power_zone_target_line,
    target_segment_at_time_with_shift,
)
from workouts.services.workout_helpers import estimate_workout_avg_speed_mph, estimate_workout_if_from_tss
from .services.library_metrics import build_class_library_metrics

import logging

logger = logging.getLogger(__name__)

# Initialize service instances
metrics_calculator = MetricsCalculator()


# Wrapper functions that need access to metrics_calculator
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


def _target_segment_at_time_with_shift(segments, t_seconds, shift_seconds=0):
    """Wrapper for target_segment_at_time_with_shift from core.utils.workout_targets."""
    return target_segment_at_time_with_shift(segments, t_seconds, shift_seconds)

@login_required
def class_library(request):
    """Display all available classes/rides with filtering and pagination"""
    # ClassLibraryFilter is imported at module level from .services.filters
    
    # Get base queryset - only allowed types
    rides = RideDetail.objects.filter(
        Q(workout_type__slug__in=ClassLibraryFilter.ALLOWED_TYPES) |
        Q(fitness_discipline__in=ClassLibraryFilter.ALLOWED_DISCIPLINES)
    ).exclude(
        class_type__in=['warm_up', 'cool_down']
    ).exclude(
        Q(title__icontains='warm up') | Q(title__icontains='warmup') |
        Q(title__icontains='cool down') | Q(title__icontains='cooldown')
    ).select_related('workout_type', 'instructor')
    
    # Apply filters using the service
    class_filter = ClassLibraryFilter(rides)
    
    # Apply all filters from request using chainable API
    class_filter.apply_search(request.GET.get('search', '').strip())
    class_filter.apply_workout_type_filter(request.GET.get('type', ''))
    class_filter.apply_instructor_filter(request.GET.get('instructor', ''))
    class_filter.apply_duration_filter(request.GET.get('duration', ''))
    class_filter.apply_year_filter(request.GET.get('year', ''))
    class_filter.apply_month_filter(request.GET.get('year', ''), request.GET.get('month', ''))
    class_filter.apply_ordering(request.GET.get('order_by', '-original_air_time'))
    
    rides = class_filter.get_queryset()
    filters = class_filter.get_filters()
    
    # For backward compatibility, extract individual filters
    search_query = filters.get('search', '')
    workout_type_filter = filters.get('workout_type', '')
    instructor_filter = filters.get('instructor', '')
    duration_filter = filters.get('duration', '')
    year_filter = filters.get('year', '')
    month_filter = filters.get('month', '')
    order_by = filters.get('order_by', '-original_air_time')
    
    # TSS filter (not part of ClassLibraryFilter yet - applied post-metrics calculation)
    tss_filter = request.GET.get('tss', '')
    
    # Pagination
    paginator = Paginator(rides, 12)  # 12 rides per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Add pagination flag for template
    is_paginated = page_obj.has_other_pages()
    
    # Get base queryset for filter options
    base_rides = RideDetail.objects.filter(
        Q(workout_type__slug__in=ClassLibraryFilter.ALLOWED_TYPES) |
        Q(fitness_discipline__in=ClassLibraryFilter.ALLOWED_DISCIPLINES)
    ).exclude(
        class_type__in=['warm_up', 'cool_down']
    ).exclude(
        Q(title__icontains='warm up') | Q(title__icontains='warmup') |
        Q(title__icontains='cool down') | Q(title__icontains='cooldown')
    )
    
    # Get filter options - only show allowed types
    workout_types = WorkoutType.objects.filter(
        Q(slug__in=ClassLibraryFilter.ALLOWED_TYPES) |
        Q(ride_details__fitness_discipline__in=ClassLibraryFilter.ALLOWED_DISCIPLINES)
    ).distinct().order_by('name')
    
    # Get instructors from the filtered rides
    instructors = Instructor.objects.filter(
        Q(ride_details__workout_type__slug__in=ClassLibraryFilter.ALLOWED_TYPES) |
        Q(ride_details__fitness_discipline__in=ClassLibraryFilter.ALLOWED_DISCIPLINES)
    ).distinct().order_by('name')
    
    # Get available durations using service method
    durations = ClassLibraryFilter.get_available_durations(base_rides)
    
    # Get available years using service method
    available_years_list = ClassLibraryFilter.get_available_years(base_rides)
    
    # Get available months using service method
    available_months = ClassLibraryFilter.get_available_months(base_rides, year_filter) if year_filter else []
    
    # Calculate TSS/IF and zone data for each ride (for card display)
    user_profile = request.user.profile if hasattr(request.user, 'profile') else None
    rides_with_metrics = build_class_library_metrics(
        page_obj=page_obj,
        user_profile=user_profile,
        tss_filter=tss_filter,
        metrics_calculator=metrics_calculator,
    )
    
    # Handle AJAX requests for live search
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('ajax') == '1':
        # Return JSON response for AJAX requests
        results = []
        for ride_data in rides_with_metrics[:12]:  # Limit to 12 for preview
            ride = ride_data['ride']
            results.append({
                'id': ride.id,
                'title': ride.title,
                'duration_minutes': ride.duration_minutes,
                'instructor': ride.instructor.name if ride.instructor else None,
                'workout_type': ride.workout_type.name if ride.workout_type else None,
                'original_air_date': ride.original_air_date.strftime('%b %d, %Y') if ride.original_air_date else None,
                'url': f'/workouts/library/{ride.id}/',
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total': page_obj.paginator.count,
            'has_more': page_obj.has_next(),
        })
    
    # Get user's pace zones for both running and walking from the pace level data files
    user_running_pace_zones = None
    user_walking_pace_zones = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS
        from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS
        
        # Running pace zones (7 zones)
        running_pace_entry = request.user.pace_entries.filter(activity_type='running', is_active=True).first()
        if running_pace_entry and running_pace_entry.level in DEFAULT_RUNNING_PACE_LEVELS:
            level_data = DEFAULT_RUNNING_PACE_LEVELS[running_pace_entry.level]
            user_running_pace_zones = {}
            for zone_name, (min_mph, max_mph, min_pace, max_pace, desc) in level_data.items():
                # Use min_pace (the faster/lower end of the range) as target
                # Convert decimal minutes to seconds
                user_running_pace_zones[zone_name] = int(min_pace * 60)
        
        # Walking pace zones (5 zones)
        walking_pace_entry = request.user.pace_entries.filter(activity_type='walking', is_active=True).first()
        if walking_pace_entry and walking_pace_entry.level in DEFAULT_WALKING_PACE_LEVELS:
            level_data = DEFAULT_WALKING_PACE_LEVELS[walking_pace_entry.level]
            user_walking_pace_zones = {}
            for zone_name, (min_mph, max_mph, min_pace, max_pace, desc) in level_data.items():
                # Use min_pace (the faster/lower end of the range) as target
                # Convert decimal minutes to seconds
                user_walking_pace_zones[zone_name] = int(min_pace * 60)
    
    context = {
        'rides_with_metrics': rides_with_metrics,
        'page_obj': page_obj,
        'is_paginated': is_paginated,
        'search_query': search_query,
        'workout_type_filter': workout_type_filter,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'available_years': available_years_list,
        'available_months': available_months,
        'instructor_filter': instructor_filter,
        'duration_filter': duration_filter,
        'tss_filter': tss_filter,
        'workout_types': workout_types,
        'instructors': instructors,
        'durations': durations,
        'order_by': order_by,
        'user_running_pace_zones': user_running_pace_zones,
        'user_walking_pace_zones': user_walking_pace_zones,
    }
    
    # Add year/month filter variables to context
    context.update({
        'year_filter': year_filter,
        'month_filter': month_filter,
        'available_years': available_years_list,
        'available_months': available_months,
    })
    
    # If HTMX request, return appropriate partial
    if request.headers.get('HX-Request'):
        # For filters/pagination, return full class list
        return render(request, 'classes/partials/class_list.html', context)
    
    # Otherwise return full page
    return render(request, "classes/class_library.html", context)


@login_required
def class_detail(request, pk):
    """Display detailed view of a single class/ride"""
    ride = get_object_or_404(
        RideDetail.objects.select_related('workout_type', 'instructor').prefetch_related('playlist'),
        pk=pk
    )
    
    # Get user profile for target metrics calculations
    try:
        user_profile = request.user.profile
    except:
        from accounts.models import Profile
        user_profile = Profile.objects.get_or_create(user=request.user)[0]
    
    # Prepare target metrics data based on class type
    target_metrics = None
    target_metrics_json = None
    zone_distribution = []
    class_segments = []
    target_line_data = None  # Initialize outside block for scope
    user_pace_level = None  # Initialize early to avoid UnboundLocalError for non-pace classes
    user_pace_bands = None  # Initialize early to avoid UnboundLocalError for non-pace classes
    spin_up_intervals = _extract_spin_up_intervals(ride)
    
    if ride.class_type == 'power_zone' or ride.is_power_zone_class:
        # Power Zone class - get user's FTP for zone calculations
        user_ftp = user_profile.get_current_ftp()
        segments = ride.get_power_zone_segments(user_ftp=user_ftp)
        zone_ranges = user_profile.get_power_zone_ranges() if user_ftp else None
        target_metrics = {
            'type': 'power_zone',
            'segments': segments,
            'zone_ranges': zone_ranges,
            'user_ftp': user_ftp
        }
        
        # Build chart data for power zone classes (similar to pace target)
        # Prefer segments_data (segment_list) as it has exact class plan timings
        power_zone_chart = None
        total_duration = ride.duration_seconds
        
        # Create 7 power zones (1-7)
        chart_zones = []
        zone_labels = ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5", "Zone 6", "Zone 7"]
        zone_colors = ["#9333ea", "#3b82f6", "#10b981", "#eab308", "#f97316", "#ef4444", "#ec4899"]
        
        for i in range(7):
            chart_zones.append({
                "name": zone_labels[i],
                "label": zone_labels[i],
                "color": zone_colors[i]
            })
        
        chart_segments = []
        
        # Method 1: Use segments_data (segment_list) if available - this has exact class plan timings
        if ride.segments_data and ride.segments_data.get('segment_list'):
            segment_list = ride.segments_data.get('segment_list', [])
            
            for seg in segment_list:
                subsegments = seg.get('subsegments_v2', [])
                section_start = seg.get('start_time_offset', 0)
                
                for subseg in subsegments:
                    subseg_offset = subseg.get('offset', 0)
                    subseg_length = subseg.get('length', 0)
                    display_name = subseg.get('display_name', '')
                    
                    if subseg_length > 0 and display_name:
                        # Calculate absolute start/end times
                        abs_start = section_start + subseg_offset
                        abs_end = abs_start + subseg_length
                        
                        # Extract zone number from display_name (e.g., "Zone 1", "Zone 2", etc.)
                        zone_num = 1  # Default
                        zone_match = re.search(r'zone\s*(\d+)', display_name, re.IGNORECASE)
                        if zone_match:
                            zone_num = int(zone_match.group(1))
                        
                        # Clamp zone to 1-7 range
                        chart_zone = max(1, min(7, int(zone_num)))
                        
                        chart_segments.append({
                            "duration": subseg_length,
                            "zone": chart_zone,
                            "start": abs_start,
                            "end": abs_end,
                        })
        
        # Method 2: Fallback to target_metrics_data segments if segments_data not available
        if not chart_segments and segments:
            for i, segment in enumerate(segments):
                zone_num = segment.get('zone', 1)  # Power zone 1-7
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                
                # If start == end (point-in-time segment), use next segment's start as end
                if start == end and i < len(segments) - 1:
                    next_segment = segments[i + 1]
                    end = next_segment.get('start', start + 60)  # Default to 60 seconds if no next segment
                elif start == end:
                    # Last segment with start==end, extend to class duration
                    end = total_duration
                
                # Ensure end doesn't exceed class duration
                end = min(end, total_duration)
                
                # For the last segment, ensure it extends to exactly the class duration
                if i == len(segments) - 1:
                    end = total_duration
                
                duration = end - start
                
                # Skip segments with zero or negative duration
                if duration <= 0:
                    continue
                
                # Clamp zone to 1-7 range (power zones are 1-7, not 0-6)
                chart_zone = max(1, min(7, int(zone_num)))
                
                chart_segments.append({
                    "duration": duration,
                    "zone": chart_zone,  # Power zones are 1-7
                    "start": start,
                    "end": end,
                })
        
        if chart_segments:
            # Sort segments by start time to ensure proper order
            chart_segments.sort(key=lambda x: x['start'])
            
            # Use exact class duration (no offset)
            power_zone_chart = {
                'chart_data': {
                    'type': 'power_zone',
                    'segments': chart_segments,
                    'zones': chart_zones,
                    'total_duration': total_duration,  # Exact class duration
                }
            }
        
        # Calculate target line data for visualization (matching workout_detail approach)
        if segments and len(segments) > 0 and user_ftp and zone_ranges:
            # Generate timestamps array for target line (every 5 seconds, matching workout_detail)
            timestamps = list(range(0, total_duration + 1, 5))
            
            # Calculate target line from segments
            target_line_data = _calculate_target_line_from_segments(
                segments,
                zone_ranges,
                timestamps,
                user_ftp,
                spin_up_intervals=spin_up_intervals,
            )
        
        # Calculate zone distribution
        if segments:
            zone_times = {}
            for segment in segments:
                zone = segment.get('zone', 0)
                duration = segment.get('end', 0) - segment.get('start', 0)
                zone_times[zone] = zone_times.get(zone, 0) + duration
            
            total_duration = ride.duration_seconds
            for zone in range(1, 8):
                time_sec = zone_times.get(zone, 0)
                if time_sec > 0:
                    minutes = time_sec // 60
                    seconds = time_sec % 60
                    percentage = (time_sec / total_duration * 100) if total_duration > 0 else 0
                    zone_distribution.append({
                        'zone': zone,
                        'time_sec': time_sec,
                        'time_str': f"{minutes:02d}:{seconds:02d}",
                        'percentage': int(percentage)
                    })
    elif ride.fitness_discipline in ['running', 'walking', 'run']:
        # Running/Walking class - build chart data
        # Prefer segments_data (segment_list) as it has exact class plan timings
        pace_chart = None
        total_duration = ride.duration_seconds
        
        # Create 7 pace zones (0-6)
        chart_zones = []
        pace_labels = ["Recovery", "Easy", "Moderate", "Challenging", "Hard", "Very Hard", "Max"]
        pace_colors = ["#6f42c1", "#4c6ef5", "#228be6", "#0ca678", "#ff922b", "#f76707", "#fa5252"]
        
        for i in range(7):
            chart_zones.append({
                "name": pace_labels[i],
                "label": pace_labels[i],
                "color": pace_colors[i]
            })
        
        chart_segments = []
        
        # Method 1: Use segments_data (segment_list) if available - this has exact class plan timings
        if ride.segments_data and ride.segments_data.get('segment_list'):
            segment_list = ride.segments_data.get('segment_list', [])
            
            # Map pace names to zone numbers (0-6)
            # Handle various formats: "Recovery", "Easy", "Moderate", "Challenging", "Hard", "Very Hard", "Max"
            # Also handle variations like "Very Hard" vs "VeryHard" vs "very_hard"
            pace_name_to_zone = {
                'recovery': 0, 
                'easy': 1, 
                'moderate': 2, 
                'challenging': 3,
                'hard': 4, 
                'very hard': 5, 
                'veryhard': 5,
                'very_hard': 5,
                'max': 6,
                'maximum': 6,
                'drills': 1,  # Map drills to Easy pace (not a measured pace target)
                'drill': 1
            }
            
            for seg in segment_list:
                subsegments = seg.get('subsegments_v2', [])
                section_start = seg.get('start_time_offset', 0)
                
                for subseg in subsegments:
                    # NOTE: subseg 'offset' is already absolute from class start, not relative to section
                    subseg_offset = subseg.get('offset', 0)  # Absolute offset from class start
                    subseg_length = subseg.get('length', 0)
                    display_name = subseg.get('display_name', '')
                    
                    if subseg_length > 0 and display_name:
                        # Calculate absolute start/end times
                        # offset is already absolute, so use it directly
                        abs_start = subseg_offset
                        abs_end = abs_start + subseg_length
                        
                        # Skip segments that start beyond the class duration
                        if abs_start >= total_duration:
                            continue
                        
                        # Clamp end time to class duration
                        abs_end = min(abs_end, total_duration)
                        subseg_length = abs_end - abs_start
                        
                        if subseg_length <= 0:
                            continue
                        
                        # Extract pace level from display_name (e.g., "Recovery", "Easy", "Moderate", etc.)
                        # Try exact match first, then substring match (longest phrases first to avoid partial matches)
                        pace_level = 2  # Default to Moderate
                        display_lower = display_name.lower().strip()
                        
                        # Try exact match first (most reliable)
                        if display_lower in pace_name_to_zone:
                            pace_level = pace_name_to_zone[display_lower]
                        else:
                            # Try substring match (handle cases like "Moderate Pace" or "Easy Run")
                            # Sort by length descending to match longer phrases first (e.g., "very hard" before "hard")
                            sorted_pace_names = sorted(pace_name_to_zone.items(), key=lambda x: len(x[0]), reverse=True)
                            for pace_name, zone_num in sorted_pace_names:
                                # Check if pace name is at the start of display_name or as a whole word
                                if display_lower.startswith(pace_name) or \
                                   f' {pace_name} ' in f' {display_lower} ' or \
                                   display_lower.endswith(f' {pace_name}'):
                                    pace_level = zone_num
                                    break
                        
                        chart_segments.append({
                            "duration": subseg_length,
                            "zone": pace_level,
                            "pace_level": pace_level,
                            "start": abs_start,
                            "end": abs_end,
                        })
        
        # Method 2: Fallback to target_metrics_data if segments_data not available
        if not chart_segments and ride.target_metrics_data and isinstance(ride.target_metrics_data, dict):
            target_metrics_list = ride.target_metrics_data.get('target_metrics', [])
            if target_metrics_list and isinstance(target_metrics_list, list):
                for idx, metric in enumerate(target_metrics_list):
                    if 'offsets' in metric and 'metrics' in metric:
                        start_time = metric['offsets']['start']
                        end_time = metric['offsets']['end']
                        duration = end_time - start_time
                        
                        if duration <= 0:
                            continue
                        
                        # Ensure end doesn't exceed class duration
                        end_time = min(end_time, total_duration)
                        
                        # For the last segment, ensure it extends to exactly the class duration
                        if idx == len(target_metrics_list) - 1:
                            end_time = total_duration
                        
                        duration = end_time - start_time
                        
                        if duration <= 0:
                            continue
                        
                        # Find pace intensity from metrics (0-6)
                        pace_intensity = 0
                        for m in metric['metrics']:
                            if m.get('name') == 'pace_intensity':
                                # Use upper value as the pace intensity (0-6)
                                pace_intensity = m.get('upper', 0)
                                break
                        
                        # Clamp to 0-6 range
                        pace_level = max(0, min(6, int(pace_intensity)))
                        
                        chart_segments.append({
                            "duration": duration,
                            "zone": pace_level,  # Use 'zone' to match reference format
                            "pace_level": pace_level,
                            "start": start_time,
                            "end": end_time,
                        })
        
        if chart_segments:
            # Sort segments by start time to ensure proper order
            chart_segments.sort(key=lambda x: x['start'])
            
            # Calculate actual duration from segments (use last segment's end time)
            # This ensures we match the actual class plan duration from segments_data
            actual_duration = total_duration
            if chart_segments:
                last_segment_end = max(seg.get('end', 0) for seg in chart_segments)
                # Use last segment end time, but don't exceed ride duration
                # If segments only go to 23:10 but ride is 30:00, use 23:10 (actual class plan)
                actual_duration = min(last_segment_end, total_duration)
            
            # Use actual duration from segments (matches class plan)
            pace_chart = {
                'chart_data': {
                    'type': 'pace_target',
                    'segments': chart_segments,
                    'zones': chart_zones,
                    'total_duration': actual_duration,  # Actual duration from segments
                }
            }
        
        # Fallback: use get_pace_segments if segments_data and target_metrics_data approaches didn't work
        # But first double-check segments_data wasn't missed
        if not pace_chart and ride.segments_data and ride.segments_data.get('segment_list'):
            # Try segments_data one more time (in case it was skipped earlier)
            segment_list = ride.segments_data.get('segment_list', [])
            fallback_chart_segments = []
            
            # Map pace names to zone numbers (0-6)
            # Handle various formats: "Recovery", "Easy", "Moderate", "Challenging", "Hard", "Very Hard", "Max"
            pace_name_to_zone = {
                'recovery': 0, 
                'easy': 1, 
                'moderate': 2, 
                'challenging': 3,
                'hard': 4, 
                'very hard': 5, 
                'veryhard': 5,
                'very_hard': 5,
                'max': 6,
                'maximum': 6,
                'drills': 1,  # Map drills to Easy pace (not a measured pace target)
                'drill': 1
            }
            
            for seg in segment_list:
                subsegments = seg.get('subsegments_v2', [])
                section_start = seg.get('start_time_offset', 0)
                
                for subseg in subsegments:
                    # NOTE: subseg 'offset' is already absolute from class start, not relative to section
                    subseg_offset = subseg.get('offset', 0)  # Absolute offset from class start
                    subseg_length = subseg.get('length', 0)
                    display_name = subseg.get('display_name', '')
                    
                    if subseg_length > 0 and display_name:
                        # Calculate absolute start/end times
                        # offset is already absolute, so use it directly
                        abs_start = subseg_offset
                        abs_end = abs_start + subseg_length
                        
                        # Skip segments that start beyond the class duration
                        if abs_start >= total_duration:
                            continue
                        
                        # Clamp end time to class duration
                        abs_end = min(abs_end, total_duration)
                        subseg_length = abs_end - abs_start
                        
                        if subseg_length <= 0:
                            continue
                        
                        # Extract pace level from display_name (e.g., "Recovery", "Easy", "Moderate", etc.)
                        # Try exact match first, then substring match (longest phrases first to avoid partial matches)
                        pace_level = 2  # Default to Moderate
                        display_lower = display_name.lower().strip()
                        
                        # Try exact match first (most reliable)
                        if display_lower in pace_name_to_zone:
                            pace_level = pace_name_to_zone[display_lower]
                        else:
                            # Try substring match (handle cases like "Moderate Pace" or "Easy Run")
                            # Sort by length descending to match longer phrases first (e.g., "very hard" before "hard")
                            sorted_pace_names = sorted(pace_name_to_zone.items(), key=lambda x: len(x[0]), reverse=True)
                            for pace_name, zone_num in sorted_pace_names:
                                # Check if pace name is at the start of display_name or as a whole word
                                if display_lower.startswith(pace_name) or \
                                   f' {pace_name} ' in f' {display_lower} ' or \
                                   display_lower.endswith(f' {pace_name}'):
                                    pace_level = zone_num
                                    break
                        
                        fallback_chart_segments.append({
                            "duration": subseg_length,
                            "zone": pace_level,
                            "pace_level": pace_level,
                            "start": abs_start,
                            "end": abs_end,
                        })
            
            if fallback_chart_segments:
                # Sort segments by start time to ensure proper order
                fallback_chart_segments.sort(key=lambda x: x['start'])
                
                # Calculate actual duration from segments (use last segment's end time)
                actual_duration = total_duration
                if fallback_chart_segments:
                    last_segment_end = max(seg.get('end', 0) for seg in fallback_chart_segments)
                    # Use last segment end time, but don't exceed ride duration
                    # If segments only go to 23:10 but ride is 30:00, use 23:10 (actual class plan)
                    actual_duration = min(last_segment_end, total_duration)
                
                pace_chart = {
                    'chart_data': {
                        'type': 'pace_target',
                        'segments': fallback_chart_segments,
                        'zones': chart_zones,
                        'total_duration': actual_duration,  # Actual duration from segments
                    }
                }
        
        # Final fallback: use get_pace_segments if all else fails
        if not pace_chart:
            # Determine activity type for pace zone targets
            activity_type = 'running'
            if user_profile and ride.fitness_discipline in ['running', 'run', 'walking', 'walk']:
                activity_type = 'running' if ride.fitness_discipline in ['running', 'run'] else 'walking'
            pace_zones = user_profile.get_pace_zone_targets(activity_type=activity_type) if user_profile else None
            segments = ride.get_pace_segments(user_pace_zones=pace_zones)
            target_metrics = {
                'type': 'pace',
                'segments': segments,
                'pace_zones': pace_zones
            }
            
            # Build pace chart data for interactive visualization
            # Use default pace zones if user doesn't have them set (for visualization)
            if segments:
                # Default pace zones (Level 5 - moderate pace) if user doesn't have pace_target_level
                default_pace_zones = {
                    'recovery': 10.0,      # 10:00/mile
                    'easy': 9.0,           # 9:00/mile
                    'moderate': 8.5,        # 8:30/mile
                    'challenging': 8.0,     # 8:00/mile
                    'hard': 7.5,           # 7:30/mile
                    'very_hard': 7.0,      # 7:00/mile
                    'max': 6.5             # 6:30/mile
                }
                effective_pace_zones = pace_zones if pace_zones else default_pace_zones
                
                # Build chart_data structure matching reference template (fallback method)
                # Segments with zone/pace_level (0-6) and duration
                # Note: get_pace_segments returns zones 1-7, but chart expects 0-6
                # Use segments as-is from Peloton API (they already include full class duration)
                chart_segments = []
                for i, segment in enumerate(segments):
                    zone_num = segment.get('zone', 1)  # Pace intensity from get_pace_segments (1-7)
                    zone_name = segment.get('zone_name', 'recovery')
                    start = segment.get('start', 0)
                    end = segment.get('end', 0)
                    
                    # If start == end (point-in-time segment), use next segment's start as end
                    if start == end and i < len(segments) - 1:
                        next_segment = segments[i + 1]
                        end = next_segment.get('start', start + 60)  # Default to 60 seconds if no next segment
                    elif start == end:
                        # Last segment with start==end, extend to class duration
                        end = total_duration
                    
                    # Ensure end doesn't exceed class duration
                    end = min(end, total_duration)
                    
                    # For the last segment, ensure it extends to exactly the class duration
                    if i == len(segments) - 1:
                        end = total_duration
                    
                    duration = end - start
                    
                    # Skip segments with zero or negative duration
                    if duration <= 0:
                        continue
                    
                    # Convert zone from 1-7 to 0-6 for chart (1->0, 2->1, ..., 7->6)
                    chart_zone = zone_num - 1 if zone_num > 0 else 0
                    chart_zone = max(0, min(6, chart_zone))  # Clamp to 0-6
                    
                    chart_segments.append({
                        'zone': chart_zone,  # 0-6 for chart
                        'pace_level': chart_zone,  # Same as zone for pace target
                        'duration': duration,
                        'start': start,
                        'end': end,
                        'zone_name': zone_name,
                    })
                
                # Build zones array for chart (0-6 pace levels)
                chart_zones = []
                pace_labels = ["Recovery", "Easy", "Moderate", "Challenging", "Hard", "Very Hard", "Max"]
                pace_colors = ["#6f42c1", "#4c6ef5", "#228be6", "#0ca678", "#ff922b", "#f76707", "#fa5252"]
                
                for i in range(7):
                    chart_zones.append({
                        'name': pace_labels[i],
                        'label': pace_labels[i],
                        'color': pace_colors[i],
                    })
                
                total_duration = ride.duration_seconds
                # Use exact class duration (no offset)
                pace_chart = {
                    'chart_data': {
                        'type': 'pace_target',
                        'segments': chart_segments,
                        'zones': chart_zones,
                        'total_duration': total_duration,  # Exact class duration
                    }
                }
        
        # Calculate target line data for visualization (matching power zone approach)
        if chart_segments and len(chart_segments) > 0:
            # Generate timestamps array for target line (every 5 seconds, matching power zone)
            timestamps = list(range(0, total_duration + 1, 5))
            
            # Calculate target line from segments
            target_line_data = _calculate_pace_target_line_from_segments(
                chart_segments,
                timestamps
            )
        # Set target_metrics for backward compatibility
        if pace_chart:
            # Still create target_metrics structure for other parts of the template
            # Determine activity type for pace zone targets
            activity_type = 'running'
            if user_profile and ride.fitness_discipline in ['running', 'run', 'walking', 'walk']:
                activity_type = 'running' if ride.fitness_discipline in ['running', 'run'] else 'walking'
            pace_zones = user_profile.get_pace_zone_targets(activity_type=activity_type) if user_profile else None
            segments = ride.get_pace_segments(user_pace_zones=pace_zones) if hasattr(ride, 'get_pace_segments') else []
            target_metrics = {
                'type': 'pace',
                'segments': segments,
                'pace_zones': pace_zones
            }
        else:
            target_metrics = {
                'type': 'pace',
                'segments': [],
                'pace_zones': None
            }
        
        # Set target_metrics for backward compatibility (if not already set)
        if 'target_metrics' not in locals() or not target_metrics:
            if pace_chart:
                # Still create target_metrics structure for other parts of the template
                # Determine activity type for pace zone targets
                activity_type = 'running'
                if user_profile and ride.fitness_discipline in ['running', 'run', 'walking', 'walk']:
                    activity_type = 'running' if ride.fitness_discipline in ['running', 'run'] else 'walking'
                pace_zones = user_profile.get_pace_zone_targets(activity_type=activity_type) if user_profile else None
                segments = ride.get_pace_segments(user_pace_zones=pace_zones) if hasattr(ride, 'get_pace_segments') else []
                target_metrics = {
                    'type': 'pace',
                    'segments': segments,
                    'pace_zones': pace_zones
                }
            else:
                target_metrics = {
                    'type': 'pace',
                    'segments': [],
                    'pace_zones': None
                }
        
        # Pace Target class - get user's pace level for pace calculations (matching FTP pattern)
        # (Class library override is client-side only; server provides defaults + full ranges)
        activity_type = 'running' if ride.fitness_discipline in ['running', 'run'] else 'walking'
        user_pace_level = None
        user_pace_bands = None  # Pace bands data for JavaScript
        pace_ranges_by_level = None  # {level: {zone_name: {min_mph, max_mph, middle_mph, min_pace, max_pace}}}
        pace_ranges = None  # Active level's ranges (same shape as above)
        pace_zones_from_level = None  # Legacy compatibility (seconds-per-mile-ish ints)
        
        if user_profile and ride.fitness_discipline in ['running', 'run', 'walking', 'walk']:
            # Get the latest active pace target from user's profile (matching get_current_ftp pattern)
            user_pace_level = user_profile.get_current_pace(activity_type=activity_type)
            
            # If no active PaceEntry, try to get the latest PaceEntry regardless of is_active status
            if user_pace_level is None:
                from accounts.models import PaceEntry
                latest_pace_entry = PaceEntry.objects.filter(
                    user=request.user,
                    activity_type=activity_type
                ).order_by('-recorded_date', '-created_at').first()
                if latest_pace_entry:
                    user_pace_level = latest_pace_entry.level
            
            # Fallback to pace_target_level if no PaceEntry exists at all
            if user_pace_level is None:
                if user_profile and user_profile.pace_target_level is not None:
                    user_pace_level = user_profile.pace_target_level
                else:
                    user_pace_level = 5  # Default to level 5

            # Build full pace range data (mph) for the active level and all levels (for client-side override)
            default_data = DEFAULT_RUNNING_PACE_LEVELS if activity_type == 'running' else DEFAULT_WALKING_PACE_LEVELS
            if default_data:
                pace_ranges_by_level = {}
                for lvl, lvl_data in default_data.items():
                    if not isinstance(lvl_data, dict):
                        continue
                    lvl_ranges = {}
                    lvl_pace_zones = {}
                    for zone_name, (min_mph, max_mph, min_pace, max_pace, _desc) in lvl_data.items():
                        middle_mph = (min_mph + max_mph) / 2
                        lvl_ranges[zone_name] = {
                            'min_mph': min_mph,
                            'max_mph': max_mph,
                            'middle_mph': middle_mph,
                            'min_pace': min_pace,
                            'max_pace': max_pace,
                        }
                        # Keep "pace_zones" compatibility (older code expects ints)
                        try:
                            lvl_pace_zones[zone_name] = int(float(min_pace) * 60)
                        except Exception:
                            pass
                    pace_ranges_by_level[int(lvl)] = lvl_ranges

                if user_pace_level in pace_ranges_by_level:
                    pace_ranges = pace_ranges_by_level.get(int(user_pace_level))
                    # Also provide "pace_zones" for this level if template logic wants it
                    pace_zones_from_level = {}
                    for zone_name, r in (pace_ranges or {}).items():
                        try:
                            pace_zones_from_level[zone_name] = int(float(r.get('min_pace')) * 60)
                        except Exception:
                            pass
            
            # Get the PaceLevel object with bands for this level (similar to how FTP is used for power zones)
            if user_pace_level:
                from accounts.models import PaceLevel
                user_pace_level_obj = PaceLevel.objects.filter(
                    user=request.user,
                    activity_type=activity_type,
                    level=user_pace_level
                ).order_by('-recorded_date').first()
                
                # If no PaceLevel found, use defaults
                if not user_pace_level_obj:
                    from datetime import date
                    from decimal import Decimal
                    
                    # Define DefaultPaceLevel class locally (same as in accounts/views.py)
                    class DefaultPaceLevel:
                        def __init__(self, level, default_data):
                            self.level = level
                            self.recorded_date = date.today()
                            self._default_data = default_data
                        
                        @property
                        def bands(self):
                            class DefaultBands:
                                def __init__(self, default_data):
                                    self._default_data = default_data
                                
                                def all(self):
                                    class DefaultBand:
                                        def __init__(self, zone, data):
                                            self.zone = zone
                                            self.min_mph = Decimal(str(data[0]))
                                            self.max_mph = Decimal(str(data[1]))
                                            self.min_pace = Decimal(str(data[2]))
                                            self.max_pace = Decimal(str(data[3]))
                                            self.description = data[4]
                                    
                                    return [DefaultBand(zone, data) for zone, data in self._default_data.items()]
                            
                            return DefaultBands(self._default_data)
                    
                    default_data = DEFAULT_RUNNING_PACE_LEVELS if activity_type == 'running' else DEFAULT_WALKING_PACE_LEVELS
                    if user_pace_level in default_data:
                        user_pace_level_obj = DefaultPaceLevel(user_pace_level, default_data[user_pace_level])
                
                # Extract bands data for JavaScript
                if user_pace_level_obj:
                    bands_list = []
                    # Use get_bands() for database PaceLevel objects, or bands attribute for DefaultPaceLevel
                    bands_data = user_pace_level_obj.get_bands() if hasattr(user_pace_level_obj, 'get_bands') else user_pace_level_obj.bands
                    # If bands_data is DefaultBands, use .all() to get iterable
                    if hasattr(bands_data, 'all'):
                        bands_iter = bands_data.all()
                    else:
                        bands_iter = bands_data
                    for band in bands_iter:
                        # Handle both dict (from get_bands) and object (from DefaultPaceLevel)
                        if isinstance(band, dict):
                            bands_list.append({
                                'zone': band['zone'],
                                'min_mph': float(band['min_mph']),
                                'max_mph': float(band['max_mph']),
                                'min_pace': float(band['min_pace']),
                                'max_pace': float(band['max_pace']),
                            })
                        else:
                            bands_list.append({
                                'zone': band.zone,
                                'min_mph': float(band.min_mph),
                                'max_mph': float(band.max_mph),
                                'min_pace': float(band.min_pace),
                                'max_pace': float(band.max_pace),
                            })
                    # Sort by zone order (recovery, easy, moderate, etc.)
                    zone_order = ['recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max', 'brisk', 'power']
                    bands_list.sort(key=lambda x: zone_order.index(x['zone']) if x['zone'] in zone_order else 999)
                    user_pace_bands = bands_list
        else:
            # Fallback if no user profile or unknown activity type
            if user_profile and user_profile.pace_target_level is not None:
                user_pace_level = user_profile.pace_target_level
            else:
                user_pace_level = 5

            # Provide defaults for chart rendering / client-side override even without a user profile
            default_data = DEFAULT_RUNNING_PACE_LEVELS if activity_type == 'running' else DEFAULT_WALKING_PACE_LEVELS
            if default_data:
                pace_ranges_by_level = {}
                for lvl, lvl_data in default_data.items():
                    if not isinstance(lvl_data, dict):
                        continue
                    lvl_ranges = {}
                    for zone_name, (min_mph, max_mph, min_pace, max_pace, _desc) in lvl_data.items():
                        middle_mph = (min_mph + max_mph) / 2
                        lvl_ranges[zone_name] = {
                            'min_mph': min_mph,
                            'max_mph': max_mph,
                            'middle_mph': middle_mph,
                            'min_pace': min_pace,
                            'max_pace': max_pace,
                        }
                    pace_ranges_by_level[int(lvl)] = lvl_ranges
                pace_ranges = pace_ranges_by_level.get(int(user_pace_level))

        # Ensure target_metrics carries mph pace range data (workout-parity) for the chart
        try:
            if target_metrics and isinstance(target_metrics, dict) and target_metrics.get('type') == 'pace':
                target_metrics['pace_level'] = user_pace_level
                if pace_zones_from_level is not None:
                    # Only set if we successfully computed (don't clobber existing meaningful values)
                    target_metrics['pace_zones'] = target_metrics.get('pace_zones') or pace_zones_from_level
                target_metrics['pace_ranges'] = pace_ranges
                target_metrics['pace_ranges_by_level'] = pace_ranges_by_level
        except Exception:
            pass
        
        # Calculate time in zones for running (L0-L6 format matching reference template)
        time_in_zones = {}
        if pace_chart and pace_chart.get('chart_data'):
            chart_data = pace_chart.get('chart_data', {})
            segments = chart_data.get('segments', [])
            total_duration = chart_data.get('total_duration', ride.duration_seconds)
            
            # Initialize time_in_zones with L0-L6 keys
            for level in range(7):
                time_in_zones[f'L{level}'] = 0
            
            # Calculate time in each pace level (0-6)
            for segment in segments:
                zone = segment.get('zone', 0)  # 0-6 pace level
                duration = segment.get('duration', 0)
                if 0 <= zone <= 6:
                    time_in_zones[f'L{zone}'] = time_in_zones.get(f'L{zone}', 0) + duration
            
            # Format times as MM:SS
            for level in range(7):
                seconds = time_in_zones.get(f'L{level}', 0)
                minutes = seconds // 60
                secs = seconds % 60
                time_in_zones[f'L{level}'] = f"{minutes}:{secs:02d}"
        else:
            # Default empty times
            for level in range(7):
                time_in_zones[f'L{level}'] = "0:00"
        
        # Calculate zone distribution for running using chart_data (Time in Targets)
        # Use the same data structure as the chart for consistency
        if pace_chart and pace_chart.get('chart_data'):
            chart_data = pace_chart.get('chart_data', {})
            segments = chart_data.get('segments', [])
            total_duration = chart_data.get('total_duration', ride.duration_seconds)
            
            # Map zone numbers (0-6) to zone names
            zone_name_map = {
                0: 'recovery',
                1: 'easy',
                2: 'moderate',
                3: 'challenging',
                4: 'hard',
                5: 'very_hard',
                6: 'max'
            }
            
            # Display names for zones
            zone_display_map = {
                0: 'Recovery',
                1: 'Easy',
                2: 'Moderate',
                3: 'Challenging',
                4: 'Hard',
                5: 'Very Hard',
                6: 'Max'
            }
            
            # Calculate time in each zone
            zone_times = {}
            for segment in segments:
                zone = segment.get('zone', 0)  # 0-6 pace level
                duration = segment.get('duration', 0)
                if 0 <= zone <= 6:
                    zone_name = zone_name_map.get(zone, 'recovery')
                    zone_times[zone_name] = zone_times.get(zone_name, 0) + duration
            
            # Order zones from highest to lowest intensity (for display)
            zone_order = ['max', 'very_hard', 'hard', 'challenging', 'moderate', 'easy', 'recovery']
            for zone_name in zone_order:
                time_sec = zone_times.get(zone_name, 0)
                if time_sec > 0:
                    minutes = time_sec // 60
                    seconds = time_sec % 60
                    percentage = (time_sec / total_duration * 100) if total_duration > 0 else 0
                    # Find the zone number for display
                    zone_num = [k for k, v in zone_name_map.items() if v == zone_name][0] if zone_name in zone_name_map.values() else 0
                    zone_distribution.append({
                        'zone': zone_name,
                        'zone_display': zone_display_map.get(zone_num, zone_name.replace('_', ' ').title()),
                        'time_sec': time_sec,
                        'time_str': f"{minutes:02d}:{seconds:02d}",
                        'percentage': int(percentage)
                    })
        else:
            # Fallback: use get_pace_segments if chart_data not available
            intensity_zones = ['recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max']
            zone_times = {}
            # Determine activity type for pace zone targets
            activity_type = 'running'
            if user_profile and ride.fitness_discipline in ['running', 'run', 'walking', 'walk']:
                activity_type = 'running' if ride.fitness_discipline in ['running', 'run'] else 'walking'
            pace_zones = user_profile.get_pace_zone_targets(activity_type=activity_type) if user_profile else None
            segments = ride.get_pace_segments(user_pace_zones=pace_zones) if hasattr(ride, 'get_pace_segments') else []
            if segments:
                for segment in segments:
                    # Use zone_name if available, otherwise map from zone number
                    zone_name = segment.get('zone_name', '')
                    if not zone_name:
                        zone_num = segment.get('zone', 1)
                        zone_map = {1: 'recovery', 2: 'easy', 3: 'moderate', 4: 'challenging', 
                                   5: 'hard', 6: 'very_hard', 7: 'max'}
                        zone_name = zone_map.get(zone_num, 'moderate')
                    duration = segment.get('end', 0) - segment.get('start', 0)
                    if zone_name in intensity_zones:
                        zone_times[zone_name] = zone_times.get(zone_name, 0) + duration
            
            total_duration = ride.duration_seconds
            # Order zones from highest to lowest intensity (for display)
            zone_order = ['max', 'very_hard', 'hard', 'challenging', 'moderate', 'easy', 'recovery']
            zone_display_map = {
                'recovery': 'Recovery',
                'easy': 'Easy',
                'moderate': 'Moderate',
                'challenging': 'Challenging',
                'hard': 'Hard',
                'very_hard': 'Very Hard',
                'max': 'Max'
            }
            for zone_name in zone_order:
                time_sec = zone_times.get(zone_name, 0)
                if time_sec > 0:
                    minutes = time_sec // 60
                    seconds = time_sec % 60
                    percentage = (time_sec / total_duration * 100) if total_duration > 0 else 0
                    zone_distribution.append({
                        'zone': zone_name,
                        'zone_display': zone_display_map.get(zone_name, zone_name.replace('_', ' ').title()),
                        'time_sec': time_sec,
                        'time_str': f"{minutes:02d}:{seconds:02d}",
                        'percentage': int(percentage)
                    })
    else:
        # Standard cycling class - cadence/resistance ranges
        segments = ride.get_cadence_resistance_segments()
        target_metrics = {
            'type': 'cadence_resistance',
            'segments': segments
        }
    
    # Organize class segments into Warm Up, Main, and Cool Down sections
    # Use segments_data (segment_list) if available, otherwise fall back to target_metrics_data
    class_sections = {}
    
    # Map icon_name to section key
    icon_to_section = {
        'warmup': 'warm_up',
        'warm_up': 'warm_up',
        'cycling': 'main',
        'running': 'main',
        'walking': 'main',
        'rowing': 'main',
        'cooldown': 'cool_down',
        'cool_down': 'cool_down',
    }
    
    # Map fitness discipline to appropriate icons and names
    discipline_icons = {
        'running': '🏃',
        'walking': '🚶',
        'cycling': '🚴',
        'rowing': '🚣',
    }
    main_icon = discipline_icons.get(ride.fitness_discipline, '🏃')
    main_name = ride.fitness_discipline_display_name or ride.fitness_discipline.title() if ride.fitness_discipline else 'Main Set'
    
    # Initialize sections
    section_templates = {
        'warm_up': {'name': 'Warm Up', 'icon': '🔥', 'description': 'Gradually increase your effort to prepare for the main class.'},
        'main': {'name': main_name, 'icon': main_icon, 'description': f"Main {ride.fitness_discipline_display_name.lower() if ride.fitness_discipline_display_name else 'class'} segment."},
        'cool_down': {'name': 'Cool Down', 'icon': '❄️', 'description': 'Gradually decrease your effort to recover.'}
    }
    
    # Try to use segments_data first (more accurate structure)
    if ride.segments_data and ride.segments_data.get('segment_list'):
        segment_list = ride.segments_data.get('segment_list', [])
        
        for seg in segment_list:
            icon_name = seg.get('icon_name', '').lower()
            section_key = icon_to_section.get(icon_name)
            
            if not section_key:
                # Default to main if we can't determine
                section_key = 'main'
            
            # Initialize section if not exists
            if section_key not in class_sections:
                class_sections[section_key] = {
                    'name': section_templates[section_key]['name'],
                    'icon': section_templates[section_key]['icon'],
                    'description': section_templates[section_key]['description'],
                    'segments': [],
                    'duration': 0
                }
            
            # Get subsegments from subsegments_v2
            subsegments = seg.get('subsegments_v2', [])
            section_start = seg.get('start_time_offset', 0)
            
            for subseg in subsegments:
                # NOTE: subseg 'offset' is already absolute from class start, not relative to section
                subseg_offset = subseg.get('offset', 0)  # Absolute offset from class start
                subseg_length = subseg.get('length', 0)
                display_name = subseg.get('display_name', '')
                
                if subseg_length > 0 and display_name:
                    # Calculate absolute start/end times
                    # offset is already absolute, so use it directly
                    abs_start = subseg_offset
                    abs_end = abs_start + subseg_length
                    
                    # Skip segments that start at or beyond the class duration
                    total_duration = ride.duration_seconds
                    if abs_start >= total_duration:
                        continue
                    
                    # Clamp end time to class duration
                    abs_end = min(abs_end, total_duration)
                    subseg_length = abs_end - abs_start
                    
                    if subseg_length <= 0:
                        continue
                    
                    class_sections[section_key]['segments'].append({
                        'name': display_name,
                        'start': abs_start,
                        'end': abs_end,
                        'duration': subseg_length,
                        'duration_str': f"{subseg_length // 60}:{(subseg_length % 60):02d}"
                    })
                    class_sections[section_key]['duration'] += subseg_length
    
    # Fallback: Use target_metrics_data if segments_data not available
    if not class_sections and ride.target_metrics_data:
        # Initialize sections
        for key, template in section_templates.items():
            class_sections[key] = {
                'name': template['name'],
                'icon': template['icon'],
                'description': template['description'],
                'segments': [],
                'duration': 0
            }
        
        target_metrics_list = ride.target_metrics_data.get('target_metrics', [])
        total_duration = ride.duration_seconds
        
        if total_duration > 0 and target_metrics_list:
            warm_up_cutoff = total_duration * 0.15
            cool_down_start = total_duration * 0.90
            
            # Get segments based on class type
            if ride.fitness_discipline in ['running', 'walking']:
                # Determine activity type for pace zone targets
                activity_type = 'running' if ride.fitness_discipline in ['running', 'run'] else 'walking'
                pace_zones = user_profile.get_pace_zone_targets(activity_type=activity_type) if hasattr(user_profile, 'get_pace_zone_targets') and user_profile else None
                pace_segs = ride.get_pace_segments(user_pace_zones=pace_zones)
                # Map zone numbers (1-7) and zone names to display names
                pace_name_map = {
                    'recovery': 'Recovery',
                    'easy': 'Easy',
                    'moderate': 'Moderate',
                    'challenging': 'Challenging',
                    'hard': 'Hard',
                    'very_hard': 'Very Hard',
                    'max': 'Max',
                    'brisk': 'Brisk',
                    'power': 'Power',
                    # Also map zone numbers for backward compatibility
                    '1': 'Recovery',
                    '2': 'Easy',
                    '3': 'Moderate',
                    '4': 'Challenging',
                    '5': 'Hard',
                    '6': 'Very Hard',
                    '7': 'Max',
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
                    
                    # Use zone_name if available, otherwise map from zone number
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
                    
            elif ride.is_power_zone_class or any(s.get('segment_type', '').lower() == 'power_zone' for s in target_metrics_list):
                # Check if this is a power zone class (by flag or by segment types)
                pz_segs = ride.get_power_zone_segments(user_ftp=user_profile.get_current_ftp() if hasattr(user_profile, 'get_current_ftp') else None)
                
                # If get_power_zone_segments returns empty but we have power_zone segments, extract directly
                if not pz_segs and any(s.get('segment_type', '').lower() == 'power_zone' for s in target_metrics_list):
                    for segment in target_metrics_list:
                        if segment.get('segment_type', '').lower() == 'power_zone':
                            offsets = segment.get('offsets', {})
                            start = offsets.get('start', 0)
                            end = offsets.get('end', 0)
                            duration = end - start
                            
                            # Extract zone number from metrics
                            zone_num = None
                            for metric in segment.get('metrics', []):
                                if metric.get('name') == 'power_zone':
                                    zone_lower = metric.get('lower')
                                    zone_upper = metric.get('upper')
                                    zone_num = zone_lower if zone_lower == zone_upper else zone_lower
                                    break
                            
                            if duration > 0 and zone_num:
                                if start < warm_up_cutoff:
                                    section_key = 'warm_up'
                                elif start >= cool_down_start:
                                    section_key = 'cool_down'
                                else:
                                    section_key = 'main'
                                
                                class_sections[section_key]['segments'].append({
                                    'name': f"Zone {zone_num}",
                                    'start': start,
                                    'end': end,
                                    'duration': duration,
                                    'duration_str': f"{duration // 60}:{(duration % 60):02d}",
                                    'zone': zone_num
                                })
                                class_sections[section_key]['duration'] += duration
                else:
                    # Use the method result
                    for pz_seg in pz_segs:
                        seg_start = pz_seg['start']
                        seg_end = pz_seg['end']
                        seg_duration = seg_end - seg_start
                        zone_num = pz_seg.get('zone')
                        
                        if seg_start < warm_up_cutoff:
                            section_key = 'warm_up'
                        elif seg_start >= cool_down_start:
                            section_key = 'cool_down'
                        else:
                            section_key = 'main'
                        
                        class_sections[section_key]['segments'].append({
                            'name': f"Zone {zone_num}",
                            'start': seg_start,
                            'end': seg_end,
                            'duration': seg_duration,
                            'duration_str': f"{seg_duration // 60}:{(seg_duration % 60):02d}",
                            'zone': zone_num
                        })
                        class_sections[section_key]['duration'] += seg_duration
            else:
                # For other classes (non-PZ cycling, rowing, etc.), use target_metrics segments
                # Group segments by their segment_type to determine sections
                for segment in target_metrics_list:
                    segment_type = segment.get('segment_type', '').lower()
                    offsets = segment.get('offsets', {})
                    start = offsets.get('start', 0)
                    end = offsets.get('end', 0)
                    duration = end - start
                    
                    if duration > 0:
                        # Determine section based on segment_type or timing
                        if segment_type in ['warm_up', 'warmup']:
                            section_key = 'warm_up'
                        elif segment_type in ['cooldown', 'cool_down']:
                            section_key = 'cool_down'
                        elif start < warm_up_cutoff:
                            section_key = 'warm_up'
                        elif start >= cool_down_start:
                            section_key = 'cool_down'
                        else:
                            section_key = 'main'
                        
                        # Try to get a meaningful name from metrics
                        segment_name = segment_type.replace('_', ' ').title() if segment_type else 'Segment'
                        metrics = segment.get('metrics', [])
                        
                        # For cadence/resistance classes, try to extract meaningful info
                        if metrics:
                            metric_names = [m.get('name', '') for m in metrics]
                            if 'cadence' in str(metric_names).lower():
                                segment_name = 'Cadence Segment'
                            elif 'resistance' in str(metric_names).lower():
                                segment_name = 'Resistance Segment'
                        
                        class_sections[section_key]['segments'].append({
                            'name': segment_name,
                            'start': start,
                            'end': end,
                            'duration': duration,
                            'duration_str': f"{duration // 60}:{(duration % 60):02d}"
                        })
                        class_sections[section_key]['duration'] += duration
    
    # Filter out empty sections and sort segments within each section
    for section_key in list(class_sections.keys()):
        if not class_sections[section_key]['segments']:
            del class_sections[section_key]
        else:
            # Sort segments by start time
            class_sections[section_key]['segments'].sort(key=lambda x: x['start'])
    
    # Calculate TSS and IF based on zone distribution
    # This must happen after zone_distribution is populated
    tss = None
    if_value = None
    
    # Try to get from target_class_metrics first (if Peloton provides it)
    if ride.target_class_metrics:
        tss = ride.target_class_metrics.get('total_expected_output') or ride.target_class_metrics.get('tss')
        if_value = ride.target_class_metrics.get('if') or ride.target_class_metrics.get('intensity_factor')
    
    # Calculate TSS and IF from zone distribution if not available and we have zone data
    if (tss is None or if_value is None) and zone_distribution and ride.duration_seconds:
        total_duration_hours = ride.duration_seconds / 3600.0
        
        if ride.class_type == 'power_zone' or ride.is_power_zone_class:
            # Power Zone TSS/IF calculation
            user_ftp = user_profile.get_current_ftp() if user_profile else None
            if user_ftp and user_ftp > 0:
                # Calculate normalized power from time in zones
                # Use mid-point of each zone as representative power
                zone_power_percentages = metrics_calculator.ZONE_POWER_PERCENTAGES
                
                # Calculate weighted average power
                total_weighted_power = 0.0
                total_time = 0.0
                
                for zone_info in zone_distribution:
                    zone = zone_info.get('zone')
                    time_sec = zone_info.get('time_sec', 0)
                    if zone and zone in zone_power_percentages and time_sec > 0:
                        zone_power = user_ftp * zone_power_percentages[zone]
                        total_weighted_power += zone_power * time_sec
                        total_time += time_sec
                
                if total_time > 0:
                    normalized_power = total_weighted_power / total_time
                    # IF = normalized power / FTP
                    if_value = normalized_power / user_ftp
                    # TSS = (duration in hours) × IF² × 100
                    tss = total_duration_hours * (if_value ** 2) * 100
        
        elif ride.class_type == 'pace_target' or ride.fitness_discipline in ['running', 'walking', 'run']:
            # Pace Target TSS/IF calculation
            # Use threshold pace (moderate pace) as reference
            user_pace_level = user_profile.pace_target_level if user_profile else 5
            if user_pace_level:
                # Map pace zones to intensity factors relative to threshold (moderate)
                # Recovery = 0.5, Easy = 0.7, Moderate = 1.0, Challenging = 1.15, Hard = 1.3, Very Hard = 1.5, Max = 1.8
                pace_zone_intensity_factors = {
                    'recovery': 0.5,
                    'easy': 0.7,
                    'moderate': 1.0,
                    'challenging': 1.15,
                    'hard': 1.3,
                    'very_hard': 1.5,
                    'max': 1.8,
                }
                
                # Calculate weighted average intensity factor
                total_weighted_intensity = 0.0
                total_time = 0.0
                
                for zone_info in zone_distribution:
                    zone_key = zone_info.get('zone')  # This is the zone name like 'recovery', 'easy', etc.
                    time_sec = zone_info.get('time_sec', 0)
                    
                    # Handle both string zone names and zone_display
                    if isinstance(zone_key, str) and zone_key.lower() in pace_zone_intensity_factors:
                        zone_if = pace_zone_intensity_factors[zone_key.lower()]
                    elif isinstance(zone_key, int):
                        # If zone is numeric (0-6), map to zone names
                        zone_map = {0: 'recovery', 1: 'easy', 2: 'moderate', 3: 'challenging', 
                                   4: 'hard', 5: 'very_hard', 6: 'max'}
                        zone_name = zone_map.get(zone_key, 'moderate')
                        zone_if = pace_zone_intensity_factors.get(zone_name, 1.0)
                    else:
                        # Try to get from zone_display
                        zone_display = zone_info.get('zone_display', '').lower()
                        zone_if = pace_zone_intensity_factors.get(zone_display, 1.0)
                    
                    if time_sec > 0:
                        total_weighted_intensity += zone_if * time_sec
                        total_time += time_sec
                
                if total_time > 0:
                    # IF = weighted average intensity factor
                    if_value = total_weighted_intensity / total_time
                    # TSS = (duration in hours) × IF² × 100
                    tss = total_duration_hours * (if_value ** 2) * 100
    
    # Convert to JSON for template
    if target_metrics:
        target_metrics_json = mark_safe(json.dumps(target_metrics))
    
    # Get playlist if available
    playlist = None
    try:
        playlist = ride.playlist
    except:
        pass
    
    # Convert chart data to JSON for template (for both pace target and power zone)
    pace_chart_json = None
    power_zone_chart_json = None
    chart_data = None  # For reference template compatibility
    # Note: user_pace_level should already be set in the pace target block above (line 1345-1438)
    # Don't set a default here as it would overwrite the value already set
    
    # Handle pace target chart data
    if 'pace_chart' in locals() and pace_chart and pace_chart.get('chart_data'):
        # Use chart_data structure for JavaScript (matches reference template)
        chart_data_for_js = pace_chart.get('chart_data', {})
        if chart_data_for_js and chart_data_for_js.get('segments') and chart_data_for_js.get('zones'):
            pace_chart_json = mark_safe(json.dumps(chart_data_for_js))
            chart_data = chart_data_for_js  # Also pass as chart_data for reference template (matches reference template variable name)
    
    # Handle power zone chart data
    if 'power_zone_chart' in locals() and power_zone_chart and power_zone_chart.get('chart_data'):
        chart_data_for_js = power_zone_chart.get('chart_data', {})
        if chart_data_for_js and chart_data_for_js.get('segments') and chart_data_for_js.get('zones'):
            power_zone_chart_json = mark_safe(json.dumps(chart_data_for_js))
            chart_data = chart_data_for_js  # Use same variable name for consistency
    
    # Ensure user_pace_level is set (fallback, matching user_ftp pattern)
    # Only set if not already set in the pace target block above
    # Note: user_pace_level should already be set in the pace target block (line 1345-1438)
    # This is just a safety fallback in case it wasn't set (shouldn't happen, but defensive programming)
    # IMPORTANT: Use new system (PaceEntry) first, fallback to old system (pace_target_level) only if needed
    if user_pace_level is None:
        # For pace target classes, try to get current pace from PaceEntry (new system)
        if user_profile and ride.fitness_discipline in ['running', 'run', 'walking', 'walk']:
            activity_type = 'running' if ride.fitness_discipline in ['running', 'run'] else 'walking'
            # Use new system: get_current_pace() looks for active PaceEntry
            user_pace_level = user_profile.get_current_pace(activity_type=activity_type)
            
            # If no active PaceEntry, try to get the latest PaceEntry regardless of is_active status
            if user_pace_level is None:
                from accounts.models import PaceEntry
                latest_pace_entry = PaceEntry.objects.filter(
                    user=request.user,
                    activity_type=activity_type
                ).order_by('-recorded_date', '-created_at').first()
                if latest_pace_entry:
                    user_pace_level = latest_pace_entry.level
            
            # Fallback to old system: pace_target_level (deprecated but still used as fallback)
            if user_pace_level is None:
                if user_profile and user_profile.pace_target_level is not None:
                    user_pace_level = user_profile.pace_target_level
                else:
                    user_pace_level = 5
        else:
            # For non-pace classes, use old system as fallback
            if user_profile and user_profile.pace_target_level is not None:
                user_pace_level = user_profile.pace_target_level
            else:
                user_pace_level = 5
    
    # Format class date (matching reference template)
    class_date = None
    if ride.original_air_time:
        try:
            # Peloton timestamps are in milliseconds
            timestamp = ride.original_air_time
            if timestamp > 1e10:  # If timestamp is in milliseconds, convert to seconds
                timestamp = timestamp / 1000
            dt = datetime.fromtimestamp(timestamp)
            class_date = dt.strftime("%d/%m/%y @ %I:%M%p ET")
        except (ValueError, OSError, TypeError):
            # Fallback to created_at if conversion fails
            if hasattr(ride, 'created_at') and ride.created_at:
                class_date = ride.created_at.strftime("%d/%m/%y @ %I:%M%p ET")
    elif hasattr(ride, 'created_at') and ride.created_at:
        class_date = ride.created_at.strftime("%d/%m/%y @ %I:%M%p ET")
    
    # Past workouts for this class (used for Power Zone / Pace Target / Cycling comparisons)
    times_taken = 0
    workouts_page_obj = None
    qs_workouts = request.GET.copy()
    try:
        qs_workouts.pop('workouts_page')
    except Exception:
        pass
    qs_without_workouts_page = qs_workouts.urlencode()

    try:
        class_workouts_qs = (
            Workout.objects.filter(user=request.user, ride_detail=ride)
            .select_related('ride_detail', 'details')
            .order_by('-completed_date', 'id')
        )
        times_taken = class_workouts_qs.count()
        if times_taken > 0:
            paginator = Paginator(class_workouts_qs, 20)
            workouts_page_number = request.GET.get('workouts_page', 1)
            workouts_page_obj = paginator.get_page(workouts_page_number)

            # Derived fields for run/walk tables (pace/speed/IF)
            fd = (getattr(ride, 'fitness_discipline', '') or '').lower()
            is_run_walk = (ride.class_type == 'pace_target') or (fd in ['running', 'walking', 'run', 'walk'])
            if is_run_walk:
                for w in workouts_page_obj.object_list:
                    avg_speed_mph = _estimate_workout_avg_speed_mph(w)
                    w.derived_avg_speed_mph = avg_speed_mph
                    w.derived_avg_pace_str = _pace_str_from_mph(avg_speed_mph) if avg_speed_mph else None
                    w.derived_if = _estimate_workout_if_from_tss(w)
        else:
            workouts_page_obj = None
    except Exception:
        times_taken = 0
        workouts_page_obj = None

    # Generate Peloton URL (matching reference template)
    peloton_url = None
    if ride.peloton_class_url:
        peloton_url = ride.peloton_class_url
    else:
        # Generate URL based on ride ID and discipline
        base_url = "https://members.onepeloton.com/classes"
        discipline_map = {
            'cycling': 'cycling',
            'running': 'tread',
            'walking': 'tread',
            'strength': 'strength',
            'stretching': 'yoga'
        }
        discipline = discipline_map.get(ride.fitness_discipline, 'cycling')
        peloton_url = f"{base_url}/{discipline}?modal=classDetailsModal&classId={ride.peloton_ride_id}"
    
    # Pass target_line_data as Python object for json_script filter (not pre-encoded JSON)
    # The json_script filter will handle JSON encoding automatically
    # Note: target_line_data is already a Python list/dict, not a JSON string
    context = {
        'ride': ride,
        'target_metrics': target_metrics,
        'target_metrics_json': target_metrics_json,
        'target_line_data': target_line_data if target_line_data else None,  # Pass Python object, not JSON string
        'zone_distribution': zone_distribution,
        'class_segments': class_segments,
        'class_sections': class_sections,
        'spin_up_intervals': spin_up_intervals,
        'user_profile': user_profile,
        'tss': tss,
        'if_value': if_value,
        'playlist': playlist,
        'pace_chart': pace_chart if 'pace_chart' in locals() else None,
        'pace_chart_json': pace_chart_json,
        'power_zone_chart': power_zone_chart if 'power_zone_chart' in locals() else None,
        'power_zone_chart_json': power_zone_chart_json,
        'chart_data': chart_data,  # For reference template compatibility
        'user_pace_level': user_pace_level if user_pace_level is not None else (user_profile.pace_target_level if user_profile and user_profile.pace_target_level is not None else 5),
        'user_pace_bands': user_pace_bands if 'user_pace_bands' in locals() else None,
        'has_pace_target': bool(user_profile.pace_target_level) if user_profile else False,
        'time_in_zones': time_in_zones if 'time_in_zones' in locals() else {},
        'class_date': class_date,
        'peloton_url': peloton_url,
        'user_ftp': user_ftp if 'user_ftp' in locals() else (user_profile.get_current_ftp() if user_profile else None),
        'times_taken': times_taken,
        'workouts_page_obj': workouts_page_obj,
        'qs_without_workouts_page': qs_without_workouts_page,
    }
    
    return render(request, 'classes/class_detail.html', context)
