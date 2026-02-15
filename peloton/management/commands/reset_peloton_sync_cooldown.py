from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from peloton.models import PelotonConnection
from django.utils import timezone

class Command(BaseCommand):
    help = 'Reset Peloton sync cooldown for a user by email.'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user to reset sync cooldown for')

    def handle(self, *args, **options):
        email = options['email']
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with email '{email}' not found."))
            return
        qs = PelotonConnection.objects.filter(user=user)
        count = 0
        for conn in qs:
            conn.sync_cooldown_until = timezone.now() - timezone.timedelta(minutes=1)
            conn.save(update_fields=['sync_cooldown_until'])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Reset sync cooldown for {count} Peloton connection(s) for user {email}."))
