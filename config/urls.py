from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("plans.urls")),
    path("instructor-recommender/", include("recommender.urls")),
    path("tracker/", include("tracker.urls")),
    path("challenges/", include("challenges.urls")),
    path("workouts/", include("workouts.urls")),
    path("peloton/", include("peloton.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
