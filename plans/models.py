from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.cache import cache
import secrets
import json

def exercise_image_path(instance, filename):
    """Generate path for exercise images"""
    return f'exercises/{instance.name.replace(" ", "_")}/{filename}'

class Exercise(models.Model):
    CATEGORY_CHOICES = [
        ("kegel", "Kegel"),
        ("mobility", "Mobility"),
        ("yoga", "Yoga"),
    ]
    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    position = models.CharField(max_length=120, blank=True)
    key_cue = models.TextField()
    reps_hold = models.CharField(max_length=60)
    primary_use = models.CharField(max_length=120, blank=True)
    video_url = models.URLField(blank=True)
    image = models.ImageField(upload_to=exercise_image_path, blank=True, null=True, help_text="Image showing the exercise")

    def __str__(self):
        return self.name


class PlanTemplate(models.Model):
    """
    Defines a reusable weekly structure (e.g., PZE Mon, Run Tue, Yoga Wed...)
    """
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class PlanTemplateDay(models.Model):
    DAY_CHOICES = [
        (0, "Sun"), (1, "Mon"), (2, "Tue"), (3, "Wed"),
        (4, "Thu"), (5, "Fri"), (6, "Sat"),
    ]
    template = models.ForeignKey(PlanTemplate, on_delete=models.CASCADE, related_name="days")
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    peloton_focus = models.CharField(max_length=120)  # e.g. "PZE (Z2)", "Run Tempo", "Yoga Recovery"
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("template", "day_of_week")
        ordering = ["day_of_week"]

    def __str__(self):
        return f"{self.template.name} - {self.get_day_of_week_display()}"


class RecapShare(models.Model):
    """Model for sharing yearly recap pages publicly"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recap_shares")
    year = models.IntegerField(help_text="Year for this recap")
    token = models.CharField(max_length=64, unique=True, db_index=True, help_text="Unique token for the share link")
    is_enabled = models.BooleanField(default=True, help_text="Whether this share link is active")
    view_count = models.IntegerField(default=0, help_text="Number of times this recap has been viewed")
    last_viewed_at = models.DateTimeField(null=True, blank=True, help_text="Last time this recap was viewed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("user", "year")
        ordering = ["-year", "-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "year"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.year} Recap"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    
    def regenerate_token(self):
        """Regenerate the share token"""
        self.token = secrets.token_urlsafe(32)
        self.save(update_fields=['token'])
    
    def increment_view_count(self):
        """Increment view count and update last viewed timestamp"""
        self.view_count += 1
        self.last_viewed_at = timezone.now()
        self.save(update_fields=['view_count', 'last_viewed_at'])
    
    def is_valid(self):
        """Check if the share link is valid (enabled)"""
        return self.is_enabled
    
    @classmethod
    def get_or_create_for_user_year(cls, user, year):
        """Get or create a RecapShare for a user and year"""
        share, created = cls.objects.get_or_create(
            user=user,
            year=year,
            defaults={'is_enabled': True}
        )
        return share, created


class RecapCache(models.Model):
    """Cache for yearly recap data to reduce database load"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recap_caches")
    year = models.IntegerField(help_text="Year for this recap cache")
    
    # Store all calculated metrics as JSON
    daily_activities = models.JSONField(default=dict, blank=True)
    daily_calories = models.JSONField(default=dict, blank=True)
    daily_power = models.JSONField(default=dict, blank=True)
    distance_stats = models.JSONField(default=dict, blank=True)
    total_hours = models.JSONField(default=dict, blank=True)
    streaks = models.JSONField(default=dict, blank=True)
    rest_days = models.JSONField(default=dict, blank=True)
    start_times = models.JSONField(default=dict, blank=True)
    activity_count = models.JSONField(default=dict, blank=True)
    training_load = models.JSONField(default=dict, blank=True)
    personal_records = models.JSONField(default=dict, blank=True)
    consistency_metrics = models.JSONField(default=dict, blank=True)
    summary_stats = models.JSONField(default=dict, blank=True)
    top_instructors = models.JSONField(default=dict, blank=True)
    top_songs = models.JSONField(default=dict, blank=True)
    duration_distribution = models.JSONField(default=dict, blank=True)
    peak_performance = models.JSONField(default=dict, blank=True)
    elevation_stats = models.JSONField(default=dict, blank=True)
    weekday_patterns = models.JSONField(default=dict, blank=True)
    workout_type_breakdown = models.JSONField(default=dict, blank=True)
    progress_over_time = models.JSONField(default=dict, blank=True)
    best_workouts_by_discipline = models.JSONField(default=dict, blank=True)
    calorie_efficiency = models.JSONField(default=dict, blank=True)
    average_metrics_breakdown = models.JSONField(default=dict, blank=True)
    monthly_comparison = models.JSONField(default=dict, blank=True)
    favorite_class_types = models.JSONField(default=dict, blank=True)
    time_of_day_patterns = models.JSONField(default=dict, blank=True)
    year_over_year = models.JSONField(default=dict, blank=True)
    challenge_participation = models.JSONField(default=dict, blank=True)
    intensity_zones = models.JSONField(default=dict, blank=True)
    distance_milestones = models.JSONField(default=dict, blank=True)
    consistency_score = models.JSONField(default=dict, blank=True)
    heart_rate_zones = models.JSONField(default=dict, blank=True)
    cadence_resistance_trends = models.JSONField(default=dict, blank=True)
    yearly_calendar = models.JSONField(default=dict, blank=True)
    
    # Metadata
    total_workouts_count = models.IntegerField(default=0)
    last_workout_updated_at = models.DateTimeField(null=True, blank=True)
    last_regenerated_at = models.DateTimeField(null=True, blank=True, help_text="Last time user manually regenerated this cache")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("user", "year")
        ordering = ["-year", "-updated_at"]
        indexes = [
            models.Index(fields=["user", "year"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.year} Recap Cache"
    
    def is_stale(self):
        """Check if cache is stale (needs recalculation)"""
        from workouts.models import Workout
        
        # Check if cache exists
        if not self.id:
            return True
        
        # If cache has 0 workouts but workouts exist, cache is stale
        if self.total_workouts_count == 0:
            workout_count = Workout.objects.filter(
                user=self.user,
                completed_date__year=self.year
            ).count()
            if workout_count > 0:
                # Workouts exist but cache says 0 - cache is stale
                return True
        
        # Check if workouts have been updated since cache was created
        if self.last_workout_updated_at:
            latest_workout = Workout.objects.filter(
                user=self.user,
                completed_date__year=self.year
            ).order_by('-last_synced_at').values_list('last_synced_at', flat=True).first()
            
            if latest_workout and latest_workout > self.last_workout_updated_at:
                return True
        
        # Check Django cache for fast staleness check
        cache_key = f"recap_cache_stale_{self.user.id}_{self.year}"
        is_stale_cached = cache.get(cache_key)
        if is_stale_cached is not None:
            return is_stale_cached
        
        # Default: cache is valid
        return False
    
    @classmethod
    def get_cache_for_user_year(cls, user, year):
        """Get cache for user and year if it exists and is not stale"""
        try:
            cache_obj = cls.objects.get(user=user, year=year)
            if not cache_obj.is_stale():
                return cache_obj
        except cls.DoesNotExist:
            pass
        return None
    
    @classmethod
    def get_or_create_for_user_year(cls, user, year):
        """Get or create cache for user and year"""
        cache_obj, created = cls.objects.get_or_create(
            user=user,
            year=year,
            defaults={}
        )
        return cache_obj, created
    
    @classmethod
    def invalidate_for_user_year(cls, user, year):
        """Invalidate cache for user and year"""
        cache_key = f"recap_cache_stale_{user.id}_{year}"
        cache.set(cache_key, True, 3600)  # Mark as stale for 1 hour
        cls.objects.filter(user=user, year=year).delete()
