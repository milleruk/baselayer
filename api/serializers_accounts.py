from rest_framework import serializers
from accounts.models import User, Profile, WeightEntry, FTPEntry, PaceEntry


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User, representing a registered user account.
    """
    email = serializers.EmailField(help_text="User's email address.")
    class Meta:
        model = User
        fields = ['id', 'email']


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for Profile, representing extended user profile information.
    """
    full_name = serializers.CharField(help_text="Full name of the user.", required=False)
    date_of_birth = serializers.DateField(help_text="Date of birth.", required=False)
    peloton_leaderboard_name = serializers.CharField(help_text="Peloton leaderboard name.", required=False)
    peloton_total_workouts = serializers.IntegerField(help_text="Total Peloton workouts completed.", required=False)
    peloton_total_output = serializers.IntegerField(help_text="Total output in kilojoules from Peloton workouts.", required=False)
    peloton_total_distance = serializers.FloatField(help_text="Total distance in miles from Peloton workouts.", required=False)
    peloton_total_calories = serializers.IntegerField(help_text="Total calories burned from Peloton workouts.", required=False)
    peloton_total_pedaling_duration = serializers.IntegerField(help_text="Total pedaling duration in seconds.", required=False)
    peloton_last_synced_at = serializers.DateTimeField(help_text="Last time Peloton data was synced.", required=False)
    class Meta:
        model = Profile
        fields = '__all__'


class WeightEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for WeightEntry, representing a user's weight log entry.
    """
    weight = serializers.FloatField(help_text="Weight value in pounds.")
    recorded_date = serializers.DateField(help_text="Date the weight was recorded.")
    class Meta:
        model = WeightEntry
        fields = '__all__'


class FTPEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for FTPEntry, representing a user's FTP (Functional Threshold Power) entry.
    """
    ftp_value = serializers.FloatField(help_text="FTP value in watts.")
    recorded_date = serializers.DateField(help_text="Date the FTP was recorded.")
    is_active = serializers.BooleanField(help_text="Whether this FTP entry is currently active.")
    class Meta:
        model = FTPEntry
        fields = '__all__'


class PaceEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for PaceEntry, representing a user's running or walking pace entry.
    """
    activity_type = serializers.CharField(help_text="Type of activity (running or walking).")
    pace_value = serializers.CharField(help_text="Pace value (e.g., min/mile or min/km).")
    recorded_date = serializers.DateField(help_text="Date the pace was recorded.")
    class Meta:
        model = PaceEntry
        fields = '__all__'
