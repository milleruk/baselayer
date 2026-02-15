from rest_framework import viewsets
from challenges.models import Challenge
from api.serializers_challenge import ChallengeSerializer

class ChallengeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing admin-defined challenges.
    """
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
