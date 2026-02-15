import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from workouts.models import Workout, WorkoutType, RideDetail
from django.db import transaction

def infer_discipline_from_device_and_title(device_type, title):
    device_type = (device_type or '').lower()
    title = (title or '').lower()
    if device_type == 'garmin connect':
        return 'other'
    if 'bike' in device_type or 'bike +' in device_type:
        return 'cycling'
    if 'tread' in device_type or 'tread +' in device_type:
        return 'running'
    if device_type == 'app':
        # App could be anything, fallback to title
        pass
    # Title heuristics
    if 'cycle' in title or 'bike' in title:
        return 'cycling'
    if 'yoga' in title:
        return 'yoga'
    if 'row' in title:
        return 'rowing'
    if 'run' in title:
        return 'running'
    if 'walk' in title:
        return 'walking'
    if 'strength' in title:
        return 'strength'
    if 'stretch' in title:
        return 'stretching'
    if 'meditat' in title:
        return 'meditation'
    if 'cardio' in title:
        return 'cardio'
    return 'other'

type_mapping = {
    'cycling': 'cycling',
    'running': 'running',
    'walking': 'walking',
    'yoga': 'yoga',
    'strength': 'strength',
    'stretching': 'stretching',
    'meditation': 'meditation',
    'cardio': 'cardio',
    'rowing': 'rowing',
    'other': 'other',
}

def patch_single_workout(workout_id):
    try:
        workout = Workout.objects.get(id=workout_id)
    except Workout.DoesNotExist:
        print(f"Workout with id {workout_id} does not exist.")
        return
    device_type = getattr(workout, 'device_type_display_name', None)
    title = workout.title_override or (workout.ride_detail.title if workout.ride_detail else workout.title)
    inferred = infer_discipline_from_device_and_title(device_type, title)
    mapped = type_mapping.get(inferred, 'other')
    orig_type = workout.ride_detail.workout_type.slug if workout.ride_detail and workout.ride_detail.workout_type else None
    if orig_type != mapped:
        wt, _ = WorkoutType.objects.get_or_create(slug=mapped, defaults={'name': mapped.title()})
        workout.ride_detail.workout_type = wt
        workout.ride_detail.save()
        print(f"Patched workout {workout.id}: '{title}' from '{orig_type}' to '{mapped}'")
    else:
        print(f"Workout {workout.id} already has correct type '{mapped}'. No change.")

if __name__ == "__main__":
    patch_single_workout(6658)
