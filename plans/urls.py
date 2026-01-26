from django.urls import path
from .views import landing, dashboard, exercise_list, guide, metrics, privacy_policy, terms_and_conditions

app_name = "plans"

urlpatterns = [
    path("", landing, name="landing"),
    path("dashboard/", dashboard, name="dashboard"),
    path("exercises/", exercise_list, name="exercise_list"),
    path("guide/", guide, name="guide"),
    path("metrics/", metrics, name="metrics"),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("terms-and-conditions/", terms_and_conditions, name="terms_and_conditions"),
]
