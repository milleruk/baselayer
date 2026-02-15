import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from workouts.models import Workout

def print_workout_fields(workout_id):
    try:
        workout = Workout.objects.get(id=workout_id)
    except Workout.DoesNotExist:
        print(f"Workout with id {workout_id} does not exist.")
        return
    print(f"id: {workout.id}")
    print(f"title: {workout.title}")
    print(f"title_override: {getattr(workout, 'title_override', None)}")
    if workout.ride_detail:
        print(f"ride_detail.title: {workout.ride_detail.title}")
    else:
        print("ride_detail: None")

if __name__ == "__main__":
    print_workout_fields(6658)
