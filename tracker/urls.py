from django.urls import path
from .views import weekly_plans, generate, plan_detail, toggle_done, edit_item, delete_plan, toggle_activity

app_name = "tracker"

urlpatterns = [
    path("", weekly_plans, name="weekly_plans"),
    path("generate/", generate, name="generate"),
    path("<int:pk>/", plan_detail, name="plan_detail"),
    path("<int:pk>/delete/", delete_plan, name="delete_plan"),
    path("item/<int:pk>/toggle/", toggle_done, name="toggle_done"),
    path("item/<int:pk>/toggle-activity/<str:activity>/", toggle_activity, name="toggle_activity"),
    path("item/<int:pk>/edit/", edit_item, name="edit_item"),
]
