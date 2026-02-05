from django.contrib import admin
from .models import SiteSettings, RideSyncQueue


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin interface for site-wide settings (singleton)."""
    
    def has_add_permission(self, request):
        """Prevent adding more than one instance."""
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the singleton instance."""
        return False
    
    fieldsets = (
        ('User Registration Settings', {
            'fields': ('require_user_activation',),
            'description': 'Configure how new user registrations are handled.'
        }),
        ('Annual Challenge Settings', {
            'fields': ('annual_challenge_id', 'annual_challenge_name'),
            'description': 'Peloton challenge ID used to track annual challenge progress.'
        }),
    )


@admin.register(RideSyncQueue)
class RideSyncQueueAdmin(admin.ModelAdmin):
    """Admin interface for Ride Sync Queue."""
    list_display = ('class_id', 'status', 'created_at', 'synced_at')
    list_filter = ('status', 'created_at')
    search_fields = ('class_id', 'error_message')
    readonly_fields = ('created_at', 'synced_at')
    ordering = ('-created_at',)
