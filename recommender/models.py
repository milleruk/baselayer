from django.db import models


class InstructorProfile(models.Model):
    """
    Optional curated metadata for instructors (hybrid recommender).
    Keeps Peloton-synced identity in workouts.Instructor and stores human curation here.
    """

    instructor = models.OneToOneField(
        "workouts.Instructor",
        on_delete=models.CASCADE,
        related_name="recommender_profile",
    )

    enabled = models.BooleanField(default=True)

    vibe = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)  # list[str]

    # Not currently populated by Peloton sync, but kept for future parity with reference UI.
    languages = models.JSONField(default=list, blank=True)  # list[str]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["instructor__name"]

    def __str__(self) -> str:
        return f"Profile: {self.instructor.name}"

