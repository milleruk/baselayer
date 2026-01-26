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

from .models import Workout, WorkoutType, Instructor, RideDetail, WorkoutDetails, Playlist
from peloton.models import PelotonConnection


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
    pace_target_type = ride_data.get('pace_target_type') or (ride_details.get('pace_target_type') if ride_details else None)
    if pace_target_type:
        return 'pace_target'
    
    # Priority 3: Check target_metrics_data for segment types
    target_metrics_data = ride_data.get('target_metrics_data') or (ride_details.get('target_metrics_data') if ride_details else {})
    if target_metrics_data:
        target_metrics = target_metrics_data.get('target_metrics', [])
        segment_types = [s.get('segment_type', '').lower() for s in target_metrics if s.get('segment_type')]
        if 'power_zone' in segment_types:
            return 'power_zone'
        if any('pace' in st for st in segment_types):
            return 'pace_target'
    
    # Priority 4: Check title keywords (case-insensitive)
    title = (ride_data.get('title') or '').lower()
    fitness_discipline = (ride_data.get('fitness_discipline') or '').lower()
    
    # Check for power zone in title first (works across disciplines)
    if 'power zone' in title or ' pz ' in title or title.startswith('pz ') or title.endswith(' pz'):
        return 'power_zone'
    
    # Cycling class types
    if fitness_discipline in ['cycling', 'ride']:
        if 'climb' in title:
            return 'climb'
        if 'interval' in title:
            return 'intervals'
        if 'progression' in title:
            return 'progression'
        if 'low impact' in title:
            return 'low_impact'
        if 'beginner' in title:
            return 'beginner'
        if 'groove' in title:
            return 'groove'
        if 'pro cyclist' in title or 'pro cyclist' in title:
            return 'pro_cyclist'
        if 'live dj' in title:
            return 'live_dj'
        if 'peloton studio original' in title:
            return 'peloton_studio_original'
        if 'warm up' in title or 'warmup' in title:
            return 'warm_up'
        if 'cool down' in title or 'cooldown' in title:
            return 'cool_down'
        if 'music' in title or 'theme' in title:
            return 'music' if 'music' in title else 'theme'
    
    # Running class types
    elif fitness_discipline in ['running', 'run']:
        if 'pace' in title or 'pace target' in title:
            return 'pace_target'
        if 'speed' in title:
            return 'speed'
        if 'endurance' in title:
            return 'endurance'
        if 'walk' in title and 'run' in title:
            return 'walk_run'
        if 'form' in title or 'drill' in title:
            return 'form_drills'
        if 'warm up' in title or 'warmup' in title:
            return 'warm_up'
        if 'cool down' in title or 'cooldown' in title:
            return 'cool_down'
        if 'beginner' in title:
            return 'beginner'
        if 'music' in title or 'theme' in title:
            return 'music' if 'music' in title else 'theme'
    
    # Walking class types
    elif fitness_discipline in ['walking', 'walk']:
        if 'pace' in title or 'pace target' in title:
            return 'pace_target'
        if 'power walk' in title:
            return 'power_walk'
        if 'hiking' in title:
            return 'hiking'
        if 'warm up' in title or 'warmup' in title:
            return 'warm_up'
        if 'cool down' in title or 'cooldown' in title:
            return 'cool_down'
        if 'music' in title or 'theme' in title:
            return 'music' if 'music' in title else 'theme'
        if 'peloton studio original' in title:
            return 'peloton_studio_original'
    
    # Strength class types
    elif fitness_discipline in ['strength', 'strength_training']:
        if 'full body' in title or 'total strength' in title:
            return 'full_body'
        if 'core' in title:
            return 'core'
        if 'upper body' in title:
            return 'upper_body'
        if 'lower body' in title or 'glutes' in title or 'legs' in title:
            return 'lower_body'
        if 'strength basics' in title or ('basics' in title and 'strength' in title):
            return 'strength_basics'
        if ('arms' in title and 'light' in title) or 'arms & light weights' in title:
            return 'arms_light_weights'
        if 'strength for sport' in title or ('sport' in title and 'strength' in title):
            return 'strength_for_sport'
        if 'resistance bands' in title or 'resistance band' in title:
            return 'resistance_bands'
        if 'adaptive' in title:
            return 'adaptive'
        if 'barre' in title:
            return 'barre'
        if 'kettlebell' in title:
            return 'kettlebells'
        if 'boxing' in title or 'bootcamp' in title:
            return 'boxing_bootcamp'
        if 'bodyweight' in title or 'body weight' in title:
            return 'bodyweight'
        if 'warm up' in title or 'warmup' in title:
            return 'warm_up'
        if 'cool down' in title or 'cooldown' in title:
            return 'cool_down'
    
    # Yoga class types
    elif fitness_discipline in ['yoga']:
        if 'focus flow' in title:
            return 'focus_flow'
        if 'slow flow' in title:
            return 'slow_flow'
        if 'sculpt flow' in title:
            return 'sculpt_flow'
        if 'yoga + pilates' in title or 'yoga pilates' in title or 'pilates' in title:
            return 'yoga_pilates'
        if 'yin yoga' in title or 'yin' in title:
            return 'yin_yoga'
        if 'yoga anywhere' in title:
            return 'yoga_anywhere'
        if 'yoga basics' in title or 'basics' in title:
            return 'yoga_basics'
        if 'family' in title or 'pre/postnatal' in title or 'prenatal' in title or 'postnatal' in title:
            return 'family_pre_postnatal'
        if 'beyond the pose' in title:
            return 'beyond_the_pose'
        if 'power' in title:
            return 'power'
        if 'restorative' in title:
            return 'restorative'
        if 'morning' in title:
            return 'morning'
        if 'flow' in title:
            return 'flow'
        if 'theme' in title:
            return 'theme'
    
    # Meditation class types
    elif fitness_discipline in ['meditation']:
        if 'daily meditation' in title:
            return 'daily_meditation'
        if 'sleep' in title:
            return 'sleep'
        if 'relaxation' in title:
            return 'relaxation'
        if 'emotions' in title:
            return 'emotions'
        if 'meditation basics' in title or 'basics' in title:
            return 'meditation_basics'
        if 'breath' in title or 'breathing' in title:
            return 'breath'
        if 'mindfulness' in title:
            return 'mindfulness'
        if 'walking meditation' in title:
            return 'walking_meditation'
        if 'morning' in title:
            return 'morning'
        if 'theme' in title:
            return 'theme'
        if 'family' in title or 'pre/postnatal' in title or 'prenatal' in title or 'postnatal' in title:
            return 'family_pre_postnatal'
    
    # Default: return None (will be stored as empty/null)
    return None


@login_required
def class_library(request):
    """Display all available classes/rides with filtering and pagination"""
    # Get all ride details - filter to only show Running/Tread, Cycling, Walking, and Rowing
    # Also filter by fitness_discipline to catch variations
    allowed_types = ['running', 'cycling', 'walking', 'rowing']
    allowed_disciplines = ['running', 'run', 'cycling', 'ride', 'walking', 'rowing', 'row']
    
    rides = RideDetail.objects.filter(
        Q(workout_type__slug__in=allowed_types) |
        Q(fitness_discipline__in=allowed_disciplines)
    ).exclude(
        class_type__in=['warm_up', 'cool_down']
    ).exclude(
        Q(title__icontains='warm up') | Q(title__icontains='warmup') |
        Q(title__icontains='cool down') | Q(title__icontains='cooldown')
    ).select_related('workout_type', 'instructor').order_by('-original_air_time')
    
    # Search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        rides = rides.filter(
            Q(title__icontains=search_query) |
            Q(instructor__name__icontains=search_query)
        )
    
    # Filter by workout type
    workout_type_filter = request.GET.get('type', '')
    if workout_type_filter and workout_type_filter in allowed_types:
        rides = rides.filter(workout_type__slug=workout_type_filter)
    
    # Filter by instructor
    instructor_filter = request.GET.get('instructor', '')
    if instructor_filter:
        rides = rides.filter(instructor_id=instructor_filter)
    
    # Filter by duration
    duration_filter = request.GET.get('duration', '')
    if duration_filter:
        try:
            duration_min = int(duration_filter)
            rides = rides.filter(
                Q(duration_seconds__gte=duration_min * 60 - 30) &
                Q(duration_seconds__lte=duration_min * 60 + 30)
            )
        except ValueError:
            pass
    
    # Filter by TSS (Training Stress Score) - filter based on calculated TSS
    tss_filter = request.GET.get('tss', '')
    
    # Ordering
    order_by = request.GET.get('order_by', '-original_air_time')
    if order_by in ['original_air_time', '-original_air_time', 'title', '-title', 'duration_seconds', '-duration_seconds']:
        rides = rides.order_by(order_by)
    else:
        rides = rides.order_by('-original_air_time')
    
    # Pagination
    paginator = Paginator(rides, 12)  # 12 rides per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Add pagination flag for template
    is_paginated = page_obj.has_other_pages()
    
    # Get filter options - only show allowed types
    workout_types = WorkoutType.objects.filter(
        Q(slug__in=allowed_types) |
        Q(ride_details__fitness_discipline__in=allowed_disciplines)
    ).distinct().order_by('name')
    
    # Get instructors from the filtered rides
    instructors = Instructor.objects.filter(
        Q(ride_details__workout_type__slug__in=allowed_types) |
        Q(ride_details__fitness_discipline__in=allowed_disciplines)
    ).distinct().order_by('name')
    
    # Get unique durations for filter - standard durations
    standard_durations = [5, 10, 15, 20, 30, 45, 60, 75, 90, 120]
    # Also get actual durations from rides
    actual_durations = RideDetail.objects.filter(
        Q(workout_type__slug__in=allowed_types) |
        Q(fitness_discipline__in=allowed_disciplines)
    ).values_list('duration_seconds', flat=True).distinct()
    
    # Convert to minutes and round to nearest standard duration
    duration_set = set(standard_durations)
    for duration_sec in actual_durations:
        if duration_sec:
            duration_min = round(duration_sec / 60)
            # Find closest standard duration
            closest = min(standard_durations, key=lambda x: abs(x - duration_min))
            duration_set.add(closest)
    
    durations = sorted(list(duration_set))
    
    # Calculate TSS/IF and zone data for each ride (for card display)
    user_profile = request.user.profile if hasattr(request.user, 'profile') else None
    rides_with_metrics = []
    for ride in page_obj:
        ride_data = {
            'ride': ride,
            'tss': None,
            'if_value': None,
            'zone_data': None,
            'chart_data': None,  # For mini chart visualization
            'difficulty': None,
        }
        
        # Try to get from target_class_metrics first
        if ride.target_class_metrics:
            ride_data['tss'] = ride.target_class_metrics.get('total_expected_output') or ride.target_class_metrics.get('tss')
            ride_data['if_value'] = ride.target_class_metrics.get('if') or ride.target_class_metrics.get('intensity_factor')
        
        # Calculate zone distribution for chart
        zone_distribution = []
        if ride.class_type == 'power_zone' or ride.is_power_zone_class:
            user_ftp = user_profile.get_current_ftp() if user_profile else None
            if user_ftp:
                segments = ride.get_power_zone_segments(user_ftp=user_ftp)
                if segments:
                    zone_times = {}
                    total_duration = ride.duration_seconds
                    warm_up_cutoff = total_duration * 0.15  # First 15% is warm up
                    cool_down_start = total_duration * 0.90  # Last 10% is cool down
                    
                    for segment in segments:
                        start = segment.get('start', 0)
                        # Skip warm up and cool down segments
                        if start < warm_up_cutoff or start >= cool_down_start:
                            continue
                        zone = segment.get('zone', 0)
                        duration = segment.get('end', 0) - segment.get('start', 0)
                        zone_times[zone] = zone_times.get(zone, 0) + duration
                    
                    # Calculate total time excluding warm up and cool down for percentage calculation
                    main_workout_duration = total_duration * 0.75  # 75% of class is main workout (excluding 15% warm up + 10% cool down)
                    
                    # Order zones from Zone 1 to Zone 7 for proper stacking (bottom to top)
                    for zone in range(1, 8):
                        time_sec = zone_times.get(zone, 0)
                        if time_sec > 0:
                            # Calculate percentage based on main workout duration (excluding warm up/cool down)
                            percentage = (time_sec / main_workout_duration * 100) if main_workout_duration > 0 else 0
                            zone_distribution.append({
                                'zone': zone,
                                'percentage': percentage
                            })
                    
                    # Calculate TSS/IF if not already set
                    if ride_data['tss'] is None or ride_data['if_value'] is None:
                        zone_power_percentages = {
                            1: 0.275, 2: 0.65, 3: 0.825, 4: 0.975,
                            5: 1.125, 6: 1.35, 7: 1.75
                        }
                        total_weighted_power = 0.0
                        total_time = 0.0
                        for zone_info in zone_distribution:
                            zone = zone_info.get('zone')
                            time_sec = zone_times.get(zone, 0)
                            if zone and zone in zone_power_percentages and time_sec > 0:
                                zone_power = user_ftp * zone_power_percentages[zone]
                                total_weighted_power += zone_power * time_sec
                                total_time += time_sec
                        
                        if total_time > 0:
                            normalized_power = total_weighted_power / total_time
                            ride_data['if_value'] = normalized_power / user_ftp
                            ride_data['tss'] = (ride.duration_seconds / 3600.0) * (ride_data['if_value'] ** 2) * 100
                    
                    # Generate chart data for mini chart (including full class with warm up and cool down)
                    if segments:
                        chart_segments = []
                        total_duration = ride.duration_seconds
                        
                        for i, segment in enumerate(segments):
                            zone_num = segment.get('zone', 1)
                            start = segment.get('start', 0)
                            end = segment.get('end', 0)
                            
                            if start == end and i < len(segments) - 1:
                                next_segment = segments[i + 1]
                                end = next_segment.get('start', start + 60)
                            elif start == end:
                                end = start + 60
                            
                            duration = end - start
                            if duration <= 0:
                                continue
                            
                            chart_zone = max(1, min(7, int(zone_num)))
                            chart_segments.append({
                                'duration': duration,
                                'zone': chart_zone,
                                'start': start,
                                'end': end,
                            })
                        
                        if chart_segments:
                            ride_data['chart_data'] = mark_safe(json.dumps({
                                'type': 'power_zone',
                                'segments': chart_segments,
                                'total_duration': ride.duration_seconds,
                                'zones': [
                                    {'name': 'Zone 1', 'color': '#9333ea'},
                                    {'name': 'Zone 2', 'color': '#3b82f6'},
                                    {'name': 'Zone 3', 'color': '#10b981'},
                                    {'name': 'Zone 4', 'color': '#eab308'},
                                    {'name': 'Zone 5', 'color': '#f97316'},
                                    {'name': 'Zone 6', 'color': '#ef4444'},
                                    {'name': 'Zone 7', 'color': '#ec4899'},
                                ]
                            }))
        
        elif ride.class_type == 'pace_target' or ride.fitness_discipline in ['running', 'walking', 'run']:
            # Always try to generate chart data for running/walking classes
            chart_segments = []
            zone_times = {}
            zone_name_map = {0: 'recovery', 1: 'easy', 2: 'moderate', 3: 'challenging', 
                            4: 'hard', 5: 'very_hard', 6: 'max'}
            
            # Try method 1: target_metrics_data
            if ride.target_metrics_data and isinstance(ride.target_metrics_data, dict):
                target_metrics_list = ride.target_metrics_data.get('target_metrics', [])
                if target_metrics_list:
                    segments = ride.get_target_metrics_segments()
                    
                    total_duration = ride.duration_seconds
                    warm_up_cutoff = total_duration * 0.15  # First 15% is warm up
                    cool_down_start = total_duration * 0.90  # Last 10% is cool down
                    
                    for segment in segments:
                        if segment.get('type') == 'pace_target':
                            start = segment.get('start', 0)
                            # Skip warm up and cool down segments
                            if start < warm_up_cutoff or start >= cool_down_start:
                                continue
                            for metric in segment.get('metrics', []):
                                if metric.get('name') == 'pace_target':
                                    zone = metric.get('lower') or metric.get('upper')
                                    if zone is not None:
                                        zone = int(zone) - 1  # Convert 1-7 to 0-6
                                        duration = segment.get('end', 0) - segment.get('start', 0)
                                        zone_times[zone] = zone_times.get(zone, 0) + duration
                    
                    # Generate chart segments from target_metrics_segments (including full class with warm up and cool down)
                    total_duration = ride.duration_seconds
                    
                    for i, segment in enumerate(segments):
                        if segment.get('type') == 'pace_target':
                            for metric in segment.get('metrics', []):
                                if metric.get('name') == 'pace_target':
                                    zone = metric.get('lower') or metric.get('upper')
                                    if zone is not None:
                                        zone = int(zone) - 1  # Convert 1-7 to 0-6
                                        start = segment.get('start', 0)
                                        end = segment.get('end', 0)
                                        
                                        if start == end and i < len(segments) - 1:
                                            next_segment = segments[i + 1] if i + 1 < len(segments) else None
                                            if next_segment:
                                                end = next_segment.get('start', start + 60)
                                        elif start == end:
                                            end = start + 60
                                        
                                        duration = end - start
                                        if duration <= 0:
                                            continue
                                        
                                        chart_segments.append({
                                            'duration': duration,
                                            'zone': zone,
                                            'start': start,
                                            'end': end,
                                        })
            
            # Method 2: Fallback to get_pace_segments if no chart data yet
            if not chart_segments and hasattr(ride, 'get_pace_segments'):
                pace_zones = user_profile.get_pace_zone_targets() if user_profile else None
                pace_segments = ride.get_pace_segments(user_pace_zones=pace_zones)
                if pace_segments:
                    total_duration = ride.duration_seconds
                    
                    for i, segment in enumerate(pace_segments):
                        zone_num = segment.get('zone', 1)  # 1-7 from get_pace_segments
                        zone = zone_num - 1  # Convert to 0-6
                        start = segment.get('start', 0)
                        end = segment.get('end', 0)
                        
                        if start == end and i < len(pace_segments) - 1:
                            next_segment = pace_segments[i + 1]
                            end = next_segment.get('start', start + 60)
                        elif start == end:
                            end = start + 60
                        
                        duration = end - start
                        if duration <= 0:
                            continue
                        
                        chart_segments.append({
                            'duration': duration,
                            'zone': zone,
                            'start': start,
                            'end': end,
                        })
                    
                    # Also populate zone_times for zone_distribution (excluding warm up and cool down)
                    total_duration = ride.duration_seconds
                    warm_up_cutoff = total_duration * 0.15  # First 15% is warm up
                    cool_down_start = total_duration * 0.90  # Last 10% is cool down
                    
                    for segment in pace_segments:
                        start = segment.get('start', 0)
                        # Skip warm up and cool down segments
                        if start < warm_up_cutoff or start >= cool_down_start:
                            continue
                        zone_num = segment.get('zone', 1)
                        zone = zone_num - 1  # Convert to 0-6
                        duration = segment.get('end', 0) - segment.get('start', 0)
                        zone_times[zone] = zone_times.get(zone, 0) + duration
            
            # Generate chart data if we have segments
            if chart_segments:
                ride_data['chart_data'] = mark_safe(json.dumps({
                    'type': 'pace_target',
                    'segments': chart_segments,
                    'total_duration': ride.duration_seconds,
                    'zones': [
                        {'name': 'Recovery', 'color': '#6f42c1'},
                        {'name': 'Easy', 'color': '#4c6ef5'},
                        {'name': 'Moderate', 'color': '#228be6'},
                        {'name': 'Challenging', 'color': '#0ca678'},
                        {'name': 'Hard', 'color': '#ff922b'},
                        {'name': 'Very Hard', 'color': '#f76707'},
                        {'name': 'Max', 'color': '#fa5252'},
                    ]
                }))
            
            # Calculate zone distribution for display
            total_duration = ride.duration_seconds
            # Calculate total time excluding warm up and cool down for percentage calculation
            main_workout_duration = total_duration * 0.75  # 75% of class is main workout (excluding 15% warm up + 10% cool down)
            
            if zone_times:
                # Order zones from recovery (0) to max (6) for proper stacking (bottom to top)
                zone_order = ['recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max']
                for zone_name in zone_order:
                    # Find zone number for this zone name
                    zone_num = [k for k, v in zone_name_map.items() if v == zone_name]
                    if zone_num:
                        time_sec = zone_times.get(zone_num[0], 0) if zone_num else 0
                        if time_sec > 0:
                            # Calculate percentage based on main workout duration (excluding warm up/cool down)
                            percentage = (time_sec / main_workout_duration * 100) if main_workout_duration > 0 else 0
                            zone_distribution.append({
                                'zone': zone_name,
                                'percentage': percentage
                            })
                
                # Calculate difficulty from intensity distribution
                if zone_distribution:
                    pace_zone_intensity_factors = {
                        'recovery': 0.5, 'easy': 0.7, 'moderate': 1.0,
                        'challenging': 1.15, 'hard': 1.3, 'very_hard': 1.5, 'max': 1.8
                    }
                    total_weighted_intensity = 0.0
                    total_time = 0.0
                    for zone_info in zone_distribution:
                        zone_name = zone_info.get('zone')
                        # Find the zone number for this zone name
                        zone_num = [k for k, v in zone_name_map.items() if v == zone_name]
                        time_sec = zone_times.get(zone_num[0], 0) if zone_num else 0
                        zone_if = pace_zone_intensity_factors.get(zone_name, 1.0)
                        if time_sec > 0:
                            total_weighted_intensity += zone_if * time_sec
                            total_time += time_sec
                    
                    if total_time > 0:
                        avg_intensity = total_weighted_intensity / total_time
                        # Convert to difficulty rating (0-10 scale)
                        ride_data['difficulty'] = round((avg_intensity / 1.8) * 10, 1)
                        
                        # Also calculate IF/TSS
                        ride_data['if_value'] = avg_intensity
                        ride_data['tss'] = (ride.duration_seconds / 3600.0) * (avg_intensity ** 2) * 100
        
        ride_data['zone_data'] = zone_distribution
        
        # Apply TSS filter if specified
        if tss_filter:
            try:
                tss_value = float(tss_filter)
                if ride_data['tss'] is None or ride_data['tss'] < tss_value:
                    continue  # Skip this ride if TSS doesn't meet filter
            except (ValueError, TypeError):
                pass
        
        rides_with_metrics.append(ride_data)
    
    context = {
        'rides_with_metrics': rides_with_metrics,
        'page_obj': page_obj,
        'is_paginated': is_paginated,
        'search_query': search_query,
        'workout_type_filter': workout_type_filter,
        'instructor_filter': instructor_filter,
        'duration_filter': duration_filter,
        'tss_filter': tss_filter,
        'workout_types': workout_types,
        'instructors': instructors,
        'durations': durations,
        'order_by': order_by,
    }
    
    return render(request, "workouts/class_library.html", context)


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
        power_zone_chart = None
        if segments:
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
            
            # Process segments to create chart segments
            chart_segments = []
            for i, segment in enumerate(segments):
                zone_num = segment.get('zone', 1)  # Power zone 1-7
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                
                # If start == end (point-in-time segment), use next segment's start as end
                if start == end and i < len(segments) - 1:
                    next_segment = segments[i + 1]
                    end = next_segment.get('start', start + 60)  # Default to 60 seconds if no next segment
                elif start == end:
                    # Last segment with start==end, use ride duration
                    end = start + 60  # Default to 60 seconds
                
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
                power_zone_chart = {
                    'chart_data': {
                        'type': 'power_zone',
                        'segments': chart_segments,
                        'zones': chart_zones,
                        'total_duration': total_duration,
                    }
                }
        
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
        # Running/Walking class - build chart data directly from target_metrics_data
        # This matches the reference implementation from pelodads
        pace_chart = None
        if ride.target_metrics_data and isinstance(ride.target_metrics_data, dict):
            target_metrics_list = ride.target_metrics_data.get('target_metrics', [])
            if target_metrics_list and isinstance(target_metrics_list, list):
                # Build chart data directly from target_metrics_data (matching reference)
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
                
                # Process target metrics to create segments
                chart_segments = []
                for metric in target_metrics_list:
                    if 'offsets' in metric and 'metrics' in metric:
                        start_time = metric['offsets']['start']
                        end_time = metric['offsets']['end']
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
                    pace_chart = {
                        'chart_data': {
                            'type': 'pace_target',
                            'segments': chart_segments,
                            'zones': chart_zones,
                            'total_duration': total_duration,
                        }
                    }
        
        # Fallback: use get_pace_segments if target_metrics_data approach didn't work
        if not pace_chart:
            pace_zones = user_profile.get_pace_zone_targets()
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
                        # Last segment with start==end, use ride duration
                        end = start + 60  # Default to 60 seconds
                    
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
                pace_chart = {
                    'chart_data': {
                        'type': 'pace_target',
                        'segments': chart_segments,
                        'zones': chart_zones,
                        'total_duration': total_duration,
                    }
                }
        
        # Set target_metrics for backward compatibility
        if pace_chart:
            # Still create target_metrics structure for other parts of the template
            pace_zones = user_profile.get_pace_zone_targets() if user_profile else None
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
                pace_zones = user_profile.get_pace_zone_targets() if user_profile else None
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
        
        # Add user pace level to context
        user_pace_level = user_profile.pace_target_level if user_profile and user_profile.pace_target_level else 5
        
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
            pace_zones = user_profile.get_pace_zone_targets() if user_profile else None
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
                subseg_offset = subseg.get('offset', 0)
                subseg_length = subseg.get('length', 0)
                display_name = subseg.get('display_name', '')
                
                if subseg_length > 0 and display_name:
                    # Calculate absolute start/end times
                    abs_start = section_start + subseg_offset
                    abs_end = abs_start + subseg_length
                    
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
                pace_segs = ride.get_pace_segments(user_pace_zones=user_profile.get_pace_zone_targets() if hasattr(user_profile, 'get_pace_zone_targets') else None)
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
                zone_power_percentages = {
                    1: 0.275,  # 0-55% FTP, use 27.5% (midpoint of 0-55%)
                    2: 0.65,   # 55-75% FTP, use 65%
                    3: 0.825,  # 75-90% FTP, use 82.5%
                    4: 0.975,  # 90-105% FTP, use 97.5%
                    5: 1.125,  # 105-120% FTP, use 112.5%
                    6: 1.35,   # 120-150% FTP, use 135%
                    7: 1.75,   # 150%+ FTP, use 175% (conservative estimate)
                }
                
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
    user_pace_level = 5  # Default
    
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
    
    if 'user_pace_level' in locals():
        user_pace_level = locals()['user_pace_level']
    elif hasattr(user_profile, 'pace_target_level') and user_profile.pace_target_level:
        user_pace_level = user_profile.pace_target_level
    
    # Format class date (matching reference template)
    class_date = None
    if ride.original_air_time:
        from datetime import datetime
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
    
    context = {
        'ride': ride,
        'target_metrics': target_metrics,
        'target_metrics_json': target_metrics_json,
        'zone_distribution': zone_distribution,
        'class_segments': class_segments,
        'class_sections': class_sections,
        'user_profile': user_profile,
        'tss': tss,
        'if_value': if_value,
        'playlist': playlist,
        'pace_chart': pace_chart if 'pace_chart' in locals() else None,
        'pace_chart_json': pace_chart_json,
        'power_zone_chart': power_zone_chart if 'power_zone_chart' in locals() else None,
        'power_zone_chart_json': power_zone_chart_json,
        'chart_data': chart_data,  # For reference template compatibility
        'user_pace_level': user_pace_level if 'user_pace_level' in locals() else (user_profile.pace_target_level if user_profile and user_profile.pace_target_level else 5),
        'has_pace_target': bool(user_profile.pace_target_level) if user_profile else False,
        'time_in_zones': time_in_zones if 'time_in_zones' in locals() else {},
        'class_date': class_date,
        'peloton_url': peloton_url,
        'user_ftp': user_ftp if 'user_ftp' in locals() else (user_profile.get_current_ftp() if user_profile else None),
    }
    
    return render(request, 'workouts/class_detail.html', context)


@login_required
def workout_history(request):
    """Display user's workout history with filtering and pagination"""
    # Get user's workouts - all class data comes from ride_detail via SQL joins
    workouts = Workout.objects.filter(user=request.user).select_related(
        'ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details'
    ).prefetch_related('performance_data')
    
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
    
    # Ordering - title ordering uses ride_detail__title via SQL join
    order_by = request.GET.get('order_by', '-completed_date')
    if order_by in ['completed_date', '-completed_date', 'recorded_date', '-recorded_date']:
        workouts = workouts.order_by(order_by)
    elif order_by in ['title', '-title']:
        # Order by ride_detail title via SQL join
        workouts = workouts.order_by('ride_detail__title' if order_by == 'title' else '-ride_detail__title')
    else:
        workouts = workouts.order_by('-completed_date')
    
    # Pagination
    paginator = Paginator(workouts, 12)  # 12 workouts per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
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
    
    context = {
        'workouts': page_obj,
        'workout_types': workout_types,
        'instructors': instructors,
        'durations': all_durations,
        'fitness_disciplines': fitness_disciplines,
        'peloton_connection': peloton_connection,
        'search_query': search_query,
        'workout_type_filter': workout_type_filter,
        'instructor_filter': instructor_filter,
        'duration_filter': duration_filter,
        'tss_filter': tss_filter,
        'order_by': order_by,
        'total_workouts': paginator.count,
        'is_paginated': is_paginated,
    }
    
    return render(request, 'workouts/history.html', context)


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
    
    # Prepare target metrics data based on class type
    target_metrics = None
    target_metrics_json = None
    if workout.ride_detail:
        ride_detail = workout.ride_detail
        
        if ride_detail.is_power_zone_class:
            # Power Zone class - get user's FTP for zone calculations
            user_ftp = user_profile.get_current_ftp()
            segments = ride_detail.get_power_zone_segments(user_ftp=user_ftp)
            zone_ranges = user_profile.get_power_zone_ranges() if user_ftp else None
            target_metrics = {
                'type': 'power_zone',
                'segments': segments,
                'zone_ranges': zone_ranges
            }
        elif ride_detail.fitness_discipline in ['running', 'walking']:
            # Running/Walking class - get user's pace zones
            pace_zones = user_profile.get_pace_zone_targets()
            segments = ride_detail.get_pace_segments(user_pace_zones=pace_zones)
            target_metrics = {
                'type': 'pace',
                'segments': segments,
                'pace_zones': pace_zones
            }
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
    
    # Get playlist if available
    playlist = None
    if workout.ride_detail:
        try:
            playlist = workout.ride_detail.playlist
        except:
            pass
    
    context = {
        'workout': workout,
        'performance_data': performance_data,
        'target_metrics': target_metrics,
        'target_metrics_json': target_metrics_json,
        'user_profile': user_profile,
        'playlist': playlist,
    }
    
    return render(request, 'workouts/detail.html', context)


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
                
                # Parse completed_date from start_time (for display - convert to user's timezone if needed)
                # For now, we'll use UTC date (can be converted in templates if needed)
                if start_time:
                    if isinstance(start_time, (int, float)):
                        # Unix timestamp - convert to UTC datetime then date
                        dt_utc = datetime.fromtimestamp(start_time, tz=UTC)
                        completed_date = dt_utc.date()
                    else:
                        try:
                            dt_str = str(start_time).replace('Z', '+00:00')
                            dt = datetime.fromisoformat(dt_str)
                            if dt.tzinfo is None:
                                dt = timezone.make_aware(dt, UTC)
                            else:
                                dt = dt.astimezone(UTC)
                            completed_date = dt.date()
                        except:
                            completed_date = timezone.now().date()
                else:
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
                                'home_peloton_id': ride_data.get('home_peloton_id', ''),
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
        
        # If AJAX request, return JSON
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
    """Return sync status for AJAX polling"""
    try:
        connection = PelotonConnection.objects.get(user=request.user)
        status = {
            'connected': True,
            'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            'workout_count': Workout.objects.filter(user=request.user).count(),
        }
    except PelotonConnection.DoesNotExist:
        status = {
            'connected': False,
            'last_sync_at': None,
            'workout_count': 0,
        }
    
    return JsonResponse(status)
