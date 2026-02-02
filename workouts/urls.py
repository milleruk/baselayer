from django.urls import path
from .views import (
    workout_history,
    workout_history_suggest,
    workout_detail,
    sync_workouts,
    connect,
    sync_status,
)

app_name = "workouts"

urlpatterns = [
    path("", workout_history, name="history"),
    path("history/suggest/", workout_history_suggest, name="history_suggest"),
    path("<int:pk>/", workout_detail, name="detail"),
    path("sync/", sync_workouts, name="sync"),
    path("sync/status/", sync_status, name="sync_status"),
    path("connect/", connect, name="connect"),
]
