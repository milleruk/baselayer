from django.urls import path
from .views import workout_history, workout_detail, sync_workouts, connect

app_name = "workouts"

urlpatterns = [
    path("", workout_history, name="history"),
    path("<int:pk>/", workout_detail, name="detail"),
    path("sync/", sync_workouts, name="sync"),
    path("connect/", connect, name="connect"),
]
