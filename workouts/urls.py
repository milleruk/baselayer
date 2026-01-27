from django.urls import path
from .views import workout_history, workout_detail, sync_workouts, connect, sync_status, class_library, class_detail, pace_zones_reference

app_name = "workouts"

urlpatterns = [
    path("", workout_history, name="history"),
    path("library/", class_library, name="library"),
    path("library/<int:pk>/", class_detail, name="class_detail"),
    path("<int:pk>/", workout_detail, name="detail"),
    path("sync/", sync_workouts, name="sync"),
    path("sync/status/", sync_status, name="sync_status"),
    path("connect/", connect, name="connect"),
    path("pace-zones/", pace_zones_reference, name="pace_zones_reference"),
]
