from rest_framework import viewsets
from plans.models import PlanTemplate, PlanTemplateDay
from api.serializers_plan_templates import PlanTemplateSerializer, PlanTemplateDaySerializer


class PlanTemplateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing plan templates (weekly structures).
    """
    queryset = PlanTemplate.objects.all()
    serializer_class = PlanTemplateSerializer


class PlanTemplateDayViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing plan template days (individual days in a template).
    """
    queryset = PlanTemplateDay.objects.all()
    serializer_class = PlanTemplateDaySerializer
