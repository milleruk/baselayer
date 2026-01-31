from __future__ import annotations

from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from workouts.models import Workout

from .services import compute_tier_progress, days_elapsed_in_year, days_in_year


@login_required
def index(request):
    today = date.today()
    year_start = date(today.year, 1, 1)
    year_end = date(today.year, 12, 31)

    total_minutes = (
        Workout.objects.filter(user=request.user, completed_date__gte=year_start, completed_date__lte=year_end)
        .aggregate(total=Sum("ride_detail__duration_seconds"))
        .get("total")
    )
    minutes_ytd = int((int(total_minutes) if total_minutes else 0) / 60)

    elapsed_days = days_elapsed_in_year(today)
    total_days = days_in_year(today.year)
    avg_per_day = (minutes_ytd / elapsed_days) if elapsed_days else 0.0
    avg_per_week = avg_per_day * 7.0

    tier_rows = compute_tier_progress(minutes_ytd=minutes_ytd, today=today)

    context = {
        "minutes_ytd": minutes_ytd,
        "avg_per_day": avg_per_day,
        "avg_per_week": avg_per_week,
        "year": today.year,
        "tier_rows": tier_rows,
    }
    return render(request, "annual_challenge/index.html", context)

