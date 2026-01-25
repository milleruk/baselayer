from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import PelotonConnection


@admin.register(PelotonConnection)
class PelotonConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'peloton_user_id', 'is_active', 'workout_count', 'last_sync_at', 'created_at', 'view_workouts_link')
    list_filter = ('is_active', 'created_at', 'last_sync_at')
    search_fields = ('user__email', 'user__username', 'peloton_user_id')
    readonly_fields = ('created_at', 'updated_at', 'last_sync_at', 'workout_count_display', 'view_workouts_link')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Peloton Account', {
            'fields': ('peloton_user_id', 'is_active')
        }),
        ('Sync Statistics', {
            'fields': ('workout_count_display', 'last_sync_at', 'view_workouts_link'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def workout_count(self, obj):
        """Display number of synced workouts for this user"""
        from workouts.models import Workout
        count = Workout.objects.filter(user=obj.user, peloton_id__isnull=False).count()
        return count
    workout_count.short_description = 'Workouts'
    
    def workout_count_display(self, obj):
        """Display workout count in detail view"""
        from workouts.models import Workout
        count = Workout.objects.filter(user=obj.user, peloton_id__isnull=False).count()
        if count > 0:
            return f'{count} workouts synced'
        return 'No workouts synced yet'
    workout_count_display.short_description = 'Synced Workouts'
    
    def view_workouts_link(self, obj):
        """Link to view user's workouts in admin"""
        from workouts.models import Workout
        count = Workout.objects.filter(user=obj.user, peloton_id__isnull=False).count()
        if count > 0:
            url = reverse('admin:workouts_workout_changelist') + f'?user__id__exact={obj.user.id}'
            return format_html('<a href="{}">View {} workouts →</a>', url, count)
        return '—'
    view_workouts_link.short_description = 'View Workouts'
