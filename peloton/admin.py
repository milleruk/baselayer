from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import PelotonConnection


@admin.register(PelotonConnection)
class PelotonConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'peloton_user_id', 'is_active', 'workout_count', 'last_sync_at', 'created_at', 'view_workouts_link')
    list_filter = ('is_active', 'created_at', 'last_sync_at')
    search_fields = ('user__email', 'user__username', 'peloton_user_id')
    readonly_fields = ('created_at', 'updated_at', 'last_sync_at', 'workout_count_display', 'view_workouts_link', 'reset_sync_button')
    raw_id_fields = ('user',)
    actions = ['reset_last_sync']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Peloton Account', {
            'fields': ('peloton_user_id', 'is_active')
        }),
        ('Sync Statistics', {
            'fields': ('workout_count_display', 'last_sync_at', 'reset_sync_button', 'view_workouts_link'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def workout_count(self, obj):
        """Display number of synced workouts for this user"""
        from workouts.models import Workout
        count = Workout.objects.filter(user=obj.user, peloton_workout_id__isnull=False).count()
        return count
    workout_count.short_description = 'Workouts'
    
    def workout_count_display(self, obj):
        """Display workout count in detail view"""
        from workouts.models import Workout
        count = Workout.objects.filter(user=obj.user, peloton_workout_id__isnull=False).count()
        if count > 0:
            return f'{count} workouts synced'
        return 'No workouts synced yet'
    workout_count_display.short_description = 'Synced Workouts'
    
    def view_workouts_link(self, obj):
        """Link to view user's workouts in admin"""
        from workouts.models import Workout
        count = Workout.objects.filter(user=obj.user, peloton_workout_id__isnull=False).count()
        if count > 0:
            url = reverse('admin:workouts_workout_changelist') + f'?user__id__exact={obj.user.id}'
            return format_html('<a href="{}">View {} workouts →</a>', url, count)
        return '—'
    view_workouts_link.short_description = 'View Workouts'
    
    def reset_sync_button(self, obj):
        """Button to reset last sync time"""
        if obj.pk:
            url = reverse('admin:peloton_pelotonconnection_reset_sync', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" onclick="return confirm(\'This will reset the last sync time. '
                'After deleting workouts, the user can do a full re-sync. Continue?\');">Reset Last Sync</a>',
                url
            )
        return '—'
    reset_sync_button.short_description = 'Reset Sync'
    
    def reset_last_sync(self, request, queryset):
        """Admin action to reset last_sync_at for selected connections"""
        count = queryset.update(last_sync_at=None)
        self.message_user(
            request,
            f'Successfully reset last sync time for {count} connection(s). Users can now do a full re-sync.',
            messages.SUCCESS
        )
    reset_last_sync.short_description = 'Reset last sync time for selected connections'
    
    def get_urls(self):
        """Add custom URL for reset sync action"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/reset-sync/',
                self.admin_site.admin_view(self.reset_sync_view),
                name='peloton_pelotonconnection_reset_sync',
            ),
        ]
        return custom_urls + urls
    
    def reset_sync_view(self, request, object_id):
        """View to reset last sync time for a single connection"""
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponseRedirect
        
        connection = get_object_or_404(PelotonConnection, pk=object_id)
        connection.last_sync_at = None
        connection.save()
        
        self.message_user(
            request,
            f'Successfully reset last sync time for {connection.user.email}. User can now do a full re-sync.',
            messages.SUCCESS
        )
        
        return HttpResponseRedirect(
            reverse('admin:peloton_pelotonconnection_change', args=[object_id])
        )
