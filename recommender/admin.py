from django.contrib import admin

from .models import InstructorProfile


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ("instructor", "enabled", "updated_at")
    list_filter = ("enabled",)
    search_fields = ("instructor__name", "vibe")

