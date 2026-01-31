from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from workouts.models import RideDetail

from .services import recommend_instructors, suggest_instructors


def _discipline_options() -> list[str]:
    vals = (
        RideDetail.objects.exclude(fitness_discipline__isnull=True)
        .exclude(fitness_discipline__exact="")
        .values_list("fitness_discipline", flat=True)
        .distinct()
    )
    out = sorted({(v or "").strip().lower() for v in vals if v})
    return out


@login_required
def index(request):
    discipline = (request.GET.get("discipline") or "").strip().lower() or None

    # New, list-based flow uses instructor names as values.
    love_1_name = (request.GET.get("love_1") or "").strip()
    love_2_name = (request.GET.get("love_2") or "").strip()
    exclude_name = (request.GET.get("exclude") or "").strip()

    results = []
    error = None

    try:
        if love_1_name and love_2_name:
            results = recommend_instructors(
                love_1_name=love_1_name,
                love_2_name=love_2_name,
                exclude_name=exclude_name or None,
                discipline_filter=discipline,
                limit=3,
            )
    except Exception:
        error = "Could not compute recommendations for those inputs."

    context = {
        "discipline_options": _discipline_options(),
        "discipline": discipline or "",
        "love_1_name": love_1_name,
        "love_2_name": love_2_name,
        "exclude_name": exclude_name,
        "results": results,
        "error": error,
    }
    return render(request, "recommender/index.html", context)


@login_required
def suggest(request):
    q = (request.GET.get("q") or "").strip()
    discipline = (request.GET.get("discipline") or "").strip().lower() or None

    results = suggest_instructors(q=q, discipline_filter=discipline, limit=12)
    return JsonResponse({"results": results})

