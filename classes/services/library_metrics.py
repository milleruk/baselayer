import json
from django.utils.safestring import mark_safe


def build_class_library_metrics(*, page_obj, user_profile, tss_filter, metrics_calculator):
    """
    Build per-class card metrics for class_library view.

    Returns:
        List of ride_data dicts with tss/if/zone/chart/difficulty for each ride.
    """
    rides_with_metrics = []
    for ride in page_obj:
        ride_data = {
            'ride': ride,
            'tss': None,
            'if_value': None,
            'zone_data': None,
            'chart_data': None,
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
                        zone = segment.get('zone', 0)
                        start = segment.get('start', 0)
                        # Skip warm up and cool down segments
                        if start < warm_up_cutoff or start >= cool_down_start:
                            continue
                        duration = segment.get('end', 0) - segment.get('start', 0)
                        zone_times[zone] = zone_times.get(zone, 0) + duration

                    # Calculate total time excluding warm up and cool down for percentage calculation
                    main_workout_duration = total_duration * 0.75  # 75% of class is main workout

                    # Order zones from Zone 1 to Zone 7 for proper stacking (bottom to top)
                    for zone in range(1, 8):
                        time_sec = zone_times.get(zone, 0)
                        if time_sec > 0:
                            percentage = (time_sec / main_workout_duration * 100) if main_workout_duration > 0 else 0
                            zone_distribution.append({
                                'zone': zone,
                                'percentage': percentage
                            })

                    # Calculate TSS/IF if not already set
                    if ride_data['tss'] is None or ride_data['if_value'] is None:
                        zone_power_percentages = metrics_calculator.ZONE_POWER_PERCENTAGES
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

        elif ride.class_type == 'pace_target' or ride.fitness_discipline in ['running', 'walking', 'run', 'walk']:
            activity_type = 'running'
            if ride.fitness_discipline in ['walking', 'walk']:
                activity_type = 'walking'
            elif ride.workout_type and ride.workout_type.slug in ['walking', 'walk']:
                activity_type = 'walking'
            elif 'walk' in (ride.title or '').lower():
                activity_type = 'walking'

            chart_segments = []
            zone_times = {}
            zone_name_map = {0: 'recovery', 1: 'easy', 2: 'moderate', 3: 'challenging',
                            4: 'hard', 5: 'very_hard', 6: 'max'}

            if ride.target_metrics_data and isinstance(ride.target_metrics_data, dict):
                target_metrics_list = ride.target_metrics_data.get('target_metrics', [])
                if target_metrics_list:
                    segments = ride.get_target_metrics_segments()

                    total_duration = ride.duration_seconds
                    warm_up_cutoff = total_duration * 0.15
                    cool_down_start = total_duration * 0.90

                    for segment in segments:
                        if segment.get('type') == 'pace_target':
                            start = segment.get('start', 0)
                            if start < warm_up_cutoff or start >= cool_down_start:
                                continue
                            for metric in segment.get('metrics', []):
                                if metric.get('name') == 'pace_target':
                                    zone = metric.get('lower') or metric.get('upper')
                                    if zone is not None:
                                        zone = int(zone) - 1
                                        duration = segment.get('end', 0) - segment.get('start', 0)
                                        zone_times[zone] = zone_times.get(zone, 0) + duration

                    for i, segment in enumerate(segments):
                        if segment.get('type') == 'pace_target':
                            for metric in segment.get('metrics', []):
                                if metric.get('name') == 'pace_target':
                                    zone = metric.get('lower') or metric.get('upper')
                                    if zone is not None:
                                        zone = int(zone) - 1
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

            if not chart_segments and hasattr(ride, 'get_pace_segments'):
                pace_zones = user_profile.get_pace_zone_targets(activity_type=activity_type) if user_profile else None
                pace_segments = ride.get_pace_segments(user_pace_zones=pace_zones)
                if pace_segments:
                    total_duration = ride.duration_seconds

                    for i, segment in enumerate(pace_segments):
                        zone_num = segment.get('zone', 1)
                        zone = zone_num - 1
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

                    total_duration = ride.duration_seconds
                    warm_up_cutoff = total_duration * 0.15
                    cool_down_start = total_duration * 0.90

                    for segment in pace_segments:
                        start = segment.get('start', 0)
                        if start < warm_up_cutoff or start >= cool_down_start:
                            continue
                        zone_num = segment.get('zone', 1)
                        zone = zone_num - 1
                        duration = segment.get('end', 0) - segment.get('start', 0)
                        zone_times[zone] = zone_times.get(zone, 0) + duration

            if chart_segments:
                ride_data['chart_data'] = mark_safe(json.dumps({
                    'type': 'pace_target',
                    'activity_type': activity_type,
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

            total_duration = ride.duration_seconds
            main_workout_duration = total_duration * 0.75

            if zone_times:
                zone_order = ['recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max']
                for zone_name in zone_order:
                    zone_num = [k for k, v in zone_name_map.items() if v == zone_name]
                    if zone_num:
                        time_sec = zone_times.get(zone_num[0], 0) if zone_num else 0
                        if time_sec > 0:
                            percentage = (time_sec / main_workout_duration * 100) if main_workout_duration > 0 else 0
                            zone_distribution.append({
                                'zone': zone_name,
                                'percentage': percentage
                            })

                if zone_distribution:
                    pace_zone_intensity_factors = {
                        'recovery': 0.5, 'easy': 0.7, 'moderate': 1.0,
                        'challenging': 1.15, 'hard': 1.3, 'very_hard': 1.5, 'max': 1.8
                    }
                    total_weighted_intensity = 0.0
                    total_time = 0.0
                    for zone_info in zone_distribution:
                        zone_name = zone_info.get('zone')
                        zone_num = [k for k, v in zone_name_map.items() if v == zone_name]
                        time_sec = zone_times.get(zone_num[0], 0) if zone_num else 0
                        zone_if = pace_zone_intensity_factors.get(zone_name, 1.0)
                        if time_sec > 0:
                            total_weighted_intensity += zone_if * time_sec
                            total_time += time_sec

                    if total_time > 0:
                        avg_intensity = total_weighted_intensity / total_time
                        ride_data['difficulty'] = round((avg_intensity / 1.8) * 10, 1)
                        ride_data['if_value'] = avg_intensity
                        ride_data['tss'] = (ride.duration_seconds / 3600.0) * (avg_intensity ** 2) * 100

        ride_data['zone_data'] = zone_distribution

        if tss_filter:
            try:
                tss_value = float(tss_filter)
                if ride_data['tss'] is None or ride_data['tss'] < tss_value:
                    continue
            except (ValueError, TypeError):
                pass

        rides_with_metrics.append(ride_data)

    return rides_with_metrics
