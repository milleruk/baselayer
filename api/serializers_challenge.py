from rest_framework import serializers
from challenges.models import Challenge

class ChallengeSerializer(serializers.ModelSerializer):
    """
    Serializer for Challenge, representing an admin-defined challenge (team, mini, individual).
    """
    name = serializers.CharField(help_text="Name of the challenge.")
    description = serializers.CharField(help_text="Description of the challenge.", required=False)
    start_date = serializers.DateField(help_text="Challenge start date.")
    end_date = serializers.DateField(help_text="Challenge end date.")
    challenge_type = serializers.CharField(help_text="Type of challenge (team, mini, individual).")
    categories = serializers.CharField(help_text="Comma-separated categories (cycling, running, strength, yoga).", required=False)
    image = serializers.ImageField(help_text="Challenge logo/image.", required=False)
    class Meta:
        model = Challenge
        fields = '__all__'
