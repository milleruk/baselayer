from django.urls import path
from .views import challenges_list, select_challenge_template, join_challenge, complete_challenge, leave_challenge, challenge_detail, hide_completed_challenge, retake_challenge
from .admin_views import admin_challenges_list, admin_challenge_create, admin_challenge_edit, admin_challenge_delete, admin_assign_workouts

app_name = "challenges"

urlpatterns = [
    # Public challenge views
    path("", challenges_list, name="challenges_list"),
    path("<int:challenge_id>/week/<int:week_number>/", challenge_detail, name="challenge_detail_week"),
    path("<int:challenge_id>/", challenge_detail, name="challenge_detail"),
    path("<int:challenge_id>/select-template/", select_challenge_template, name="select_challenge_template"),
    path("<int:challenge_id>/join/", join_challenge, name="join_challenge"),
    path("instance/<int:challenge_instance_id>/complete/", complete_challenge, name="complete_challenge"),
    path("instance/<int:challenge_instance_id>/leave/", leave_challenge, name="leave_challenge"),
    path("instance/<int:challenge_instance_id>/hide/", hide_completed_challenge, name="hide_completed_challenge"),
    path("<int:challenge_id>/retake/", retake_challenge, name="retake_challenge"),
    # Admin routes
    path("admin/", admin_challenges_list, name="admin_challenges_list"),
    path("admin/create/", admin_challenge_create, name="admin_challenge_create"),
    path("admin/<int:challenge_id>/edit/", admin_challenge_edit, name="admin_challenge_edit"),
    path("admin/<int:challenge_id>/delete/", admin_challenge_delete, name="admin_challenge_delete"),
    path("admin/<int:challenge_id>/assign-workouts/", admin_assign_workouts, name="admin_assign_workouts"),
]
