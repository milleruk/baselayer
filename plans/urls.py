from django.urls import path
from .views import landing, dashboard, exercise_list, guide, metrics

app_name = "plans"

urlpatterns = [
    path("", landing, name="landing"),
    path("dashboard/", dashboard, name="dashboard"),
    path("exercises/", exercise_list, name="exercise_list"),
    path("guide/", guide, name="guide"),
    path("metrics/", metrics, name="metrics"),
]
