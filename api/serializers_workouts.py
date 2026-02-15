from rest_framework import serializers
from workouts.models import Workout, WorkoutDetails, WorkoutPerformanceData


class WorkoutSerializer(serializers.ModelSerializer):
    """
    Serializer for Workout, representing a user's workout session.
    """
    # Add help_text for key fields as needed
    class Meta:
        model = Workout
        fields = '__all__'


class WorkoutDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for WorkoutDetails, representing detailed data for a workout.
    """
    class Meta:
        model = WorkoutDetails
        fields = '__all__'


class WorkoutPerformanceDataSerializer(serializers.ModelSerializer):
    """
    Serializer for WorkoutPerformanceData, representing performance metrics for a workout.
    """
    class Meta:
        model = WorkoutPerformanceData
        fields = '__all__'
