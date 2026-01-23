"""
Default pace level data for running (Levels 1-10)
Each level contains 7 zones: Recovery, Easy, Moderate, Challenging, Hard, Very Hard, Max
Format: (min_mph, max_mph, min_pace_minutes, max_pace_minutes, description)
Pace values are stored as decimal minutes (e.g., 18.183 for 18:11)
"""

from .pace_converter import DEFAULT_RUNNING_PACE_LEVELS, ZONE_COLORS

# Re-export for convenience
__all__ = ['DEFAULT_RUNNING_PACE_LEVELS', 'ZONE_COLORS']
