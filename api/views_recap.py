from rest_framework import viewsets
from plans.models import RecapShare, RecapCache
from api.serializers_recap import RecapShareSerializer, RecapCacheSerializer


class RecapShareViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing recap share links (public yearly recaps).
    """
    queryset = RecapShare.objects.all()
    serializer_class = RecapShareSerializer


class RecapCacheViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing recap cache data (cached yearly stats).
    """
    queryset = RecapCache.objects.all()
    serializer_class = RecapCacheSerializer
