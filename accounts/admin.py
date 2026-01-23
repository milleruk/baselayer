from django.contrib import admin
from .models import Profile, WeightEntry


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'date_of_birth']
    search_fields = ['user__username', 'user__email', 'full_name']
    list_filter = ['date_of_birth']

@admin.register(WeightEntry)
class WeightEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'weight', 'recorded_date', 'created_at']
    search_fields = ['user__username', 'user__email']
    list_filter = ['recorded_date', 'created_at']
    date_hierarchy = 'recorded_date'
    ordering = ['-recorded_date', '-created_at']
