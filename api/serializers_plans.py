from rest_framework import serializers
from plans.models import Exercise

class ExerciseSerializer(serializers.ModelSerializer):
    """
    Serializer for Exercise model, representing a single exercise (e.g., yoga, pilates, breathwork, mobility).
    """
    name = serializers.CharField(help_text="Name of the exercise.")
    category = serializers.CharField(help_text="Category of the exercise (yoga, pilates, breathwork, mobility).")
    position = serializers.CharField(help_text="Position or body part focus.", required=False)
    key_cue = serializers.CharField(help_text="Key cue or instruction for the exercise.")
    reps_hold = serializers.CharField(help_text="Repetitions or hold duration.")
    primary_use = serializers.CharField(help_text="Primary use or benefit.", required=False)
    video_url = serializers.URLField(help_text="Optional video URL for the exercise.", required=False)
    image = serializers.ImageField(help_text="Image showing the exercise.", required=False)

    class Meta:
        model = Exercise
        fields = '__all__'
