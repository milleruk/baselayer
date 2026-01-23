from django.conf import settings
from django.db import models
from django.utils import timezone


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
    peloton_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ["name"]
    
    def __str__(self):
        return self.name


class Workout(models.Model):
    """Main workout model storing Peloton workout data"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workouts")
    workout_type = models.ForeignKey(WorkoutType, on_delete=models.PROTECT, related_name="workouts")
    instructor = models.ForeignKey(Instructor, on_delete=models.PROTECT, related_name="workouts", null=True, blank=True)
    
    # Basic information
    title = models.CharField(max_length=500)
    duration_minutes = models.IntegerField(help_text="Workout duration in minutes")
    
    # Peloton integration
    peloton_id = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Peloton workout ID")
    peloton_url = models.URLField(blank=True, null=True, help_text="Link to workout on Peloton")
    
    # Dates
    recorded_date = models.DateField(help_text="Date when workout was originally recorded/created on Peloton")
    completed_date = models.DateField(help_text="Date when user completed this workout")
    
    # Sync information
    synced_at = models.DateTimeField(auto_now_add=True, help_text="When this workout was synced from Peloton")
    last_synced_at = models.DateTimeField(auto_now=True, help_text="Last time this workout was synced")
    
    # Additional metadata
    description = models.TextField(blank=True)
    difficulty_rating = models.FloatField(null=True, blank=True, help_text="Workout difficulty rating")
    total_ratings = models.IntegerField(default=0, help_text="Total number of ratings")
    
    class Meta:
        ordering = ["-completed_date", "-recorded_date"]
        indexes = [
            models.Index(fields=["user", "-completed_date"]),
            models.Index(fields=["workout_type"]),
            models.Index(fields=["instructor"]),
            models.Index(fields=["peloton_id"]),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username} ({self.completed_date})"


class WorkoutMetrics(models.Model):
    """Metrics for a workout (TSS, output, distance, speed, etc.)"""
    workout = models.OneToOneField(Workout, on_delete=models.CASCADE, related_name="metrics")
    
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
        verbose_name_plural = "Workout Metrics"
    
    def __str__(self):
        return f"Metrics for {self.workout.title}"


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
        return f"{self.workout.title} - {self.timestamp}s"


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
