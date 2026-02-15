from rest_framework import serializers

class MetricsSerializer(serializers.Serializer):
    """
    Serializer for user metrics summary.
    Returns challenge completion, weight, points, power-to-weight, and time-in-zone stats.
    """
    fully_completed_challenges = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of challenge IDs fully completed by the user."
    )
    partially_completed_challenges = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of challenge IDs partially completed by the user."
    )
    current_weight = serializers.FloatField(
        allow_null=True,
        help_text="User's most recent weight in pounds (or null if not available)."
    )
    total_points = serializers.IntegerField(
        help_text="Total points earned by the user across all plans."
    )
    current_cycling_pw = serializers.FloatField(
        allow_null=True,
        help_text="Current cycling power-to-weight ratio (FTP/kg) or null if not available."
    )
    cycling_zones_all = serializers.DictField(
        help_text="Time spent in each cycling power zone (all time)."
    )
    cycling_zones_month = serializers.DictField(
        help_text="Time spent in each cycling power zone (this month)."
    )
    cycling_zones_year = serializers.DictField(
        help_text="Time spent in each cycling power zone (this year)."
    )
    running_zones_all = serializers.DictField(
        help_text="Time spent in each running intensity zone (all time)."
    )
    running_zones_month = serializers.DictField(
        help_text="Time spent in each running intensity zone (this month)."
    )
    running_zones_year = serializers.DictField(
        help_text="Time spent in each running intensity zone (this year)."
    )
