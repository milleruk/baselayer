from django.urls import path

from .views import index, suggest

app_name = "recommender"

urlpatterns = [
    path("", index, name="index"),
    path("suggest/", suggest, name="suggest"),
]

