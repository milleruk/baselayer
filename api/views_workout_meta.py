from rest_framework import viewsets
from workouts.models import ClassType, WorkoutType, Instructor
from api.serializers_workout_meta import ClassTypeSerializer, WorkoutTypeSerializer, InstructorSerializer


class ClassTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing Peloton class types/categories.
    """
    queryset = ClassType.objects.all()
    serializer_class = ClassTypeSerializer


class WorkoutTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing workout types/categories.
    """
    queryset = WorkoutType.objects.all()
    serializer_class = WorkoutTypeSerializer


class InstructorViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing Peloton instructors.
    """
    queryset = Instructor.objects.all()
    serializer_class = InstructorSerializer
