from datetime import date, timedelta
import json

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Avg, Count, DateField, F, Sum
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import TruncWeek
from django.shortcuts import render
from django.utils import timezone
from django.utils.safestring import mark_safe

from core.services import DateRangeService
from plans.services import get_dashboard_period, get_dashboard_challenge_context


def _dash_cache_key(user_id: int, period: str, hide_manual: bool) -> str:
    return f"ctz:dash:v3:user={user_id}:period={period}:hide_manual={int(hide_manual)}"


def _pace_str_from_mph(mph):
    try:
        mph = float(mph)
        if mph <= 0:
            return None
        pace_min_per_mile = 60.0 / mph
        minutes = int(pace_min_per_mile)
        seconds = int(round((pace_min_per_mile - minutes) * 60.0))
        if seconds == 60:
            minutes += 1
            seconds = 0
        return f"{minutes}:{seconds:02d}/mi"
    except Exception:
        return None


@login_required
def dashboard(request):
    # -----------------------------
    # Inputs
    # -----------------------------
    period = request.GET.get("period", "7d")
    hide_manual = request.GET.get("hide_manual") == "1"
    today = timezone.now().date()

    # -----------------------------
    # Period context (small + cheap)
    # -----------------------------
    period_ctx = get_dashboard_period(period, today=today)
    start_date = period_ctx["start_date"]
    period_label = period_ctx["period_label"]
    period_description = period_ctx["period_description"]
    comparison_label = period_ctx["comparison_label"]
    comparison_start = period_ctx["comparison_start"]
    comparison_end = period_ctx["comparison_end"]

    # -----------------------------
    # Challenge context (keep LIVE)
    # -----------------------------
    current_week_start = DateRangeService.sunday_of_current_week(date.today())
    challenge_context = get_dashboard_challenge_context(
        user=request.user,
        current_week_start=current_week_start,
    )

    # Cached analytics (heavy)
    # -----------------------------
    key = _dash_cache_key(request.user.pk, period, hide_manual)
    cached = cache.get(key)

    from workouts.models import Workout  # cheap import, keep here

    manual_filter = {}
    if hide_manual:
        manual_filter = {"ride_detail__peloton_ride_id__regex": r"^(?!manual_).*"}

    # Base QS (used for recent workouts every time — cheap)
    base_qs = (
        Workout.objects
        .filter(user=request.user, **manual_filter)
        .select_related("ride_detail", "ride_detail__workout_type", "ride_detail__instructor", "details")
    )

    # Recent workouts should NOT be cached (QS/model objects)
    recent_workouts = base_qs.order_by("-completed_date")[:5]

    if cached is None:
        # Totals (all time, within manual filter)
        total_workouts_count = base_qs.count()
        workout_stats = base_qs.aggregate(
            total_output_sum=Sum("details__total_output"),
            total_distance_sum=Sum("details__distance"),
            total_calories_sum=Sum("details__total_calories"),
            avg_output=Avg("details__avg_output"),
            avg_heart_rate=Avg("details__avg_heart_rate"),
        )

        # Period QS (ALWAYS defined)
        period_qs = base_qs.filter(completed_date__gte=start_date) if start_date else base_qs

        # Comparison QS
        if comparison_start and comparison_end:
            comparison_qs = base_qs.filter(
                completed_date__gte=comparison_start,
                completed_date__lt=comparison_end,
            )
        else:
            comparison_qs = base_qs.none()

        # Period + comparison stats (DB side)
        period_agg = period_qs.aggregate(
            count=Count("id"),
            output=Sum("details__total_output"),
            calories=Sum("details__total_calories"),
        )
        comparison_agg = comparison_qs.aggregate(
            count=Count("id"),
            output=Sum("details__total_output"),
        )

        period_count = period_agg["count"] or 0
        period_output = period_agg["output"] or 0
        comparison_count = comparison_agg["count"] or 0
        comparison_output = comparison_agg["output"] or 0
        period_diff = period_count - comparison_count

        # This week (DB-side)
        week_start_date = today - timedelta(days=today.weekday())
        this_week_agg = base_qs.filter(completed_date__gte=week_start_date).aggregate(
            count=Count("id"),
            output=Sum("details__total_output"),
            calories=Sum("details__total_calories"),
        )
        this_week_count = this_week_agg["count"] or 0
        this_week_output = this_week_agg["output"] or 0
        this_week_calories = this_week_agg["calories"] or 0

        # Backward-compat: last 7 days / previous 7 days
        seven_days_ago = today - timedelta(days=7)
        fourteen_days_ago = today - timedelta(days=14)

        last7_agg = base_qs.filter(completed_date__gte=seven_days_ago).aggregate(
            count=Count("id"),
            output=Sum("details__total_output"),
        )
        prev7_agg = base_qs.filter(
            completed_date__gte=fourteen_days_ago,
            completed_date__lt=seven_days_ago,
        ).aggregate(
            count=Count("id"),
            output=Sum("details__total_output"),
        )

        last_7_days_count = last7_agg["count"] or 0
        last_7_days_output = last7_agg["output"] or 0
        previous_7_days_count = prev7_agg["count"] or 0
        previous_7_days_output = prev7_agg["output"] or 0
        last_7_days_diff = last_7_days_count - previous_7_days_count

        # This month / previous month (DB-side)
        month_start = today.replace(day=1)
        this_month_agg = base_qs.filter(completed_date__gte=month_start).aggregate(
            count=Count("id"),
            output=Sum("details__total_output"),
            calories=Sum("details__total_calories"),
        )
        this_month_count = this_month_agg["count"] or 0
        this_month_output = this_month_agg["output"] or 0
        this_month_calories = this_month_agg["calories"] or 0

        if month_start.month == 1:
            previous_month_start = date(month_start.year - 1, 12, 1)
        else:
            previous_month_start = date(month_start.year, month_start.month - 1, 1)

        if previous_month_start.month == 12:
            previous_month_end = date(previous_month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            previous_month_end = date(previous_month_start.year, previous_month_start.month + 1, 1) - timedelta(days=1)

        prev_month_agg = base_qs.filter(
            completed_date__gte=previous_month_start,
            completed_date__lte=previous_month_end,
        ).aggregate(
            count=Count("id"),
            output=Sum("details__total_output"),
        )
        previous_month_count = prev_month_agg["count"] or 0
        previous_month_output = prev_month_agg["output"] or 0
        this_month_diff = this_month_count - previous_month_count

        # ✅ Workouts by type (DB-side)
        type_rows = (
            base_qs
            .exclude(ride_detail__workout_type__name__isnull=True)
            .values(name=F("ride_detail__workout_type__name"))
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        workouts_by_type_dict = {r["name"]: r["count"] for r in type_rows}

        # ✅ Workouts by week (DB-side)
        shifted = ExpressionWrapper(F("completed_date") - timedelta(days=1), output_field=DateField())
        week_start_expr = ExpressionWrapper(TruncWeek(shifted) + timedelta(days=1), output_field=DateField())

        week_rows = (
            period_qs  # <-- FIX: was period_workouts
            .annotate(week=week_start_expr)
            .values("week")
            .annotate(
                count=Count("id"),
                total_output=Sum("details__total_output"),
                total_calories=Sum("details__total_calories"),
            )
            .order_by("week")
        )

        def _as_date(d):
            if d is None:
                return None
            return d if isinstance(d, date) else d.date()

        workouts_by_week_list = [
            {
                "date": _as_date(r["week"]),
                "count": r["count"] or 0,
                "total_output": float(r["total_output"] or 0),
                "total_calories": float(r["total_calories"] or 0),
            }
            for r in week_rows
            if r["week"] is not None
        ]

        # JSON for templates/JS
        workouts_by_week_json = json.dumps([
            {
                "date": w["date"].strftime("%Y-%m-%d"),
                "count": w["count"],
                "total_output": w["total_output"],
                "total_calories": w["total_calories"],
            }
            for w in workouts_by_week_list
        ])
        workouts_by_type_json = json.dumps(workouts_by_type_dict)

        # Discipline KPIs (period, DB-side)
        cycling_period = period_qs.filter(ride_detail__fitness_discipline__iexact="cycling")
        running_period = period_qs.filter(ride_detail__fitness_discipline__iexact="running")
        walking_period = period_qs.filter(ride_detail__fitness_discipline__iexact="walking")

        cycling_kpis_raw = cycling_period.aggregate(
            count=Count("id"),
            distance=Sum("details__distance"),
            total_output=Sum("details__total_output"),
            avg_output=Avg("details__avg_output"),
            tss=Sum("details__tss"),
            avg_cadence=Avg("details__avg_cadence"),
            avg_resistance=Avg("details__avg_resistance"),
            calories=Sum("details__total_calories"),
        )

        running_kpis_raw = running_period.aggregate(
            count=Count("id"),
            distance=Sum("details__distance"),
            avg_speed=Avg("details__avg_speed"),
            avg_heart_rate=Avg("details__avg_heart_rate"),
            calories=Sum("details__total_calories"),
        )

        walking_kpis_raw = walking_period.aggregate(
            count=Count("id"),
            distance=Sum("details__distance"),
            avg_speed=Avg("details__avg_speed"),
            avg_heart_rate=Avg("details__avg_heart_rate"),
            calories=Sum("details__total_calories"),
        )

        # Fallback avg_speed from time-series if missing
        avg_speed = running_kpis_raw.get("avg_speed")
        if not avg_speed:
            try:
                from workouts.models import WorkoutPerformanceData
                avg_speed = WorkoutPerformanceData.objects.filter(
                    workout__in=running_period,
                    speed__isnull=False,
                ).aggregate(avg_speed=Avg("speed")).get("avg_speed")
            except Exception:
                avg_speed = None

        avg_walk_speed = walking_kpis_raw.get("avg_speed")
        if not avg_walk_speed:
            try:
                from workouts.models import WorkoutPerformanceData
                avg_walk_speed = WorkoutPerformanceData.objects.filter(
                    workout__in=walking_period,
                    speed__isnull=False,
                ).aggregate(avg_speed=Avg("speed")).get("avg_speed")
            except Exception:
                avg_walk_speed = None

        cycling_kpis = {
            "count": cycling_kpis_raw.get("count") or 0,
            "distance": cycling_kpis_raw.get("distance"),
            "total_output": cycling_kpis_raw.get("total_output"),
            "avg_output": cycling_kpis_raw.get("avg_output"),
            "tss": cycling_kpis_raw.get("tss"),
            "avg_cadence": cycling_kpis_raw.get("avg_cadence"),
            "avg_resistance": cycling_kpis_raw.get("avg_resistance"),
            "calories": cycling_kpis_raw.get("calories"),
        }

        running_kpis = {
            "count": running_kpis_raw.get("count") or 0,
            "distance": running_kpis_raw.get("distance"),
            "avg_speed": avg_speed,
            "avg_pace_str": _pace_str_from_mph(avg_speed) if avg_speed else None,
            "avg_heart_rate": running_kpis_raw.get("avg_heart_rate"),
            "calories": running_kpis_raw.get("calories"),
        }

        walking_kpis = {
            "count": walking_kpis_raw.get("count") or 0,
            "distance": walking_kpis_raw.get("distance") or 0,
            "avg_speed": avg_walk_speed,
            "avg_pace_str": _pace_str_from_mph(avg_walk_speed) if avg_walk_speed else None,
            "avg_heart_rate": walking_kpis_raw.get("avg_heart_rate"),
            "calories": walking_kpis_raw.get("calories"),
        }

        cached = {
            "total_workouts_count": total_workouts_count,
            "workout_stats": workout_stats,

            # store as plain strings; mark_safe when rendering
            "workouts_by_type": workouts_by_type_json,
            "workouts_by_week": workouts_by_week_json,

            "period_count": period_count,
            "period_output": period_output,
            "period_diff": period_diff,
            "comparison_count": comparison_count,

            "this_week_count": this_week_count,
            "this_week_output": this_week_output,
            "this_week_calories": this_week_calories,

            "last_7_days_count": last_7_days_count,
            "last_7_days_output": last_7_days_output,
            "previous_7_days_count": previous_7_days_count,
            "previous_7_days_output": previous_7_days_output,
            "last_7_days_diff": last_7_days_diff,

            "this_month_count": this_month_count,
            "this_month_output": this_month_output,
            "this_month_calories": this_month_calories,
            "previous_month_count": previous_month_count,
            "previous_month_output": previous_month_output,
            "this_month_diff": this_month_diff,

            "cycling_kpis": cycling_kpis,
            "running_kpis": running_kpis,
            "walking_kpis": walking_kpis,
        }

        cache.set(key, cached, 60)  # 60s

    # Ensure recent_workouts is always present (non-cached)
    cached = {**cached, "recent_workouts": recent_workouts}

    # If your templates expect mark_safe:
    cached["workouts_by_type"] = mark_safe(cached["workouts_by_type"])
    cached["workouts_by_week"] = mark_safe(cached["workouts_by_week"])

    # -----------------------------
    # Peloton profile stats (cheap)
    # -----------------------------
    profile = request.user.profile
    peloton_stats = {
        "total_workouts": profile.peloton_total_workouts or 0,
        "total_output": profile.peloton_total_output or 0,
        "total_distance": profile.peloton_total_distance or 0,
        "total_calories": profile.peloton_total_calories or 0,
        "current_weekly_streak": profile.peloton_current_weekly_streak or 0,
        "best_weekly_streak": profile.peloton_best_weekly_streak or 0,
        "current_daily_streak": profile.peloton_current_daily_streak or 0,
        "total_achievements": profile.peloton_total_achievements or 0,
        "workout_counts": profile.peloton_workout_counts or {},
    }

    # -----------------------------
    # Final context
    # -----------------------------
    context = {
        **challenge_context,

        "peloton_stats": peloton_stats,

        "selected_period": period,
        "period_label": period_label,
        "period_description": period_description,
        "comparison_label": comparison_label,

        "hide_manual": hide_manual,

        **cached,
    }

    # HTMX request -> return shell (period bar + content)
    if request.headers.get("HX-Request") == "true":
        return render(request, "core/partials/dashboard_shell.html", context)

    return render(request, "core/dashboard.html", context)


# Public/Marketing Views
def landing(request):
    return render(request, "plans/landing.html")


def features(request):
    return render(request, "plans/features.html")


def about(request):
    return render(request, "plans/about.html")


def how_it_works(request):
    return render(request, "plans/how_it_works.html")


def faq(request):
    return render(request, "plans/faq.html")


def contact(request):
    return render(request, "plans/contact.html")


def privacy_policy(request):
    return render(request, "plans/privacy_policy.html")


def terms_and_conditions(request):
    return render(request, "plans/terms_and_conditions.html")
