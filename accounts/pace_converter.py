"""
Helper functions to convert pace formats
MM:SS format to decimal minutes
"""

def mmss_to_decimal(mmss_str):
    """
    Convert MM:SS format to decimal minutes
    Example: "18:11" -> 18.183 (18 minutes + 11/60 seconds)
    """
    if ':' in mmss_str:
        parts = mmss_str.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes + (seconds / 60.0)
    return float(mmss_str)

# Convert all the pace values from the images
# Level 1
LEVEL_1 = {
    'recovery': (1.0, 3.0, mmss_to_decimal('20:00'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (3.1, 3.3, mmss_to_decimal('18:11'), mmss_to_decimal('20:00'), 'Conversational pace'),
    'moderate': (3.4, 3.6, mmss_to_decimal('16:40'), mmss_to_decimal('18:11'), 'Comfortably hard effort'),
    'challenging': (3.7, 4.0, mmss_to_decimal('15:00'), mmss_to_decimal('16:40'), 'Moderate intensity intervals'),
    'hard': (4.1, 4.4, mmss_to_decimal('13:38'), mmss_to_decimal('15:00'), 'High intensity intervals'),
    'very_hard': (4.5, 4.9, mmss_to_decimal('12:15'), mmss_to_decimal('13:38'), 'Very high intensity'),
    'max': (5.0, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('12:15'), 'All-out sprint effort'),
}

# Level 2
LEVEL_2 = {
    'recovery': (1.0, 3.2, mmss_to_decimal('18:45'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (3.3, 3.6, mmss_to_decimal('16:40'), mmss_to_decimal('18:45'), 'Conversational pace'),
    'moderate': (3.7, 3.9, mmss_to_decimal('15:23'), mmss_to_decimal('16:40'), 'Comfortably hard effort'),
    'challenging': (4.0, 4.3, mmss_to_decimal('13:57'), mmss_to_decimal('15:23'), 'Moderate intensity intervals'),
    'hard': (4.4, 4.7, mmss_to_decimal('12:46'), mmss_to_decimal('13:57'), 'High intensity intervals'),
    'very_hard': (4.8, 5.2, mmss_to_decimal('11:32'), mmss_to_decimal('12:46'), 'Very high intensity'),
    'max': (5.3, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('11:32'), 'All-out sprint effort'),
}

# Level 3
LEVEL_3 = {
    'recovery': (1.0, 3.5, mmss_to_decimal('17:08'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (3.6, 3.9, mmss_to_decimal('15:23'), mmss_to_decimal('17:08'), 'Conversational pace'),
    'moderate': (4.0, 4.2, mmss_to_decimal('14:17'), mmss_to_decimal('15:23'), 'Comfortably hard effort'),
    'challenging': (4.3, 4.6, mmss_to_decimal('13:03'), mmss_to_decimal('14:17'), 'Moderate intensity intervals'),
    'hard': (4.7, 5.1, mmss_to_decimal('11:46'), mmss_to_decimal('13:03'), 'High intensity intervals'),
    'very_hard': (5.2, 5.6, mmss_to_decimal('10:43'), mmss_to_decimal('11:46'), 'Very high intensity'),
    'max': (5.7, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('10:43'), 'All-out sprint effort'),
}

# Level 4
LEVEL_4 = {
    'recovery': (1.0, 3.7, mmss_to_decimal('16:13'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (3.8, 4.1, mmss_to_decimal('15:13'), mmss_to_decimal('16:13'), 'Conversational pace'),
    'moderate': (4.2, 4.5, mmss_to_decimal('13:20'), mmss_to_decimal('15:13'), 'Comfortably hard effort'),
    'challenging': (4.6, 5.0, mmss_to_decimal('12:00'), mmss_to_decimal('13:20'), 'Moderate intensity intervals'),
    'hard': (5.1, 5.4, mmss_to_decimal('11:07'), mmss_to_decimal('12:00'), 'High intensity intervals'),
    'very_hard': (5.5, 6.1, mmss_to_decimal('09:50'), mmss_to_decimal('11:07'), 'Very high intensity'),
    'max': (6.2, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('09:50'), 'All-out sprint effort'),
}

# Level 5
LEVEL_5 = {
    'recovery': (1.0, 4.1, mmss_to_decimal('15:13'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (4.2, 4.5, mmss_to_decimal('13:20'), mmss_to_decimal('15:13'), 'Conversational pace'),
    'moderate': (4.6, 4.9, mmss_to_decimal('12:15'), mmss_to_decimal('13:20'), 'Comfortably hard effort'),
    'challenging': (5.0, 5.4, mmss_to_decimal('11:07'), mmss_to_decimal('12:15'), 'Moderate intensity intervals'),
    'hard': (5.5, 6.0, mmss_to_decimal('10:00'), mmss_to_decimal('11:07'), 'High intensity intervals'),
    'very_hard': (6.1, 6.6, mmss_to_decimal('09:05'), mmss_to_decimal('10:00'), 'Very high intensity'),
    'max': (6.7, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('09:05'), 'All-out sprint effort'),
}

# Level 6
LEVEL_6 = {
    'recovery': (1.0, 4.5, mmss_to_decimal('13:20'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (4.6, 4.9, mmss_to_decimal('12:15'), mmss_to_decimal('13:20'), 'Conversational pace'),
    'moderate': (5.0, 5.4, mmss_to_decimal('11:07'), mmss_to_decimal('12:15'), 'Comfortably hard effort'),
    'challenging': (5.5, 6.0, mmss_to_decimal('10:00'), mmss_to_decimal('11:07'), 'Moderate intensity intervals'),
    'hard': (6.1, 6.6, mmss_to_decimal('09:05'), mmss_to_decimal('10:00'), 'High intensity intervals'),
    'very_hard': (6.7, 7.3, mmss_to_decimal('08:13'), mmss_to_decimal('09:05'), 'Very high intensity'),
    'max': (7.4, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('08:13'), 'All-out sprint effort'),
}

# Level 7
LEVEL_7 = {
    'recovery': (1.0, 5.0, mmss_to_decimal('12:00'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (5.1, 5.5, mmss_to_decimal('10:54'), mmss_to_decimal('12:00'), 'Conversational pace'),
    'moderate': (5.6, 6.0, mmss_to_decimal('10:00'), mmss_to_decimal('10:54'), 'Comfortably hard effort'),
    'challenging': (6.1, 6.7, mmss_to_decimal('08:57'), mmss_to_decimal('10:00'), 'Moderate intensity intervals'),
    'hard': (6.8, 7.3, mmss_to_decimal('08:13'), mmss_to_decimal('08:57'), 'High intensity intervals'),
    'very_hard': (7.4, 8.1, mmss_to_decimal('07:24'), mmss_to_decimal('08:13'), 'Very high intensity'),
    'max': (8.2, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('07:24'), 'All-out sprint effort'),
}

# Level 8
LEVEL_8 = {
    'recovery': (1.0, 5.7, mmss_to_decimal('10:30'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (5.8, 6.2, mmss_to_decimal('09:41'), mmss_to_decimal('10:30'), 'Conversational pace'),
    'moderate': (6.3, 6.8, mmss_to_decimal('08:49'), mmss_to_decimal('09:41'), 'Comfortably hard effort'),
    'challenging': (6.9, 7.5, mmss_to_decimal('08:00'), mmss_to_decimal('08:49'), 'Moderate intensity intervals'),
    'hard': (7.6, 8.2, mmss_to_decimal('07:19'), mmss_to_decimal('08:00'), 'High intensity intervals'),
    'very_hard': (8.3, 9.1, mmss_to_decimal('06:35'), mmss_to_decimal('07:19'), 'Very high intensity'),
    'max': (9.2, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('06:35'), 'All-out sprint effort'),
}

# Level 9
LEVEL_9 = {
    'recovery': (1.0, 6.5, mmss_to_decimal('09:13'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (6.6, 7.2, mmss_to_decimal('08:20'), mmss_to_decimal('09:13'), 'Conversational pace'),
    'moderate': (7.3, 7.8, mmss_to_decimal('07:42'), mmss_to_decimal('08:20'), 'Comfortably hard effort'),
    'challenging': (7.9, 8.6, mmss_to_decimal('06:59'), mmss_to_decimal('07:42'), 'Moderate intensity intervals'),
    'hard': (8.7, 9.4, mmss_to_decimal('06:23'), mmss_to_decimal('06:59'), 'High intensity intervals'),
    'very_hard': (9.5, 10.4, mmss_to_decimal('05:46'), mmss_to_decimal('06:23'), 'Very high intensity'),
    'max': (10.5, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('05:46'), 'All-out sprint effort'),
}

# Level 10
LEVEL_10 = {
    'recovery': (1.0, 7.6, mmss_to_decimal('07:54'), mmss_to_decimal('60:00'), 'Base building, recovery'),
    'easy': (7.7, 8.4, mmss_to_decimal('07:09'), mmss_to_decimal('07:54'), 'Conversational pace'),
    'moderate': (8.5, 9.0, mmss_to_decimal('06:40'), mmss_to_decimal('07:09'), 'Comfortably hard effort'),
    'challenging': (9.1, 10.0, mmss_to_decimal('06:00'), mmss_to_decimal('06:40'), 'Moderate intensity intervals'),
    'hard': (10.1, 10.9, mmss_to_decimal('05:30'), mmss_to_decimal('06:00'), 'High intensity intervals'),
    'very_hard': (11.0, 12.2, mmss_to_decimal('04:55'), mmss_to_decimal('05:30'), 'Very high intensity'),
    'max': (12.3, 12.5, mmss_to_decimal('04:48'), mmss_to_decimal('04:55'), 'All-out sprint effort'),
}

DEFAULT_RUNNING_PACE_LEVELS = {
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

# Zone colors for display
ZONE_COLORS = {
    'recovery': 'bg-green-500',
    'easy': 'bg-blue-500',
    'moderate': 'bg-yellow-500',
    'challenging': 'bg-orange-500',
    'hard': 'bg-red-500',
    'very_hard': 'bg-purple-500',
    'max': 'bg-pink-500',
}
