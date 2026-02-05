from django.contrib import admin

from .models import AnnualChallengeProgress


@admin.register(AnnualChallengeProgress)
class AnnualChallengeProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "challenge_id",
        "minutes_ytd",
        "has_joined",
        "challenge_status",
        "last_synced_at",
        "updated_at",
    )
    list_filter = ("has_joined", "challenge_status", "challenge_id")
    search_fields = ("user__email", "challenge_id")
    readonly_fields = ("updated_at",)
