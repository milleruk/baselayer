from django.urls import path

from .views import index

app_name = "annual_challenge"

urlpatterns = [
    path("", index, name="index"),
]

