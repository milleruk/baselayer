from django import template

register = template.Library()

@register.filter
def format_pace(pace_value):
    """Format pace value (decimal minutes per mile) as MM:SS min/mile"""
    if not pace_value:
        return 'Not set'
    
    try:
        pace_float = float(pace_value)
        minutes = int(pace_float)
        seconds = int((pace_float - minutes) * 60)
        return f"{minutes}:{seconds:02d} min/mi"
    except (ValueError, TypeError):
        return 'Invalid'

@register.filter
def format_pace_range(min_pace, max_pace):
    """Format a pace range"""
    if not min_pace or not max_pace:
        return '—'
    return f"{min_pace|format_pace} - {max_pace|format_pace}"
