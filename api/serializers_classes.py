from rest_framework import serializers
from workouts.models import RideDetail


class RideDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for RideDetail, representing a Peloton ride/class detail.
    """
    # Add help_text for key fields as needed
    class Meta:
        model = RideDetail
        fields = '__all__'
