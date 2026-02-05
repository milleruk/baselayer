from __future__ import annotations

from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.models import SiteSettings

from .models import AnnualChallengeProgress
from .services import compute_tier_progress, days_elapsed_in_year, days_in_year


@login_required
def index(request):
    today = date.today()
    settings = SiteSettings.get_settings()
    challenge_id = settings.annual_challenge_id
    challenge_name = settings.annual_challenge_name

    progress = None
    if challenge_id:
        progress = AnnualChallengeProgress.objects.filter(
            user=request.user,
            challenge_id=challenge_id,
        ).first()

    has_joined = bool(progress and progress.has_joined and progress.minutes_ytd is not None)
    minutes_ytd = progress.minutes_ytd if has_joined else 0

    elapsed_days = days_elapsed_in_year(today)
    total_days = days_in_year(today.year)
    avg_per_day = (minutes_ytd / elapsed_days) if (elapsed_days and has_joined) else 0.0
    avg_per_week = avg_per_day * 7.0

    tier_rows = compute_tier_progress(minutes_ytd=minutes_ytd, today=today) if has_joined else []

    if not challenge_id:
        join_message = "Annual challenge is not configured yet."
    elif not has_joined:
        join_message = "Join the Peloton annual challenge, then sync to see your progress here."
    else:
        join_message = None

    context = {
        "minutes_ytd": minutes_ytd,
        "avg_per_day": avg_per_day,
        "avg_per_week": avg_per_week,
        "has_joined": has_joined,
        "join_message": join_message,
        "last_synced_at": progress.last_synced_at if progress else None,
        "challenge_id": challenge_id,
        "challenge_name": challenge_name,
        "year": today.year,
        "tier_rows": tier_rows,
    }
    return render(request, "annual_challenge/index.html", context)

