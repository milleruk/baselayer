from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from peloton.models import PelotonConnection
from django.contrib.auth import get_user_model
from rest_framework import status

class PelotonConnectAPIView(APIView):
    """
    Connect a user's Peloton account by saving credentials (username/password or bearer token).

    Operation Summary:
    Connect Peloton account for the authenticated user. Accepts either username/password or bearer_token.

    Usage Example:
    POST /api/peloton/connect/
    {
        "username": "user@email.com",
        "password": "yourpassword"
    }
    OR
    {
        "bearer_token": "tokenstring"
    }
    """
    permission_classes = [IsAuthenticated]

    class InputSerializer(serializers.Serializer):
        username = serializers.CharField(required=False, help_text="Peloton username")
        password = serializers.CharField(required=False, help_text="Peloton password")
        bearer_token = serializers.CharField(required=False, help_text="Peloton OAuth2 bearer token")

    serializer_class = InputSerializer

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data.get('username')
        password = serializer.validated_data.get('password')
        bearer_token = serializer.validated_data.get('bearer_token')
        user = request.user
        if not (username and password) and not bearer_token:
            return Response({'detail': 'Provide username/password or bearer_token.'}, status=status.HTTP_400_BAD_REQUEST)
        connection, _ = PelotonConnection.objects.get_or_create(user=user)
        if username and password:
            connection.username = username
            connection.password = password
        if bearer_token:
            connection.bearer_token = bearer_token
        connection.is_active = True
        connection.save()
        return Response({'detail': 'Peloton account connected.'})

class PelotonDisconnectAPIView(APIView):
    """
    Disconnect a user's Peloton account and remove credentials.

    Operation Summary:
    Disconnect Peloton account for the authenticated user.

    Usage Example:
    POST /api/peloton/disconnect/
    {}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            connection = PelotonConnection.objects.get(user=user)
            connection.delete()
            return Response({'detail': 'Peloton account disconnected.'})
        except PelotonConnection.DoesNotExist:
            return Response({'detail': 'No Peloton connection found.'}, status=status.HTTP_404_NOT_FOUND)
