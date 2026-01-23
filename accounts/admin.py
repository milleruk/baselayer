from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, WeightEntry, FTPEntry, PaceEntry, PaceLevel, PaceBand


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model"""
    list_display = ['email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    
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


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'date_of_birth']
    search_fields = ['user__email', 'full_name']
    list_filter = ['date_of_birth']

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


class PaceBandInline(admin.TabularInline):
    model = PaceBand
    extra = 0
    fields = ['zone', 'min_mph', 'max_mph', 'min_pace', 'max_pace', 'description']


@admin.register(PaceLevel)
class PaceLevelAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'level', 'recorded_date', 'notes', 'created_at']
    search_fields = ['user__email', 'notes']
    list_filter = ['activity_type', 'level', 'recorded_date', 'created_at']
    date_hierarchy = 'recorded_date'
    ordering = ['-recorded_date', '-level']
    inlines = [PaceBandInline]


@admin.register(PaceBand)
class PaceBandAdmin(admin.ModelAdmin):
    list_display = ['pace_level', 'zone', 'min_mph', 'max_mph', 'min_pace', 'max_pace']
    search_fields = ['pace_level__user__email', 'description']
    list_filter = ['zone', 'pace_level__level']
    ordering = ['pace_level', 'zone']
