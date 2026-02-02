"""
Workout target calculation utilities for power and pace targets.

Extracted from workouts/views.py for reuse across applications.
Handles calculation of target lines from segment data for power zone and pace workouts.
"""
from typing import List, Dict, Optional, Any


def target_value_at_time(segments: List[Dict], t_seconds: int) -> Optional[Any]:
    """
    Find the segment covering time t_seconds and return its 'target' value.
    
    Args:
        segments: List of segment dicts with 'start', 'end', 'target' keys
        t_seconds: Timestamp in seconds
        
    Returns:
        Target value from matching segment or None if not found
        
    Example:
        >>> segments = [{'start': 0, 'end': 60, 'target': 100}, {'start': 60, 'end': 120, 'target': 150}]
        >>> target_value_at_time(segments, 30)
        100
    """
    if not segments or not isinstance(t_seconds, int):
        return None
    for seg in segments:
        try:
            start = int(seg.get('start', 0))
            end = int(seg.get('end', 0))
        except Exception:
            continue
        if t_seconds >= start and (end == 0 or t_seconds < end):
            return seg.get('target')
    return None


def target_value_at_time_with_shift(segments: List[Dict], t_seconds: int, shift_seconds: int = 0) -> Optional[Any]:
    """
    Return target value at time t_seconds, applying a time shift to the *segment windows*.

    A negative shift (e.g. -60) means the target segments start earlier on the chart.
    Equivalent lookup: target(t) = target_original(t - shift).
    
    Args:
        segments: List of segment dicts with 'start', 'end', 'target' keys
        t_seconds: Timestamp in seconds
        shift_seconds: Time shift to apply (negative = earlier, positive = later)
        
    Returns:
        Target value from matching segment or None if not found
        
    Example:
        >>> segments = [{'start': 60, 'end': 120, 'target': 150}]
        >>> target_value_at_time_with_shift(segments, 30, shift_seconds=-60)
        150  # Shifted segment now starts at 0
    """
    if not isinstance(t_seconds, int):
        return None
    try:
        s = int(shift_seconds or 0)
    except Exception:
        s = 0
    return target_value_at_time(segments, t_seconds - s)


def target_segment_at_time_with_shift(segments: List[Dict], t_seconds: int, shift_seconds: int = 0) -> Optional[Dict]:
    """
    Return the target segment dict at time t_seconds with optional time shift.
    
    Args:
        segments: List of segment dicts with 'start', 'end' keys
        t_seconds: Timestamp in seconds
        shift_seconds: Time shift to apply (negative = earlier, positive = later)
        
    Returns:
        Segment dict or None if not found
        
    Example:
        >>> segments = [{'start': 0, 'end': 60, 'zone': 2}]
        >>> seg = target_segment_at_time_with_shift(segments, 30)
        >>> seg['zone']
        2
    """
    if not segments or not isinstance(t_seconds, int):
        return None
    try:
        s = int(shift_seconds or 0)
    except Exception:
        s = 0
    t = t_seconds - s
    for seg in segments:
        try:
            start = int(seg.get('start', 0))
            end = int(seg.get('end', 0))
        except Exception:
            continue
        if t >= start and (end == 0 or t < end):
            return seg
    return None


def extract_spin_up_intervals(ride_detail) -> List[Dict[str, int]]:
    """
    Return list of {'start': int, 'end': int} intervals covering Spin Ups segments.
    
    Args:
        ride_detail: RideDetail object with segments_data or target_metrics_data
        
    Returns:
        List of interval dicts with 'start' and 'end' keys
        
    Example:
        >>> intervals = extract_spin_up_intervals(ride_detail)
        >>> print(intervals[0])
        {'start': 120, 'end': 180}
    """
    intervals = []
    if not ride_detail:
        return intervals

    total_duration = ride_detail.duration_seconds or 0

    # Prefer segments_data (includes display names such as "Spin Ups")
    segments_data = getattr(ride_detail, 'segments_data', None) or {}
    segment_list = segments_data.get('segment_list') if isinstance(segments_data, dict) else None
    if segment_list:
        for seg in segment_list:
            subsegments = seg.get('subsegments_v2', [])
            section_start = seg.get('start_time_offset', 0) or 0
            for subseg in subsegments:
                display_name = (subseg.get('display_name') or '').lower()
                if 'spin' not in display_name or 'up' not in display_name:
                    continue
                sub_offset = subseg.get('offset', 0) or 0
                duration = subseg.get('length', 0) or 0
                if duration <= 0:
                    continue
                start = section_start + sub_offset
                end = start + duration
                if total_duration:
                    start = max(0, min(start, total_duration))
                    end = max(start, min(end, total_duration))
                intervals.append({'start': int(start), 'end': int(end)})

    # Fallback to target_metrics_data if needed
    if not intervals and ride_detail.target_metrics_data:
        target_metrics_list = ride_detail.target_metrics_data.get('target_metrics', []) or []
        for segment in target_metrics_list:
            segment_type = (segment.get('segment_type') or '').lower()
            if 'spin' not in segment_type or 'up' not in segment_type:
                continue
            offsets = segment.get('offsets', {})
            start = offsets.get('start', 0) or 0
            end = offsets.get('end', 0) or 0
            if end > start:
                intervals.append({'start': int(max(0, start)), 'end': int(max(start, end))})

    if not intervals:
        return intervals

    # Merge overlapping intervals
    intervals.sort(key=lambda x: x['start'])
    merged = [intervals[0]]
    for current in intervals[1:]:
        last = merged[-1]
        if current['start'] <= last['end']:
            last['end'] = max(last['end'], current['end'])
        else:
            merged.append(current)
    return merged


def calculate_target_line_from_segments(
    segments: List[Dict],
    zone_ranges: Dict,
    seconds_array: List[int],
    user_ftp: Optional[float] = None,
    spin_up_intervals: Optional[List[Dict]] = None,
    zone_power_percentages: Optional[Dict[int, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate target output line from class plan segments (from ride_detail.get_power_zone_segments()).
    Uses the middle of each zone's watt range as the target.
    Shifts target line 60 seconds backwards (earlier).
    Optionally accepts spin_up_intervals to backfill gaps (Spin Ups) so the line stays continuous.
    
    Args:
        segments: List of segment dicts with 'start', 'end', 'zone' keys
        zone_ranges: Dict mapping zone number to (lower, upper) watt bounds
        seconds_array: List of timestamps to generate targets for
        user_ftp: User's FTP value
        spin_up_intervals: Optional list of spin-up interval dicts to fill gaps
        zone_power_percentages: Optional dict mapping zone to FTP percentage (default from MetricsCalculator)
        
    Returns:
        List of dicts with 'timestamp' and 'target_output' keys
        
    Example:
        >>> segments = [{'start': 0, 'end': 120, 'zone': 2}]
        >>> zone_ranges = {2: (100, 150)}
        >>> seconds = list(range(0, 120))
        >>> targets = calculate_target_line_from_segments(segments, zone_ranges, seconds)
        >>> targets[0]['target_output']
        125  # Midpoint of zone 2
    """
    if not segments or not zone_ranges or not seconds_array:
        return []
    
    # Default zone power percentages if not provided
    if zone_power_percentages is None:
        zone_power_percentages = {
            1: 0.45,    # Z1: 45% (active recovery target)
            2: 0.65,    # Z2: 65% (midpoint of 55-75%)
            3: 0.825,   # Z3: 82.5% (midpoint of 75-90%)
            4: 0.975,   # Z4: 97.5% (midpoint of 90-105%)
            5: 1.125,   # Z5: 112.5% (midpoint of 105-120%)
            6: 1.35,    # Z6: 135% (midpoint of 120-150%)
            7: 1.60,    # Z7: 160% (sprint target)
        }
    
    sample_count = len(seconds_array)
    target_series = [None] * sample_count
    max_timestamp = seconds_array[-1] if seconds_array else None
    
    # Shift target line 60 seconds backwards
    TIME_SHIFT = -60
    
    # Try to get FTP directly; fallback to zone range upper bound (Z1 upper ≈ 55% FTP)
    ftp_value = None
    try:
        if user_ftp:
            ftp_value = float(user_ftp)
    except (TypeError, ValueError):
        ftp_value = None

    zone_ranges_map = zone_ranges or {}

    if ftp_value is None and zone_ranges_map:
        zone1 = zone_ranges_map.get(1)
        if zone1 and zone1[1]:
            try:
                ftp_value = float(zone1[1]) / 0.55
            except (TypeError, ValueError, ZeroDivisionError):
                ftp_value = None

    # Helper function to calculate target watts from zone number
    def _zone_to_watts(zone_num):
        if zone_num and ftp_value and zone_num in zone_power_percentages:
            return round(ftp_value * zone_power_percentages[zone_num])

        if zone_num and zone_num in zone_ranges_map:
            lower, upper = zone_ranges_map[zone_num]
            if lower is not None and upper is not None:
                return round((lower + upper) / 2)
            elif lower is not None:
                if zone_num == 7:
                    target_pct = zone_power_percentages.get(7)
                    if target_pct and lower > 0:
                        # lower ≈ 1.50 * FTP → rescale to target_pct
                        scaling = target_pct / 1.50
                        return round(lower * scaling)
                return round(lower * 1.25)
        return None
    
    base_segments = list(segments or [])

    # Process each segment from the class plan
    for segment in base_segments:
        zone_num = segment.get('zone')
        if not zone_num:
            continue
        
        # Shift segment times 60 seconds backwards
        start_time = max(0, segment.get('start', 0) + TIME_SHIFT)
        end_time = max(0, segment.get('end', 0) + TIME_SHIFT)
        
        if end_time <= start_time:
            continue
        
        # Skip segments that start after the workout ends
        if max_timestamp is not None and start_time > max_timestamp:
            continue
        
        # Calculate target watts for this zone (middle of zone range)
        target_watts = _zone_to_watts(zone_num)
        if target_watts is None:
            continue
        
        # Map time offsets to array indices using seconds_array
        start_idx = 0
        end_idx = sample_count
        
        for i, timestamp in enumerate(seconds_array):
            if isinstance(timestamp, (int, float)) and timestamp >= start_time:
                start_idx = i
                break
        
        for i in range(len(seconds_array) - 1, -1, -1):
            timestamp = seconds_array[i]
            if isinstance(timestamp, (int, float)) and timestamp <= end_time:
                end_idx = i + 1
                break
        
        # Fill target_series for this segment
        for i in range(start_idx, min(end_idx, sample_count)):
            target_series[i] = target_watts

    # Fill any gaps (None values) using spin-up intervals (treated as Zone 1 unless specified)
    if spin_up_intervals:
        for interval in spin_up_intervals:
            if not isinstance(interval, dict):
                continue
            start_raw = interval.get('start')
            end_raw = interval.get('end')
            if start_raw is None or end_raw is None:
                continue
            try:
                start_val = int(start_raw)
                end_val = int(end_raw)
            except (TypeError, ValueError):
                continue
            if end_val <= start_val:
                continue

            # Shift interval to match chart alignment
            start_time = max(0, start_val + TIME_SHIFT)
            end_time = max(0, end_val + TIME_SHIFT)
            if end_time <= start_time:
                continue
            if max_timestamp is not None and start_time > max_timestamp:
                continue

            spin_zone = interval.get('zone') or 1
            target_watts = _zone_to_watts(spin_zone)
            if target_watts is None:
                continue

            start_idx = 0
            end_idx = sample_count

            for i, timestamp in enumerate(seconds_array):
                if isinstance(timestamp, (int, float)) and timestamp >= start_time:
                    start_idx = i
                    break

            for i in range(len(seconds_array) - 1, -1, -1):
                timestamp = seconds_array[i]
                if isinstance(timestamp, (int, float)) and timestamp <= end_time:
                    end_idx = i + 1
                    break

            for i in range(start_idx, min(end_idx, sample_count)):
                if target_series[i] is None:
                    target_series[i] = target_watts
    
    # Convert to list of {timestamp, target_output} objects for template
    target_line_list = []
    for i, timestamp in enumerate(seconds_array):
        if not isinstance(timestamp, (int, float)):
            continue
        target_line_list.append({
            'timestamp': int(timestamp),
            'target_output': target_series[i] if i < len(target_series) else None
        })
    
    return target_line_list


def calculate_pace_target_line_from_segments(segments: List[Dict], seconds_array: List[int]) -> List[Dict[str, Any]]:
    """
    Calculate target pace line from class plan segments (for running/walking classes).
    Returns a list matching seconds_array length with target pace zones (0-6) for each timestamp.
    No time shift applied for pace targets (unlike power zones).
    
    Args:
        segments: List of segment dicts with 'start', 'end', 'zone'/'pace_level' keys
        seconds_array: List of timestamps to generate targets for
        
    Returns:
        List of dicts with 'timestamp' and 'target_pace_zone' keys
        
    Example:
        >>> segments = [{'start': 0, 'end': 120, 'zone': 2}]
        >>> seconds = list(range(0, 120))
        >>> targets = calculate_pace_target_line_from_segments(segments, seconds)
        >>> targets[0]['target_pace_zone']
        2
    """
    if not segments or not seconds_array:
        return []
    
    sample_count = len(seconds_array)
    max_timestamp = seconds_array[-1] if seconds_array else None
    target_series = [None] * sample_count
    
    # Process each segment from the class plan
    for idx, segment in enumerate(segments):
        # Get pace zone/level (0-6)
        zone_num = segment.get('zone') or segment.get('pace_level')
        if zone_num is None:
            continue
        
        # Ensure zone is in 0-6 range
        zone_num = max(0, min(6, int(zone_num)))
        
        # Get segment times (no shift for pace targets)
        start_time = max(0, segment.get('start', 0))
        end_time = max(0, segment.get('end', 0))
        
        if end_time <= start_time:
            continue
        
        # Skip segments that start after the workout ends
        if max_timestamp is not None and start_time > max_timestamp:
            continue
        
        # Map time offsets to array indices using seconds_array
        start_idx = 0
        end_idx = sample_count
        
        for i, timestamp in enumerate(seconds_array):
            if isinstance(timestamp, (int, float)) and timestamp >= start_time:
                start_idx = i
                break
        
        for i in range(len(seconds_array) - 1, -1, -1):
            timestamp = seconds_array[i]
            if isinstance(timestamp, (int, float)) and timestamp <= end_time:
                end_idx = i + 1
                break
        
        # Fill target_series for this segment
        for i in range(start_idx, min(end_idx, sample_count)):
            target_series[i] = zone_num
    
    # Convert to list of {timestamp, target_pace_zone} objects for template
    target_line_list = []
    for i, timestamp in enumerate(seconds_array):
        if not isinstance(timestamp, (int, float)):
            continue
        target_line_list.append({
            'timestamp': int(timestamp),
            'target_pace_zone': target_series[i] if i < len(target_series) else None
        })
    
    return target_line_list


def calculate_power_zone_target_line(
    target_metrics_list: List[Dict],
    user_ftp: float,
    seconds_array: List[int],
    zone_power_percentages: Optional[Dict[int, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate target output line data points from target_metrics_performance_data.
    Shifts target line 60 seconds backwards (earlier).
    
    Args:
        target_metrics_list: List of target metric dicts from ride_detail.target_metrics_data
        user_ftp: User's FTP value
        seconds_array: List of timestamps to generate targets for
        zone_power_percentages: Optional dict mapping zone to FTP percentage
        
    Returns:
        List of dicts with 'timestamp' and 'target_output' keys
        
    Example:
        >>> metrics = [{'segment_type': 'power_zone', 'offsets': {'start': 0, 'end': 120}, 'metrics': [{'name': 'power_zone', 'lower': 2, 'upper': 2}]}]
        >>> seconds = list(range(0, 120))
        >>> targets = calculate_power_zone_target_line(metrics, 200, seconds)
        >>> targets[0]['target_output']
        130  # 65% of FTP 200
    """
    # Default zone power percentages if not provided
    if zone_power_percentages is None:
        zone_power_percentages = {
            1: 0.45,    # Z1: 45% (active recovery target)
            2: 0.65,    # Z2: 65% (midpoint of 55-75%)
            3: 0.825,   # Z3: 82.5% (midpoint of 75-90%)
            4: 0.975,   # Z4: 97.5% (midpoint of 90-105%)
            5: 1.125,   # Z5: 112.5% (midpoint of 105-120%)
            6: 1.35,    # Z6: 135% (midpoint of 120-150%)
            7: 1.60,    # Z7: 160% (sprint target)
        }
    
    # Shift target line 60 seconds backwards
    TIME_SHIFT = -60
    
    # Create target series array matching seconds_array length
    sample_count = len(seconds_array)
    target_series = [None] * sample_count
    max_timestamp = seconds_array[-1] if seconds_array else None
    
    # Helper function to calculate target watts from zone number
    def _zone_to_watts(zone_num):
        if zone_num and zone_num in zone_power_percentages:
            return round(user_ftp * zone_power_percentages[zone_num])
        return None
    
    # Process each target metric segment
    for segment in target_metrics_list:
        if segment.get('segment_type') != 'power_zone':
            continue
            
        offsets = segment.get('offsets', {})
        # Shift segment times 60 seconds backwards
        start_offset = max(0, offsets.get('start', 0) + TIME_SHIFT)
        end_offset = max(0, offsets.get('end', 0) + TIME_SHIFT)
        
        if start_offset is None or end_offset is None or end_offset <= start_offset:
            continue
        
        # Skip segments that start after the workout ends
        if max_timestamp is not None and start_offset > max_timestamp:
            continue
        
        # Extract zone number from metrics
        zone_num = None
        for metric in segment.get('metrics', []):
            if metric.get('name') == 'power_zone':
                zone_lower = metric.get('lower')
                zone_upper = metric.get('upper')
                # Use lower if they match, otherwise use lower
                zone_num = zone_lower if zone_lower == zone_upper else zone_lower
                break
        
        if zone_num is None:
            continue
        
        # Calculate target watts for this zone
        target_watts = _zone_to_watts(zone_num)
        if target_watts is None:
            continue
        
        # Map time offsets to array indices using seconds_array
        start_idx = 0
        end_idx = sample_count
        
        for i, timestamp in enumerate(seconds_array):
            if isinstance(timestamp, (int, float)) and timestamp >= start_offset:
                start_idx = i
                break
        
        for i in range(len(seconds_array) - 1, -1, -1):
            timestamp = seconds_array[i]
            if isinstance(timestamp, (int, float)) and timestamp <= end_offset:
                end_idx = i + 1
                break
        
        # Fill target_series for this segment
        for i in range(start_idx, min(end_idx, sample_count)):
            target_series[i] = target_watts
    
    # Convert to list of {timestamp, target_output} objects for template
    target_line_list = []
    for i, timestamp in enumerate(seconds_array):
        if not isinstance(timestamp, (int, float)):
            continue
        target_line_list.append({
            'timestamp': int(timestamp),
            'target_output': target_series[i] if i < len(target_series) else None
        })
    
    return target_line_list
