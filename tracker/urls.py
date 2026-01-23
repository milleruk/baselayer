from django.urls import path
from .views import weekly_plans, generate, plan_detail, challenge_detail, toggle_done, edit_item, complete_challenge, leave_challenge, join_challenge, challenges_list, delete_plan, toggle_activity, select_challenge_template
from .admin_views import admin_challenges_list, admin_challenge_create, admin_challenge_edit, admin_challenge_delete, admin_assign_workouts

app_name = "tracker"

urlpatterns = [
    path("", weekly_plans, name="weekly_plans"),
    path("challenges/", challenges_list, name="challenges_list"),
    path("challenges/<int:challenge_id>/week/<int:week_number>/", challenge_detail, name="challenge_detail_week"),
    path("challenges/<int:challenge_id>/", challenge_detail, name="challenge_detail"),
    path("challenge/<int:challenge_id>/select-template/", select_challenge_template, name="select_challenge_template"),
    path("challenge/<int:challenge_id>/join/", join_challenge, name="join_challenge"),
    path("generate/", generate, name="generate"),
    path("<int:pk>/", plan_detail, name="plan_detail"),
    path("<int:pk>/delete/", delete_plan, name="delete_plan"),
    path("item/<int:pk>/toggle/", toggle_done, name="toggle_done"),
    path("item/<int:pk>/toggle-activity/<str:activity>/", toggle_activity, name="toggle_activity"),
    path("item/<int:pk>/edit/", edit_item, name="edit_item"),
    path("challenge/<int:challenge_instance_id>/complete/", complete_challenge, name="complete_challenge"),
    path("challenge/<int:challenge_instance_id>/leave/", leave_challenge, name="leave_challenge"),
    # Admin routes
    path("admin/challenges/", admin_challenges_list, name="admin_challenges_list"),
    path("admin/challenges/create/", admin_challenge_create, name="admin_challenge_create"),
    path("admin/challenges/<int:challenge_id>/edit/", admin_challenge_edit, name="admin_challenge_edit"),
    path("admin/challenges/<int:challenge_id>/delete/", admin_challenge_delete, name="admin_challenge_delete"),
    path("admin/challenges/<int:challenge_id>/assign-workouts/", admin_assign_workouts, name="admin_assign_workouts"),
]
