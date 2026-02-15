from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from plans.models import Exercise
from .serializers_plans import ExerciseSerializer

class ExerciseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing exercises (yoga, pilates, breathwork, mobility).
    """
    serializer_class = ExerciseSerializer
    permission_classes = [IsAuthenticated]
    queryset = Exercise.objects.all()

