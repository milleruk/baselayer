from django.contrib import admin
from django.utils.html import format_html
from .models import WorkoutType, Instructor, Workout, WorkoutDetails, WorkoutMetrics, WorkoutPerformanceData, RideDetail, Playlist, ClassType


@admin.register(WorkoutType)
class WorkoutTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'workout_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']
    
    def workout_count(self, obj):
        """Display number of workouts of this type"""
        # Count workouts via ride_details (all class data comes from RideDetail)
        from .models import Workout
        return Workout.objects.filter(ride_detail__workout_type=obj).count()
    workout_count.short_description = 'Workouts'


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['name', 'username', 'peloton_id', 'location', 'workout_count', 'has_image', 'synced_at']
    list_filter = ['synced_at', 'location']
    search_fields = ['name', 'username', 'peloton_id', 'location', 'bio']
    readonly_fields = ['synced_at', 'last_synced_at']
    
    def workout_count(self, obj):
        """Display number of workouts for this instructor"""
        # Count workouts that use ride_details with this instructor
        from .models import Workout
        return Workout.objects.filter(ride_detail__instructor=obj).count()
    workout_count.short_description = 'Workouts'
    
    def has_image(self, obj):
        """Check if instructor has image URL"""
        return bool(obj.image_url)
    has_image.boolean = True
    has_image.short_description = 'Has Image'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'username', 'peloton_id', 'location')
        }),
        ('Profile', {
            'fields': ('image_url', 'bio'),
            'classes': ('collapse',)
        }),
        ('Sync Information', {
            'fields': ('synced_at', 'last_synced_at'),
            'classes': ('collapse',)
        }),
    )


class WorkoutDetailsInline(admin.StackedInline):
    model = WorkoutDetails
    can_delete = False
    verbose_name_plural = 'Workout Details'
    fields = (
        ('tss', 'tss_target'),
        ('avg_output', 'total_output', 'max_output'),
        ('avg_speed', 'max_speed'),
        ('distance', 'total_calories'),
        ('avg_heart_rate', 'max_heart_rate'),
        ('avg_cadence', 'max_cadence'),
        ('avg_resistance', 'max_resistance'),
    )
    classes = ('collapse',)


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ['display_title', 'user', 'display_workout_type', 'display_instructor', 'display_duration', 'completed_date', 'peloton_workout_id', 'has_peloton_url', 'synced_at']
    list_filter = ['ride_detail__workout_type', 'completed_date', 'synced_at', 'ride_detail__instructor']
    search_fields = ['ride_detail__title', 'user__username', 'user__email', 'ride_detail__instructor__name', 'peloton_workout_id', 'ride_detail__description']
    readonly_fields = ['synced_at', 'last_synced_at', 'peloton_workout_id', 'peloton_url_link', 'ride_detail_info', 'completed_at', 'peloton_created_at', 'peloton_timezone']
    date_hierarchy = 'completed_date'
    raw_id_fields = ['user', 'ride_detail']
    inlines = [WorkoutDetailsInline]
    actions = ['delete_selected_workouts']
    list_per_page = 100  # Show more per page to reduce pagination
    
    def get_queryset(self, request):
        """Optimize queryset with select_related - all class data comes from ride_detail via SQL joins"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'user', 'ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details'
        )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'ride_detail', 'ride_detail_info')
        }),
        ('Peloton Integration', {
            'fields': ('peloton_workout_id', 'peloton_url'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('recorded_date', 'completed_date', 'completed_at', 'peloton_created_at', 'peloton_timezone')
        }),
        ('Sync Information', {
            'fields': ('synced_at', 'last_synced_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_title(self, obj):
        """Display title from ride_detail via join"""
        if obj.ride_detail:
            return obj.ride_detail.title
        return '— (No ride detail)'
    display_title.short_description = 'Title'
    display_title.admin_order_field = 'ride_detail__title'
    
    def display_workout_type(self, obj):
        """Display workout_type from ride_detail via join"""
        if obj.ride_detail and obj.ride_detail.workout_type:
            return obj.ride_detail.workout_type.name
        return '—'
    display_workout_type.short_description = 'Type'
    display_workout_type.admin_order_field = 'ride_detail__workout_type__name'
    
    def display_instructor(self, obj):
        """Display instructor from ride_detail via join"""
        if obj.ride_detail and obj.ride_detail.instructor:
            return obj.ride_detail.instructor.name
        return '—'
    display_instructor.short_description = 'Instructor'
    display_instructor.admin_order_field = 'ride_detail__instructor__name'
    
    def display_duration(self, obj):
        """Display duration from ride_detail via join"""
        if obj.ride_detail:
            return f"{obj.ride_detail.duration_minutes}min"
        return '—'
    display_duration.short_description = 'Duration'
    
    def ride_detail_info(self, obj):
        """Display ride detail information"""
        if obj.ride_detail:
            return format_html(
                '<strong>Class:</strong> {}<br>'
                '<strong>Type:</strong> {}<br>'
                '<strong>Instructor:</strong> {}<br>'
                '<strong>Duration:</strong> {}min<br>'
                '<strong>Difficulty:</strong> {} ({})<br>'
                '<strong>Ride ID:</strong> {}',
                obj.ride_detail.title,
                obj.ride_detail.workout_type.name if obj.ride_detail.workout_type else '—',
                obj.ride_detail.instructor.name if obj.ride_detail.instructor else '—',
                obj.ride_detail.duration_minutes,
                obj.ride_detail.difficulty_level or '—',
                obj.ride_detail.difficulty_rating_avg or '—',
                obj.ride_detail.peloton_ride_id
            )
        return format_html(
            '<span style="color: red;">⚠ No ride detail linked</span><br>'
            '<small>This workout needs to be re-synced to link to a ride detail.</small>'
        )
    ride_detail_info.short_description = 'Ride Detail Information'
    
    def has_peloton_url(self, obj):
        """Check if workout has Peloton URL"""
        return bool(obj.peloton_url)
    has_peloton_url.boolean = True
    has_peloton_url.short_description = 'Has URL'
    
    def has_peloton_data(self, obj):
        """Check if workout has Peloton data (ID or URL)"""
        return bool(obj.peloton_id or obj.peloton_url)
    has_peloton_data.boolean = True
    has_peloton_data.short_description = 'Peloton Data'
    
    def peloton_url_link(self, obj):
        """Display Peloton URL as clickable link"""
        if obj.peloton_url:
            return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">View on Peloton ↗</a>', obj.peloton_url)
        return '—'
    peloton_url_link.short_description = 'Peloton Link'
    
    def delete_selected_workouts(self, request, queryset):
        """Custom delete action that handles large numbers of workouts"""
        count = queryset.count()
        # Delete related details and performance data first
        from .models import WorkoutDetails, WorkoutPerformanceData
        workout_ids = list(queryset.values_list('id', flat=True))
        
        # Delete in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(workout_ids), batch_size):
            batch_ids = workout_ids[i:i+batch_size]
            WorkoutPerformanceData.objects.filter(workout_id__in=batch_ids).delete()
            WorkoutDetails.objects.filter(workout_id__in=batch_ids).delete()
        
        # Now delete the workouts
        queryset.delete()
        self.message_user(request, f'Successfully deleted {count} workout(s) and their related data.')
    delete_selected_workouts.short_description = 'Delete selected workouts'


@admin.register(WorkoutDetails)
class WorkoutDetailsAdmin(admin.ModelAdmin):
    list_display = ['workout', 'tss', 'avg_output', 'total_output', 'distance', 'total_calories', 'avg_heart_rate']
    list_filter = ['workout__ride_detail__workout_type', 'workout__completed_date']
    search_fields = ['workout__ride_detail__title', 'workout__user__username', 'workout__user__email']
    raw_id_fields = ['workout']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('workout', 'workout__ride_detail', 'workout__user')
    
    fieldsets = (
        ('Workout', {
            'fields': ('workout',)
        }),
        ('Training Stress', {
            'fields': ('tss', 'tss_target'),
            'classes': ('collapse',)
        }),
        ('Output Metrics (Cycling)', {
            'fields': ('avg_output', 'total_output', 'max_output'),
            'classes': ('collapse',)
        }),
        ('Speed Metrics (Running)', {
            'fields': ('avg_speed', 'max_speed'),
            'classes': ('collapse',)
        }),
        ('Distance & Calories', {
            'fields': ('distance', 'total_calories')
        }),
        ('Heart Rate', {
            'fields': ('avg_heart_rate', 'max_heart_rate'),
            'classes': ('collapse',)
        }),
        ('Cadence (Cycling)', {
            'fields': ('avg_cadence', 'max_cadence'),
            'classes': ('collapse',)
        }),
        ('Resistance (Cycling)', {
            'fields': ('avg_resistance', 'max_resistance'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkoutPerformanceData)
class WorkoutPerformanceDataAdmin(admin.ModelAdmin):
    list_display = ['workout', 'timestamp', 'output', 'speed', 'heart_rate', 'power_zone', 'intensity_zone']
    list_filter = ['power_zone', 'intensity_zone']
    search_fields = ['workout__ride_detail__title', 'workout__user__username']
    raw_id_fields = ['workout']
    ordering = ['workout', 'timestamp']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('workout', 'workout__ride_detail', 'workout__user')


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['ride_detail', 'song_count', 'peloton_playlist_id', 'synced_at']
    list_filter = ['synced_at', 'is_playlist_shown']
    search_fields = ['ride_detail__title', 'peloton_playlist_id']
    readonly_fields = ['synced_at', 'last_synced_at', 'song_count']
    raw_id_fields = ['ride_detail']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('ride_detail', 'peloton_playlist_id')
        }),
        ('Playlist Data', {
            'fields': ('songs', 'top_artists', 'top_albums'),
            'classes': ('collapse',)
        }),
        ('Stream Information', {
            'fields': ('stream_id', 'stream_url'),
            'classes': ('collapse',)
        }),
        ('Display Flags', {
            'fields': ('is_top_artists_shown', 'is_playlist_shown', 'is_in_class_music_shown')
        }),
        ('Sync Information', {
            'fields': ('synced_at', 'last_synced_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RideDetail)
class RideDetailAdmin(admin.ModelAdmin):
    list_display = ['title', 'workout_type', 'instructor', 'duration_minutes', 'fitness_discipline', 'class_type', 'chart_type_display', 'difficulty_level', 'workout_count', 'synced_at']
    list_filter = ['workout_type', 'fitness_discipline', 'class_type', 'is_power_zone_class', 'difficulty_level', 'is_archived', 'synced_at']
    search_fields = ['title', 'description', 'peloton_ride_id', 'instructor__name', 'fitness_discipline']
    readonly_fields = ['synced_at', 'last_synced_at', 'peloton_ride_id', 'image_preview', 'chart_type_display']
    raw_id_fields = ['workout_type', 'instructor']
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('peloton_ride_id', 'title', 'description', 'duration_seconds', 'workout_type', 'instructor')
        }),
        ('Fitness Discipline', {
            'fields': ('fitness_discipline', 'fitness_discipline_display_name')
        }),
        ('Ratings & Difficulty', {
            'fields': ('difficulty_rating_avg', 'difficulty_rating_count', 'difficulty_level', 'overall_estimate', 'difficulty_estimate')
        }),
        ('Media & Links', {
            'fields': ('image_url', 'image_preview', 'home_peloton_id', 'peloton_class_url')
        }),
        ('Timing', {
            'fields': ('original_air_time', 'scheduled_start_time', 'created_at_timestamp')
        }),
        ('Class Types & Equipment', {
            'fields': ('class_type_ids', 'equipment_ids', 'equipment_tags'),
            'classes': ('collapse',)
        }),
        ('Content Information', {
            'fields': ('content_format', 'content_provider', 'has_closed_captions', 'is_archived'),
            'classes': ('collapse',)
        }),
        ('Class Type', {
            'fields': ('class_type', 'is_power_zone_class'),
            'description': 'Class type determines what kind of chart/segments to display. Power Zone classes show zones, others show cadence/resistance or pace. Chart type is shown in the list view.'
        }),
        ('Target Metrics', {
            'fields': ('target_metrics_data', 'target_class_metrics', 'pace_target_type'),
            'classes': ('collapse',),
            'description': 'Class-specific target metrics: Power Zone ranges, cadence/resistance ranges, or pace targets'
        }),
        ('Sync Information', {
            'fields': ('synced_at', 'last_synced_at'),
            'classes': ('collapse',)
        }),
    )
    
    def workout_count(self, obj):
        """Display number of workouts using this ride detail"""
        return obj.workouts.count()  # This is correct - RideDetail has related_name="workouts"
    workout_count.short_description = 'Workouts'
    
    def image_preview(self, obj):
        """Display image preview"""
        if obj.image_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.image_url)
        return '—'
    image_preview.short_description = 'Image Preview'
    
    def chart_type_display(self, obj):
        """Display what type of chart/segments this class uses"""
        if obj is None:
            return '—'
        
        try:
            chart_type = obj.chart_type
        except (AttributeError, TypeError, Exception):
            return '—'
        
        if not chart_type:
            return '—'
        
        # Use mark_safe for simple HTML strings (no placeholders needed)
        from django.utils.safestring import mark_safe
        
        if chart_type == 'zones':
            return mark_safe('<span style="color: #059669; font-weight: bold;">Zones (Power Zone)</span>')
        elif chart_type == 'cadence_resistance':
            return mark_safe('<span style="color: #2563eb; font-weight: bold;">Cadence & Resistance</span>')
        elif chart_type == 'pace':
            return mark_safe('<span style="color: #dc2626; font-weight: bold;">Pace Targets</span>')
        else:
            return '—'
    chart_type_display.short_description = 'Chart Type'


@admin.register(ClassType)
class ClassTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'fitness_discipline', 'peloton_id', 'is_active', 'synced_at']
    list_filter = ['fitness_discipline', 'is_active', 'synced_at']
    search_fields = ['name', 'peloton_id', 'fitness_discipline']
    readonly_fields = ['synced_at', 'last_synced_at']
    ordering = ['fitness_discipline', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('peloton_id', 'name', 'slug', 'fitness_discipline')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Sync Information', {
            'fields': ('synced_at', 'last_synced_at'),
            'classes': ('collapse',)
        }),
    )


# Note: PelotonConnection is registered in peloton/admin.py
