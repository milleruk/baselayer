from rest_framework import serializers
from plans.models import PlanTemplate, PlanTemplateDay


class PlanTemplateDaySerializer(serializers.ModelSerializer):
    """
    Serializer for PlanTemplateDay, representing a day in a weekly plan template.
    """
    day_of_week = serializers.IntegerField(help_text="Day of the week (0=Sun, 1=Mon, ... 6=Sat).")
    peloton_focus = serializers.CharField(help_text="Peloton focus for the day (e.g., 'PZE (Z2)', 'Run Tempo').")
    notes = serializers.CharField(help_text="Optional notes for the day.", required=False)
    class Meta:
        model = PlanTemplateDay
        fields = '__all__'

class PlanTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for PlanTemplate, a reusable weekly structure for plans.
    """
    name = serializers.CharField(help_text="Name of the plan template.")
    description = serializers.CharField(help_text="Description of the template.", required=False)
    days = PlanTemplateDaySerializer(many=True, read_only=True, help_text="List of days in the template.")
    class Meta:
        model = PlanTemplate
        fields = '__all__'
