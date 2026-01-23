from django.contrib import admin
from .models import WorkoutType, Instructor, Workout, WorkoutMetrics, WorkoutPerformanceData, PelotonConnection


@admin.register(WorkoutType)
class WorkoutTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['name', 'peloton_id']
    search_fields = ['name', 'peloton_id']


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'workout_type', 'instructor', 'duration_minutes', 'completed_date', 'synced_at']
    list_filter = ['workout_type', 'completed_date', 'synced_at']
    search_fields = ['title', 'user__username', 'instructor__name']
    readonly_fields = ['synced_at', 'last_synced_at']
    date_hierarchy = 'completed_date'
    raw_id_fields = ['user', 'instructor']


@admin.register(WorkoutMetrics)
class WorkoutMetricsAdmin(admin.ModelAdmin):
    list_display = ['workout', 'tss', 'avg_output', 'total_output', 'distance']
    search_fields = ['workout__title', 'workout__user__username']
    raw_id_fields = ['workout']


@admin.register(WorkoutPerformanceData)
class WorkoutPerformanceDataAdmin(admin.ModelAdmin):
    list_display = ['workout', 'timestamp', 'output', 'speed', 'heart_rate', 'power_zone', 'intensity_zone']
    list_filter = ['power_zone', 'intensity_zone']
    search_fields = ['workout__title', 'workout__user__username']
    raw_id_fields = ['workout']
    ordering = ['workout', 'timestamp']


@admin.register(PelotonConnection)
class PelotonConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_connected', 'peloton_username', 'last_sync_at', 'connected_at']
    list_filter = ['is_connected', 'auto_sync_enabled']
    search_fields = ['user__username', 'peloton_username', 'peloton_user_id']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']
