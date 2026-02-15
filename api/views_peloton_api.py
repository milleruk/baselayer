from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from peloton.models import PelotonConnection
from django.contrib.auth import get_user_model

class PelotonStatusAPIView(APIView):
    """
    Returns Peloton connection status and metadata for the authenticated user.

    Operation Summary:
    Get Peloton connection status for the authenticated user.

    Usage Example:
    GET /api/peloton/status/
    Response:
    {
        "is_active": true,
        "peloton_user_id": "123456",
        "last_sync_at": "2024-01-01T12:00:00Z",
        "has_bearer_token": true
    }
    """
    permission_classes = [IsAuthenticated]

    class OutputSerializer(serializers.Serializer):
        is_active = serializers.BooleanField()
        peloton_user_id = serializers.CharField(allow_null=True)
        last_sync_at = serializers.DateTimeField(allow_null=True)
        has_bearer_token = serializers.BooleanField()

    serializer_class = OutputSerializer

    def get(self, request):
        user = request.user
        try:
            connection = PelotonConnection.objects.get(user=user)
            data = {
                'is_active': connection.is_active,
                'peloton_user_id': connection.peloton_user_id,
                'last_sync_at': connection.last_sync_at,
                'has_bearer_token': bool(connection.bearer_token),
            }
        except PelotonConnection.DoesNotExist:
            data = {'is_active': False, 'peloton_user_id': None, 'last_sync_at': None, 'has_bearer_token': False}
        serializer = self.OutputSerializer(data)
        return Response(serializer.data)
