from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from peloton.models import PelotonConnection
from django.utils import timezone
from rest_framework import status

class PelotonSyncAPIView(APIView):
    """
    Trigger a Peloton data sync for the authenticated user.

    Operation Summary:
    Triggers a sync of Peloton data for the authenticated user.

    Usage Example:
    POST /api/peloton/sync/
    {}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            connection = PelotonConnection.objects.get(user=user)
            if connection.sync_in_progress:
                return Response({'detail': 'Sync already in progress.'}, status=status.HTTP_409_CONFLICT)
            # Mark sync as started
            connection.sync_in_progress = True
            connection.sync_started_at = timezone.now()
            connection.save(update_fields=['sync_in_progress', 'sync_started_at'])
            # Here you would trigger the actual sync task (e.g., Celery task)
            # For now, just simulate immediate completion
            connection.last_sync_at = timezone.now()
            connection.sync_in_progress = False
            connection.save(update_fields=['last_sync_at', 'sync_in_progress'])
            return Response({'detail': 'Peloton sync triggered.'})
        except PelotonConnection.DoesNotExist:
            return Response({'detail': 'No Peloton connection found.'}, status=status.HTTP_404_NOT_FOUND)
