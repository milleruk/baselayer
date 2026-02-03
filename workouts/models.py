from django.conf import settings
from django.db import models
from django.utils import timezone
import json

# Use Django's built-in JSONField (works with all databases)
try:
    from django.db.models import JSONField
except ImportError:
    # Fallback for older Django versions
    from django.contrib.postgres.fields import JSONField


class ClassType(models.Model):
    """
    Class types/categories synced from Peloton API /api/ride/filters endpoint.
    This replaces the hardcoded CLASS_TYPE_CHOICES with dynamic data from Peloton.
    """
    # Peloton class type ID (unique identifier from API)
    peloton_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Peloton class type ID")
    
    # Display information
    name = models.CharField(max_length=200, help_text="Display name (e.g., 'Power Zone', 'Climb')")
    slug = models.SlugField(max_length=200, blank=True, help_text="URL-friendly slug")
    
    # Fitness discipline this class type belongs to
    fitness_discipline = models.CharField(max_length=50, blank=True, db_index=True, help_text="e.g., 'cycling', 'running', 'strength', 'yoga'")
    
    # Additional metadata from API
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata from Peloton API")
    
    # Sync information
    synced_at = models.DateTimeField(auto_now_add=True, help_text="When this class type was first synced")
    last_synced_at = models.DateTimeField(auto_now=True, help_text="Last time this class type was synced")
    is_active = models.BooleanField(default=True, help_text="Whether this class type is currently active")
    
    class Meta:
        ordering = ['fitness_discipline', 'name']
        indexes = [
            models.Index(fields=['peloton_id']),
            models.Index(fields=['fitness_discipline']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "Class Type"
        verbose_name_plural = "Class Types"
    
    def __str__(self):
        discipline = f" ({self.fitness_discipline})" if self.fitness_discipline else ""
        return f"{self.name}{discipline}"
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.slug and self.name:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class WorkoutType(models.Model):
    """Workout type/category (Cycling, Running, Yoga, Strength, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon identifier (e.g., 'bicycle', 'running', 'yoga')")
    
    class Meta:
        ordering = ["name"]
    
    def __str__(self):
        return self.name


class Instructor(models.Model):
    """Peloton instructor information"""
    name = models.CharField(max_length=200)
    peloton_id = models.CharField(max_length=100, unique=True, blank=True, null=True, db_index=True)
    image_url = models.URLField(blank=True, null=True, help_text="Profile image URL")
    
    # Additional instructor details
    bio = models.TextField(blank=True, help_text="Instructor biography")
    location = models.CharField(max_length=200, blank=True, help_text="Instructor location")
    username = models.CharField(max_length=100, blank=True, help_text="Peloton username")
    
    # Sync information
    synced_at = models.DateTimeField(null=True, blank=True, help_text="When this instructor was first synced")
    last_synced_at = models.DateTimeField(null=True, blank=True, help_text="Last time this instructor was synced")
    
    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["peloton_id"]),
        ]
    
    def __str__(self):
        return self.name


class RideDetail(models.Model):
    """
    Peloton class/ride template details (shared across all users who took this class).
    This stores the class information from /api/ride/{rideId}/details endpoint.
    """
    # Peloton ride/class ID (unique identifier)
    peloton_ride_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Peloton ride/class ID")
    
    # Basic class information
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    duration_seconds = models.IntegerField(help_text="Class duration in seconds")
    
    # Relationships
    workout_type = models.ForeignKey(WorkoutType, on_delete=models.PROTECT, related_name="ride_details")
    instructor = models.ForeignKey(Instructor, on_delete=models.PROTECT, related_name="ride_details", null=True, blank=True)
    
    # Class metadata
    fitness_discipline = models.CharField(max_length=50, blank=True, help_text="e.g., 'cycling', 'yoga', 'running'")
    fitness_discipline_display_name = models.CharField(max_length=100, blank=True, help_text="e.g., 'Cycling', 'Yoga', 'Running'")
    
    # Ratings and difficulty
    difficulty_rating_avg = models.FloatField(null=True, blank=True, help_text="Average difficulty rating")
    difficulty_rating_count = models.IntegerField(default=0, help_text="Number of difficulty ratings")
    difficulty_level = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., 'beginner', 'intermediate', 'advanced'")
    overall_estimate = models.FloatField(null=True, blank=True)
    difficulty_estimate = models.FloatField(null=True, blank=True)
    
    # Media
    image_url = models.URLField(blank=True, null=True, help_text="Class thumbnail/image URL")
    home_peloton_id = models.CharField(max_length=100, blank=True, null=True, help_text="Home Peloton ID")
    peloton_class_url = models.URLField(blank=True, null=True, help_text="Link to class on Peloton website")
    
    # Timing
    original_air_time = models.BigIntegerField(null=True, blank=True, help_text="Unix timestamp when class originally aired")
    scheduled_start_time = models.BigIntegerField(null=True, blank=True, help_text="Unix timestamp of scheduled start")
    created_at_timestamp = models.BigIntegerField(null=True, blank=True, help_text="Unix timestamp when class was created")
    
    # Class types and equipment (stored as JSON)
    class_type_ids = models.JSONField(default=list, blank=True, help_text="List of class type IDs")
    equipment_ids = models.JSONField(default=list, blank=True, help_text="List of equipment IDs")
    equipment_tags = models.JSONField(default=list, blank=True, help_text="List of equipment tag objects")
    
    # Content information
    content_format = models.CharField(max_length=50, blank=True, help_text="e.g., 'video', 'audio'")
    content_provider = models.CharField(max_length=50, blank=True, help_text="e.g., 'peloton'")
    has_closed_captions = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # Class type (replaces is_power_zone_class with more granular types)
    CLASS_TYPE_CHOICES = [
        # Cycling class types
        ('power_zone', 'Power Zone'),
        ('climb', 'Climb'),
        ('intervals', 'Intervals'),
        ('progression', 'Progression'),
        ('low_impact', 'Low Impact'),
        ('beginner', 'Beginner'),
        ('groove', 'Groove'),
        ('pro_cyclist', 'Pro Cyclist'),
        ('music', 'Music'),
        ('theme', 'Theme'),
        ('live_dj', 'Live DJ'),
        ('peloton_studio_original', 'Peloton Studio Original'),
        # Running class types
        ('pace_target', 'Pace Target'),
        ('speed', 'Speed'),
        ('endurance', 'Endurance'),
        ('walk_run', 'Walk + Run'),
        ('form_drills', 'Form & Drills'),
        # Walking class types
        ('power_walk', 'Power Walk'),
        ('hiking', 'Hiking'),
        # Strength class types
        ('bodyweight', 'Bodyweight'),
        ('full_body', 'Full Body'),
        ('core', 'Core'),
        ('upper_body', 'Upper Body'),
        ('lower_body', 'Lower Body'),
        ('strength_basics', 'Strength Basics'),
        ('arms_light_weights', 'Arms & Light Weights'),
        ('strength_for_sport', 'Strength for Sport'),
        ('resistance_bands', 'Resistance Bands'),
        ('adaptive', 'Adaptive'),
        ('barre', 'Barre'),
        ('kettlebells', 'Kettlebells'),
        ('boxing_bootcamp', 'Boxing Bootcamp'),
        # Yoga class types
        ('flow', 'Flow'),
        ('focus_flow', 'Focus Flow'),
        ('slow_flow', 'Slow Flow'),
        ('power', 'Power'),
        ('sculpt_flow', 'Sculpt Flow'),
        ('yoga_pilates', 'Yoga + Pilates'),
        ('morning', 'Morning'),
        ('restorative', 'Restorative'),
        ('yin_yoga', 'Yin Yoga'),
        ('yoga_anywhere', 'Yoga Anywhere'),
        ('yoga_basics', 'Yoga Basics'),
        ('family_pre_postnatal', 'Family & Pre/Postnatal'),
        ('beyond_the_pose', 'Beyond the Pose'),
        # Meditation class types
        ('daily_meditation', 'Daily Meditation'),
        ('sleep', 'Sleep'),
        ('relaxation', 'Relaxation'),
        ('emotions', 'Emotions'),
        ('meditation_basics', 'Meditation Basics'),
        ('breath', 'Breath'),
        ('mindfulness', 'Mindfulness'),
        ('walking_meditation', 'Walking Meditation'),
        # Rowing class types (to be expanded)
        # Generic/Common types
        ('warm_up', 'Warm Up'),
        ('cool_down', 'Cool Down'),
        ('other', 'Other'),
    ]
    class_type = models.CharField(
        max_length=50,
        choices=CLASS_TYPE_CHOICES,
        blank=True,
        null=True,
        db_index=True,
        help_text="Type of class (Power Zone, Pace Target, Climb, Intervals, etc.)"
    )
    
    # Keep is_power_zone_class for backward compatibility (will be deprecated)
    is_power_zone_class = models.BooleanField(default=False, help_text="Whether this is a Power Zone class (deprecated - use class_type instead)")
    
    # Target metrics (class-specific targets for users to aim for)
    # For Power Zone classes: power zone ranges (1-7) with output ranges
    # For non-PZ cycling: cadence and resistance ranges
    # For tread runs: pace target ranges (recovery, easy, moderate, etc.)
    target_metrics_data = models.JSONField(default=dict, blank=True, help_text="Target metrics data structure with segments, zones, and ranges")
    target_class_metrics = models.JSONField(default=dict, blank=True, help_text="Target class metrics (e.g., total_expected_output)")
    pace_target_type = models.CharField(max_length=50, blank=True, null=True, help_text="Pace target type for tread runs (e.g., 'pace_target', 'pace_zone')")
    
    # Segments structure (from ride details API)
    # Contains segment_list with Warm Up, Main, Cool Down sections and their subsegments_v2
    segments_data = models.JSONField(default=dict, blank=True, help_text="Segments structure with segment_list containing Warm Up, Main, Cool Down sections and subsegments")
    
    # Sync information
    synced_at = models.DateTimeField(auto_now_add=True, help_text="When this ride detail was first synced")
    last_synced_at = models.DateTimeField(auto_now=True, help_text="Last time this ride detail was synced")
    
    class Meta:
        ordering = ["-original_air_time", "title"]
        indexes = [
            models.Index(fields=["peloton_ride_id"]),
            models.Index(fields=["workout_type"]),
            models.Index(fields=["instructor"]),
            models.Index(fields=["fitness_discipline"]),
        ]
        verbose_name = "Ride Detail"
        verbose_name_plural = "Ride Details"
    
    def __str__(self):
        return f"{self.title} ({self.fitness_discipline_display_name or self.fitness_discipline})"
    
    def get_peloton_url(self):
        """
        Get the standardized Peloton class URL in UK modal format.
        
        This method ensures a consistent URL format across the application:
        https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=[ID]
        
        Returns:
            str: The standardized Peloton URL for this class
        """
        from challenges.utils import generate_peloton_url
        if self.peloton_ride_id:
            return generate_peloton_url(self.peloton_ride_id)
        return self.peloton_class_url or ''
    
    @property
    def duration_minutes(self):
        """Return duration in minutes"""
        return int(self.duration_seconds / 60) if self.duration_seconds else 0
    
    @property
    def chart_type(self):
        """
        Determine what type of chart/segments to display based on class_type.
        Returns: 'zones', 'cadence_resistance', 'pace', or None
        """
        if self.class_type == 'power_zone' or self.is_power_zone_class:
            return 'zones'
        elif self.class_type == 'pace_target' or self.fitness_discipline in ['running', 'walking']:
            return 'pace'
        elif self.fitness_discipline == 'cycling':
            return 'cadence_resistance'
        return None
    
    @property
    def original_air_date(self):
        """Return original_air_time as a date object"""
        if self.original_air_time:
            from datetime import datetime
            try:
                timestamp = self.original_air_time
                # Peloton timestamps can be in milliseconds (13 digits) or seconds (10 digits)
                # Check the magnitude to determine the format:
                # - >= 1e12: milliseconds (13+ digits, e.g., 1735689600000)
                # - < 1e10: seconds (9 or fewer digits, e.g., 1735689600)
                # - 1e10 to 1e12: ambiguous, but based on DB inspection, Peloton stores in seconds
                if timestamp >= 1e12:
                    # Definitely milliseconds (13+ digits) - convert to seconds
                    timestamp = timestamp / 1000
                # Otherwise, it's already in seconds (no conversion needed)
                
                return datetime.fromtimestamp(timestamp).date()
            except (ValueError, OSError, OverflowError):
                return None
        return None
    
    def get_target_metrics_segments(self):
        """
        Extract target metrics segments from target_metrics_data.
        Returns a list of segments with time offsets and target values.
        """
        if not self.target_metrics_data:
            return []
        
        target_metrics = self.target_metrics_data.get('target_metrics', [])
        if not target_metrics:
            return []
        
        segments = []
        for segment in target_metrics:
            offsets = segment.get('offsets', {})
            segment_type = segment.get('segment_type', '')
            metrics = segment.get('metrics', [])
            
            segments.append({
                'start': offsets.get('start', 0),
                'end': offsets.get('end', 0),
                'type': segment_type,
                'metrics': metrics
            })
        
        return segments
    
    def get_power_zone_segments(self, user_ftp=None):
        """
        Get power zone target segments for Power Zone classes.
        Returns segments with zone numbers and calculated watt ranges based on user's FTP.
        """
        # Check both class_type and is_power_zone_class for backward compatibility
        if self.class_type != 'power_zone' and not self.is_power_zone_class:
            return []
        
        segments = self.get_target_metrics_segments()
        if not segments:
            return []
        
        # Calculate zone ranges from FTP if provided
        zone_ranges = {}
        if user_ftp:
            zone_ranges = {
                1: (0, int(user_ftp * 0.55)),
                2: (int(user_ftp * 0.55), int(user_ftp * 0.75)),
                3: (int(user_ftp * 0.75), int(user_ftp * 0.90)),
                4: (int(user_ftp * 0.90), int(user_ftp * 1.05)),
                5: (int(user_ftp * 1.05), int(user_ftp * 1.20)),
                6: (int(user_ftp * 1.20), int(user_ftp * 1.50)),
                7: (int(user_ftp * 1.50), None)
            }
        
        power_zone_segments = []
        for segment in segments:
            segment_type = (segment.get('type') or '').lower()
            zone_num = None

            if segment_type == 'power_zone':
                for metric in segment.get('metrics', []):
                    if metric.get('name') == 'power_zone':
                        zone_lower = metric.get('lower')
                        zone_upper = metric.get('upper')
                        zone_num = zone_lower if zone_lower == zone_upper else zone_lower
                        break
            elif 'spin' in segment_type and 'up' in segment_type:
                zone_num = 1  # Treat all spin-up segments as Zone 1 targets

            if zone_num is None:
                continue

            try:
                zone_num = int(zone_num)
            except (TypeError, ValueError):
                continue

            zone_num = max(1, min(7, zone_num))

            power_zone_segments.append({
                'start': segment.get('start', 0),
                'end': segment.get('end', 0),
                'zone': zone_num,
                'watt_range': zone_ranges.get(zone_num) if user_ftp else None,
                'segment_type': segment_type,
                'type': segment_type
            })
        
        return power_zone_segments
    
    def get_cadence_resistance_segments(self):
        """
        Get cadence and resistance target segments for non-PZ cycling classes.
        Returns segments with cadence/resistance ranges.
        """
        # Only return for non-PZ cycling classes
        if self.class_type == 'power_zone' or self.is_power_zone_class:
            return []
        
        segments = self.get_target_metrics_segments()
        if not segments:
            return []
        
        cadence_resistance_segments = []
        for segment in segments:
            cadence_range = None
            resistance_range = None
            
            for metric in segment.get('metrics', []):
                metric_name = metric.get('name', '')
                if metric_name == 'cadence':
                    cadence_range = {
                        'lower': metric.get('lower'),
                        'upper': metric.get('upper')
                    }
                elif metric_name == 'resistance':
                    resistance_range = {
                        'lower': metric.get('lower'),
                        'upper': metric.get('upper')
                    }
            
            if cadence_range or resistance_range:
                cadence_resistance_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'cadence': cadence_range,
                    'resistance': resistance_range
                })
        
        return cadence_resistance_segments
    
    def get_pace_segments(self, user_pace_zones=None):
        """
        Get pace target segments for running/walking classes.
        Returns segments with pace zone numbers (1-7) and calculated pace ranges based on user's pace zones.
        Zone mapping: 1=recovery, 2=easy, 3=moderate, 4=challenging, 5=hard, 6=very_hard, 7=max
        """
        if self.fitness_discipline not in ['running', 'walking']:
            return []
        
        segments = self.get_target_metrics_segments()
        if not segments:
            return []
        
        pace_segments = []
        for segment in segments:
            for metric in segment.get('metrics', []):
                metric_name = metric.get('name', '')
                if 'pace' in metric_name.lower() or 'pace_intensity' in metric_name.lower():
                    # Get pace intensity value (typically 0-6 from Peloton API)
                    pace_intensity = metric.get('lower') or metric.get('upper')
                    if pace_intensity is None:
                        continue
                    
                    # Ensure it's an integer
                    try:
                        pace_intensity = int(pace_intensity)
                    except (ValueError, TypeError):
                        continue
                    
                    # Map pace_intensity (0-6) to pace zone (1-7)
                    # Peloton pace_intensity: 0=Recovery, 1=Easy, 2=Moderate, 3=Challenging, 4=Hard, 5=Very Hard, 6=Max
                    # Our pace zones: 1=Recovery, 2=Easy, 3=Moderate, 4=Challenging, 5=Hard, 6=Very Hard, 7=Max
                    pace_zone = pace_intensity + 1  # Convert 0-6 to 1-7
                    
                    # Ensure pace_zone is in valid range (1-7)
                    if pace_zone < 1:
                        pace_zone = 1
                    elif pace_zone > 7:
                        pace_zone = 7
                    
                    # Map zone number to zone name for pace_range lookup
                    zone_map = {1: 'recovery', 2: 'easy', 3: 'moderate', 4: 'challenging', 
                               5: 'hard', 6: 'very_hard', 7: 'max'}
                    zone_name = zone_map.get(pace_zone, 'moderate')
                    
                    # Get pace range from user's pace zones if available
                    pace_range = None
                    if user_pace_zones and zone_name in user_pace_zones:
                        pace_range = user_pace_zones[zone_name]
                    
                    pace_segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'zone': pace_zone,  # Keep as integer (1-7)
                        'zone_name': zone_name,  # Add zone name for easier lookup
                        'pace_range': pace_range
                    })
        
        return pace_segments


class Playlist(models.Model):
    """
    Music playlist for a Peloton class/ride.
    Stores the complete playlist including songs, artists, and albums.
    """
    # Link to the ride/class
    ride_detail = models.OneToOneField(
        RideDetail,
        on_delete=models.CASCADE,
        related_name='playlist',
        help_text="The class/ride this playlist belongs to"
    )
    
    # Peloton playlist ID
    peloton_playlist_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text="Peloton playlist ID"
    )
    
    # Songs array - stores complete song data with artists, albums, etc.
    songs = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of songs with full details (title, artists, album, timing, etc.)"
    )
    
    # Top artists and albums
    top_artists = models.JSONField(
        default=list,
        blank=True,
        help_text="Top artists featured in this playlist"
    )
    top_albums = models.JSONField(
        default=list,
        blank=True,
        help_text="Top albums featured in this playlist"
    )
    
    # Stream information
    stream_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Stream ID for playlist"
    )
    stream_url = models.URLField(
        blank=True,
        null=True,
        help_text="Stream URL for playlist"
    )
    
    # Display flags
    is_top_artists_shown = models.BooleanField(
        default=False,
        help_text="Whether to show top artists"
    )
    is_playlist_shown = models.BooleanField(
        default=False,
        help_text="Whether to show playlist"
    )
    is_in_class_music_shown = models.BooleanField(
        default=False,
        help_text="Whether to show in-class music"
    )
    
    # Sync information
    synced_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this playlist was first synced"
    )
    last_synced_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time this playlist was synced"
    )
    
    class Meta:
        ordering = ["-synced_at"]
        indexes = [
            models.Index(fields=["peloton_playlist_id"]),
            models.Index(fields=["ride_detail"]),
        ]
        verbose_name = "Playlist"
        verbose_name_plural = "Playlists"
    
    def __str__(self):
        return f"Playlist for {self.ride_detail.title}"
    
    @property
    def song_count(self):
        """Return the number of songs in the playlist"""
        return len(self.songs) if self.songs else 0
    
    @property
    def total_duration_estimate(self):
        """Estimate total playlist duration based on song offsets"""
        if not self.songs:
            return None
        
        # Find the last song's start_time_offset and estimate duration
        # This is rough - we'd need actual song durations for accuracy
        last_song = max(self.songs, key=lambda s: s.get('start_time_offset', 0))
        return last_song.get('start_time_offset', 0)


class Workout(models.Model):
    """
    User's specific workout instance (when they completed a class).
    All class information (title, duration, instructor, etc.) comes from RideDetail via SQL joins.
    This model only stores user-specific and workout-instance-specific data.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workouts")
    
    # Reference to the class/ride template (REQUIRED for new workouts - all class data comes from here via SQL joins)
    # Note: nullable=True for backward compatibility with existing workouts, but sync code requires it
    ride_detail = models.ForeignKey(RideDetail, on_delete=models.PROTECT, related_name="workouts", null=True, blank=True, help_text="The class/ride this workout is based on. All class details come from here via SQL joins.")
    
    # Peloton workout ID (unique identifier for this specific workout instance)
    peloton_workout_id = models.CharField(max_length=100, unique=True, blank=True, null=True, db_index=True, help_text="Peloton workout ID (unique per workout instance)")
    
    # Dates (user-specific)
    recorded_date = models.DateField(help_text="Date when workout was originally recorded/created on Peloton")
    completed_date = models.DateField(help_text="Date when user completed this workout")
    
    # Peloton URL (workout-instance-specific)
    peloton_url = models.URLField(blank=True, null=True, help_text="Link to workout on Peloton")
    
    # Sync information
    synced_at = models.DateTimeField(auto_now_add=True, help_text="When this workout was synced from Peloton")
    last_synced_at = models.DateTimeField(auto_now=True, help_text="Last time this workout was synced")
    
    class Meta:
        ordering = ["-completed_date", "-recorded_date"]
        indexes = [
            models.Index(fields=["user", "-completed_date"]),
            models.Index(fields=["ride_detail"]),
            models.Index(fields=["peloton_workout_id"]),
        ]
    
    def __str__(self):
        if self.ride_detail:
            return f"{self.ride_detail.title} - {self.user.username} ({self.completed_date})"
        return f"Workout - {self.user.username} ({self.completed_date})"
    
    # Properties to access RideDetail fields via SQL joins (no duplicate storage)
    # These use SQL joins - data is stored once in RideDetail, accessed via foreign key
    @property
    def title(self):
        """Get title from ride_detail via join"""
        if self.ride_detail:
            return self.ride_detail.title
        return 'Workout'
    
    @property
    def duration_minutes(self):
        """Get duration from ride_detail via join"""
        if self.ride_detail:
            return self.ride_detail.duration_minutes
        return 0
    
    @property
    def workout_type(self):
        """Get workout_type from ride_detail via join"""
        if self.ride_detail:
            return self.ride_detail.workout_type
        return None
    
    @property
    def instructor(self):
        """Get instructor from ride_detail via join"""
        if self.ride_detail:
            return self.ride_detail.instructor
        return None
    
    @property
    def description(self):
        """Get description from ride_detail via join"""
        if self.ride_detail:
            return self.ride_detail.description
        return ''
    
    @property
    def difficulty_rating(self):
        """Get difficulty rating from ride_detail via join"""
        if self.ride_detail:
            return self.ride_detail.difficulty_rating_avg
        return None


class WorkoutDetails(models.Model):
    """
    User-specific performance metrics for a workout.
    Renamed from WorkoutMetrics to better reflect that this is user-specific data.
    """
    workout = models.OneToOneField(Workout, on_delete=models.CASCADE, related_name="details")
    
    # Training Stress Score
    tss = models.FloatField(null=True, blank=True, help_text="Training Stress Score")
    tss_target = models.FloatField(null=True, blank=True, help_text="Target TSS")
    
    # Output metrics (for cycling)
    avg_output = models.FloatField(null=True, blank=True, help_text="Average output in watts")
    total_output = models.FloatField(null=True, blank=True, help_text="Total output in kilojoules")
    max_output = models.FloatField(null=True, blank=True, help_text="Maximum output in watts")
    
    # Speed metrics (for running)
    avg_speed = models.FloatField(null=True, blank=True, help_text="Average speed in mph")
    max_speed = models.FloatField(null=True, blank=True, help_text="Maximum speed in mph")
    
    # Distance
    distance = models.FloatField(null=True, blank=True, help_text="Distance in miles")
    
    # Heart rate
    avg_heart_rate = models.IntegerField(null=True, blank=True, help_text="Average heart rate in bpm")
    max_heart_rate = models.IntegerField(null=True, blank=True, help_text="Maximum heart rate in bpm")
    
    # Cadence (for cycling)
    avg_cadence = models.IntegerField(null=True, blank=True, help_text="Average cadence in rpm")
    max_cadence = models.IntegerField(null=True, blank=True, help_text="Maximum cadence in rpm")
    
    # Resistance (for cycling)
    avg_resistance = models.FloatField(null=True, blank=True, help_text="Average resistance")
    max_resistance = models.FloatField(null=True, blank=True, help_text="Maximum resistance")
    
    # Calories
    total_calories = models.IntegerField(null=True, blank=True, help_text="Total calories burned")
    
    class Meta:
        verbose_name = "Workout Details"
        verbose_name_plural = "Workout Details"
    
    def __str__(self):
        return f"Details for {self.workout.ride_detail.title} - {self.workout.user.username}"


# Alias for backward compatibility
WorkoutMetrics = WorkoutDetails


class WorkoutPerformanceData(models.Model):
    """Time-series performance data for workout graphs (power zones, intensity zones, etc.)"""
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="performance_data")
    
    # Time point in the workout (in seconds from start)
    timestamp = models.IntegerField(help_text="Time in seconds from workout start")
    
    # Power/Output data (for cycling)
    output = models.FloatField(null=True, blank=True, help_text="Output in watts at this timestamp")
    cadence = models.IntegerField(null=True, blank=True, help_text="Cadence in rpm at this timestamp")
    resistance = models.FloatField(null=True, blank=True, help_text="Resistance at this timestamp")
    
    # Speed data (for running)
    speed = models.FloatField(null=True, blank=True, help_text="Speed in mph at this timestamp")
    
    # Heart rate
    heart_rate = models.IntegerField(null=True, blank=True, help_text="Heart rate in bpm at this timestamp")
    
    # Zone information
    power_zone = models.IntegerField(null=True, blank=True, help_text="Power zone (1-7) at this timestamp")
    intensity_zone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("recovery", "Recovery"),
            ("easy", "Easy"),
            ("moderate", "Moderate"),
            ("challenging", "Challenging"),
            ("hard", "Hard"),
            ("very_hard", "Very Hard"),
            ("max", "Max"),
        ],
        help_text="Intensity zone at this timestamp"
    )
    
    class Meta:
        ordering = ["workout", "timestamp"]
        indexes = [
            models.Index(fields=["workout", "timestamp"]),
        ]
        verbose_name_plural = "Workout Performance Data"
    
    def __str__(self):
        return f"{self.workout.ride_detail.title} - {self.timestamp}s"


class PelotonConnection(models.Model):
    """Stores Peloton API connection information for users"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="peloton_connection")
    
    # Connection status
    is_connected = models.BooleanField(default=False)
    connected_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    
    # Peloton user information
    peloton_username = models.CharField(max_length=200, blank=True)
    peloton_user_id = models.CharField(max_length=100, blank=True)
    
    # API credentials (encrypted in production)
    api_token = models.TextField(blank=True, help_text="Peloton API token")
    refresh_token = models.TextField(blank=True, help_text="Peloton API refresh token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Sync settings
    auto_sync_enabled = models.BooleanField(default=False, help_text="Enable automatic syncing")
    sync_frequency_hours = models.IntegerField(default=24, help_text="Hours between automatic syncs")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Peloton Connection"
        verbose_name_plural = "Peloton Connections"
    
    def __str__(self):
        status = "Connected" if self.is_connected else "Disconnected"
        return f"{self.user.username} - {status}"
