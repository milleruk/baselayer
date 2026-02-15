from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MetricsAPIView
from .views_accounts import ProfileViewSet, WeightEntryViewSet, FTPEntryViewSet, PaceEntryViewSet
from .views_workouts import WorkoutViewSet, WorkoutDetailsViewSet, WorkoutPerformanceDataViewSet
from .views_classes import RideDetailViewSet
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

router = DefaultRouter()
router.register(r'profile', ProfileViewSet, basename='profile')
router.register(r'weight-entries', WeightEntryViewSet, basename='weightentry')
router.register(r'ftp-entries', FTPEntryViewSet, basename='ftpentry')
router.register(r'pace-entries', PaceEntryViewSet, basename='paceentry')
# Workouts
router.register(r'workouts', WorkoutViewSet, basename='workout')
router.register(r'workout-details', WorkoutDetailsViewSet, basename='workoutdetails')
router.register(r'workout-performance', WorkoutPerformanceDataViewSet, basename='workoutperformance')
# Class Library
router.register(r'classes', RideDetailViewSet, basename='ridedetail')

# Plans
from .views_plans import ExerciseViewSet
router.register(r'exercises', ExerciseViewSet, basename='exercise')

# Plan Templates
from .views_plan_templates import PlanTemplateViewSet, PlanTemplateDayViewSet
router.register(r'plan-templates', PlanTemplateViewSet, basename='plantemplate')
router.register(r'plan-template-days', PlanTemplateDayViewSet, basename='plantemplateday')

# Challenges (admin-defined)
from .views_challenge import ChallengeViewSet
router.register(r'challenges-admin', ChallengeViewSet, basename='challenge')

# Recap/Analytics
from .views_recap import RecapShareViewSet, RecapCacheViewSet
router.register(r'recap-shares', RecapShareViewSet, basename='recapshare')
router.register(r'recap-caches', RecapCacheViewSet, basename='recapcache')

# Workout Metadata
from .views_workout_meta import ClassTypeViewSet, WorkoutTypeViewSet, InstructorViewSet
router.register(r'class-types', ClassTypeViewSet, basename='classtype')
router.register(r'workout-types', WorkoutTypeViewSet, basename='workouttype')
router.register(r'instructors', InstructorViewSet, basename='instructor')

# Core/Site Settings
from .views_core import SiteSettingsViewSet, RideSyncQueueViewSet
router.register(r'site-settings', SiteSettingsViewSet, basename='sitesettings')
router.register(r'ride-sync-queue', RideSyncQueueViewSet, basename='ridesyncqueue')

# Challenges
from .views_challenges import ChallengeInstanceViewSet
router.register(r'challenges', ChallengeInstanceViewSet, basename='challengeinstance')

    # PelotonWorkoutViewSet removed: PelotonWorkout model does not exist

urlpatterns = [
    path('', include(router.urls)),
    path('metrics/', MetricsAPIView.as_view(), name='api-metrics'),
    path('dashboard-stats/', __import__('api.views_dashboard').views_dashboard.DashboardStatsAPIView.as_view(), name='api-dashboard-stats'),
    path('peloton-status/', __import__('api.views_peloton_api').views_peloton_api.PelotonStatusAPIView.as_view(), name='api-peloton-status'),
    path('peloton-connect/', __import__('api.views_peloton_connect').views_peloton_connect.PelotonConnectAPIView.as_view(), name='api-peloton-connect'),
    path('peloton-disconnect/', __import__('api.views_peloton_connect').views_peloton_connect.PelotonDisconnectAPIView.as_view(), name='api-peloton-disconnect'),
    path('peloton-sync/', __import__('api.views_peloton_sync').views_peloton_sync.PelotonSyncAPIView.as_view(), name='api-peloton-sync'),
    path('schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),
]
