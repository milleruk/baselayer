from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.services import DateRangeService
from plans.services import get_dashboard_period, get_dashboard_challenge_context
from workouts.models import Workout, WorkoutDetails
from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS
from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS
from accounts.rowing_pace_levels_data import DEFAULT_ROWING_PACE_LEVELS
from django.utils import timezone
from datetime import date

class DashboardStatsAPIView(APIView):
    """
    Returns dashboard analytics and challenge context for the authenticated user.

    Operation Summary:
    Get dashboard stats and challenge context for the authenticated user.

    Usage Example:
    GET /api/dashboard/stats/?period=7d
    Response:
    {
        "period_label": "Last 7 days",
        "comparison_label": "Previous 7 days",
        "challenge_context": {...},
        "recent_workouts": [
            {"id": 1, "completed_date": "2024-01-01", "title": "Workout Title"},
            ...
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.GET.get('period', '7d')
        today = timezone.now().date()
        period_context = get_dashboard_period(period, today=today)
        start_date = period_context['start_date']
        period_label = period_context['period_label']
        comparison_label = period_context['comparison_label']
        comparison_start = period_context['comparison_start']
        comparison_end = period_context['comparison_end']

        current_week_start = DateRangeService.sunday_of_current_week(date.today())
        challenge_context = get_dashboard_challenge_context(
            user=request.user,
            current_week_start=current_week_start,
        )

        # Recent workouts
        recent_workouts = Workout.objects.filter(user=request.user).order_by('-completed_date')[:10]
        recent_workouts_data = [
            {
                'id': w.id,
                'completed_date': w.completed_date,
                'title': str(w),
            } for w in recent_workouts
        ]

        data = {
            'period_label': period_label,
            'comparison_label': comparison_label,
            'challenge_context': challenge_context,
            'recent_workouts': recent_workouts_data,
        }
        return Response(data)
