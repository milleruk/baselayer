from django.contrib import admin
from .models import Exercise, PlanTemplate, PlanTemplateDay

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'position', 'primary_use']
    list_filter = ['category']
    search_fields = ['name', 'key_cue', 'primary_use']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'image')
        }),
        ('Exercise Details', {
            'fields': ('position', 'reps_hold', 'primary_use', 'key_cue')
        }),
        ('Media', {
            'fields': ('video_url',)
        }),
    )

admin.site.register(PlanTemplate)
admin.site.register(PlanTemplateDay)
