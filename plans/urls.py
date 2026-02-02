from django.urls import path
from .views import exercise_list, guide, metrics, recap, recap_share, recap_share_manage, recap_regenerate, eddington, pace_zones_reference

app_name = "plans"

urlpatterns = [
    path("exercises/", exercise_list, name="exercise_list"),
    path("guide/", guide, name="guide"),
    path("guide/pace-zones/", pace_zones_reference, name="pace_zones_reference"),
    path("metrics/", metrics, name="metrics"),
    path("recap/", recap, name="recap"),
    path("recap/regenerate/", recap_regenerate, name="recap_regenerate"),
    path("recap/share/<str:token>/", recap_share, name="recap_share"),
    path("recap/share/manage/", recap_share_manage, name="recap_share_manage"),
    path("eddington/", eddington, name="eddington"),
]
