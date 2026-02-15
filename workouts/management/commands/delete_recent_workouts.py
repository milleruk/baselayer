from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from workouts.models import Workout

class Command(BaseCommand):
    help = 'Delete all Workout objects created or updated after or on Feb 14, 2026 (UTC)'

    def handle(self, *args, **options):
        cutoff = timezone.datetime(2026, 2, 14, tzinfo=timezone.utc)
        qs = Workout.objects.filter(
            models.Q(synced_at__gte=cutoff) | models.Q(last_synced_at__gte=cutoff)
        )
        count = qs.count()
        self.stdout.write(f"Deleting {count} workouts created/updated on or after 2026-02-14...")
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} workouts."))
