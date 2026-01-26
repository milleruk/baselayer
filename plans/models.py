from django.conf import settings
from django.db import models
from django.utils import timezone
import secrets

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
