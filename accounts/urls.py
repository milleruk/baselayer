from django.urls import path
from django.contrib.auth import views as auth_views
from .views import register, profile, delete_weight_entry

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", profile, name="profile"),
    path("profile/weight/<int:entry_id>/delete/", delete_weight_entry, name="delete_weight_entry"),
]
