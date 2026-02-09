from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.conf import settings
from django.utils.safestring import mark_safe
from .models import User, Profile, WeightEntry, FTPEntry, PaceEntry, PaceLevel, OnboardingWizard


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # To re-enable hijack, use:
    # class UserAdmin(HijackUserAdminMixin, BaseUserAdmin):
    """Custom admin for User model"""
    list_display = ['email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'inactive_status']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']  # Show newest users first (likely inactive)
    actions = ['activate_users', 'deactivate_users', 'reset_user_accounts']
    
    def inactive_status(self, obj):
        """Display status badge for inactive users"""
        if not obj.is_active:
            return mark_safe('<span style="color: red; font-weight: bold;">⚠️ Inactive - Requires Activation</span>')
        return mark_safe('<span style="color: green;">✓ Active</span>')
    inactive_status.short_description = 'Status'
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    def activate_users(self, request, queryset):
        """Admin action to activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'Successfully activated {count} user(s).')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Admin action to deactivate selected users"""
        # Don't allow deactivating superusers
        queryset = queryset.exclude(is_superuser=True)
        count = queryset.update(is_active=False)
        self.message_user(request, f'Successfully deactivated {count} user(s).')
    deactivate_users.short_description = 'Deactivate selected users'
    
    def reset_user_accounts(self, request, queryset):
        """Admin action to reset user accounts - clears all profile data and forces re-onboarding"""
        from peloton.models import PelotonConnection
        
        # Don't allow resetting superusers
        queryset = queryset.exclude(is_superuser=True)
        
        reset_count = 0
        for user in queryset:
            # Reset onboarding wizard
            OnboardingWizard.objects.filter(user=user).delete()
            
            # Clear profile data but keep the profile record
            if hasattr(user, 'profile'):
                profile = user.profile
                profile.full_name = ''
                profile.date_of_birth = None
                profile.ftp_score = None
                profile.pace_target_level = None
                profile.peloton_leaderboard_name = ''
                profile.save()
            
            # Delete all performance entries
            WeightEntry.objects.filter(user=user).delete()
            FTPEntry.objects.filter(user=user).delete()
            PaceEntry.objects.filter(user=user).delete()
            
            # Delete custom pace levels (PaceBands will cascade delete automatically)
            PaceLevel.objects.filter(user=user).delete()
            
            # Deactivate Peloton connection (but keep credentials in case they want to reconnect)
            PelotonConnection.objects.filter(user=user).update(
                is_active=False,
                peloton_user_id=None
            )
            
            reset_count += 1
        
        self.message_user(
            request, 
            f'Successfully reset {reset_count} user account(s). They will need to complete the onboarding wizard on next login.'
        )
    reset_user_accounts.short_description = 'Reset user accounts (clear all data, force re-onboarding)'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'date_of_birth', 'peloton_leaderboard_name', 'peloton_total_workouts', 'peloton_current_weekly_streak', 'peloton_total_achievements', 'peloton_last_synced_at']
    search_fields = ['user__email', 'full_name', 'peloton_leaderboard_name']
    list_filter = ['date_of_birth', 'peloton_last_synced_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'full_name', 'date_of_birth')
        }),
        ('Peloton Integration', {
            'fields': (
                'peloton_leaderboard_name',
                'peloton_total_workouts',
                'peloton_total_pedaling_metric_workouts',
                'peloton_total_non_pedaling_metric_workouts',
                'peloton_current_weekly_streak',
                'peloton_best_weekly_streak',
                'peloton_current_daily_streak',
                'peloton_total_achievements',
                'peloton_total_output',
                'peloton_total_distance',
                'peloton_total_calories',
                'peloton_total_pedaling_duration',
                'peloton_last_synced_at',
            ),
            'classes': ('collapse',)
        }),
        ('Fitness Metrics', {
            'fields': ('ftp_score', 'pace_target_level'),
            'classes': ('collapse',)
        }),
    )

@admin.register(WeightEntry)
class WeightEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'weight', 'recorded_date', 'created_at']
    search_fields = ['user__email']
    list_filter = ['recorded_date', 'created_at']
    date_hierarchy = 'recorded_date'
    ordering = ['-recorded_date', '-created_at']


@admin.register(FTPEntry)
class FTPEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'ftp_value', 'recorded_date', 'source', 'is_active', 'created_at']
    search_fields = ['user__email']
    list_filter = ['source', 'is_active', 'recorded_date', 'created_at']
    date_hierarchy = 'recorded_date'
    ordering = ['-recorded_date', '-created_at']


@admin.register(PaceEntry)
class PaceEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'activity_type', 'recorded_date', 'source', 'is_active', 'created_at']
    search_fields = ['user__email']
    list_filter = ['activity_type', 'level', 'source', 'is_active', 'recorded_date', 'created_at']
    date_hierarchy = 'recorded_date'
    ordering = ['-recorded_date', '-created_at']


@admin.register(PaceLevel)
class PaceLevelAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'level', 'recorded_date', 'notes', 'created_at']
    search_fields = ['user__email', 'notes']
    list_filter = ['activity_type', 'level', 'recorded_date', 'created_at']
    date_hierarchy = 'recorded_date'
    ordering = ['-recorded_date', '-level']


@admin.register(OnboardingWizard)
class OnboardingWizardAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_stage', 'completed_stages_display', 'progress_display', 'created_at', 'completed_at']
    search_fields = ['user__email']
    list_filter = ['current_stage', 'created_at', 'completed_at']
    readonly_fields = ['user', 'created_at', 'updated_at', 'completed_at', 'progress_display']
    
    def completed_stages_display(self, obj):
        """Display completed stages as a list"""
        if not obj.completed_stages:
            return "—"
        stages = ', '.join(str(s) for s in sorted(obj.completed_stages))
        return f"Stages {stages}"
    completed_stages_display.short_description = 'Completed Stages'
    
    def progress_display(self, obj):
        """Display progress bar"""
        percentage = obj.get_progress_percentage()
        return mark_safe(f'<div style="width: 200px; height: 20px; background-color: #e0e0e0; border-radius: 10px; overflow: hidden;"><div style="width: {percentage}%; height: 100%; background-color: #4CAF50; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: bold;">{percentage}%</div></div>')
    progress_display.short_description = 'Progress'

