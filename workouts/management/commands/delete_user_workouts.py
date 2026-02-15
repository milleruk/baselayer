from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from workouts.models import Workout

class Command(BaseCommand):
    help = 'Delete all Workout objects for a specific user (by email/username)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user to delete workouts for')

    def handle(self, *args, **options):
        email = options['email']
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with email '{email}' not found."))
            return
        qs = Workout.objects.filter(user=user)
        count = qs.count()
        self.stdout.write(f"Deleting {count} workouts for user {email}...")
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} workouts for user {email}."))
