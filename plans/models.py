from django.conf import settings
from django.db import models

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
