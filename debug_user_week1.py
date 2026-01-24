#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from challenges.models import ChallengeInstance
from tracker.models import WeeklyPlan
from challenges.views import sunday_of_current_week
from datetime import date, timedelta

User = get_user_model()
user = User.objects.get(id=3)
print(f'User: {user.email} ({user.first_name} {user.last_name})')

ci = ChallengeInstance.objects.filter(user=user, is_active=True).first()
if not ci:
    print('No active challenge instance found')
    exit()

challenge = ci.challenge
print(f'Challenge: {challenge.name}')
print(f'Challenge start: {challenge.start_date}')

challenge_start = challenge.start_date
first_week_start = sunday_of_current_week(challenge_start)
print(f'First week start (Sunday): {first_week_start}')

# Check all weekly plans
all_plans = ci.weekly_plans.all().order_by('week_start')
print(f'\nAll weekly plans for this user:')
for plan in all_plans:
    print(f'  Week start: {plan.week_start}, Points: {plan.total_points}, Completed: {plan.completed_at is not None}')

week_plan = ci.weekly_plans.filter(week_start=first_week_start).first()
if not week_plan:
    print(f'\nNo week 1 plan found for week_start={first_week_start}')
    # Try to find the first plan
    first_plan = all_plans.first()
    if first_plan:
        print(f'First plan found with week_start={first_plan.week_start}')
        week_plan = first_plan
    else:
        print('No plans found at all')
        exit()

print(f'\nWeek 1 Plan Details:')
print(f'  Week start: {week_plan.week_start}')
print(f'  Total points: {week_plan.total_points}')
print(f'  Core workout count (days with workouts): {week_plan.core_workout_count}')
print(f'  Completed core workouts (days completed): {week_plan.completed_core_workouts}')
print(f'  Completion rate: {week_plan.completion_rate:.1f}%')
print(f'  Completed at: {week_plan.completed_at}')

# Check completion logic
core_count = week_plan.core_workout_count
completed_core_count = week_plan.completed_core_workouts
is_completed = (core_count > 0 and completed_core_count >= core_count) or bool(week_plan.completed_at)
print(f'\nCompletion Check:')
print(f'  Core count: {core_count}')
print(f'  Completed count: {completed_core_count}')
print(f'  Is completed: {is_completed}')

# Check items
print(f'\nItems with activities:')
from django.db.models import Q
items = week_plan.items.filter(
    Q(ride_done=True) | Q(run_done=True) | Q(yoga_done=True) | Q(strength_done=True)
)
print(f'  Total items with activities done: {items.count()}')
for item in items.order_by('day_of_week'):
    activities = []
    if item.ride_done:
        activities.append('ride')
    if item.run_done:
        activities.append('run')
    if item.yoga_done:
        activities.append('yoga')
    if item.strength_done:
        activities.append('strength')
    print(f'  Day {item.day_of_week}: {item.peloton_focus} - {", ".join(activities) if activities else "none"}')

# Check all items with workouts assigned
print(f'\nAll items with workouts assigned:')
workout_items = week_plan.items.filter(
    (Q(peloton_ride_url__isnull=False) & ~Q(peloton_ride_url='')) |
    (Q(peloton_run_url__isnull=False) & ~Q(peloton_run_url='')) |
    (Q(peloton_yoga_url__isnull=False) & ~Q(peloton_yoga_url='')) |
    (Q(peloton_strength_url__isnull=False) & ~Q(peloton_strength_url=''))
).exclude(peloton_focus__icontains="Bonus")

days_with_workouts = set()
for item in workout_items:
    days_with_workouts.add(item.day_of_week)

print(f'  Days with workouts assigned: {sorted(days_with_workouts)}')
print(f'  Total days: {len(days_with_workouts)}')

days_completed = set()
for item in items:
    days_completed.add(item.day_of_week)

print(f'  Days with completed activities: {sorted(days_completed)}')
print(f'  Total days completed: {len(days_completed)}')
