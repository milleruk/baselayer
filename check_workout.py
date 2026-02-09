#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from workouts.models import Workout
from django.utils import timezone

# Check the workout
w = Workout.objects.filter(peloton_workout_id='31dd5aca99fa4f9780415dd1eea41cd7').first()
print(f'Workout found: {w is not None}')
if w:
    print(f'Current date: {w.completed_date}')
    # If peloton_created_at exists, use its date
    if w.peloton_created_at:
        utc_date = w.peloton_created_at.date()
        print(f'Peloton created_at date: {utc_date}')
        if w.completed_date != utc_date:
            w.completed_date = utc_date
            w.save()
            print(f'Updated completed_date to: {utc_date}')
        else:
            print('Date already correct')
    else:
        print('No peloton_created_at to update from')