from django.urls import path
from .views import class_library, class_detail

app_name = "classes"

urlpatterns = [
    path("", class_library, name="library"),
    path("<int:pk>/", class_detail, name="detail"),
]
