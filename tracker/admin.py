from django.contrib import admin
from .models import DailyPlanItem, WeeklyPlan

admin.site.register(WeeklyPlan)
admin.site.register(DailyPlanItem)
