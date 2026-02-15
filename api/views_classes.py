from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from workouts.models import RideDetail
from .serializers_classes import RideDetailSerializer


class RideDetailViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing Peloton ride/class details.
    """
    serializer_class = RideDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RideDetail.objects.all()
