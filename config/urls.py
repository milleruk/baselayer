from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views import defaults as default_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),  # django-allauth
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),  # Dashboard and core views
    path("plans/", include("plans.urls")),
    path("instructor-recommender/", include("recommender.urls")),
    path("annual-challenge/", include("annual_challenge.urls")),
    path("tracker/", include("tracker.urls")),
    path("challenges/", include("challenges.urls")),
    path("classes/", include("classes.urls")),  # Class library/catalog
    path("workouts/", include("workouts.urls")),  # Workout history & tracking
    path("peloton/", include("peloton.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler403 = default_views.permission_denied
