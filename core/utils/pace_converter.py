"""
Pace and speed conversion utilities for workout data.

Extracted from workouts/views.py for reuse across tracker, plans, challenges, and workouts apps.
Handles conversions between mph, pace (min/mile), and pace zone levels.
"""
from typing import Optional, Dict, Any, Tuple


# Pace zone constants
PACE_ZONE_LEVEL_TO_KEY = {
    1: 'recovery',
    2: 'easy',
    3: 'moderate',
    4: 'challenging',
    5: 'hard',
    6: 'very_hard',
    7: 'max',
}

PACE_ZONE_KEY_TO_LEVEL = {v: k for k, v in PACE_ZONE_LEVEL_TO_KEY.items()}

PACE_ZONE_LEVEL_ORDER = tuple(PACE_ZONE_LEVEL_TO_KEY.keys())

PACE_ZONE_LEVEL_LABELS = {
    1: "RECOVERY",
    2: "EASY",
    3: "MODERATE",
    4: "CHALLENGING",
    5: "HARD",
    6: "VERY HARD",
    7: "MAX",
}

PACE_ZONE_LEVEL_DISPLAY = {
    1: "Recovery",
    2: "Easy",
    3: "Moderate",
    4: "Challenging",
    5: "Hard",
    6: "Very Hard",
    7: "Max",
}

PACE_ZONE_COLORS = {
    7: "rgba(239, 68, 68, 0.55)",
    6: "rgba(249, 115, 22, 0.55)",
    5: "rgba(245, 158, 11, 0.55)",
    4: "rgba(34, 197, 94, 0.55)",
    3: "rgba(20, 184, 166, 0.55)",
    2: "rgba(59, 130, 246, 0.55)",
    1: "rgba(124, 58, 237, 0.55)",
}


def pace_zone_to_level(zone) -> Optional[int]:
    """
    Map pace intensity zone identifier (string/int) to 1-7 level.
    
    Args:
        zone: Zone identifier (int, float, or string like 'moderate', 'easy', etc.)
        
    Returns:
        Level 1-7 or None if unknown
        
    Example:
        >>> pace_zone_to_level('moderate')
        3
        >>> pace_zone_to_level(2)
        3
    """
    if isinstance(zone, (int, float)):
        try:
            value = int(round(float(zone)))
        except Exception:
            return None
        if 0 <= value <= 6:
            return value + 1
        if 1 <= value <= 7:
            return value
        return None
    
    if not isinstance(zone, str) or not zone:
        return None
    
    z = zone.strip().lower().replace('-', '_').replace(' ', '_')
    
    if z.isdigit():
        try:
            val = int(z)
        except ValueError:
            val = None
        if val is not None:
            return pace_zone_to_level(val)
    
    if z in PACE_ZONE_KEY_TO_LEVEL:
        return PACE_ZONE_KEY_TO_LEVEL[z]
    
    compressed = z.replace('_', '')
    for key, value in PACE_ZONE_KEY_TO_LEVEL.items():
        if key.replace('_', '') == compressed:
            return value
    
    return None


def pace_str_from_mph(mph: float) -> Optional[str]:
    """
    Convert mph to pace string (mm:ss/mi format).
    
    Args:
        mph: Speed in miles per hour
        
    Returns:
        Pace string like "8:30/mi" or None if invalid
        
    Example:
        >>> pace_str_from_mph(7.5)
        '8:00/mi'
    """
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


def mph_from_pace_value(pace_value) -> Optional[float]:
    """
    Convert pace value to mph.
    
    Handles multiple formats:
    - Numeric minutes per mile (e.g., 8.5 for 8:30/mi)
    - String with colon (e.g., "8:30")
    - Seconds per mile (e.g., 360 for 6:00/mi)
    
    Args:
        pace_value: Pace in various formats (int, float, or string)
        
    Returns:
        Speed in mph or None if invalid
        
    Example:
        >>> mph_from_pace_value("8:00")
        7.5
        >>> mph_from_pace_value(8.0)
        7.5
    """
    def _minutes_from_numeric(value):
        try:
            minutes = float(value)
        except (TypeError, ValueError):
            return None
        if minutes <= 0:
            return None
        # Peloton APIs sometimes return pace as seconds per mile (e.g., 360 for 6:00/mi).
        # Detect clearly out-of-range "minutes" values and treat them as seconds.
        if minutes >= 60:
            minutes = minutes / 60.0
        return minutes

    if isinstance(pace_value, (int, float)):
        minutes = _minutes_from_numeric(pace_value)
        return 60.0 / minutes if minutes else None

    if isinstance(pace_value, str):
        pace_value = pace_value.strip()
        if not pace_value:
            return None
        try:
            if ':' in pace_value:
                mins, secs = pace_value.split(':', 1)
                total_minutes = int(mins) + float(secs) / 60.0
            else:
                total_minutes = _minutes_from_numeric(float(pace_value))
            if total_minutes and total_minutes > 0:
                return 60.0 / total_minutes
        except (ValueError, ZeroDivisionError):
            return None
    
    return None


def pace_zone_level_from_speed(speed_mph: float, pace_ranges: Dict) -> Optional[int]:
    """
    Get pace zone level (1-7) from speed in mph.
    
    Args:
        speed_mph: Speed in miles per hour
        pace_ranges: Dict mapping level to range data with 'max_mph' key
        
    Returns:
        Pace zone level 1-7 or None if invalid
        
    Example:
        >>> ranges = {1: {'max_mph': 5.0}, 2: {'max_mph': 6.0}}
        >>> pace_zone_level_from_speed(5.5, ranges)
        2
    """
    if not isinstance(speed_mph, (int, float)) or not pace_ranges:
        return None
    
    speed = float(speed_mph)
    for level in PACE_ZONE_LEVEL_ORDER:
        rng = pace_ranges.get(level)
        if not rng:
            continue
        max_mph = rng.get('max_mph')
        if isinstance(max_mph, (int, float)) and speed <= max_mph + 1e-6:
            return level
    
    return PACE_ZONE_LEVEL_ORDER[-1]


def scaled_pace_zone_value_from_speed(speed_mph: float, pace_ranges: Dict) -> Optional[float]:
    """
    Map speed to scaled zone value for charting (zone number with fractional position within zone).
    
    Args:
        speed_mph: Speed in miles per hour
        pace_ranges: Dict mapping level to range data with 'min_mph' and 'max_mph' keys
        
    Returns:
        Scaled value (e.g., 2.7 for 70% through zone 3) or None if invalid
        
    Example:
        >>> ranges = {2: {'min_mph': 5.0, 'max_mph': 6.0}}
        >>> scaled_pace_zone_value_from_speed(5.5, ranges)
        2.0  # Midpoint of zone 2
    """
    level = pace_zone_level_from_speed(speed_mph, pace_ranges)
    if not isinstance(level, int):
        return None
    
    rng = pace_ranges.get(level) or {}
    try:
        min_mph = float(rng.get('min_mph', 0.0))
        max_mph = float(rng.get('max_mph', min_mph + 0.5))
        speed = float(speed_mph)
    except (TypeError, ValueError):
        return float(level)
    
    span = max(max_mph - min_mph, 0.25)
    clamped = min(max(speed, min_mph), max_mph)
    frac = (clamped - min_mph) / span
    return (level - 0.5) + max(0.0, min(frac, 1.0))


def pace_zone_label_from_level(level: int, uppercase: bool = True) -> Optional[str]:
    """
    Get display label for pace zone level.
    
    Args:
        level: Pace zone level 1-7
        uppercase: If True, return uppercase label (e.g., "EASY"), else title case
        
    Returns:
        Zone label string or None if invalid level
        
    Example:
        >>> pace_zone_label_from_level(2, uppercase=True)
        'EASY'
        >>> pace_zone_label_from_level(2, uppercase=False)
        'Easy'
    """
    try:
        lvl = int(level)
    except Exception:
        return None
    
    labels = PACE_ZONE_LEVEL_LABELS if uppercase else PACE_ZONE_LEVEL_DISPLAY
    return labels.get(lvl)


def resolve_pace_context(user_profile, workout_date, discipline: str) -> Dict[str, Any]:
    """
    Resolve pace context (activity type, pace level, pace ranges) for a user and workout.
    
    Args:
        user_profile: User profile object with pace settings
        workout_date: Date of the workout
        discipline: Workout discipline ('running', 'walking', etc.)
        
    Returns:
        Dict with keys: activity_type, pace_level, pace_ranges, pace_zone_thresholds
        
    Example:
        >>> context = resolve_pace_context(profile, date(2025, 1, 1), 'running')
        >>> print(context['activity_type'])
        'running'
        >>> print(context['pace_level'])
        5
    """
    activity_type = 'walking' if discipline in ['walking', 'walk'] else 'running'
    pace_level = None
    
    if user_profile and workout_date and hasattr(user_profile, 'get_pace_at_date'):
        try:
            pace_level = user_profile.get_pace_at_date(workout_date, activity_type=activity_type)
        except Exception:
            pace_level = None
    
    if pace_level is None and user_profile and hasattr(user_profile, 'get_current_pace'):
        try:
            pace_level = user_profile.get_current_pace(activity_type=activity_type)
        except Exception:
            pace_level = None
    
    if pace_level is None and user_profile:
        pace_level = getattr(user_profile, 'pace_target_level', None)
    
    try:
        pace_level = int(pace_level)
    except Exception:
        pace_level = None
    
    if pace_level is None or pace_level < 1 or pace_level > 10:
        pace_level = 5

    pace_level_data = None
    try:
        if activity_type == 'walking':
            from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS
            pace_level_data = DEFAULT_WALKING_PACE_LEVELS.get(pace_level)
        else:
            from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS
            pace_level_data = DEFAULT_RUNNING_PACE_LEVELS.get(pace_level)
    except Exception:
        pace_level_data = None

    pace_ranges = {}
    pace_zone_thresholds = {}
    
    if pace_level_data:
        for level in PACE_ZONE_LEVEL_ORDER:
            key = PACE_ZONE_LEVEL_TO_KEY[level]
            zone_tuple = pace_level_data.get(key)
            if not zone_tuple or len(zone_tuple) < 5:
                continue
            try:
                min_mph = float(zone_tuple[0])
                max_mph = float(zone_tuple[1])
                min_pace = float(zone_tuple[2])  # decimal minutes per mile
            except (TypeError, ValueError):
                continue
            
            pace_ranges[level] = {
                'min_mph': min_mph,
                'max_mph': max_mph,
                'mid_mph': (min_mph + max_mph) / 2.0,
                'zone_key': key,
            }
            
            try:
                pace_zone_thresholds[key] = int(round(min_pace * 60.0))
            except Exception:
                continue

    return {
        'activity_type': activity_type,
        'pace_level': pace_level,
        'pace_ranges': pace_ranges or None,
        'pace_zone_thresholds': pace_zone_thresholds or None,
    }
