from rest_framework import viewsets
from core.models import SiteSettings, RideSyncQueue
from api.serializers_core import SiteSettingsSerializer, RideSyncQueueSerializer


class SiteSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing global site settings (read-only).
    """
    queryset = SiteSettings.objects.all()
    serializer_class = SiteSettingsSerializer


class RideSyncQueueViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing Peloton ride sync queue entries.
    """
    queryset = RideSyncQueue.objects.all()
    serializer_class = RideSyncQueueSerializer
