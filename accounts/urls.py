from django.urls import path
from django.contrib.auth import views as auth_views
from .views import register, profile, delete_weight_entry, delete_ftp_entry, toggle_ftp_active, delete_pace_entry, toggle_pace_active, create_pace_level, delete_pace_level, CustomLoginView, account_inactive

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("account-inactive/", account_inactive, name="account_inactive"),
    path("profile/", profile, name="profile"),
    path("profile/weight/<int:entry_id>/delete/", delete_weight_entry, name="delete_weight_entry"),
    path("profile/ftp/<int:entry_id>/delete/", delete_ftp_entry, name="delete_ftp_entry"),
    path("profile/ftp/<int:entry_id>/toggle/", toggle_ftp_active, name="toggle_ftp_active"),
    path("profile/pace/<int:entry_id>/delete/", delete_pace_entry, name="delete_pace_entry"),
    path("profile/pace/<int:entry_id>/toggle/", toggle_pace_active, name="toggle_pace_active"),
    path("profile/pace-level/create/", create_pace_level, name="create_pace_level"),
    path("profile/pace-level/<int:level_id>/delete/", delete_pace_level, name="delete_pace_level"),
]
