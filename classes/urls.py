from django.urls import path
from .views import class_library, class_detail
from workouts.admin_views import admin_library

app_name = "classes"

urlpatterns = [
    path("", class_library, name="library"),
    path("<int:pk>/", class_detail, name="detail"),
    path("admin/", admin_library, name="admin"),
]
