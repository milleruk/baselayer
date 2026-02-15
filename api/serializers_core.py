from rest_framework import serializers
from core.models import SiteSettings, RideSyncQueue


class SiteSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for SiteSettings, representing global site configuration.
    """
    require_user_activation = serializers.BooleanField(help_text="If enabled, new user accounts require admin activation before login.")
    annual_challenge_id = serializers.CharField(help_text="Annual challenge ID to track for the current year.", required=False)
    annual_challenge_name = serializers.CharField(help_text="Display name for the current annual challenge.", required=False)
    class Meta:
        model = SiteSettings
        fields = '__all__'


class RideSyncQueueSerializer(serializers.ModelSerializer):
    """
    Serializer for RideSyncQueue, representing Peloton class sync queue entries.
    """
    class_id = serializers.CharField(help_text="Peloton class ID.")
    status = serializers.CharField(help_text="Current sync status (pending, synced, failed).")
    error_message = serializers.CharField(help_text="Error details if sync failed.", required=False)
    created_at = serializers.DateTimeField(help_text="When this queue entry was created.")
    synced_at = serializers.DateTimeField(help_text="When this class was synced or failed.", required=False)
    class Meta:
        model = RideSyncQueue
        fields = '__all__'
