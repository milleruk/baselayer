from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from workouts.models import Workout, WorkoutDetails, WorkoutPerformanceData
from .serializers_workouts import WorkoutSerializer, WorkoutDetailsSerializer, WorkoutPerformanceDataSerializer


class WorkoutViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing user workouts.
    """
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workout.objects.filter(user=self.request.user)


class WorkoutDetailsViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing workout details (per-session data).
    """
    serializer_class = WorkoutDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkoutDetails.objects.filter(workout__user=self.request.user)


class WorkoutPerformanceDataViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing workout performance data (metrics, time series, etc.).
    """
    serializer_class = WorkoutPerformanceDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkoutPerformanceData.objects.filter(workout__user=self.request.user)
