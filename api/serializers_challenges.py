from rest_framework import serializers
from challenges.models import ChallengeInstance


class ChallengeInstanceSerializer(serializers.ModelSerializer):
    """
    Serializer for ChallengeInstance, representing a user's participation in a challenge.
    """
    # Add help_text for key fields as needed
    class Meta:
        model = ChallengeInstance
        fields = '__all__'
