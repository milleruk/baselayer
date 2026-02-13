from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from peloton.models import PelotonConnection

logger = logging.getLogger(__name__)


@shared_task
def clear_stale_sync_flags(minutes=120):
    """Clear `sync_in_progress` on PelotonConnection records older than `minutes`.

    This helps recover from processes that died while a sync was running.
    """
    cutoff = timezone.now() - timedelta(minutes=minutes)
    stale_qs = PelotonConnection.objects.filter(sync_in_progress=True, sync_started_at__lt=cutoff)
    count = stale_qs.count()
    for conn in stale_qs:
        logger.info(f"Clearing stale sync flag for PelotonConnection id={conn.id} user_id={getattr(conn.user, 'id', None)} started_at={conn.sync_started_at}")
        conn.sync_in_progress = False
        conn.sync_started_at = None
        conn.save(update_fields=['sync_in_progress', 'sync_started_at'])
    logger.info(f"clear_stale_sync_flags: cleared {count} stale connections (older than {minutes} minutes)")
    return {'cleared': count}
