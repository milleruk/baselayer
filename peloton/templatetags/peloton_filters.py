from django import template

register = template.Library()


@register.filter
def format_duration_seconds(seconds):
    """Format seconds into hours and minutes (e.g., 3661 -> '1h 1m')"""
    if not seconds:
        return "0h 0m"
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    except (ValueError, TypeError):
        return "0h 0m"
