"""
Default rowing pace level data (Levels 1-10)
Each level contains 4 zones: Easy, Moderate, Challenging, Max
Format: (pace_minutes, pace_seconds) for min/500m
Pace values are stored as decimal minutes (e.g., 4.183 for 04:11)
"""

def mmss_to_decimal(mmss_str):
    """Convert MM:SS format to decimal minutes"""
    if ':' in mmss_str:
        parts = mmss_str.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes + (seconds / 60.0)
    return float(mmss_str)

# Level 1
LEVEL_1 = {
    'easy': (mmss_to_decimal('04:11'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('03:43'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('03:26'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('03:12'), 'All-out sprint effort'),
}

# Level 2
LEVEL_2 = {
    'easy': (mmss_to_decimal('03:40'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('03:16'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('03:01'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('02:47'), 'All-out sprint effort'),
}

# Level 3
LEVEL_3 = {
    'easy': (mmss_to_decimal('03:18'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('02:56'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('02:43'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('02:31'), 'All-out sprint effort'),
}

# Level 4
LEVEL_4 = {
    'easy': (mmss_to_decimal('03:02'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('02:42'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('02:30'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('02:19'), 'All-out sprint effort'),
}

# Level 5
LEVEL_5 = {
    'easy': (mmss_to_decimal('02:50'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('02:31'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('02:19'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('02:09'), 'All-out sprint effort'),
}

# Level 6
LEVEL_6 = {
    'easy': (mmss_to_decimal('02:37'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('02:20'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('02:09'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('02:00'), 'All-out sprint effort'),
}

# Level 7
LEVEL_7 = {
    'easy': (mmss_to_decimal('02:26'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('02:10'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('02:00'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('01:51'), 'All-out sprint effort'),
}

# Level 8
LEVEL_8 = {
    'easy': (mmss_to_decimal('02:17'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('02:02'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('01:52'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('01:44'), 'All-out sprint effort'),
}

# Level 9
LEVEL_9 = {
    'easy': (mmss_to_decimal('02:07'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('01:53'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('01:45'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('01:37'), 'All-out sprint effort'),
}

# Level 10
LEVEL_10 = {
    'easy': (mmss_to_decimal('01:58'), 'Conversational pace'),
    'moderate': (mmss_to_decimal('01:45'), 'Comfortably hard effort'),
    'challenging': (mmss_to_decimal('01:37'), 'Moderate intensity intervals'),
    'max': (mmss_to_decimal('01:30'), 'All-out sprint effort'),
}

DEFAULT_ROWING_PACE_LEVELS = {
    1: LEVEL_1,
    2: LEVEL_2,
    3: LEVEL_3,
    4: LEVEL_4,
    5: LEVEL_5,
    6: LEVEL_6,
    7: LEVEL_7,
    8: LEVEL_8,
    9: LEVEL_9,
    10: LEVEL_10,
}

# Zone colors for rowing
ROWING_ZONE_COLORS = {
    'easy': '#3b82f6',      # Blue
    'moderate': '#10b981',   # Green
    'challenging': '#eab308', # Yellow
    'max': '#ef4444',       # Red
}
