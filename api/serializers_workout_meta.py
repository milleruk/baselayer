from rest_framework import serializers
from workouts.models import ClassType, WorkoutType, Instructor


class ClassTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for ClassType, representing a Peloton class type/category.
    """
    peloton_id = serializers.CharField(help_text="Peloton class type ID.")
    name = serializers.CharField(help_text="Display name of the class type.")
    fitness_discipline = serializers.CharField(help_text="Fitness discipline (e.g., cycling, running, yoga).", required=False)
    class Meta:
        model = ClassType
        fields = '__all__'


class WorkoutTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for WorkoutType, representing a workout type/category (Cycling, Running, Yoga, etc.).
    """
    name = serializers.CharField(help_text="Name of the workout type.")
    slug = serializers.CharField(help_text="Slug for the workout type.")
    icon = serializers.CharField(help_text="Icon identifier.", required=False)
    class Meta:
        model = WorkoutType
        fields = '__all__'


class InstructorSerializer(serializers.ModelSerializer):
    """
    Serializer for Instructor, representing a Peloton instructor.
    """
    name = serializers.CharField(help_text="Instructor's name.")
    peloton_id = serializers.CharField(help_text="Peloton instructor ID.", required=False)
    image_url = serializers.URLField(help_text="Profile image URL.", required=False)
    bio = serializers.CharField(help_text="Instructor biography.", required=False)
    location = serializers.CharField(help_text="Instructor location.", required=False)
    username = serializers.CharField(help_text="Peloton username.", required=False)
    class Meta:
        model = Instructor
        fields = '__all__'
