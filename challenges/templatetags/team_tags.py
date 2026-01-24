from django import template
from challenges.models import Team

register = template.Library()

@register.simple_tag
def get_user_teams(user):
    """Get all teams where user is a leader"""
    if not user or not user.is_authenticated:
        return []
    return Team.objects.filter(leader=user)

@register.filter
def is_team_leader(user, team):
    """Check if user is the leader of a team"""
    if not user or not user.is_authenticated:
        return False
    return team.leader == user
