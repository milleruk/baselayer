from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import WeeklyPlan, DailyPlanItem, Challenge, ChallengeInstance, ChallengeWorkoutAssignment, ChallengeBonusWorkout

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("name", "challenge_type", "start_date", "end_date", "signup_deadline", "is_active", "is_visible", "can_signup", "duration_weeks")
    list_filter = ("is_active", "is_visible", "challenge_type", "start_date", "end_date")
    search_fields = ("name", "description", "categories")
    date_hierarchy = "start_date"
    filter_horizontal = ("available_templates",)  # Better UX for ManyToMany field
    fieldsets = (
        (None, {
            "fields": ("name", "description")
        }),
        ("Visibility & Status", {
            "fields": ("is_active", "is_visible")
        }),
        ("Challenge Details", {
            "fields": ("challenge_type", "categories", "image")
        }),
        ("Time Period", {
            "fields": ("start_date", "end_date", "signup_opens_date", "signup_deadline"),
            "description": "Challenge runs from start_date to end_date. Challenges cannot overlap. Signup opens date (optional) controls when users can start signing up. Signup deadline (optional) controls when signup closes."
        }),
        ("Plan Templates", {
            "fields": ("available_templates", "default_template"),
            "description": "Select which plan templates are available for this challenge. Users will choose from these when joining. The default template will be marked as recommended."
        }),
    )
    
    def can_signup(self, obj):
        return obj.can_signup
    can_signup.boolean = True
    can_signup.short_description = "Can Signup"
    
    def save_model(self, request, obj, form, change):
        """Override save_model to ensure clean() is called and validate default_template"""
        try:
            obj.full_clean()
            super().save_model(request, obj, form, change)
            
            # After saving, validate that default_template is in available_templates
            if obj.default_template and obj.available_templates.exists():
                if obj.default_template not in obj.available_templates.all():
                    from django.contrib import messages
                    messages.warning(
                        request,
                        f"Default template '{obj.default_template.name}' is not in the available templates list. "
                        f"It has been cleared. Please select a default template from the available templates."
                    )
                    obj.default_template = None
                    obj.save(update_fields=['default_template'])
        except ValidationError as e:
            # Display validation errors in admin
            from django.contrib import messages
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            raise

@admin.register(ChallengeInstance)
class ChallengeInstanceAdmin(admin.ModelAdmin):
    list_display = ("user", "challenge", "started_at", "completed_at", "is_active", "total_points")
    list_filter = ("is_active", "challenge", "started_at", "completed_at")
    search_fields = ("user__username", "challenge__name")
    readonly_fields = ("total_points", "completion_rate")

admin.site.register(WeeklyPlan)
admin.site.register(DailyPlanItem)

@admin.register(ChallengeWorkoutAssignment)
class ChallengeWorkoutAssignmentAdmin(admin.ModelAdmin):
    list_display = ("challenge", "template", "week_number", "get_day_of_week_display", "get_activity_type_display", "workout_title", "peloton_url")
    list_filter = ("challenge", "template", "week_number", "activity_type")
    search_fields = ("challenge__name", "template__name", "workout_title", "peloton_url")
    ordering = ("challenge", "template", "week_number", "day_of_week", "activity_type")

@admin.register(ChallengeBonusWorkout)
class ChallengeBonusWorkoutAdmin(admin.ModelAdmin):
    list_display = ("challenge", "week_number", "get_activity_type_display", "workout_title", "peloton_url", "points")
    list_filter = ("challenge", "week_number", "activity_type")
    search_fields = ("challenge__name", "workout_title", "peloton_url")
    ordering = ("challenge", "week_number")
