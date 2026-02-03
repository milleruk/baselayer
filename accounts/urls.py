from django.urls import path
from django.contrib.auth import views as auth_views
from .views import register, profile, delete_weight_entry, delete_ftp_entry, toggle_ftp_active, delete_pace_entry, toggle_pace_active, create_pace_level, delete_pace_level, CustomLoginView, account_inactive
from .wizard_views import (
    wizard_redirect, wizard_stage_1, wizard_stage_2, wizard_stage_3, wizard_stage_4,
    wizard_stage_4_backdated_ftp, wizard_stage_4_backdated_pace,
    wizard_stage_5, wizard_stage_5_backdated, wizard_stage_6, wizard_restart
)

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    # Logout is handled by allauth at /accounts/logout/
    path("account-inactive/", account_inactive, name="account_inactive"),
    path("profile/", profile, name="profile"),
    path("profile/weight/<int:entry_id>/delete/", delete_weight_entry, name="delete_weight_entry"),
    path("profile/ftp/<int:entry_id>/delete/", delete_ftp_entry, name="delete_ftp_entry"),
    path("profile/ftp/<int:entry_id>/toggle/", toggle_ftp_active, name="toggle_ftp_active"),
    path("profile/pace/<int:entry_id>/delete/", delete_pace_entry, name="delete_pace_entry"),
    path("profile/pace/<int:entry_id>/toggle/", toggle_pace_active, name="toggle_pace_active"),
    path("profile/pace-level/create/", create_pace_level, name="create_pace_level"),
    path("profile/pace-level/<int:level_id>/delete/", delete_pace_level, name="delete_pace_level"),
    
    # Onboarding wizard
    path("wizard/", wizard_redirect, name="wizard_redirect"),
    path("wizard/stage-1/", wizard_stage_1, name="wizard_stage_1"),
    path("wizard/stage-2/", wizard_stage_2, name="wizard_stage_2"),
    path("wizard/stage-3/", wizard_stage_3, name="wizard_stage_3"),
    path("wizard/stage-4/", wizard_stage_4, name="wizard_stage_4"),
    path("wizard/stage-4/backdated-ftp/", wizard_stage_4_backdated_ftp, name="wizard_stage_4_backdated_ftp"),
    path("wizard/stage-4/backdated-pace/", wizard_stage_4_backdated_pace, name="wizard_stage_4_backdated_pace"),
    path("wizard/stage-5/", wizard_stage_5, name="wizard_stage_5"),
    path("wizard/stage-5/backdated/", wizard_stage_5_backdated, name="wizard_stage_5_backdated"),
    path("wizard/stage-6/", wizard_stage_6, name="wizard_stage_6"),
    path("wizard/restart/", wizard_restart, name="wizard_restart"),
]

