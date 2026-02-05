"""Annual Challenge app models."""

from django.conf import settings
from django.db import models


class AnnualChallengeProgress(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="annual_challenge_progress",
	)
	challenge_id = models.CharField(max_length=64, db_index=True)
	minutes_ytd = models.IntegerField(null=True, blank=True)
	metric_display_value = models.CharField(max_length=32, blank=True)
	metric_display_unit = models.CharField(max_length=16, blank=True)
	has_joined = models.BooleanField(default=False)
	challenge_status = models.CharField(max_length=32, blank=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["user", "challenge_id"], name="unique_annual_challenge_progress"),
		]
		ordering = ["-last_synced_at", "-updated_at"]

	def __str__(self):
		return f"AnnualChallengeProgress(user={self.user_id}, challenge_id={self.challenge_id})"
