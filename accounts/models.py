from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model that uses email instead of username"""
    username = None  # Remove username field
    email = models.EmailField(unique=True, verbose_name='email address')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required as USERNAME_FIELD
    
    objects = UserManager()
    
    class Meta:
        db_table = 'accounts_user'
    
    def __str__(self):
        return self.email


class Profile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    # Peloton integration
    peloton_leaderboard_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Peloton leaderboard name (synced from Peloton account)"
    )
    peloton_total_workouts = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total number of Peloton workouts completed"
    )
    peloton_total_output = models.BigIntegerField(
        blank=True,
        null=True,
        help_text="Total output in kilojoules from all Peloton workouts"
    )
    peloton_total_distance = models.FloatField(
        blank=True,
        null=True,
        help_text="Total distance in miles from all Peloton workouts"
    )
    peloton_total_calories = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total calories burned from all Peloton workouts"
    )
    peloton_total_pedaling_duration = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total pedaling duration in seconds"
    )
    peloton_last_synced_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last time Peloton data was synced"
    )
    
    # Peloton workout breakdown
    peloton_total_pedaling_metric_workouts = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total number of Peloton workouts with pedaling metrics (cycling, etc.)"
    )
    peloton_total_non_pedaling_metric_workouts = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total number of Peloton workouts without pedaling metrics (meditation, strength, etc.)"
    )
    
    # Peloton streaks
    peloton_current_weekly_streak = models.IntegerField(
        blank=True,
        null=True,
        help_text="Current weekly workout streak"
    )
    peloton_best_weekly_streak = models.IntegerField(
        blank=True,
        null=True,
        help_text="Best weekly workout streak achieved"
    )
    peloton_current_daily_streak = models.IntegerField(
        blank=True,
        null=True,
        help_text="Current daily workout streak"
    )
    
    # Peloton achievements
    peloton_total_achievements = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total number of Peloton achievements earned"
    )
    
    # Peloton workout type breakdown (stored as JSON)
    peloton_workout_counts = models.JSONField(
        blank=True,
        null=True,
        help_text="Breakdown of Peloton workouts by type (slug -> count)"
    )
    
    # Cycling metrics
    ftp_score = models.IntegerField(
        blank=True, 
        null=True, 
        help_text="Functional Threshold Power (FTP) in watts. Used to calculate power zones 1-7 for bike/cycle rides."
    )
    
    # Running metrics
    pace_target_level = models.IntegerField(
        blank=True,
        null=True,
        choices=[(i, str(i)) for i in range(1, 11)],
        help_text="Pace target level (1-10). Used to calculate pace zones (Recovery, Easy, Moderate, Challenging, Hard, Very Hard, Max) for runs/walks."
    )
    
    class Meta:
        db_table = 'accounts_profile'
    
    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    def get_current_ftp(self):
        """Get the current active FTP value from FTPEntry, fallback to ftp_score"""
        active_ftp = self.user.ftp_entries.filter(is_active=True).first()
        if active_ftp:
            return active_ftp.ftp_value
        return self.ftp_score
    
    def get_ftp_at_date(self, date):
        """
        Get the FTP value that was active at a specific date.
        Returns the most recent FTP entry with recorded_date <= date, or current FTP if none found.
        """
        from django.db.models import Q
        
        # Get FTP entries recorded on or before the workout date, ordered by most recent first
        ftp_entry = self.user.ftp_entries.filter(
            recorded_date__lte=date
        ).order_by('-recorded_date', '-created_at').first()
        
        if ftp_entry:
            return ftp_entry.ftp_value
        
        # Fallback to current FTP
        return self.get_current_ftp()
    
    def get_current_pace(self, activity_type='running'):
        """Get the current active pace level from PaceEntry for the given activity type"""
        active_pace = self.user.pace_entries.filter(
            activity_type=activity_type, 
            is_active=True
        ).first()
        if active_pace:
            return active_pace.level
        return None
    
    def get_pace_at_date(self, date, activity_type='running'):
        """
        Get the pace level that was active at a specific date.
        Returns the most recent PaceEntry with recorded_date <= date for the given activity type,
        or current pace if none found.
        """
        from django.db.models import Q
        
        # Get pace entries recorded on or before the workout date, ordered by most recent first
        pace_entry = self.user.pace_entries.filter(
            activity_type=activity_type,
            recorded_date__lte=date
        ).order_by('-recorded_date', '-created_at').first()
        
        if pace_entry:
            return pace_entry.level
        
        # Fallback to current active pace
        return self.get_current_pace(activity_type=activity_type)
    
    def get_power_zone_ranges(self):
        """Calculate power zone ranges based on FTP (zones 1-7)"""
        ftp = self.get_current_ftp()
        if not ftp:
            return None
        
        return {
            1: (0, int(ftp * 0.55)),           # Zone 1: 0-55% FTP
            2: (int(ftp * 0.55), int(ftp * 0.75)),  # Zone 2: 55-75% FTP
            3: (int(ftp * 0.75), int(ftp * 0.90)),  # Zone 3: 75-90% FTP
            4: (int(ftp * 0.90), int(ftp * 1.05)),  # Zone 4: 90-105% FTP
            5: (int(ftp * 1.05), int(ftp * 1.20)),  # Zone 5: 105-120% FTP
            6: (int(ftp * 1.20), int(ftp * 1.50)),  # Zone 6: 120-150% FTP
            7: (int(ftp * 1.50), None)              # Zone 7: 150%+ FTP
        }
    
    def get_pace_zone_targets(self):
        """Calculate pace zone targets based on pace target level (1-10)"""
        if not self.pace_target_level:
            return None
        
        # Base paces (min/mile) for each level - these will be adjusted based on user's actual fitness
        # Level 1 = slowest, Level 10 = fastest
        base_paces = {
            1: 12.0,   # 12:00/mile
            2: 11.0,   # 11:00/mile
            3: 10.0,   # 10:00/mile
            4: 9.0,    # 9:00/mile
            5: 8.5,    # 8:30/mile
            6: 8.0,    # 8:00/mile
            7: 7.5,    # 7:30/mile
            8: 7.0,    # 7:00/mile
            9: 6.5,    # 6:30/mile
            10: 6.0    # 6:00/mile
        }
        
        base_pace = base_paces.get(self.pace_target_level, 8.0)
        
        # Calculate pace zones (faster pace = lower min/mile number)
        return {
            'recovery': base_pace + 2.0,      # Recovery: +2:00/mile
            'easy': base_pace + 1.0,          # Easy: +1:00/mile
            'moderate': base_pace,            # Moderate: base pace
            'challenging': base_pace - 0.5,   # Challenging: -0:30/mile
            'hard': base_pace - 1.0,          # Hard: -1:00/mile
            'very_hard': base_pace - 1.5,     # Very Hard: -1:30/mile
            'max': base_pace - 2.0            # Max: -2:00/mile
        }


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a profile when a user is created"""
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class WeightEntry(models.Model):
    """User weight tracking entries"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weight_entries')
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in pounds")
    recorded_date = models.DateField(help_text="Date when weight was recorded")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_date', '-created_at']
        unique_together = ('user', 'recorded_date')
    
    def __str__(self):
        return f"{self.user.email} - {self.weight} lbs on {self.recorded_date}"


class FTPEntry(models.Model):
    """User FTP (Functional Threshold Power) tracking entries"""
    SOURCE_CHOICES = [
        ('manual', 'Manually Added'),
        ('ftp_test', 'FTP Test'),
        ('ai_detected', 'AI Detected'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ftp_entries')
    ftp_value = models.IntegerField(help_text="FTP value in watts")
    recorded_date = models.DateField(help_text="Date when FTP was recorded")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual', help_text="How the FTP was determined")
    is_active = models.BooleanField(default=True, help_text="Whether this FTP is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_date', '-created_at']
        db_table = 'accounts_ftpentry'
    
    def __str__(self):
        return f"{self.user.email} - {self.ftp_value}W on {self.recorded_date} ({self.get_source_display()})"


class PaceEntry(models.Model):
    """User pace tracking entries for running and walking - tracks level (1-10)"""
    ACTIVITY_TYPE_CHOICES = [
        ('running', 'Running'),
        ('walking', 'Walking'),
    ]
    
    SOURCE_CHOICES = [
        ('manual', 'Manually Added'),
        ('pace_test', 'Pace Test'),
        ('ai_detected', 'AI Detected'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pace_entries')
    level = models.IntegerField(help_text="Pace level (1-10)", choices=[(i, f'Level {i}') for i in range(1, 11)], default=5)
    activity_type = models.CharField(max_length=10, choices=ACTIVITY_TYPE_CHOICES, help_text="Running or Walking")
    recorded_date = models.DateField(help_text="Date when pace level was recorded")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual', help_text="How the pace level was determined")
    is_active = models.BooleanField(default=True, help_text="Whether this pace level is currently active for this activity type")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_date', '-created_at']
        db_table = 'accounts_paceentry'
        unique_together = ('user', 'activity_type', 'recorded_date', 'source')
    
    def __str__(self):
        return f"{self.user.email} - Level {self.level} ({self.get_activity_type_display()}) on {self.recorded_date} ({self.get_source_display()})"


class PaceLevel(models.Model):
    """User-defined pace level definitions with pace bands"""
    ACTIVITY_TYPE_CHOICES = [
        ('running', 'Running'),
        ('walking', 'Walking'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pace_levels')
    activity_type = models.CharField(max_length=10, choices=ACTIVITY_TYPE_CHOICES, default='running', help_text="Running or Walking")
    level = models.IntegerField(help_text="Pace level (1-10)")
    recorded_date = models.DateField(help_text="Date when this pace level was set")
    notes = models.TextField(blank=True, help_text="Optional notes about this pace level")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-recorded_date', '-level']
        db_table = 'accounts_pacelevel'
        unique_together = ('user', 'activity_type', 'level', 'recorded_date')
    
    def __str__(self):
        return f"{self.user.email} - Level {self.level} ({self.get_activity_type_display()}) on {self.recorded_date}"


class PaceBand(models.Model):
    """Individual pace band within a pace level"""
    # Running zones
    RUNNING_ZONE_CHOICES = [
        ('recovery', 'Recovery'),
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('challenging', 'Challenging'),
        ('hard', 'Hard'),
        ('very_hard', 'Very Hard'),
        ('max', 'Max'),
    ]
    # Walking zones
    WALKING_ZONE_CHOICES = [
        ('recovery', 'Recovery'),
        ('easy', 'Easy'),
        ('brisk', 'Brisk'),
        ('power', 'Power'),
        ('max', 'Max'),
    ]
    
    pace_level = models.ForeignKey(PaceLevel, on_delete=models.CASCADE, related_name='bands')
    zone = models.CharField(max_length=20, help_text="Pace zone name")
    min_mph = models.DecimalField(max_digits=4, decimal_places=1, help_text="Minimum speed in MPH")
    max_mph = models.DecimalField(max_digits=4, decimal_places=1, help_text="Maximum speed in MPH")
    min_pace = models.DecimalField(max_digits=5, decimal_places=2, help_text="Minimum pace in min/mile")
    max_pace = models.DecimalField(max_digits=5, decimal_places=2, help_text="Maximum pace in min/mile")
    description = models.CharField(max_length=255, blank=True, help_text="Description of this pace zone")
    
    class Meta:
        ordering = ['zone']
        db_table = 'accounts_paceband'
        unique_together = ('pace_level', 'zone')
    
    def __str__(self):
        return f"{self.pace_level} - {self.zone.title()}"
    
    def get_zone_display(self):
        """Get display name for zone"""
        zone_map = {
            'recovery': 'Recovery',
            'easy': 'Easy',
            'moderate': 'Moderate',
            'challenging': 'Challenging',
            'hard': 'Hard',
            'very_hard': 'Very Hard',
            'brisk': 'Brisk',
            'power': 'Power',
            'max': 'Max',
        }
        return zone_map.get(self.zone, self.zone.title())
