from django.contrib import admin
from .models import Challenge, ChallengeInstance, ChallengeWorkoutAssignment, ChallengeBonusWorkout, ChallengeWeekUnlock

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "is_active", "is_visible", "challenge_type"]
    list_filter = ["is_active", "is_visible", "challenge_type", "start_date"]
    search_fields = ["name", "description"]
    filter_horizontal = ["available_templates"]
    date_hierarchy = "start_date"

@admin.register(ChallengeInstance)
class ChallengeInstanceAdmin(admin.ModelAdmin):
    list_display = ["user", "challenge", "started_at", "is_active", "completed_at"]
    list_filter = ["is_active", "challenge", "started_at"]
    search_fields = ["user__username", "user__email", "challenge__name"]
    date_hierarchy = "started_at"

@admin.register(ChallengeWorkoutAssignment)
class ChallengeWorkoutAssignmentAdmin(admin.ModelAdmin):
    list_display = ["challenge", "template", "week_number", "day_of_week", "activity_type", "points"]
    list_filter = ["challenge", "template", "week_number", "activity_type"]
    search_fields = ["challenge__name", "template__name", "workout_title"]

@admin.register(ChallengeBonusWorkout)
class ChallengeBonusWorkoutAdmin(admin.ModelAdmin):
    list_display = ["challenge", "week_number", "activity_type", "points"]
    list_filter = ["challenge", "week_number", "activity_type"]
    search_fields = ["challenge__name", "workout_title"]

@admin.register(ChallengeWeekUnlock)
class ChallengeWeekUnlockAdmin(admin.ModelAdmin):
    list_display = ["challenge", "week_number", "is_unlocked", "unlock_date"]
    list_filter = ["challenge", "is_unlocked", "unlock_date"]
    search_fields = ["challenge__name"]
