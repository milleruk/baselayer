from django.contrib import admin
from .models import Exercise, PlanTemplate, PlanTemplateDay, RecapShare

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

@admin.register(RecapShare)
class RecapShareAdmin(admin.ModelAdmin):
    list_display = ['user', 'year', 'is_enabled', 'view_count', 'created_at', 'last_viewed_at']
    list_filter = ['year', 'is_enabled', 'created_at']
    search_fields = ['user__username', 'user__email', 'token']
    readonly_fields = ['token', 'created_at', 'updated_at', 'view_count', 'last_viewed_at']
    raw_id_fields = ['user']
    
    fieldsets = (
        ('Share Information', {
            'fields': ('user', 'year', 'token')
        }),
        ('Status', {
            'fields': ('is_enabled', 'view_count', 'last_viewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
