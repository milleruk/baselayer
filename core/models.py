from django.db import models
from django.utils import timezone


class RideSyncQueue(models.Model):
    """
    Tracks Peloton class IDs that need to be synced to the local RideDetail database.
    When an admin tries to assign a class that doesn't exist locally, an entry is created
    with status='pending'. A background task processes the queue and marks entries as
    'synced' or 'failed' after attempting the API fetch.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
    ]
    
    # Peloton class ID (unique constraint per entry type)
    class_id = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="Peloton class ID (e.g., from API or extracted from class URL)"
    )
    
    # Current status of the sync
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Current sync status"
    )
    
    # Error message if sync failed
    error_message = models.TextField(
        blank=True,
        help_text="Error details if sync failed (e.g., class not found on Peloton, API error)"
    )
    
    # Timestamps for tracking
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this queue entry was created"
    )
    
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this class was successfully synced (status='synced' or 'failed')"
    )
    
    class Meta:
        verbose_name = "Ride Sync Queue"
        verbose_name_plural = "Ride Sync Queues"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['status', 'created_at']
    
    def __str__(self):
        return f"RideSyncQueue({self.class_id}, status={self.status})"
    
    def mark_synced(self):
        """Mark this queue entry as successfully synced."""
        self.status = 'synced'
        self.synced_at = timezone.now()
        self.error_message = ''
        self.save()
    
    def mark_failed(self, error_msg):
        """Mark this queue entry as failed with error message."""
        self.status = 'failed'
        self.synced_at = timezone.now()
        self.error_message = error_msg[:1000]  # Truncate long errors
        self.save()
