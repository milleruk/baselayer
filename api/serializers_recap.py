from rest_framework import serializers
from plans.models import RecapShare, RecapCache


class RecapShareSerializer(serializers.ModelSerializer):
    """
    Serializer for RecapShare, representing a public share link for a user's yearly recap.
    """
    year = serializers.IntegerField(help_text="Year for this recap.")
    token = serializers.CharField(help_text="Unique token for the share link.")
    is_enabled = serializers.BooleanField(help_text="Whether this share link is active.")
    view_count = serializers.IntegerField(help_text="Number of times this recap has been viewed.")
    last_viewed_at = serializers.DateTimeField(help_text="Last time this recap was viewed.", required=False)
    class Meta:
        model = RecapShare
        fields = '__all__'


class RecapCacheSerializer(serializers.ModelSerializer):
    """
    Serializer for RecapCache, representing cached yearly recap data for a user.
    """
    year = serializers.IntegerField(help_text="Year for this recap cache.")
    daily_activities = serializers.JSONField(help_text="Daily activities data (JSON).", required=False)
    total_workouts_count = serializers.IntegerField(help_text="Total number of workouts in this year.")
    last_workout_updated_at = serializers.DateTimeField(help_text="Last time a workout was updated.", required=False)
    class Meta:
        model = RecapCache
        fields = '__all__'
