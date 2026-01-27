from django.contrib import admin
from .models import Exercise, PlanTemplate, PlanTemplateDay, RecapShare, RecapCache

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

@admin.register(RecapCache)
class RecapCacheAdmin(admin.ModelAdmin):
    list_display = ['user', 'year', 'total_workouts_count', 'last_regenerated_at', 'updated_at', 'created_at']
    list_filter = ['year', 'created_at', 'updated_at', 'last_regenerated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']
    
    fieldsets = (
        ('Cache Information', {
            'fields': ('user', 'year', 'total_workouts_count')
        }),
        ('Metadata', {
            'fields': ('last_workout_updated_at', 'last_regenerated_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['invalidate_cache']
    
    def invalidate_cache(self, request, queryset):
        """Invalidate selected caches by deleting them"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Successfully invalidated {count} cache(s).")
    invalidate_cache.short_description = "Invalidate selected caches"
