from django.urls import path
from .views import landing, dashboard, exercise_list, guide, metrics, privacy_policy, terms_and_conditions, features, about, faq, contact, how_it_works, recap, recap_share, recap_share_manage, recap_regenerate, eddington

app_name = "plans"

urlpatterns = [
    path("", landing, name="landing"),
    path("dashboard/", dashboard, name="dashboard"),
    path("exercises/", exercise_list, name="exercise_list"),
    path("guide/", guide, name="guide"),
    path("features/", features, name="features"),
    path("about/", about, name="about"),
    path("how-it-works/", how_it_works, name="how_it_works"),
    path("faq/", faq, name="faq"),
    path("contact/", contact, name="contact"),
    path("metrics/", metrics, name="metrics"),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("terms-and-conditions/", terms_and_conditions, name="terms_and_conditions"),
    path("recap/", recap, name="recap"),
    path("recap/regenerate/", recap_regenerate, name="recap_regenerate"),
    path("recap/share/<str:token>/", recap_share, name="recap_share"),
    path("recap/share/manage/", recap_share_manage, name="recap_share_manage"),
    path("eddington/", eddington, name="eddington"),
]
