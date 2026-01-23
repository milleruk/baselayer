from django import template

register = template.Library()

@register.filter
def get_medal(completion_rate):
    """Returns medal emoji and name based on completion rate
    
    Medal thresholds based on max core points (150):
    - Platinum: 100.1%+ (150.15+ points, e.g., 160/150 = 106.67%)
    - Gold: 90-100% (135-150 points)
    - Silver: 80-89.99% (120-134.99 points)
    - Bronze: 79.99% and below (<120 points)
    """
    if completion_rate is None:
        return None
    
    completion_rate = float(completion_rate)
    
    # Platinum: 100.1% or higher (160/150 = 106.67% qualifies)
    if completion_rate >= 100.1:
        return {'emoji': '💎', 'name': 'Platinum', 'color': '#E5E4E2'}
    # Gold: 90-100% (135-150 points out of 150)
    elif completion_rate >= 90:
        return {'emoji': '🥇', 'name': 'Gold', 'color': '#FFD700'}
    # Silver: 80-89.99% (120-134.99 points out of 150)
    elif completion_rate >= 80:
        return {'emoji': '🥈', 'name': 'Silver', 'color': '#C0C0C0'}
    # Bronze: 79.99% and below (<120 points out of 150)
    elif completion_rate >= 0:
        return {'emoji': '🥉', 'name': 'Bronze', 'color': '#CD7F32'}
    else:
        return None

@register.filter
def get_medal_emoji(completion_rate):
    """Returns just the medal emoji"""
    medal = get_medal(completion_rate)
    return medal['emoji'] if medal else None

@register.filter
def get_medal_name(completion_rate):
    """Returns just the medal name"""
    medal = get_medal(completion_rate)
    return medal['name'] if medal else None

@register.filter
def get_medal_color(completion_rate):
    """Returns just the medal color"""
    medal = get_medal(completion_rate)
    return medal['color'] if medal else None
