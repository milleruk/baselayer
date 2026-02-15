
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django
import logging

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from workouts.models import Workout, WorkoutType, RideDetail
from django.db import transaction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workout_patch")

def infer_discipline_from_title(title):
    title = (title or '').lower()
    if 'cycle' in title or 'bike' in title:
        return 'cycling'
    elif 'yoga' in title:
        return 'yoga'
    elif 'row' in title:
        return 'rowing'
    elif 'run' in title:
        return 'running'
    elif 'walk' in title:
        return 'walking'
    elif 'strength' in title:
        return 'strength'
    elif 'stretch' in title:
        return 'stretching'
    elif 'meditat' in title:
        return 'meditation'
    elif 'cardio' in title:
        return 'cardio'
    else:
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
}

def patch_manual_workouts():
    manual_workouts = Workout.objects.filter(ride_detail__peloton_ride_id__startswith='manual_')
    logger.info(f"Found {manual_workouts.count()} manual/third-party workouts to check.")
    patched = 0
    with transaction.atomic():
        for workout in manual_workouts:
            orig_type = workout.ride_detail.workout_type.slug if workout.ride_detail and workout.ride_detail.workout_type else None
            inferred = infer_discipline_from_title(workout.title_override or workout.ride_detail.title or workout.title)
            mapped = type_mapping.get(inferred, 'other')
            if orig_type != mapped:
                wt, _ = WorkoutType.objects.get_or_create(slug=mapped, defaults={'name': mapped.title()})
                workout.ride_detail.workout_type = wt
                workout.ride_detail.save()
                logger.info(f"Patched workout {workout.id}: '{workout.title}' from '{orig_type}' to '{mapped}'")
                patched += 1
    logger.info(f"Patched {patched} workouts.")

if __name__ == "__main__":
    patch_manual_workouts()
