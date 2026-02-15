

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from collections import defaultdict
from accounts.models import WeightEntry, FTPEntry, PaceEntry
from tracker.models import WeeklyPlan
from challenges.models import ChallengeInstance
from core.services import ZoneCalculatorService
from workouts.models import Workout, WorkoutDetails, WorkoutPerformanceData
from django.db.models import Q
from .serializers import MetricsSerializer


class MetricsAPIView(APIView):
	permission_classes = [IsAuthenticated]
	serializer_class = MetricsSerializer

	def get(self, request):
		# --- Begin: Copy of metrics logic from plans/views.py ---
		# (Only the essential data for API, not HTML context)
		# Get all challenge instances for this user
		all_challenge_instances = ChallengeInstance.objects.filter(
			user=request.user
		).select_related('challenge').prefetch_related('weekly_plans').order_by('-started_at')

		challenge_groups = defaultdict(list)
		for ci in all_challenge_instances:
			challenge_groups[ci.challenge.id].append(ci)

		fully_completed_challenges = []
		partially_completed_challenges = []
		for challenge_id, instances in challenge_groups.items():
			latest_instance = max(instances, key=lambda x: x.started_at)
			attempt_count = len(instances)
			latest_instance.attempt_count = attempt_count
			if latest_instance.all_weeks_completed:
				fully_completed_challenges.append(latest_instance.challenge.id)
			elif latest_instance.weekly_plans.exists() and latest_instance.completion_rate > 0:
				partially_completed_challenges.append(latest_instance.challenge.id)

		weight_entries = WeightEntry.objects.filter(user=request.user).order_by('-recorded_date', '-created_at')
		current_weight = weight_entries.first().weight if weight_entries.exists() else None

		all_plans = WeeklyPlan.objects.filter(user=request.user)
		total_points = sum(plan.total_points for plan in all_plans)

		ftp_entries = FTPEntry.objects.filter(user=request.user).order_by('recorded_date')
		running_pace_entries = PaceEntry.objects.filter(user=request.user, activity_type='running').order_by('recorded_date')
		walking_pace_entries = PaceEntry.objects.filter(user=request.user, activity_type='walking').order_by('recorded_date')

		current_ftp = ftp_entries.filter(is_active=True).order_by('-recorded_date').first()
		if not current_ftp:
			current_ftp = ftp_entries.order_by('-recorded_date').first()

		current_cycling_pw = None
		if current_weight and current_ftp:
			weight_kg = float(current_weight) * 0.453592
			if weight_kg > 0:
				current_cycling_pw = round(float(current_ftp.ftp_value) / weight_kg, 2)

		# Get Peloton workout data for Personal Records and monthly stats
		all_workouts = Workout.objects.filter(user=request.user).select_related('ride_detail', 'details', 'ride_detail__workout_type')

		# Calculate Time in Zones for Cycling (Power Zones 1-7)
		cycling_zones_all = ZoneCalculatorService.calculate_cycling_zones(all_workouts, period='all', current_ftp=current_ftp)
		cycling_zones_month = ZoneCalculatorService.calculate_cycling_zones(all_workouts, period='month', current_ftp=current_ftp)
		cycling_zones_year = ZoneCalculatorService.calculate_cycling_zones(all_workouts, period='year', current_ftp=current_ftp)

		# Calculate Time in Zones for Running (Intensity Zones)
		running_zones_all = ZoneCalculatorService.calculate_running_zones(all_workouts, period='all')
		running_zones_month = ZoneCalculatorService.calculate_running_zones(all_workouts, period='month')
		running_zones_year = ZoneCalculatorService.calculate_running_zones(all_workouts, period='year')

		# Example: Only return a subset of the data for now
		data = {
			'fully_completed_challenges': fully_completed_challenges,
			'partially_completed_challenges': partially_completed_challenges,
			'current_weight': current_weight,
			'total_points': total_points,
			'current_cycling_pw': current_cycling_pw,
			'cycling_zones_all': cycling_zones_all,
			'cycling_zones_month': cycling_zones_month,
			'cycling_zones_year': cycling_zones_year,
			'running_zones_all': running_zones_all,
			'running_zones_month': running_zones_month,
			'running_zones_year': running_zones_year,
		}
		return Response(data, status=status.HTTP_200_OK)
