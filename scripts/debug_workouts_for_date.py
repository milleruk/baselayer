import os
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, datetime
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from workouts.models import Workout

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug workouts for a specific date and user.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Username/email to check')
        parser.add_argument('--date', type=str, required=True, help='Date to check (YYYY-MM-DD)')

    def handle(self, *args, **options):
        username = options['username']
        date_str = options['date']
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" does not exist'))
            return
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            self.stdout.write(self.style.ERROR(f'Invalid date format: {date_str}'))
            return

        # Query all workouts for that UTC date
        qs = Workout.objects.filter(user=user, completed_at__date=target_date)
        self.stdout.write(f"Workouts for {username} on {target_date} (UTC): {qs.count()}")
        for w in qs:
            self.stdout.write(f"  ID: {w.id}, completed_at: {w.completed_at}, peloton_workout_id: {w.peloton_workout_id}, ride_detail: {getattr(w.ride_detail, 'title', None)}")
            self.stdout.write(f"    peloton_created_at: {w.peloton_created_at}, peloton_timezone: {w.peloton_timezone}, completed_date: {w.completed_date}")
