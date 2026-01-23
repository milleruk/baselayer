"""
Default walking pace level data (Levels 1-10)
Each level contains 5 zones: Recovery, Easy, Brisk, Power, Max
Format: (min_mph, max_mph, min_pace_minutes, max_pace_minutes, description)
Pace values are stored as decimal minutes (e.g., 42.85 for 42:51)
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
    'recovery': (1.0, 1.4, mmss_to_decimal('42:51'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (1.4, 1.8, mmss_to_decimal('33:20'), mmss_to_decimal('42:51'), 'Conversational pace'),
    'brisk': (1.8, 2.2, mmss_to_decimal('27:16'), mmss_to_decimal('33:20'), 'Comfortably hard effort'),
    'power': (2.2, 2.6, mmss_to_decimal('23:05'), mmss_to_decimal('27:16'), 'High intensity intervals'),
    'max': (2.6, 5.6, mmss_to_decimal('10:43'), mmss_to_decimal('23:05'), 'All-out sprint effort'),
}

# Level 2
LEVEL_2 = {
    'recovery': (1.0, 1.9, mmss_to_decimal('31:35'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (1.9, 2.3, mmss_to_decimal('26:05'), mmss_to_decimal('31:35'), 'Conversational pace'),
    'brisk': (2.3, 2.7, mmss_to_decimal('22:13'), mmss_to_decimal('26:05'), 'Comfortably hard effort'),
    'power': (2.7, 3.1, mmss_to_decimal('19:21'), mmss_to_decimal('22:13'), 'High intensity intervals'),
    'max': (3.1, 6.1, mmss_to_decimal('09:51'), mmss_to_decimal('19:21'), 'All-out sprint effort'),
}

# Level 3
LEVEL_3 = {
    'recovery': (1.0, 2.4, mmss_to_decimal('25:00'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (2.4, 2.8, mmss_to_decimal('21:26'), mmss_to_decimal('25:00'), 'Conversational pace'),
    'brisk': (2.8, 3.2, mmss_to_decimal('18:45'), mmss_to_decimal('21:26'), 'Comfortably hard effort'),
    'power': (3.2, 3.6, mmss_to_decimal('16:40'), mmss_to_decimal('18:45'), 'High intensity intervals'),
    'max': (3.6, 6.6, mmss_to_decimal('09:05'), mmss_to_decimal('16:40'), 'All-out sprint effort'),
}

# Level 4
LEVEL_4 = {
    'recovery': (1.0, 2.9, mmss_to_decimal('20:41'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (2.9, 3.3, mmss_to_decimal('18:11'), mmss_to_decimal('20:41'), 'Conversational pace'),
    'brisk': (3.3, 3.7, mmss_to_decimal('16:13'), mmss_to_decimal('18:11'), 'Comfortably hard effort'),
    'power': (3.7, 4.1, mmss_to_decimal('14:38'), mmss_to_decimal('16:13'), 'High intensity intervals'),
    'max': (4.1, 7.1, mmss_to_decimal('08:27'), mmss_to_decimal('14:38'), 'All-out sprint effort'),
}

# Level 5
LEVEL_5 = {
    'recovery': (1.0, 3.4, mmss_to_decimal('17:39'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (3.4, 3.8, mmss_to_decimal('15:47'), mmss_to_decimal('17:39'), 'Conversational pace'),
    'brisk': (3.8, 4.2, mmss_to_decimal('14:17'), mmss_to_decimal('15:47'), 'Comfortably hard effort'),
    'power': (4.2, 4.6, mmss_to_decimal('13:03'), mmss_to_decimal('14:17'), 'High intensity intervals'),
    'max': (4.6, 7.6, mmss_to_decimal('07:54'), mmss_to_decimal('13:03'), 'All-out sprint effort'),
}

# Level 6
LEVEL_6 = {
    'recovery': (1.0, 3.8, mmss_to_decimal('15:47'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (3.8, 4.2, mmss_to_decimal('14:17'), mmss_to_decimal('15:47'), 'Conversational pace'),
    'brisk': (4.2, 4.6, mmss_to_decimal('13:03'), mmss_to_decimal('14:17'), 'Comfortably hard effort'),
    'power': (4.6, 5.1, mmss_to_decimal('11:46'), mmss_to_decimal('13:03'), 'High intensity intervals'),
    'max': (5.1, 8.1, mmss_to_decimal('07:24'), mmss_to_decimal('11:46'), 'All-out sprint effort'),
}

# Level 7
LEVEL_7 = {
    'recovery': (1.0, 4.3, mmss_to_decimal('13:57'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (4.3, 4.7, mmss_to_decimal('12:46'), mmss_to_decimal('13:57'), 'Conversational pace'),
    'brisk': (4.7, 5.1, mmss_to_decimal('11:46'), mmss_to_decimal('12:46'), 'Comfortably hard effort'),
    'power': (5.1, 5.6, mmss_to_decimal('10:43'), mmss_to_decimal('11:46'), 'High intensity intervals'),
    'max': (5.6, 8.6, mmss_to_decimal('06:59'), mmss_to_decimal('10:43'), 'All-out sprint effort'),
}

# Level 8
LEVEL_8 = {
    'recovery': (1.0, 4.7, mmss_to_decimal('12:46'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (4.7, 5.1, mmss_to_decimal('11:46'), mmss_to_decimal('12:46'), 'Conversational pace'),
    'brisk': (5.1, 5.5, mmss_to_decimal('10:55'), mmss_to_decimal('11:46'), 'Comfortably hard effort'),
    'power': (5.5, 6.1, mmss_to_decimal('09:50'), mmss_to_decimal('10:55'), 'High intensity intervals'),
    'max': (6.1, 9.1, mmss_to_decimal('06:35'), mmss_to_decimal('09:50'), 'All-out sprint effort'),
}

# Level 9
LEVEL_9 = {
    'recovery': (1.0, 5.1, mmss_to_decimal('11:46'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (5.1, 5.6, mmss_to_decimal('10:43'), mmss_to_decimal('11:46'), 'Conversational pace'),
    'brisk': (5.6, 6.0, mmss_to_decimal('10:00'), mmss_to_decimal('10:43'), 'Comfortably hard effort'),
    'power': (6.0, 6.6, mmss_to_decimal('09:05'), mmss_to_decimal('10:00'), 'High intensity intervals'),
    'max': (6.6, 9.8, mmss_to_decimal('06:07'), mmss_to_decimal('09:05'), 'All-out sprint effort'),
}

# Level 10 - extrapolated from pattern (not provided in images, but following the progression)
LEVEL_10 = {
    'recovery': (1.0, 5.5, mmss_to_decimal('10:54'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (5.5, 6.0, mmss_to_decimal('10:00'), mmss_to_decimal('10:54'), 'Conversational pace'),
    'brisk': (6.0, 6.5, mmss_to_decimal('09:14'), mmss_to_decimal('10:00'), 'Comfortably hard effort'),
    'power': (6.5, 7.1, mmss_to_decimal('08:27'), mmss_to_decimal('09:14'), 'High intensity intervals'),
    'max': (7.1, 10.1, mmss_to_decimal('05:56'), mmss_to_decimal('08:27'), 'All-out sprint effort'),
}

DEFAULT_WALKING_PACE_LEVELS = {
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

# Zone colors for walking (same as running but different zones)
WALKING_ZONE_COLORS = {
    'recovery': 'bg-green-500',
    'easy': 'bg-blue-500',
    'brisk': 'bg-yellow-500',
    'power': 'bg-orange-500',
    'max': 'bg-red-500',
}
