from rest_framework import viewsets
from challenges.models import ChallengeInstance
from api.serializers_challenges import ChallengeInstanceSerializer


class ChallengeInstanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing user challenge instances (participation records).
    """
    queryset = ChallengeInstance.objects.all()
    serializer_class = ChallengeInstanceSerializer
