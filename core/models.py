from django.db import models
from django.utils import timezone


class SiteSettings(models.Model):
    """
    Singleton model for site-wide settings.
    Only one instance should exist.
    """
    require_user_activation = models.BooleanField(
        default=True,
        help_text="If enabled, new user accounts require admin activation before they can log in. "
                  "Disable this when out of development mode to allow automatic registration."
    )

    annual_challenge_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Peloton Annual Challenge ID to track for the current year (e.g., 67bfab351b6f4e239ed17aadf28c006e)."
    )

    annual_challenge_name = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Display name for the current annual challenge (e.g., Annual Challenge 2026)."
    )
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return "Site Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton instance."""
        pass


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
