# Standard library
import json
from collections import defaultdict
from datetime import date, datetime, timedelta

# Django
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.safestring import mark_safe

# Local apps
from accounts.pace_converter import DEFAULT_RUNNING_PACE_LEVELS
from accounts.rowing_pace_levels_data import DEFAULT_ROWING_PACE_LEVELS
from accounts.walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS
from challenges.models import ChallengeInstance
from core.services import DateRangeService, ZoneCalculatorService
from tracker.models import WeeklyPlan

from .models import Exercise
from .services import (
    get_dashboard_challenge_context,
    get_dashboard_period,
)

@login_required
def exercise_list(request):
    exercises = Exercise.objects.all().order_by("category", "name")
    return render(request, "plans/exercises.html", {"exercises": exercises})

def guide(request):
    return render(request, "plans/guide.html")

def pace_zones_reference(request):
    """Display pace target zones reference page for all levels (1-10) for Running, Walking, and Rowing"""
    
    def decimal_to_mmss(decimal_minutes):
        """Convert decimal minutes to MM:SS format"""
        minutes = int(decimal_minutes)
        seconds = int((decimal_minutes - minutes) * 60)
        return f"{minutes}:{seconds:02d}"
    
    # Running pace levels
    running_levels = []
    running_zone_order = ['recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max']
    running_color_map = {
        'recovery': '#9333ea',      # Purple
        'easy': '#3b82f6',          # Blue
        'moderate': '#10b981',       # Green
        'challenging': '#eab308',    # Yellow
        'hard': '#f97316',          # Orange
        'very_hard': '#ef4444',     # Red
        'max': '#ec4899',           # Pink
    }
    
    for level_num in range(1, 11):
        level_data = DEFAULT_RUNNING_PACE_LEVELS.get(level_num, {})
        zones = []
        for zone_name in running_zone_order:
            if zone_name in level_data:
                zone_info = level_data[zone_name]
                min_mph, max_mph, min_pace, max_pace, description = zone_info
                zones.append({
                    'name': zone_name.replace('_', ' ').title(),
                    'min_mph': float(min_mph),
                    'max_mph': float(max_mph),
                    'min_pace': decimal_to_mmss(min_pace),
                    'max_pace': decimal_to_mmss(max_pace),
                    'description': description,
                    'color': running_color_map.get(zone_name, '#6b7280'),
                })
        running_levels.append({'level': level_num, 'zones': zones})
    
    # Walking pace levels
    walking_levels = []
    walking_zone_order = ['recovery', 'easy', 'brisk', 'power', 'max']
    walking_color_map = {
        'recovery': '#10b981',      # Green
        'easy': '#3b82f6',          # Blue
        'brisk': '#eab308',         # Yellow
        'power': '#f97316',         # Orange
        'max': '#ef4444',           # Red
    }
    
    for level_num in range(1, 10):  # Walking has 9 levels
        level_data = DEFAULT_WALKING_PACE_LEVELS.get(level_num, {})
        zones = []
        for zone_name in walking_zone_order:
            if zone_name in level_data:
                zone_info = level_data[zone_name]
                min_mph, max_mph, min_pace, max_pace, description = zone_info
                zones.append({
                    'name': zone_name.replace('_', ' ').title(),
                    'min_mph': float(min_mph),
                    'max_mph': float(max_mph),
                    'min_pace': decimal_to_mmss(min_pace),
                    'max_pace': decimal_to_mmss(max_pace),
                    'description': description,
                    'color': walking_color_map.get(zone_name, '#6b7280'),
                })
        walking_levels.append({'level': level_num, 'zones': zones})
    
    # Rowing pace levels
    rowing_levels = []
    rowing_zone_order = ['easy', 'moderate', 'challenging', 'max']
    rowing_color_map = {
        'easy': '#3b82f6',          # Blue
        'moderate': '#10b981',       # Green
        'challenging': '#eab308',    # Yellow
        'max': '#ef4444',           # Red
    }
    
    for level_num in range(1, 11):
        level_data = DEFAULT_ROWING_PACE_LEVELS.get(level_num, {})
        zones = []
        for zone_name in rowing_zone_order:
            if zone_name in level_data:
                zone_info = level_data[zone_name]
                pace_decimal, description = zone_info
                zones.append({
                    'name': zone_name.replace('_', ' ').title(),
                    'pace': decimal_to_mmss(pace_decimal),
                    'description': description,
                    'color': rowing_color_map.get(zone_name, '#6b7280'),
                })
        rowing_levels.append({'level': level_num, 'zones': zones})
    
    return render(request, 'workouts/pace_zones_reference.html', {
        'running_levels': running_levels,
        'walking_levels': walking_levels,
        'rowing_levels': rowing_levels,
    })

def calculate_cycling_zones(workouts, period=None, current_ftp=None):
    """Calculate time spent in each power zone (1-7) for cycling workouts.
    
    DEPRECATED: Use ZoneCalculatorService.calculate_cycling_zones() instead.
    This wrapper is kept for backward compatibility.
    """
    return ZoneCalculatorService.calculate_cycling_zones(workouts, period, current_ftp)

def calculate_running_zones(workouts, period=None):
    """Calculate time spent in each intensity zone for running workouts.
    
    DEPRECATED: Use ZoneCalculatorService.calculate_running_zones() instead.
    This wrapper is kept for backward compatibility.
    """
    return ZoneCalculatorService.calculate_running_zones(workouts, period)

@login_required
def metrics(request):
    from accounts.models import WeightEntry, FTPEntry, PaceEntry
    from workouts.models import Workout, WorkoutPerformanceData, WorkoutDetails
    # Assuming these are already in your project
    # from plans.models import WeeklyPlan, ChallengeInstance

    user = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)
    cutoff_12m = today - timedelta(days=365)

    # ----------------------------
    # Challenges (avoid N+1 on weekly_plans.exists())
    # ----------------------------
    all_challenge_instances = (
        ChallengeInstance.objects
        .filter(user=user)
        .select_related("challenge")
        .prefetch_related("weekly_plans")
        .order_by("-started_at")
    )

    challenge_groups = defaultdict(list)
    for ci in all_challenge_instances:
        challenge_groups[ci.challenge_id].append(ci)

    fully_completed_challenges = []
    partially_completed_challenges = []

    for _, instances in challenge_groups.items():
        latest = max(instances, key=lambda x: x.started_at)
        latest.attempt_count = len(instances)

        if latest.all_weeks_completed:
            fully_completed_challenges.append(latest)
        else:
            # use prefetched cache (no .exists())
            has_weekly_plans = bool(list(latest.weekly_plans.all()))
            if has_weekly_plans and latest.completion_rate > 0:
                partially_completed_challenges.append(latest)

    # ----------------------------
    # Weight / FTP / Pace
    # ----------------------------
    weight_entries = (
        WeightEntry.objects
        .filter(user=user)
        .only("recorded_date", "created_at", "weight")
        .order_by("-recorded_date", "-created_at")
    )
    current_weight = weight_entries.first()

    ftp_entries = (
        FTPEntry.objects
        .filter(user=user)
        .only("recorded_date", "ftp_value", "is_active")
        .order_by("recorded_date")
    )

    running_pace_entries = (
        PaceEntry.objects
        .filter(user=user, activity_type="running")
        .only("recorded_date", "level")
        .order_by("recorded_date")
    )
    walking_pace_entries = (
        PaceEntry.objects
        .filter(user=user, activity_type="walking")
        .only("recorded_date", "level")
        .order_by("recorded_date")
    )

    current_ftp = (
        ftp_entries.filter(is_active=True).order_by("-recorded_date").first()
        or ftp_entries.order_by("-recorded_date").first()
    )

    current_cycling_pw = None
    current_tread_pw = None
    if current_weight and current_ftp:
        weight_kg = float(current_weight.weight) * 0.453592
        if weight_kg > 0:
            current_cycling_pw = round(float(current_ftp.ftp_value) / weight_kg, 2)

    # ----------------------------
    # P/W history (no extra DB calls)
    # ----------------------------
    weight_by_month = {}
    for w in weight_entries.order_by("recorded_date").only("recorded_date", "weight"):
        key_date = w.recorded_date.replace(day=1)
        k = key_date.strftime("%b %Y")
        prev = weight_by_month.get(k)
        if not prev or w.recorded_date > prev["source_date"]:
            weight_by_month[k] = {"weight": w.weight, "sort_date": key_date, "source_date": w.recorded_date}

    ftp_by_month = {}
    for f in ftp_entries.order_by("recorded_date").only("recorded_date", "ftp_value"):
        key_date = f.recorded_date.replace(day=1)
        k = key_date.strftime("%b %Y")
        prev = ftp_by_month.get(k)
        if not prev or f.recorded_date > prev["source_date"]:
            ftp_by_month[k] = {"ftp": f.ftp_value, "sort_date": key_date, "source_date": f.recorded_date}

    all_months = set(weight_by_month.keys()) | set(ftp_by_month.keys())
    cycling_history_entries = []
    for mk in all_months:
        w = weight_by_month.get(mk)
        f = ftp_by_month.get(mk)
        weight = w["weight"] if w else None
        ftp = f["ftp"] if f else None
        sort_date = (w or f)["sort_date"] if (w or f) else None

        pw_ratio = None
        if weight and ftp:
            wkg = float(weight) * 0.453592
            if wkg > 0:
                pw_ratio = round(float(ftp) / wkg, 2)

        cycling_history_entries.append({
            "date": mk,
            "ftp": ftp,
            "weight": weight,
            "pw_ratio": pw_ratio,
            "sort_date": sort_date
        })

    pw_history_cycling = sorted(
        cycling_history_entries,
        key=lambda x: x["sort_date"] or datetime(1900, 1, 1).date(),
        reverse=True
    )
    pw_history_tread = []

    # ----------------------------
    # Workouts base queryset (use DB aggregates for stats)
    # ----------------------------
    all_workouts = (
        Workout.objects
        .filter(user=user)
        .select_related("ride_detail", "ride_detail__workout_type", "details")
        .only(
            "id", "completed_date",
            "ride_detail__fitness_discipline",
            "ride_detail__workout_type__name", "ride_detail__workout_type__slug",
            "ride_detail__duration_seconds",
            "details__distance", "details__total_output", "details__tss", "details__avg_heart_rate",
        )
    )

    def agg_stats(qs):
        a = qs.aggregate(
            distance=Coalesce(Sum("details__distance"), 0.0),
            output=Coalesce(Sum("details__total_output"), 0.0),
            tss=Coalesce(Sum("details__tss"), 0.0),
        )
        return a["distance"], a["output"], a["tss"]

    this_month = all_workouts.filter(completed_date__gte=month_start)

    cycling_monthly_distance, cycling_monthly_output, cycling_monthly_tss = agg_stats(
        this_month.filter(ride_detail__fitness_discipline__in=["cycling", "ride"])
    )
    running_monthly_distance, running_monthly_output, running_monthly_tss = agg_stats(
        this_month.filter(ride_detail__fitness_discipline__in=["running", "run", "walking"])
    )

    # Your template labels say "Yearly" but you were calculating "all time".
    # Keeping behavior (all-time totals) but via DB aggregates:
    cycling_yearly_distance, cycling_yearly_output, cycling_yearly_tss = agg_stats(
        all_workouts.filter(ride_detail__fitness_discipline__in=["cycling", "ride"])
    )
    running_yearly_distance, running_yearly_output, running_yearly_tss = agg_stats(
        all_workouts.filter(ride_detail__fitness_discipline__in=["running", "run", "walking"])
    )

    # ----------------------------
    # Heart rate (DB avg, no python scan)
    # ----------------------------
    def hr_block(qs):
        cycling = qs.filter(
            details__avg_heart_rate__isnull=False,
            ride_detail__fitness_discipline__in=["cycling", "ride"],
        ).aggregate(v=Avg("details__avg_heart_rate"))["v"] or 0

        tread = qs.filter(
            details__avg_heart_rate__isnull=False,
            ride_detail__fitness_discipline__in=["running", "run", "walking"],
        ).aggregate(v=Avg("details__avg_heart_rate"))["v"] or 0

        overall = qs.filter(
            details__avg_heart_rate__isnull=False
        ).aggregate(v=Avg("details__avg_heart_rate"))["v"] or 0

        return {
            "Cycling": int(cycling) if cycling else 0,
            "Tread": int(tread) if tread else 0,
            "overall": int(overall) if overall else 0,
        }

    hr_this_month = hr_block(this_month)
    hr_1m = hr_block(all_workouts.filter(completed_date__gte=today - timedelta(days=30)))
    hr_2m = hr_block(all_workouts.filter(completed_date__gte=today - timedelta(days=60)))
    hr_3m = hr_block(all_workouts.filter(completed_date__gte=today - timedelta(days=90)))
    avg_heart_rate = hr_this_month.get("overall")

    # ----------------------------
    # Personal Records (SEGMENTED: 0–30, 31–60, 61–90 days)
    # ----------------------------
    def empty_pr():
        return {"1min": 0, "3min": 0, "5min": 0, "10min": 0, "20min": 0}

    def compute_workout_power_peaks(outputs_5s):
        """
        outputs_5s: list of instantaneous outputs at ~5s resolution.
        Uses prefix sums for fast rolling averages.
        """
        peaks = empty_pr()
        if not outputs_5s:
            return peaks

        ps = [0.0]
        for v in outputs_5s:
            ps.append(ps[-1] + float(v))

        def max_avg(window_points):
            if window_points <= 0 or window_points > len(outputs_5s):
                return 0
            best = 0.0
            for i in range(0, len(outputs_5s) - window_points + 1):
                s = ps[i + window_points] - ps[i]
                best = max(best, s / window_points)
            return int(best)

        peaks["1min"] = max_avg(60 // 5)
        peaks["3min"] = max_avg(180 // 5)
        peaks["5min"] = max_avg(300 // 5)
        peaks["10min"] = max_avg(600 // 5)
        peaks["20min"] = max_avg(1200 // 5)
        return peaks

    pr_workouts = (
        all_workouts
        .filter(
            completed_date__gte=today - timedelta(days=90),
            ride_detail__fitness_discipline__in=["cycling", "ride"],
            details__total_output__isnull=False,
        )
        .values("id", "completed_date")
    )
    pr_workout_ids = [w["id"] for w in pr_workouts]
    completed_by_workout = {w["id"]: w["completed_date"] for w in pr_workouts}

    perf_rows = (
        WorkoutPerformanceData.objects
        .filter(workout_id__in=pr_workout_ids, output__isnull=False)
        .order_by("workout_id", "timestamp")
        .values_list("workout_id", "output")
    )

    outputs_by_workout = defaultdict(list)
    for wid, out in perf_rows:
        if out is not None:
            outputs_by_workout[wid].append(float(out))

    peaks_by_workout = {}
    for wid, outs in outputs_by_workout.items():
        peaks_by_workout[wid] = compute_workout_power_peaks(outs)

    pr_seg_1 = empty_pr()  # 0–30
    pr_seg_2 = empty_pr()  # 31–60
    pr_seg_3 = empty_pr()  # 61–90

    for wid, peaks in peaks_by_workout.items():
        d = completed_by_workout.get(wid)
        if not d:
            continue

        age_days = (today - d).days
        if 0 <= age_days <= 30:
            bucket = pr_seg_1
        elif 31 <= age_days <= 60:
            bucket = pr_seg_2
        elif 61 <= age_days <= 90:
            bucket = pr_seg_3
        else:
            continue

        for k in bucket.keys():
            bucket[k] = max(bucket[k], peaks.get(k, 0) or 0)

    personal_records_1m = pr_seg_1
    personal_records_2m = pr_seg_2
    personal_records_3m = pr_seg_3

    # ----------------------------
    # Time in Zones (ONLY current month + past 12 months)
    # No "all time" -> less perf data scanned
    # ----------------------------
    def format_time(seconds):
        seconds = float(seconds or 0)
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}" if days > 0 else f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def cycling_zones_month_and_12m():
        # buckets for two periods
        month = {i: 0 for i in range(1, 8)}
        yr12 = {i: 0 for i in range(1, 8)}

        cycling_ids = list(
            all_workouts.filter(
                Q(ride_detail__fitness_discipline__in=["cycling", "ride"]) |
                Q(ride_detail__workout_type__slug__in=["cycling", "ride"]) |
                Q(ride_detail__workout_type__name__icontains="cycle") |
                Q(ride_detail__workout_type__name__icontains="bike"),
                completed_date__gte=cutoff_12m,
            ).values_list("id", flat=True)
        )

        ftp_val = float(current_ftp.ftp_value) if current_ftp else None
        if not cycling_ids:
            return month, yr12

        perf_qs = (
            WorkoutPerformanceData.objects
            .filter(workout_id__in=cycling_ids)
            .select_related("workout")
            .only("workout_id", "timestamp", "power_zone", "output", "workout__completed_date")
            .order_by("workout_id", "timestamp")
        )

        last = {}
        for p in perf_qs:
            wid = p.workout_id
            completed = p.workout.completed_date

            zone = None
            if p.power_zone and 1 <= p.power_zone <= 7:
                zone = p.power_zone
            elif p.output is not None and ftp_val:
                pct = float(p.output) / ftp_val
                if pct < 0.55: zone = 1
                elif pct < 0.75: zone = 2
                elif pct < 0.90: zone = 3
                elif pct < 1.05: zone = 4
                elif pct < 1.20: zone = 5
                elif pct < 1.50: zone = 6
                else: zone = 7

            if not zone:
                continue

            prev = last.get(wid)
            if prev:
                prev_ts, prev_zone, prev_completed = prev
                dt = p.timestamp - prev_ts
                if 0 < dt < 300:
                    # past 12 months (we already filtered workouts >= cutoff_12m)
                    yr12[prev_zone] += dt
                    if prev_completed and prev_completed >= month_start:
                        month[prev_zone] += dt

            last[wid] = (p.timestamp, zone, completed)

        return month, yr12

    def running_zones_month_and_12m():
        keys = ["recovery", "easy", "moderate", "challenging", "hard", "very_hard", "max"]
        month = {k: 0 for k in keys}
        yr12 = {k: 0 for k in keys}

        running_ids = list(
            all_workouts.filter(
                Q(ride_detail__fitness_discipline__in=["running", "run", "walking"]) |
                Q(ride_detail__workout_type__slug__in=["running", "run", "walking"]) |
                Q(ride_detail__workout_type__name__icontains="run") |
                Q(ride_detail__workout_type__name__icontains="walk") |
                Q(ride_detail__workout_type__name__icontains="tread"),
                completed_date__gte=cutoff_12m,
            ).values_list("id", flat=True).distinct()
)

        if not running_ids:
            return month, yr12

        perf_qs = (
            WorkoutPerformanceData.objects
            .filter(workout_id__in=running_ids)
            .select_related("workout")
            .only("workout_id", "timestamp", "intensity_zone", "speed", "heart_rate", "workout__completed_date")
            .order_by("workout_id", "timestamp")
        )

        last = {}
        for p in perf_qs:
            wid = p.workout_id
            completed = p.workout.completed_date

            zone = None
            if p.intensity_zone in yr12:
                zone = p.intensity_zone
            elif p.speed is not None:
                s = float(p.speed)
                if s < 4.0: zone = "recovery"
                elif s < 5.5: zone = "easy"
                elif s < 7.0: zone = "moderate"
                elif s < 8.5: zone = "challenging"
                elif s < 10.0: zone = "hard"
                elif s < 12.0: zone = "very_hard"
                else: zone = "max"
            elif p.heart_rate is not None:
                hr = float(p.heart_rate)
                if hr < 120: zone = "recovery"
                elif hr < 140: zone = "easy"
                elif hr < 160: zone = "moderate"
                elif hr < 175: zone = "challenging"
                elif hr < 185: zone = "hard"
                elif hr < 195: zone = "very_hard"
                else: zone = "max"

            if not zone:
                continue

            prev = last.get(wid)
            if prev:
                prev_ts, prev_zone, prev_completed = prev
                dt = p.timestamp - prev_ts
                if 0 < dt < 300:
                    yr12[prev_zone] += dt
                    if prev_completed and prev_completed >= month_start:
                        month[prev_zone] += dt

            last[wid] = (p.timestamp, zone, completed)

        return month, yr12

    cycling_month_times, cycling_12m_times = cycling_zones_month_and_12m()
    running_month_times, running_12m_times = running_zones_month_and_12m()

    cycling_zones_month = {
        "zones": {
            1: {"name": "Recovery", "time_seconds": cycling_month_times[1], "time_formatted": format_time(cycling_month_times[1])},
            2: {"name": "Endurance", "time_seconds": cycling_month_times[2], "time_formatted": format_time(cycling_month_times[2])},
            3: {"name": "Tempo", "time_seconds": cycling_month_times[3], "time_formatted": format_time(cycling_month_times[3])},
            4: {"name": "Threshold", "time_seconds": cycling_month_times[4], "time_formatted": format_time(cycling_month_times[4])},
            5: {"name": "VO2 Max", "time_seconds": cycling_month_times[5], "time_formatted": format_time(cycling_month_times[5])},
            6: {"name": "Anaerobic", "time_seconds": cycling_month_times[6], "time_formatted": format_time(cycling_month_times[6])},
            7: {"name": "Neuromuscular", "time_seconds": cycling_month_times[7], "time_formatted": format_time(cycling_month_times[7])},
        },
        "total_seconds": sum(cycling_month_times.values()),
        "total_formatted": format_time(sum(cycling_month_times.values())),
    }

    cycling_zones_year = {
        "zones": {
            1: {"name": "Recovery", "time_seconds": cycling_12m_times[1], "time_formatted": format_time(cycling_12m_times[1])},
            2: {"name": "Endurance", "time_seconds": cycling_12m_times[2], "time_formatted": format_time(cycling_12m_times[2])},
            3: {"name": "Tempo", "time_seconds": cycling_12m_times[3], "time_formatted": format_time(cycling_12m_times[3])},
            4: {"name": "Threshold", "time_seconds": cycling_12m_times[4], "time_formatted": format_time(cycling_12m_times[4])},
            5: {"name": "VO2 Max", "time_seconds": cycling_12m_times[5], "time_formatted": format_time(cycling_12m_times[5])},
            6: {"name": "Anaerobic", "time_seconds": cycling_12m_times[6], "time_formatted": format_time(cycling_12m_times[6])},
            7: {"name": "Neuromuscular", "time_seconds": cycling_12m_times[7], "time_formatted": format_time(cycling_12m_times[7])},
        },
        "total_seconds": sum(cycling_12m_times.values()),
        "total_formatted": format_time(sum(cycling_12m_times.values())),
    }

    running_zone_names = {
        "recovery": "Recovery",
        "easy": "Easy",
        "moderate": "Moderate",
        "challenging": "Challenging",
        "hard": "Hard",
        "very_hard": "Very Hard",
        "max": "Max",
    }

    running_zones_month = {
        "zones": {
            k: {"name": running_zone_names[k], "time_seconds": running_month_times[k], "time_formatted": format_time(running_month_times[k])}
            for k in running_month_times.keys()
        },
        "total_seconds": sum(running_month_times.values()),
        "total_formatted": format_time(sum(running_month_times.values())),
    }

    running_zones_year = {
        "zones": {
            k: {"name": running_zone_names[k], "time_seconds": running_12m_times[k], "time_formatted": format_time(running_12m_times[k])}
            for k in running_12m_times.keys()
        },
        "total_seconds": sum(running_12m_times.values()),
        "total_formatted": format_time(sum(running_12m_times.values())),
    }

    # NOTE: to fully remove "All Time" zones, also remove the 3rd card+canvas in the template
    cycling_zones_all = None
    running_zones_all = None

    # ----------------------------
    # Milestones (unchanged)
    # ----------------------------
    peloton_milestones = []
    if hasattr(user, "profile") and user.profile.peloton_workout_counts:
        workout_counts = user.profile.peloton_workout_counts
        categories = [
            {"name": "Yoga", "slug": "yoga", "icon": "🧘"},
            {"name": "Bike", "slug": "cycling", "icon": "🚴"},
            {"name": "Tread", "slug": "running", "icon": "🏃"},
            {"name": "Stretching", "slug": "stretching", "icon": "🤸"},
            {"name": "Strength", "slug": "strength", "icon": "💪"},
        ]
        thresholds = [10, 50, 100, 500, 1000]

        for c in categories:
            count = workout_counts.get(c["slug"], 0)
            achieved = []
            next_milestone = None
            progress_percentage = 0

            for i, t in enumerate(thresholds):
                if count >= t:
                    achieved.append(t)
                else:
                    next_milestone = t
                    prev_t = thresholds[i - 1] if i > 0 else 0
                    if t > prev_t:
                        progress_percentage = int(((count - prev_t) / (t - prev_t)) * 100)
                        progress_percentage = max(0, min(100, progress_percentage))
                    break

            peloton_milestones.append({
                "name": c["name"],
                "icon": c["icon"],
                "count": count,
                "achieved": achieved,
                "thresholds": thresholds,
                "next_milestone": next_milestone,
                "progress_percentage": progress_percentage,
            })
    else:
        for c in [
            {"name": "Yoga", "icon": "🧘"},
            {"name": "Bike", "icon": "🚴"},
            {"name": "Tread", "icon": "🏃"},
            {"name": "Stretching", "icon": "🤸"},
            {"name": "Strength", "icon": "💪"},
        ]:
            peloton_milestones.append({
                "name": c["name"],
                "icon": c["icon"],
                "count": 0,
                "achieved": [],
                "thresholds": [10, 50, 100, 500, 1000],
                "next_milestone": 10,
                "progress_percentage": 0,
            })

    # ----------------------------
    # Context
    # ----------------------------
    context = {
        "fully_completed_challenges": fully_completed_challenges,
        "partially_completed_challenges": partially_completed_challenges,

        "current_weight": current_weight,
        "weight_entries": weight_entries,

        "current_month": today.month,
        "current_year": today.year,

        "ftp_entries": ftp_entries,
        "running_pace_entries": running_pace_entries,
        "walking_pace_entries": walking_pace_entries,

        "current_ftp": current_ftp,
        "current_cycling_pw": current_cycling_pw,
        "current_tread_pw": current_tread_pw,
        "pw_history_cycling": pw_history_cycling,
        "pw_history_tread": pw_history_tread,

        # Personal Records (segmented)
        "personal_records_1m": mark_safe(json.dumps(personal_records_1m)),
        "personal_records_2m": mark_safe(json.dumps(personal_records_2m)),
        "personal_records_3m": mark_safe(json.dumps(personal_records_3m)),

        # Monthly stats
        "cycling_monthly_distance": cycling_monthly_distance,
        "cycling_monthly_output": cycling_monthly_output,
        "cycling_monthly_tss": cycling_monthly_tss,
        "cycling_yearly_distance": cycling_yearly_distance,
        "cycling_yearly_output": cycling_yearly_output,
        "cycling_yearly_tss": cycling_yearly_tss,

        "running_monthly_distance": running_monthly_distance,
        "running_monthly_output": running_monthly_output,
        "running_monthly_tss": running_monthly_tss,
        "running_yearly_distance": running_yearly_distance,
        "running_yearly_output": running_yearly_output,
        "running_yearly_tss": running_yearly_tss,

        # Heart rate
        "avg_heart_rate": avg_heart_rate,
        "hr_this_month": mark_safe(json.dumps(hr_this_month)),
        "hr_1m": mark_safe(json.dumps(hr_1m)),
        "hr_2m": mark_safe(json.dumps(hr_2m)),
        "hr_3m": mark_safe(json.dumps(hr_3m)),

        # Zones (month + past 12 months only)
        "cycling_zones_month": mark_safe(json.dumps(cycling_zones_month)),
        "cycling_zones_year": mark_safe(json.dumps(cycling_zones_year)),
        "cycling_zones_all": cycling_zones_all,  # None so template {% if %} blocks won't render JS
        "running_zones_month": mark_safe(json.dumps(running_zones_month)),
        "running_zones_year": mark_safe(json.dumps(running_zones_year)),
        "running_zones_all": running_zones_all,  # None

        "peloton_milestones": peloton_milestones,
    }

    return render(request, "metrics/performance_metrics.html", context)

@login_required
def recap(request):
    """Yearly recap view showing comprehensive stats for a selected year"""
    from workouts.models import Workout, WorkoutDetails
    from .models import RecapShare, RecapCache
    from django.db.models import Sum, Avg, Count, Q
    from django.urls import reverse
    from django.http import HttpResponseNotFound, HttpResponseForbidden
    from django.core.exceptions import ObjectDoesNotExist
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Helper function to safely get workout details
    def get_workout_details(workout):
        """Safely get workout details, returning None if it doesn't exist"""
        try:
            return workout.details
        except (WorkoutDetails.DoesNotExist, AttributeError, ObjectDoesNotExist):
            return None
    
    # Get available years (years with workouts)
    # Exclude current year until December 21st (can't recap a year that's still in progress)
    today = timezone.now().date()
    current_year = today.year
    
    # Check if we're past December 21st
    can_view_current_year = today.month == 12 and today.day >= 21
    
    # Get all years with workouts
    all_years = list(Workout.objects.filter(
        user=request.user
    ).values_list('completed_date__year', flat=True).distinct().order_by('-completed_date__year'))
    
    # Filter out current year if we can't view it yet
    if can_view_current_year:
        available_years = all_years
    else:
        available_years = [year for year in all_years if year < current_year]
    
    # Get year from query params, default to most recent available year
    selected_year_param = request.GET.get('year')
    if selected_year_param:
        try:
            selected_year = int(selected_year_param)
            # Validate: don't allow current year if we can't view it yet
            if not can_view_current_year and selected_year == current_year:
                selected_year = available_years[0] if available_years else None
            elif selected_year not in available_years:
                selected_year = available_years[0] if available_years else None
        except ValueError:
            selected_year = available_years[0] if available_years else None
    else:
        selected_year = available_years[0] if available_years else None
    
    if not selected_year:
        context = {
            "has_workouts": False,
            "selected_year": None,
            "available_years": [],
            "no_years_message": "No completed years found. Check back next year for your recap!",
            "use_cache": False,
        }
        return render(request, "plans/recap.html", context)
    
    # Additional safety check: Never allow current year before December 21st, even if cached
    if not can_view_current_year and selected_year == current_year:
        # Redirect to most recent available year
        selected_year = available_years[0] if available_years else None
        if not selected_year:
            context = {
                "has_workouts": False,
                "selected_year": None,
                "available_years": [],
                "no_years_message": "No completed years found. Check back next year for your recap!",
                "use_cache": False,
            }
            return render(request, "plans/recap.html", context)
    
    # Try to get cached recap data first (before any expensive queries)
    recap_cache = RecapCache.get_cache_for_user_year(request.user, selected_year)
    needs_recalculation = True
    is_first_load = False
    
    # Check if cache exists (even if stale)
    cache_exists = RecapCache.objects.filter(user=request.user, year=selected_year).exists()
    
    # Check regeneration availability (only show regenerate button if cache exists)
    can_regenerate = False
    hours_until_regenerate = None
    if cache_exists:
        try:
            existing_cache = RecapCache.objects.get(user=request.user, year=selected_year)
            if existing_cache.last_regenerated_at:
                time_since = timezone.now() - existing_cache.last_regenerated_at
                hours_since = time_since.total_seconds() / 3600
                if hours_since >= 24:
                    can_regenerate = True
                else:
                    hours_until_regenerate = 24 - hours_since
            else:
                can_regenerate = True  # Never manually regenerated, can regenerate
        except RecapCache.DoesNotExist:
            pass
    
    # Check if cache exists and is valid
    if recap_cache:
        # Check if cache is stale (this includes checking if cache has 0 workouts but workouts exist)
        if recap_cache.is_stale():
            recap_cache = None
            needs_recalculation = True
            logger.debug(f"Cache is stale for user {request.user.id}, year {selected_year} - will recalculate")
        else:
            # Cache is valid - use it
            needs_recalculation = False
    
    if recap_cache and not needs_recalculation:
            logger.debug(f"Using cached recap data for user {request.user.id}, year {selected_year}")
            context = {
                "has_workouts": recap_cache.total_workouts_count > 0,
                "selected_year": selected_year,
                "available_years": list(available_years),
                "use_cache": True,
                "is_first_load": False,
                "can_regenerate": can_regenerate,
                "hours_until_regenerate": hours_until_regenerate,
                # Load all cached data
                "daily_activities": recap_cache.daily_activities,
                "daily_calories": recap_cache.daily_calories,
                "daily_power": recap_cache.daily_power,
                "distance_stats": recap_cache.distance_stats,
                "total_hours": recap_cache.total_hours,
                "streaks": recap_cache.streaks,
                "rest_days": recap_cache.rest_days,
                "start_times": recap_cache.start_times,
                "activity_count": recap_cache.activity_count,
                "training_load": recap_cache.training_load,
                "personal_records": recap_cache.personal_records,
                "consistency_metrics": recap_cache.consistency_metrics,
                "summary_stats": recap_cache.summary_stats,
                "top_instructors": recap_cache.top_instructors,
                "top_songs": recap_cache.top_songs,
                "duration_distribution": recap_cache.duration_distribution,
                "peak_performance": recap_cache.peak_performance,
                "elevation_stats": recap_cache.elevation_stats,
                "weekday_patterns": recap_cache.weekday_patterns,
                "workout_type_breakdown": recap_cache.workout_type_breakdown,
                "progress_over_time": recap_cache.progress_over_time,
                "best_workouts_by_discipline": recap_cache.best_workouts_by_discipline,
                "calorie_efficiency": recap_cache.calorie_efficiency,
                "average_metrics_breakdown": recap_cache.average_metrics_breakdown,
                "monthly_comparison": recap_cache.monthly_comparison,
                "favorite_class_types": recap_cache.favorite_class_types,
                "time_of_day_patterns": recap_cache.time_of_day_patterns,
                "year_over_year": recap_cache.year_over_year,
                "challenge_participation": recap_cache.challenge_participation,
                "intensity_zones": recap_cache.intensity_zones,
                "distance_milestones": recap_cache.distance_milestones,
                "consistency_score": recap_cache.consistency_score,
                "heart_rate_zones": recap_cache.heart_rate_zones,
                "cadence_resistance_trends": recap_cache.cadence_resistance_trends,
                "yearly_calendar": recap_cache.yearly_calendar,
            }
            return render(request, "plans/recap.html", context)
    
    # SLOW PATH: Cache is stale or missing - calculate fresh data automatically
    is_first_load = not cache_exists
    if is_first_load:
        logger.info(f"First load: Auto-generating recap for user {request.user.id}, year {selected_year}")
    else:
        logger.debug(f"Cache stale: Recalculating recap data for user {request.user.id}, year {selected_year}")
    
    # Get all workouts for the selected year
    year_start = date(selected_year, 1, 1)
    year_end = date(selected_year, 12, 31)

    # Query workouts using completed_at date (not completed_date)
    all_workouts = Workout.objects.filter(
        user=request.user,
        completed_at__date__gte=year_start,
        completed_at__date__lte=year_end
    ).select_related('ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details').prefetch_related('performance_data')

    # Log workout query results
    total_workouts_query = all_workouts.count()
    logger.info(f"STREAKS DEBUG: Found {total_workouts_query} workouts for user {request.user.username} ({request.user.id}), year {selected_year}")

    if not all_workouts.exists():
        context = {
            "has_workouts": False,
            "selected_year": selected_year,
            "available_years": list(available_years),
            "use_cache": False,
            "is_first_load": False,
            "can_regenerate": False,
            "hours_until_regenerate": None,
        }
        return render(request, "plans/recap.html", context)

    # Calculate basic statistics
    total_workouts = all_workouts.count()

    # Get workout details for metrics
    workouts_with_details = all_workouts.filter(details__isnull=False)

    # Calculate summary stats
    summary_stats = workouts_with_details.aggregate(
        total_distance=Sum('details__distance'),
        total_calories=Sum('details__total_calories'),
        total_output=Sum('details__total_output'),
        avg_output=Avg('details__avg_output'),
        avg_calories=Avg('details__total_calories'),
    )

    # Calculate active days
    workout_dates_raw = [dt.date() for dt in all_workouts.values_list('completed_at', flat=True) if dt is not None]
    workout_dates = sorted(set(workout_dates_raw))
    active_days = len(workout_dates)
    total_days_in_year = 366 if (selected_year % 4 == 0 and selected_year % 100 != 0) or (selected_year % 400 == 0) else 365
    rest_days = total_days_in_year - active_days

    # Calculate streaks (enhanced - days, weeks, months)
    # Get all unique workout dates, filtering out None values
    workout_dates_raw = [dt.date() for dt in all_workouts.values_list('completed_at', flat=True) if dt is not None]
    workout_dates = sorted(set(workout_dates_raw))

    # Logging for debugging streaks
    logger.info(f"STREAKS DEBUG for user {request.user.username} ({request.user.id}), year {selected_year}:")
    logger.info(f"  Raw workout dates count: {len(workout_dates_raw)}")
    logger.info(f"  Unique workout dates (after filtering None): {len(workout_dates)}")
    logger.info(f"  NOTE: recap now uses completed_at (UTC, no timezone conversion)")
    logger.info(f"  If streaks don't match Peloton, existing workouts may need re-sync to update dates")
    if workout_dates:
        logger.info(f"  First workout date: {workout_dates[0]}")
        logger.info(f"  Last workout date: {workout_dates[-1]}")
        logger.info(f"  Date range: {(workout_dates[-1] - workout_dates[0]).days + 1} days")
        # Check for gaps
        gaps = []
        for i in range(1, min(len(workout_dates), 100)):  # Check first 100 dates
            gap = (workout_dates[i] - workout_dates[i-1]).days
            if gap > 1:
                gaps.append(f"{workout_dates[i-1]} to {workout_dates[i]} (gap: {gap} days)")
        if gaps:
            logger.info(f"  Found {len(gaps)} gaps in first 100 dates: {gaps[:5]}")  # Show first 5 gaps
            logger.info(f"  These gaps may be due to missing workouts or import issues")
        else:
            logger.info(f"  No gaps found in first 100 dates")
    
    # Longest streak in days
    longest_streak_days = 1 if workout_dates else 0
    current_streak = 1 if workout_dates else 0
    streak_start_date = workout_dates[0] if workout_dates else None
    longest_streak_start = streak_start_date
    
    for i in range(1, len(workout_dates)):
        gap = (workout_dates[i] - workout_dates[i-1]).days
        if gap == 1:
            current_streak += 1
            if current_streak > longest_streak_days:
                longest_streak_days = current_streak
                longest_streak_start = streak_start_date
        else:
            # Streak broken - check if current streak is longest before resetting
            if current_streak > longest_streak_days:
                longest_streak_days = current_streak
                longest_streak_start = streak_start_date
            current_streak = 1
            streak_start_date = workout_dates[i]
    
    # Check final streak (in case longest streak is at the end)
    if current_streak > longest_streak_days:
        longest_streak_days = current_streak
        longest_streak_start = streak_start_date
    
    logger.info(f"  Calculated longest streak: {longest_streak_days} days")
    if longest_streak_start:
        logger.info(f"  Longest streak started: {longest_streak_start}")
        if longest_streak_days > 1:
            streak_end = longest_streak_start + timedelta(days=longest_streak_days - 1)
            logger.info(f"  Longest streak ended: {streak_end}")
    logger.info(f"  Active days count: {active_days}, Total days in year: {total_days_in_year}")
    
    # Longest streak in weeks
    longest_streak_weeks = 1 if workout_dates else 0
    current_week_streak = 1 if workout_dates else 0
    current_week = None
    for workout_date in workout_dates:
        week_start = workout_date - timedelta(days=workout_date.weekday())
        if current_week is None:
            current_week = week_start
        elif week_start == current_week + timedelta(days=7):
            current_week_streak += 1
            longest_streak_weeks = max(longest_streak_weeks, current_week_streak)
            current_week = week_start
        else:
            current_week_streak = 1
            current_week = week_start
    
    logger.info(f"  Calculated longest streak in weeks: {longest_streak_weeks}")
    
    # Longest streak in months
    longest_streak_months = 1 if workout_dates else 0
    current_month_streak = 1 if workout_dates else 0
    current_month = None
    for workout_date in workout_dates:
        month_start = workout_date.replace(day=1)
        if current_month is None:
            current_month = month_start
        elif month_start > current_month:
            # Check if consecutive month
            next_month = current_month + timedelta(days=32)
            next_month = next_month.replace(day=1)
            if month_start == next_month:
                current_month_streak += 1
                longest_streak_months = max(longest_streak_months, current_month_streak)
            else:
                current_month_streak = 1
            current_month = month_start
    
    logger.info(f"  Calculated longest streak in months: {longest_streak_months}")
    
    streaks = {
        'longest_days': longest_streak_days,
        'longest_weeks': longest_streak_weeks,
        'longest_months': longest_streak_months,
    }
    
    # Consistency Score Calculation
    workouts_per_week = total_workouts / 52.0 if total_workouts > 0 else 0
    consistency_percentage = (active_days / total_days_in_year) * 100 if total_days_in_year > 0 else 0
    
    # Calculate consistency score (0-100)
    # Factors: active days percentage (50%), workouts per week (30%), streak bonus (20%)
    active_days_score = min(consistency_percentage * 0.5, 50)
    workouts_per_week_score = min(workouts_per_week * 2.5, 30)  # Max 12 workouts/week = 30 points
    streak_bonus = min(longest_streak_days * 0.2, 20)  # Max 100 day streak = 20 points
    
    consistency_score = int(active_days_score + workouts_per_week_score + streak_bonus)
    
    # Grade based on score
    if consistency_score >= 90:
        grade = 'A+'
        grade_color = '#28a745'
    elif consistency_score >= 80:
        grade = 'A'
        grade_color = '#28a745'
    elif consistency_score >= 70:
        grade = 'B'
        grade_color = '#ffc107'
    elif consistency_score >= 60:
        grade = 'C'
        grade_color = '#ff9800'
    elif consistency_score >= 50:
        grade = 'D'
        grade_color = '#f44336'
    else:
        grade = 'F'
        grade_color = '#dc3545'
    
    consistency_score_data = {
        'score': consistency_score,
        'grade': grade,
        'grade_color': grade_color,
        'active_days': active_days,
        'total_days': total_days_in_year,
        'consistency_percentage': round(consistency_percentage, 1),
        'workouts_per_week': round(workouts_per_week, 1),
    }
    
    # Consistency Metrics
    monthly_workout_counts = {}
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_name = date(selected_year, month_num, 1).strftime('%B')
        monthly_workout_counts[month_name] = month_workouts.count()
    
    best_month = max(monthly_workout_counts.items(), key=lambda x: x[1]) if monthly_workout_counts else None
    worst_month = min(monthly_workout_counts.items(), key=lambda x: x[1]) if monthly_workout_counts else None
    
    # Most active day of week
    weekday_counts = defaultdict(int)
    for workout_date in workout_dates:
        weekday_name = workout_date.strftime('%A')
        weekday_counts[weekday_name] += 1
    
    most_active_day = max(weekday_counts.items(), key=lambda x: x[1])[0] if weekday_counts else None
    
    consistency_metrics = {
        'workouts_per_week': round(workouts_per_week, 1),
        'best_month': {'name': best_month[0], 'count': best_month[1]} if best_month else None,
        'worst_month': {'name': worst_month[0], 'count': worst_month[1]} if worst_month else None,
        'most_active_day': most_active_day,
    }
    
    # Top instructors
    top_instructors = all_workouts.filter(
        ride_detail__instructor__isnull=False
    ).values(
        'ride_detail__instructor__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Monthly breakdown
    monthly_data = []
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_count = month_workouts.count()
        monthly_data.append({
            'month': date(selected_year, month_num, 1).strftime('%B'),
            'count': month_count,
        })
    
    # Rest Days Calculation
    rest_days_data = {
        'active_days': active_days,
        'rest_days': rest_days,
        'active_percentage': round((active_days / total_days_in_year) * 100, 1) if total_days_in_year > 0 else 0,
    }
    
    # Distance Stats by Discipline (for stacked bar chart)
    distance_stats = {
        'total_distance_km': round((summary_stats['total_distance'] or 0) * 1.60934, 1),
        'monthly_data': [],
        'all_disciplines': [],
        'discipline_colors': {
            'cycling': '#4A90E2',
            'running': '#FF6B35',
            'walking': '#9BE9A8',
            'strength': '#FFD700',
            'yoga': '#9B59B6',
            'other': '#95A5A6',
        }
    }
    
    # Helper function to get discipline from workout
    def get_discipline(workout):
        if not workout.ride_detail:
            return 'other'
        discipline = workout.ride_detail.fitness_discipline or ''
        if discipline.lower() in ['cycling', 'ride']:
            return 'cycling'
        elif discipline.lower() in ['running', 'run']:
            return 'running'
        elif discipline.lower() in ['walking', 'walk']:
            return 'walking'
        elif discipline.lower() in ['strength']:
            return 'strength'
        elif discipline.lower() in ['yoga']:
            return 'yoga'
        return 'other'
    
    # Calculate monthly distance by discipline
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_name = date(selected_year, month_num, 1).strftime('%B')
        
        discipline_data = defaultdict(float)
        for workout in month_workouts:
            details = get_workout_details(workout)
            if details and details.distance:
                discipline = get_discipline(workout)
                distance_km = details.distance * 1.60934
                discipline_data[discipline] += distance_km
                if discipline not in distance_stats['all_disciplines']:
                    distance_stats['all_disciplines'].append(discipline)
        
        distance_stats['monthly_data'].append({
            'month': month_name,
            'discipline_data': [{'discipline': k, 'distance_km': round(v, 1)} for k, v in discipline_data.items()],
        })
    
    # Total Hours by Discipline
    total_hours = {
        'all_disciplines': [],
    }
    
    discipline_hours = defaultdict(float)
    for workout in all_workouts:
        if workout.ride_detail and workout.ride_detail.duration_seconds:
            discipline = get_discipline(workout)
            hours = workout.ride_detail.duration_seconds / 3600.0
            discipline_hours[discipline] += hours
            if discipline not in total_hours['all_disciplines']:
                total_hours['all_disciplines'].append(discipline)
    
    total_hours['all_disciplines'] = [{'discipline_name': d, 'hours': round(discipline_hours.get(d, 0), 1), 'color': distance_stats['discipline_colors'].get(d, '#95A5A6')} for d in total_hours['all_disciplines']]
    
    # Daily Activities Heatmap
    daily_activities = {
        'total_activities': total_workouts,
        'num_weeks': 53,  # Most years have 53 weeks
        'month_positions': {},
        'days_of_week': [],
    }
    
    # Calculate which week each day falls into
    year_start_date = date(selected_year, 1, 1)
    year_end_date = date(selected_year, 12, 31)
    
    # Get first Monday of the year (or before if Jan 1 is not Monday)
    first_monday = year_start_date
    while first_monday.weekday() != 0:  # 0 = Monday
        first_monday -= timedelta(days=1)
    
    # Count activities per day
    daily_activity_counts = defaultdict(int)
    for workout in all_workouts:
        daily_activity_counts[workout.completed_date] += 1
    
    # Build heatmap data structure (7 rows x 53 columns)
    # Each row represents a day of week (0=Monday, 6=Sunday)
    # Each column represents a week
    days_of_week_grid = [[] for _ in range(7)]  # 7 days of week
    
    current_date = first_monday
    week_num = 0
    
    # Generate exactly 53 weeks of data
    while week_num < 53:
        for day_of_week in range(7):  # Monday (0) to Sunday (6)
            if current_date > year_end_date:
                # Past year end, add empty square
                days_of_week_grid[day_of_week].append(None)
            elif current_date < year_start_date:
                # Before year start, add empty square
                days_of_week_grid[day_of_week].append(None)
            else:
                # Within year, add data
                count = daily_activity_counts.get(current_date, 0)
                # Calculate level (0-4) based on count
                if count == 0:
                    level = 0
                elif count == 1:
                    level = 1
                elif count <= 2:
                    level = 2
                elif count <= 3:
                    level = 3
                else:
                    level = 4
                
                days_of_week_grid[day_of_week].append({
                    'count': count,
                    'level': level,
                    'date': current_date.isoformat(),
                })
            current_date += timedelta(days=1)
        
        week_num += 1
    
    daily_activities['days_of_week'] = days_of_week_grid
    
    # Calculate month positions for heatmap (0-indexed, template adds 1 for CSS grid)
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_labels = []
    for month_num in range(1, 13):
        month_start = date(selected_year, month_num, 1)
        days_from_start = (month_start - first_monday).days
        week_position = days_from_start // 7  # 0-indexed (template adds 1 for CSS grid)
        daily_activities['month_positions'][month_num] = week_position
        month_labels.append({
            'num': month_num,
            'name': month_names[month_num - 1],
            'week_pos': week_position
        })
    daily_activities['month_labels'] = month_labels
    
    # Daily Calories Heatmap (similar structure)
    daily_calories = {
        'total_calories': round(summary_stats['total_calories'] or 0, 0),
        'num_weeks': 53,
        'month_positions': daily_activities['month_positions'].copy(),
        'month_labels': daily_activities['month_labels'].copy(),
        'days_of_week': [],
    }
    
    daily_calorie_totals = defaultdict(float)
    for workout in all_workouts:
        details = get_workout_details(workout)
        if details and details.total_calories:
            daily_calorie_totals[workout.completed_date] += details.total_calories
    
    max_calories = max(daily_calorie_totals.values()) if daily_calorie_totals else 1
    
    calories_grid = [[] for _ in range(7)]
    current_date = first_monday
    week_num = 0
    
    # Generate exactly 53 weeks of data
    while week_num < 53:
        for day_of_week in range(7):
            if current_date > year_end_date or current_date < year_start_date:
                calories_grid[day_of_week].append(None)
            else:
                calories = daily_calorie_totals.get(current_date, 0)
                # Calculate level (0-5) based on calories
                if calories == 0:
                    level = 0
                elif calories < 100:
                    level = 1
                elif calories < 200:
                    level = 2
                elif calories < 500:
                    level = 3
                elif calories < 1000:
                    level = 4
                else:
                    level = 5
                
                calories_grid[day_of_week].append({
                    'calories': round(calories, 0),
                    'level': level,
                    'date': current_date.isoformat(),
                })
            current_date += timedelta(days=1)
        
        week_num += 1
    
    daily_calories['days_of_week'] = calories_grid
    
    # Daily Power Output Heatmap
    daily_power = {
        'total_power': round(summary_stats['total_output'] or 0, 1),
        'num_weeks': 53,
        'month_positions': daily_activities['month_positions'].copy(),
        'month_labels': daily_activities['month_labels'].copy(),
        'days_of_week': [],
    }
    
    daily_power_totals = defaultdict(float)
    for workout in all_workouts:
        details = get_workout_details(workout)
        if details and details.total_output:
            daily_power_totals[workout.completed_date] += details.total_output
    
    max_power = max(daily_power_totals.values()) if daily_power_totals else 1
    
    power_grid = [[] for _ in range(7)]
    current_date = first_monday
    week_num = 0
    
    # Generate exactly 53 weeks of data
    while week_num < 53:
        for day_of_week in range(7):
            if current_date > year_end_date or current_date < year_start_date:
                power_grid[day_of_week].append(None)
            else:
                power = daily_power_totals.get(current_date, 0)
                # Calculate level (0-5) based on power (kJ)
                if power == 0:
                    level = 0
                elif power < 50:
                    level = 1
                elif power < 100:
                    level = 2
                elif power < 200:
                    level = 3
                elif power < 400:
                    level = 4
                else:
                    level = 5
                
                power_grid[day_of_week].append({
                    'power': round(power, 1),
                    'level': level,
                    'date': current_date.isoformat(),
                })
            current_date += timedelta(days=1)
        
        week_num += 1
    
    daily_power['days_of_week'] = power_grid
    
    # Start Times (hourly distribution)
    start_times = {
        'hourly_data': [],
    }
    
    hourly_counts = defaultdict(int)
    for workout in all_workouts:
        # Try to get start time from recorded_date or completed_date
        # For now, use a placeholder - would need actual start time data
        # Assuming workouts are evenly distributed for demo
        hour = workout.completed_date.hour if hasattr(workout.completed_date, 'hour') else 12
        hourly_counts[hour] += 1
    
    for hour in range(24):
        start_times['hourly_data'].append({
            'hour': hour,
            'count': hourly_counts.get(hour, 0),
        })
    
    # Weekday Patterns
    weekday_patterns = {
        'weekday_data': [],
        'most_active_day': None,
        'least_active_day': None,
    }
    
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_short = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weekday_counts_dict = defaultdict(int)
    
    for workout_date in workout_dates:
        weekday_idx = workout_date.weekday()
        weekday_counts_dict[weekday_idx] += 1
    
    weekday_data_list = []
    for idx, day_name in enumerate(weekday_names):
        count = weekday_counts_dict.get(idx, 0)
        weekday_data_list.append({
            'day': day_name,
            'day_short': weekday_short[idx],
            'count': count,
        })
    
    weekday_patterns['weekday_data'] = weekday_data_list
    if weekday_data_list:
        weekday_patterns['most_active_day'] = max(weekday_data_list, key=lambda x: x['count'])['day']
        weekday_patterns['least_active_day'] = min(weekday_data_list, key=lambda x: x['count'])['day']
    
    # Time of Day Patterns
    time_of_day_patterns = {
        'period_data': [],
        'most_active_period': None,
    }
    
    period_counts = {
        'Morning (5am-12pm)': 0,
        'Afternoon (12pm-5pm)': 0,
        'Evening (5pm-9pm)': 0,
        'Night (9pm-5am)': 0,
    }
    
    # Estimate time periods (would need actual start times)
    for workout in all_workouts:
        # Placeholder - distribute evenly for now
        period_counts['Morning (5am-12pm)'] += 1
    
    time_of_day_patterns['period_data'] = [
        {'period': 'Morning (5am-12pm)', 'count': period_counts['Morning (5am-12pm)']},
        {'period': 'Afternoon (12pm-5pm)', 'count': period_counts['Afternoon (12pm-5pm)']},
        {'period': 'Evening (5pm-9pm)', 'count': period_counts['Evening (5pm-9pm)']},
        {'period': 'Night (9pm-5am)', 'count': period_counts['Night (9pm-5am)']},
    ]
    
    if time_of_day_patterns['period_data']:
        time_of_day_patterns['most_active_period'] = max(time_of_day_patterns['period_data'], key=lambda x: x['count'])['period']
    
    # Activity Count by Month and Discipline
    activity_count = {
        'total_activities': total_workouts,
        'monthly_data': [],
        'all_disciplines': distance_stats['all_disciplines'].copy(),
        'discipline_colors': distance_stats['discipline_colors'].copy(),
    }
    
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_name = date(selected_year, month_num, 1).strftime('%B')
        
        discipline_counts = defaultdict(int)
        for workout in month_workouts:
            discipline = get_discipline(workout)
            discipline_counts[discipline] += 1
        
        activity_count['monthly_data'].append({
            'month': month_name,
            'discipline_data': [{'discipline': k, 'count': v} for k, v in discipline_counts.items()],
        })
    
    # Training Load (TSS)
    training_load = {
        'total_tss': 0,
        'avg_tss': 0,
        'monthly_tss': [],
    }
    
    total_tss_sum = 0
    tss_count = 0
    monthly_tss_dict = defaultdict(float)
    
    for workout in all_workouts:
        details = get_workout_details(workout)
        if details and details.tss:
            tss_value = details.tss
            total_tss_sum += tss_value
            tss_count += 1
            month_num = workout.completed_date.month
            monthly_tss_dict[month_num] += tss_value
    
    training_load['total_tss'] = round(total_tss_sum, 0)
    training_load['avg_tss'] = round(total_tss_sum / tss_count, 1) if tss_count > 0 else 0
    
    for month_num in range(1, 13):
        month_name = date(selected_year, month_num, 1).strftime('%B')
        training_load['monthly_tss'].append({
            'month': month_name,
            'tss': round(monthly_tss_dict.get(month_num, 0), 0),
        })
    
    # Duration Distribution
    duration_distribution = {
        'distribution': [],
    }
    
    duration_ranges = [
        ('0-15 min', 0, 15),
        ('15-30 min', 15, 30),
        ('30-45 min', 30, 45),
        ('45-60 min', 45, 60),
        ('60-90 min', 60, 90),
        ('90+ min', 90, 9999),
    ]
    
    for range_name, min_minutes, max_minutes in duration_ranges:
        count = 0
        for workout in all_workouts:
            if workout.ride_detail and workout.ride_detail.duration_seconds:
                duration_minutes = workout.ride_detail.duration_seconds / 60.0
                if min_minutes <= duration_minutes < max_minutes:
                    count += 1
        
        duration_distribution['distribution'].append({
            'range': range_name,
            'count': count,
        })
    
    # Progress Over Time
    progress_over_time = {
        'monthly_data': [],
        'output_trend': 'stable',
        'output_change_pct': 0,
    }
    
    monthly_output_avgs = []
    monthly_distance_avgs = []
    monthly_calorie_avgs = []
    
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_name = date(selected_year, month_num, 1).strftime('%B')
        
        month_output_sum = 0
        month_output_count = 0
        month_distance_sum = 0
        month_distance_count = 0
        month_calorie_sum = 0
        month_calorie_count = 0
        
        for workout in month_workouts:
            details = get_workout_details(workout)
            if details:
                if details.total_output:
                    month_output_sum += details.total_output
                    month_output_count += 1
                if details.distance:
                    month_distance_sum += details.distance * 1.60934
                    month_distance_count += 1
                if details.total_calories:
                    month_calorie_sum += details.total_calories
                    month_calorie_count += 1
        
        avg_output = (month_output_sum / month_output_count) if month_output_count > 0 else 0
        avg_distance = (month_distance_sum / month_distance_count) if month_distance_count > 0 else 0
        avg_calories = (month_calorie_sum / month_calorie_count) if month_calorie_count > 0 else 0
        
        monthly_output_avgs.append(avg_output)
        monthly_distance_avgs.append(avg_distance)
        monthly_calorie_avgs.append(avg_calories)
        
        progress_over_time['monthly_data'].append({
            'month': month_name,
            'avg_output_kj': round(avg_output, 1),
            'avg_distance_km': round(avg_distance, 1),
            'avg_calories': round(avg_calories, 0),
        })
    
    # Calculate trend
    if len(monthly_output_avgs) >= 2:
        first_half_avg = sum(monthly_output_avgs[:6]) / 6 if len(monthly_output_avgs) >= 6 else monthly_output_avgs[0]
        second_half_avg = sum(monthly_output_avgs[-6:]) / 6 if len(monthly_output_avgs) >= 6 else monthly_output_avgs[-1]
        if second_half_avg > first_half_avg * 1.05:
            progress_over_time['output_trend'] = 'increasing'
            progress_over_time['output_change_pct'] = round(((second_half_avg - first_half_avg) / first_half_avg) * 100, 1)
        elif second_half_avg < first_half_avg * 0.95:
            progress_over_time['output_trend'] = 'decreasing'
            progress_over_time['output_change_pct'] = round(((second_half_avg - first_half_avg) / first_half_avg) * 100, 1)
    
    # Monthly Comparison
    monthly_comparison = {
        'monthly_data': [],
    }
    
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_name = date(selected_year, month_num, 1).strftime('%B')
        
        total_hours_month = sum(
            (w.ride_detail.duration_seconds / 3600.0) for w in month_workouts
            if w.ride_detail and w.ride_detail.duration_seconds
        )
        
        total_distance_month = 0
        for w in month_workouts:
            details = get_workout_details(w)
            if details and details.distance:
                total_distance_month += details.distance * 1.60934
        
        monthly_comparison['monthly_data'].append({
            'month': month_name,
            'workout_count': month_workouts.count(),
            'total_hours': round(total_hours_month, 1),
            'total_distance_km': round(total_distance_month, 1),
        })
    
    # Year-over-Year Comparison
    year_over_year = {
        'available': False,
        'current_year': selected_year,
        'previous_year': selected_year - 1,
        'comparison_data': [],
    }
    
    previous_year_workouts = Workout.objects.filter(
        user=request.user,
        completed_date__gte=date(selected_year - 1, 1, 1),
        completed_date__lte=date(selected_year - 1, 12, 31)
    ).select_related('details')
    
    if previous_year_workouts.exists():
        year_over_year['available'] = True
        
        prev_stats = previous_year_workouts.filter(details__isnull=False).aggregate(
            total_distance=Sum('details__distance'),
            total_calories=Sum('details__total_calories'),
            total_output=Sum('details__total_output'),
            total_workouts=Count('id'),
        )
        
        current_total_distance = (summary_stats['total_distance'] or 0) * 1.60934
        prev_total_distance = (prev_stats['total_distance'] or 0) * 1.60934
        
        current_total_calories = summary_stats['total_calories'] or 0
        prev_total_calories = prev_stats['total_calories'] or 0
        
        current_total_output = summary_stats['total_output'] or 0
        prev_total_output = prev_stats['total_output'] or 0
        
        def calc_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100
        
        year_over_year['comparison_data'] = [
            {
                'metric': 'Total Workouts',
                'previous': prev_stats['total_workouts'] or 0,
                'current': total_workouts,
                'change_pct': calc_change(total_workouts, prev_stats['total_workouts'] or 1),
            },
            {
                'metric': 'Total Distance (km)',
                'previous': round(prev_total_distance, 1),
                'current': round(current_total_distance, 1),
                'change_pct': calc_change(current_total_distance, prev_total_distance or 1),
            },
            {
                'metric': 'Total Calories',
                'previous': round(prev_total_calories, 0),
                'current': round(current_total_calories, 0),
                'change_pct': calc_change(current_total_calories, prev_total_calories or 1),
            },
            {
                'metric': 'Total Output (kJ)',
                'previous': round(prev_total_output, 1),
                'current': round(current_total_output, 1),
                'change_pct': calc_change(current_total_output, prev_total_output or 1),
            },
        ]
    
    # Peak Performance
    peak_performance = {
        'monthly_data': [],
        'best_month': None,
        'worst_month': None,
        'best_month_avg': 0,
        'worst_month_avg': 0,
        'top_days': [],
    }
    
    monthly_avg_outputs = {}
    daily_outputs = []
    
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_name = date(selected_year, month_num, 1).strftime('%B')
        
        month_output_sum = 0
        month_output_count = 0
        
        for workout in month_workouts:
            details = get_workout_details(workout)
            if details and details.total_output:
                output = details.total_output
                month_output_sum += output
                month_output_count += 1
                daily_outputs.append({
                    'date': workout.completed_date.isoformat(),
                    'output_kj': round(output, 1),
                })
        
        avg_output = (month_output_sum / month_output_count) if month_output_count > 0 else 0
        monthly_avg_outputs[month_name] = avg_output
        
        peak_performance['monthly_data'].append({
            'month': month_name,
            'avg_output_kj': round(avg_output, 1),
        })
    
    if monthly_avg_outputs:
        best_month_name = max(monthly_avg_outputs.items(), key=lambda x: x[1])[0]
        worst_month_name = min(monthly_avg_outputs.items(), key=lambda x: x[1])[0]
        peak_performance['best_month'] = best_month_name
        peak_performance['worst_month'] = worst_month_name
        peak_performance['best_month_avg'] = round(monthly_avg_outputs[best_month_name], 1)
        peak_performance['worst_month_avg'] = round(monthly_avg_outputs[worst_month_name], 1)
    
    # Top 10 days by output
    daily_outputs.sort(key=lambda x: x['output_kj'], reverse=True)
    peak_performance['top_days'] = daily_outputs[:10]
    
    # Elevation Stats
    elevation_stats = {
        'total_elevation_m': 0,
        'monthly_elevation': [],
    }
    
    # Note: Elevation data may not be available in current model
    # This is a placeholder structure
    total_elevation = 0
    monthly_elevation_dict = defaultdict(float)
    
    for workout in all_workouts:
        # Elevation would come from workout details if available
        # For now, set to 0
        month_num = workout.completed_date.month
        monthly_elevation_dict[month_num] += 0  # Placeholder
    
    elevation_stats['total_elevation_m'] = round(total_elevation, 0)
    
    for month_num in range(1, 13):
        month_name = date(selected_year, month_num, 1).strftime('%B')
        elevation_stats['monthly_elevation'].append({
            'month': month_name,
            'elevation_m': round(monthly_elevation_dict.get(month_num, 0), 0),
        })
    
    # Best Workouts by Discipline
    best_workouts_by_discipline = {
        'best_workouts_by_discipline': {},
        'discipline_labels': {
            'cycling': 'Cycling',
            'running': 'Running',
            'walking': 'Walking',
            'strength': 'Strength',
            'yoga': 'Yoga',
            'other': 'Other',
        }
    }
    
    discipline_best = defaultdict(list)
    
    for workout in all_workouts:
        discipline = get_discipline(workout)
        details = get_workout_details(workout)
        if details:
            output_kj = details.total_output or 0
            distance_km = (details.distance or 0) * 1.60934
            calories = details.total_calories or 0
            
            discipline_best[discipline].append({
                'ride_title': workout.ride_detail.title if workout.ride_detail else 'Workout',
                'instructor': workout.ride_detail.instructor.name if workout.ride_detail and workout.ride_detail.instructor else None,
                'date_formatted': workout.completed_date.strftime('%b %d, %Y'),
                'total_output_kj': round(output_kj, 1),
                'distance_km': round(distance_km, 1),
                'calories': round(calories, 0),
            })
    
    # Get top 3 workouts per discipline by output
    for discipline, workouts_list in discipline_best.items():
        sorted_workouts = sorted(workouts_list, key=lambda x: x['total_output_kj'], reverse=True)
        best_workouts_by_discipline['best_workouts_by_discipline'][discipline] = sorted_workouts[:3]
    
    # Intensity Zones (Power Zones for Cycling, Pace Zones for Running)
    intensity_zones = {
        'has_power_zone_data': False,
        'has_pace_zone_data': False,
        'power_zone_data': [],
        'pace_zone_data': [],
    }
    
    # Calculate power zones for the year (cycling)
    # Get user's FTP for zone calculations
    from accounts.models import FTPEntry
    current_ftp = FTPEntry.objects.filter(user=request.user).order_by('-recorded_date', '-created_at').first()
    
    cycling_workouts_year = all_workouts.filter(
        Q(ride_detail__fitness_discipline__in=['cycling', 'ride']) |
        Q(ride_detail__workout_type__slug__in=['cycling', 'ride'])
    )
    
    if cycling_workouts_year.exists():
        cycling_zones_all = calculate_cycling_zones(cycling_workouts_year, period='all', current_ftp=current_ftp)
        if cycling_zones_all['total_seconds'] > 0:
            intensity_zones['has_power_zone_data'] = True
            total_minutes = cycling_zones_all['total_seconds'] / 60.0
            
            power_zone_colors = {
                1: '#4c6ef5', 2: '#22c55e', 3: '#f59e0b', 4: '#ef4444',
                5: '#ec4899', 6: '#a855f7', 7: '#9333ea',
            }
            
            power_zone_names = {
                1: 'Recovery', 2: 'Endurance', 3: 'Tempo', 4: 'Threshold',
                5: 'VO2 Max', 6: 'Anaerobic', 7: 'Neuromuscular',
            }
            
            for zone_num in range(1, 8):
                zone_info = cycling_zones_all['zones'][zone_num]
                time_minutes = zone_info['time_seconds'] / 60.0
                percentage = (time_minutes / total_minutes * 100) if total_minutes > 0 else 0
                
                intensity_zones['power_zone_data'].append({
                    'name': power_zone_names[zone_num],
                    'time_minutes': round(time_minutes, 0),
                    'percentage': round(percentage, 1),
                    'color': power_zone_colors[zone_num],
                })
    
    # Calculate pace zones for the year (running)
    running_workouts_year = all_workouts.filter(
        Q(ride_detail__fitness_discipline__in=['running', 'run', 'walking']) |
        Q(ride_detail__workout_type__slug__in=['running', 'run', 'walking'])
    )
    
    if running_workouts_year.exists():
        running_zones_all = calculate_running_zones(running_workouts_year, period='all')
        if running_zones_all['total_seconds'] > 0:
            intensity_zones['has_pace_zone_data'] = True
            total_minutes = running_zones_all['total_seconds'] / 60.0
            
            pace_zone_colors = {
                'recovery': '#4c6ef5', 'easy': '#22c55e', 'moderate': '#fbbf24',
                'challenging': '#f59e0b', 'hard': '#ef4444', 'very_hard': '#a855f7', 'max': '#ec4899',
            }
            
            for zone_key in ['recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max']:
                zone_info = running_zones_all['zones'][zone_key]
                time_minutes = zone_info['time_seconds'] / 60.0
                percentage = (time_minutes / total_minutes * 100) if total_minutes > 0 else 0
                
                intensity_zones['pace_zone_data'].append({
                    'name': zone_info['name'],
                    'time_minutes': round(time_minutes, 0),
                    'percentage': round(percentage, 1),
                    'color': pace_zone_colors[zone_key],
                })
    
    # Heart Rate Zones (placeholder - would need HR zone data)
    heart_rate_zones = {
        'has_hr_data': False,
        'hr_zone_data': [],
    }
    
    # Personal Records
    personal_records = {
        'records': {},
    }
    
    # Find longest distance workout
    longest_distance_workout = None
    max_distance = 0
    for workout in all_workouts:
        details = get_workout_details(workout)
        if details and details.distance:
            distance_km = details.distance * 1.60934
            if distance_km > max_distance:
                max_distance = distance_km
                longest_distance_workout = workout
    
    if longest_distance_workout:
        personal_records['records']['longest_distance'] = {
            'value_km': round(max_distance, 1),
            'workout': {'ride': {'title': longest_distance_workout.ride_detail.title if longest_distance_workout.ride_detail else 'Workout'}},
        }
    
    # Find highest power workout
    highest_power_workout = None
    max_power = 0
    for workout in all_workouts:
        details = get_workout_details(workout)
        if details and details.total_output:
            if details.total_output > max_power:
                max_power = details.total_output
                highest_power_workout = workout
    
    if highest_power_workout:
        personal_records['records']['highest_power'] = {
            'value_kj': round(max_power, 1),
            'workout': {'ride': {'title': highest_power_workout.ride_detail.title if highest_power_workout.ride_detail else 'Workout'}},
        }
    
    # Find most calories workout
    most_calories_workout = None
    max_calories = 0
    for workout in all_workouts:
        details = get_workout_details(workout)
        if details and details.total_calories:
            if details.total_calories > max_calories:
                max_calories = details.total_calories
                most_calories_workout = workout
    
    if most_calories_workout:
        personal_records['records']['most_calories'] = {
            'value': round(max_calories, 0),
            'workout': {'ride': {'title': most_calories_workout.ride_detail.title if most_calories_workout.ride_detail else 'Workout'}},
        }
    
    # Find longest duration workout
    longest_duration_workout = None
    max_duration = 0
    for workout in all_workouts:
        if workout.ride_detail and workout.ride_detail.duration_seconds:
            if workout.ride_detail.duration_seconds > max_duration:
                max_duration = workout.ride_detail.duration_seconds
                longest_duration_workout = workout
    
    if longest_duration_workout:
        hours = max_duration / 3600.0
        personal_records['records']['longest_duration'] = {
            'hours': round(hours, 1),
            'workout': {'ride': {'title': longest_duration_workout.ride_detail.title if longest_duration_workout.ride_detail else 'Workout'}},
        }
    
    # Find highest TSS workout
    highest_tss_workout = None
    max_tss = 0
    for workout in all_workouts:
        details = get_workout_details(workout)
        if details and details.tss:
            if details.tss > max_tss:
                max_tss = details.tss
                highest_tss_workout = workout
    
    if highest_tss_workout:
        personal_records['records']['highest_tss'] = {
            'value': round(max_tss, 0),
            'workout': {'ride': {'title': highest_tss_workout.ride_detail.title if highest_tss_workout.ride_detail else 'Workout'}},
        }
    
    # Distance Milestones
    distance_milestones = {
        'has_cycling_milestones': False,
        'has_running_milestones': False,
        'cycling_distance_km': 0,
        'running_distance_km': 0,
        'cycling_milestones': [],
        'running_milestones': [],
    }
    
    cycling_distance_total = 0
    for w in all_workouts:
        details = get_workout_details(w)
        if details and details.distance and get_discipline(w) == 'cycling':
            cycling_distance_total += details.distance * 1.60934
    
    running_distance_total = 0
    for w in all_workouts:
        details = get_workout_details(w)
        if details and details.distance and get_discipline(w) in ['running', 'walking']:
            running_distance_total += details.distance * 1.60934
    
    distance_milestones['cycling_distance_km'] = round(cycling_distance_total, 0)
    distance_milestones['running_distance_km'] = round(running_distance_total, 0)
    
    # Compare to common distances
    cycling_comparisons = [
        ('NYC to Boston', 306),
        ('NYC to DC', 225),
        ('Coast to Coast (US)', 4500),
        ('Tour de France', 3500),
    ]
    
    running_comparisons = [
        ('Marathon', 42.2),
        ('Half Marathon', 21.1),
        ('10K', 10),
        ('5K', 5),
    ]
    
    for name, distance_km in cycling_comparisons:
        if cycling_distance_total >= distance_km:
            distance_milestones['cycling_milestones'].append({
                'icon': '🚴',
                'comparison': f'Equivalent to {name} ({distance_km} km)',
            })
            distance_milestones['has_cycling_milestones'] = True
    
    for name, distance_km in running_comparisons:
        if running_distance_total >= distance_km:
            distance_milestones['running_milestones'].append({
                'icon': '🏃',
                'comparison': f'Equivalent to {name} ({distance_km} km)',
            })
            distance_milestones['has_running_milestones'] = True
    
    # Workout Type Breakdown
    workout_type_breakdown = {
        'type_data': [],
    }
    
    type_counts = defaultdict(int)
    type_colors = {
        'cycling': '#4A90E2',
        'running': '#FF6B35',
        'walking': '#9BE9A8',
        'strength': '#FFD700',
        'yoga': '#9B59B6',
        'other': '#95A5A6',
    }
    
    for workout in all_workouts:
        discipline = get_discipline(workout)
        type_counts[discipline] += 1
    
    total_workouts_for_types = sum(type_counts.values())
    
    for discipline, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_workouts_for_types * 100) if total_workouts_for_types > 0 else 0
        workout_type_breakdown['type_data'].append({
            'type_label': discipline.title(),
            'count': count,
            'percentage': round(percentage, 1),
            'color': type_colors.get(discipline, '#95A5A6'),
        })
    
    # Yearly Calendar (activity calendar)
    yearly_calendar = {
        'has_data': True,
        'months': [],
    }
    
    # Build calendar for each month
    for month_num in range(1, 13):
        month_start = date(selected_year, month_num, 1)
        # Get last day of month
        if month_num == 12:
            month_end = date(selected_year, 12, 31)
        else:
            month_end = date(selected_year, month_num + 1, 1) - timedelta(days=1)
        
        # Get first Monday before or on month start
        first_monday_month = month_start
        while first_monday_month.weekday() != 0:
            first_monday_month -= timedelta(days=1)
        
        month_days = []
        current_date = first_monday_month
        
        # Fill in days before month start (empty)
        while current_date < month_start:
            month_days.append({'day': None, 'type': None})
            current_date += timedelta(days=1)
        
        # Fill in actual month days
        while current_date <= month_end:
            day_workouts = all_workouts.filter(completed_date=current_date)
            
            # Determine workout type for the day
            day_type = None
            has_cardio = False
            has_strength = False
            
            for workout in day_workouts:
                discipline = get_discipline(workout)
                if discipline in ['cycling', 'running', 'walking']:
                    has_cardio = True
                elif discipline == 'strength':
                    has_strength = True
            
            if has_cardio and has_strength:
                day_type = 'cardio_and_strength'
            elif has_cardio:
                day_type = 'cardio'
            elif has_strength:
                day_type = 'strength'
            elif day_workouts.exists():
                day_type = 'other'
            
            month_days.append({
                'day': current_date.day,
                'type': day_type,
            })
            current_date += timedelta(days=1)
        
        # Fill remaining days to complete weeks (empty)
        while len(month_days) % 7 != 0:
            month_days.append({'day': None, 'type': None})
        
        yearly_calendar['months'].append({
            'name': month_start.strftime('%B'),
            'days': month_days,
        })
    
    # Check if user has a share link for this year
    try:
        share = RecapShare.objects.get(user=request.user, year=selected_year)
        share_url = request.build_absolute_uri(
            reverse('plans:recap_share', args=[share.token])
        )
    except RecapShare.DoesNotExist:
        share = None
        share_url = None
    
    context = {
        "has_workouts": True,
        "selected_year": selected_year,
        "available_years": list(available_years),
        "total_workouts": total_workouts,
        "active_days": active_days,
        "longest_streak": longest_streak_days,  # Keep for backward compatibility
        "summary_stats": {
            "total_distance_km": round((summary_stats['total_distance'] or 0) * 1.60934, 1),
            "total_calories": round(summary_stats['total_calories'] or 0, 0),
            "total_output_kj": round(summary_stats['total_output'] or 0, 1),
            "avg_output": round(summary_stats['avg_output'] or 0, 1),
            "avg_calories": round(summary_stats['avg_calories'] or 0, 0),
            "avg_duration_minutes": round(sum((w.ride_detail.duration_seconds / 60.0) for w in all_workouts if w.ride_detail and w.ride_detail.duration_seconds) / total_workouts, 1) if total_workouts > 0 else 0,
            "avg_distance_km": round((summary_stats['total_distance'] or 0) * 1.60934 / total_workouts, 1) if total_workouts > 0 else 0,
            "avg_power_kj": round((summary_stats['total_output'] or 0) / total_workouts, 1) if total_workouts > 0 else 0,
        },
        "top_instructors": list(top_instructors),
        "monthly_data": monthly_data,
        "share": share,
        "share_url": share_url,
        # New comprehensive data
        "consistency_score": consistency_score_data,
        "consistency_metrics": consistency_metrics,
        "streaks": streaks,
        "rest_days": rest_days_data,
        "distance_stats": distance_stats,
        "total_hours": total_hours,
        "daily_activities": daily_activities,
        "daily_calories": daily_calories,
        "daily_power": daily_power,
        "start_times": start_times,
        "weekday_patterns": weekday_patterns,
        "time_of_day_patterns": time_of_day_patterns,
        "activity_count": activity_count,
        "training_load": training_load,
        "duration_distribution": duration_distribution,
        "progress_over_time": progress_over_time,
        "monthly_comparison": monthly_comparison,
        "year_over_year": year_over_year,
        "peak_performance": peak_performance,
        "elevation_stats": elevation_stats,
        "best_workouts_by_discipline": best_workouts_by_discipline,
        "intensity_zones": intensity_zones,
        "heart_rate_zones": heart_rate_zones,
        "personal_records": personal_records,
        "distance_milestones": distance_milestones,
        "workout_type_breakdown": workout_type_breakdown,
        "yearly_calendar": yearly_calendar,
        "use_cache": False,  # Indicates we're calculating fresh data
        "is_first_load": is_first_load,  # Indicates this is the first time generating for this year
        "can_regenerate": can_regenerate,
        "hours_until_regenerate": hours_until_regenerate,
    }
    
    # Save to cache for next time (but not for current year before December 21st)
    try:
        # Don't cache current year if we can't view it yet
        if not can_view_current_year and selected_year == current_year:
            logger.debug(f"Skipping cache save for current year {selected_year} before December 21st")
        else:
            recap_cache, created = RecapCache.get_or_create_for_user_year(request.user, selected_year)
            # Update last_regenerated_at if this was a manual regeneration (check Django cache)
            from django.core.cache import cache
            regenerate_key = f"recap_regenerating_{request.user.id}_{selected_year}"
            if cache.get(regenerate_key):
                recap_cache.last_regenerated_at = timezone.now()
                cache.delete(regenerate_key)
            recap_cache.daily_activities = context.get("daily_activities", {})
            recap_cache.daily_calories = context.get("daily_calories", {})
            recap_cache.daily_power = context.get("daily_power", {})
            recap_cache.distance_stats = context.get("distance_stats", {})
            recap_cache.total_hours = context.get("total_hours", {})
            recap_cache.streaks = context.get("streaks", {})
            recap_cache.rest_days = context.get("rest_days", {})
            recap_cache.start_times = context.get("start_times", {})
            recap_cache.activity_count = context.get("activity_count", {})
            recap_cache.training_load = context.get("training_load", {})
            recap_cache.personal_records = context.get("personal_records", {})
            recap_cache.consistency_metrics = context.get("consistency_metrics", {})
            recap_cache.summary_stats = context.get("summary_stats", {})
            recap_cache.top_instructors = context.get("top_instructors", {})
            recap_cache.top_songs = context.get("top_songs", {})
            recap_cache.duration_distribution = context.get("duration_distribution", {})
            recap_cache.peak_performance = context.get("peak_performance", {})
            recap_cache.elevation_stats = context.get("elevation_stats", {})
            recap_cache.weekday_patterns = context.get("weekday_patterns", {})
            recap_cache.workout_type_breakdown = context.get("workout_type_breakdown", {})
            recap_cache.progress_over_time = context.get("progress_over_time", {})
            recap_cache.best_workouts_by_discipline = context.get("best_workouts_by_discipline", {})
            recap_cache.calorie_efficiency = context.get("calorie_efficiency", {})
            recap_cache.average_metrics_breakdown = context.get("average_metrics_breakdown", {})
            recap_cache.monthly_comparison = context.get("monthly_comparison", {})
            recap_cache.favorite_class_types = context.get("favorite_class_types", {})
            recap_cache.time_of_day_patterns = context.get("time_of_day_patterns", {})
            recap_cache.year_over_year = context.get("year_over_year", {})
            recap_cache.challenge_participation = context.get("challenge_participation", {})
            recap_cache.intensity_zones = context.get("intensity_zones", {})
            recap_cache.distance_milestones = context.get("distance_milestones", {})
            recap_cache.consistency_score = context.get("consistency_score", {})
            recap_cache.heart_rate_zones = context.get("heart_rate_zones", {})
            recap_cache.cadence_resistance_trends = context.get("cadence_resistance_trends", {})
            recap_cache.yearly_calendar = context.get("yearly_calendar", {})
            workout_count = all_workouts.count()
            recap_cache.total_workouts_count = workout_count
            
            # Get the most recent workout update time for this year
            latest_workout = all_workouts.order_by('-last_synced_at').values_list('last_synced_at', flat=True).first()
            if latest_workout:
                recap_cache.last_workout_updated_at = latest_workout
            elif workout_count == 0:
                # No workouts, set to None so we can detect when workouts are added later
                recap_cache.last_workout_updated_at = None
            
            recap_cache.save()
            logger.info(f"Cached recap data for user {request.user.id}, year {selected_year}: {workout_count} workouts")
    except Exception as e:
        logger.warning(f"Failed to save recap cache: {e}")
        # Don't fail the request if caching fails
    
    return render(request, "plans/recap.html", context)


def recap_share(request, token):
    """Public view for shared recap pages"""
    from workouts.models import Workout, WorkoutDetails
    from .models import RecapShare
    from django.db.models import Sum, Avg, Count
    from django.http import HttpResponseNotFound, HttpResponseForbidden
    
    try:
        share = RecapShare.objects.get(token=token)
    except RecapShare.DoesNotExist:
        return HttpResponseNotFound("Share link not found or has been removed.")
    
    # Check if share is valid
    if not share.is_valid():
        return HttpResponseForbidden("This share link is disabled or has expired.")
    
    # Increment view count
    share.increment_view_count()
    
    # Get the year from the share
    year = share.year
    user = share.user
    
    # Get all workouts for the selected year
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    
    all_workouts = Workout.objects.filter(
        user=user,
        completed_at__date__gte=year_start,
        completed_at__date__lte=year_end
    ).select_related('ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details')
    
    if not all_workouts.exists():
        context = {
            "has_workouts": False,
            "selected_year": year,
            "share": share,
            "is_public": True,
            "username": user.username,
        }
        return render(request, "plans/recap_public.html", context)
    
    # Calculate basic statistics (same as recap view)
    total_workouts = all_workouts.count()
    workouts_with_details = all_workouts.filter(details__isnull=False)
    
    summary_stats = workouts_with_details.aggregate(
        total_distance=Sum('details__distance'),
        total_calories=Sum('details__total_calories'),
        total_output=Sum('details__total_output'),
        avg_output=Avg('details__avg_output'),
        avg_calories=Avg('details__total_calories'),
    )
    
    active_days = all_workouts.values('completed_at').distinct().count()
    
    workout_dates = sorted(set(all_workouts.values_list('completed_at', flat=True) if all_workouts.exists() else []))
    longest_streak = 1
    current_streak = 1
    for i in range(1, len(workout_dates)):
        if (workout_dates[i] - workout_dates[i-1]).days == 1:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1
    
    top_instructors = all_workouts.filter(
        ride_detail__instructor__isnull=False
    ).values(
        'ride_detail__instructor__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    monthly_data = []
    for month_num in range(1, 13):
        month_workouts = all_workouts.filter(completed_date__month=month_num)
        month_count = month_workouts.count()
        monthly_data.append({
            'month': date(year, month_num, 1).strftime('%B'),
            'count': month_count,
        })
    
    context = {
        "has_workouts": True,
        "selected_year": year,
        "share": share,
        "is_public": True,
        "username": user.username,
        "total_workouts": total_workouts,
        "active_days": active_days,
        "longest_streak": longest_streak,
        "summary_stats": {
            "total_distance_km": round((summary_stats['total_distance'] or 0) * 1.60934, 1),
            "total_calories": round(summary_stats['total_calories'] or 0, 0),
            "total_output_kj": round(summary_stats['total_output'] or 0, 1),
            "avg_output": round(summary_stats['avg_output'] or 0, 1),
            "avg_calories": round(summary_stats['avg_calories'] or 0, 0),
        },
        "top_instructors": list(top_instructors),
        "monthly_data": monthly_data,
    }
    
    return render(request, "plans/recap_public.html", context)


@login_required
def recap_share_manage(request):
    """API view for managing recap shares (create, enable, disable, regenerate)"""
    from .models import RecapShare
    from django.http import JsonResponse
    from django.urls import reverse
    
    if request.method == 'POST':
        action = request.POST.get('action')
        year = request.POST.get('year')
        
        if not year:
            return JsonResponse({'error': 'Year is required'}, status=400)
        
        try:
            year = int(year)
        except ValueError:
            return JsonResponse({'error': 'Invalid year'}, status=400)
        
        if action == 'create':
            share, created = RecapShare.get_or_create_for_user_year(request.user, year)
            if not created and not share.is_enabled:
                share.is_enabled = True
                share.save(update_fields=['is_enabled'])
            
            share_url = request.build_absolute_uri(
                reverse('plans:recap_share', args=[share.token])
            )
            
            return JsonResponse({
                'success': True,
                'token': share.token,
                'share_url': share_url,
                'is_enabled': share.is_enabled,
                'view_count': share.view_count,
            })
        
        elif action == 'disable':
            try:
                share = RecapShare.objects.get(user=request.user, year=year)
                share.is_enabled = False
                share.save(update_fields=['is_enabled'])
                return JsonResponse({
                    'success': True,
                    'is_enabled': False,
                })
            except RecapShare.DoesNotExist:
                return JsonResponse({'error': 'Share not found'}, status=404)
        
        elif action == 'regenerate':
            try:
                share = RecapShare.objects.get(user=request.user, year=year)
                share.regenerate_token()
                share_url = request.build_absolute_uri(
                    reverse('plans:recap_share', args=[share.token])
                )
                return JsonResponse({
                    'success': True,
                    'token': share.token,
                    'share_url': share_url,
                })
            except RecapShare.DoesNotExist:
                return JsonResponse({'error': 'Share not found'}, status=404)
        
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
    
    elif request.method == 'GET':
        year = request.GET.get('year')
        
        if not year:
            return JsonResponse({'error': 'Year is required'}, status=400)
        
        try:
            year = int(year)
        except ValueError:
            return JsonResponse({'error': 'Invalid year'}, status=400)
        
        try:
            share = RecapShare.objects.get(user=request.user, year=year)
            share_url = request.build_absolute_uri(
                reverse('plans:recap_share', args=[share.token])
            )
            return JsonResponse({
                'exists': True,
                'token': share.token,
                'share_url': share_url,
                'is_enabled': share.is_enabled,
                'view_count': share.view_count,
                'last_viewed_at': share.last_viewed_at.isoformat() if share.last_viewed_at else None,
            })
        except RecapShare.DoesNotExist:
            return JsonResponse({
                'exists': False,
            })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def recap_regenerate(request):
    """Regenerate recap cache for a year (rate limited to once per 24 hours)"""
    from .models import RecapCache
    from django.http import JsonResponse, HttpResponseRedirect
    from django.contrib import messages
    from django.urls import reverse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    year = request.POST.get('year')
    if not year:
        return JsonResponse({'error': 'Year is required'}, status=400)
    
    try:
        year = int(year)
    except ValueError:
        return JsonResponse({'error': 'Invalid year'}, status=400)
    
    # Check if cache exists
    try:
        cache_obj = RecapCache.objects.get(user=request.user, year=year)
        
        # Check rate limiting: can only regenerate once per 24 hours
        if cache_obj.last_regenerated_at:
            time_since_regeneration = timezone.now() - cache_obj.last_regenerated_at
            hours_since = time_since_regeneration.total_seconds() / 3600
            
            if hours_since < 24:
                hours_remaining = 24 - hours_since
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': f'You can only regenerate once every 24 hours. Please wait {hours_remaining:.1f} more hours.',
                        'hours_remaining': round(hours_remaining, 1)
                    }, status=429)
                else:
                    messages.error(request, f'You can only regenerate once every 24 hours. Please wait {hours_remaining:.1f} more hours.')
                    return HttpResponseRedirect(reverse('plans:recap') + f'?year={year}')
        
        # Mark that we're regenerating (so we can update last_regenerated_at)
        from django.core.cache import cache
        regenerate_key = f"recap_regenerating_{request.user.id}_{year}"
        cache.set(regenerate_key, True, 300)  # 5 minutes should be enough
        
        # Delete the cache to force regeneration
        cache_obj.delete()
        
        # Also invalidate Django cache
        cache_key = f"recap_cache_stale_{request.user.id}_{year}"
        cache.set(cache_key, True, 86400)  # Mark as stale for 24 hours
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Cache invalidated. The recap will regenerate on next load.'
            })
        else:
            messages.success(request, 'Cache invalidated. The recap will regenerate on next load.')
            return HttpResponseRedirect(reverse('plans:recap') + f'?year={year}')
    
    except RecapCache.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'No cache found for this year'}, status=404)
        else:
            messages.info(request, 'No cache found for this year.')
            return HttpResponseRedirect(reverse('plans:recap') + f'?year={year}')


@login_required
def eddington(request):
    """Eddington number view showing distance-based achievements"""
    from workouts.models import Workout, WorkoutDetails
    from collections import defaultdict
    
    # Get discipline filter from query params
    discipline_filter = request.GET.get('discipline', 'all')
    
    # Get all workouts for the user with distance data
    all_workouts = Workout.objects.filter(
        user=request.user,
        details__distance__isnull=False,
        details__distance__gt=0
    ).select_related('ride_detail', 'details').order_by("completed_date")
    
    if not all_workouts.exists():
        context = {
            "has_workouts": False,
            "discipline_filter": discipline_filter,
        }
        return render(request, "plans/eddington.html", context)
    
    # Filter by discipline if specified
    if discipline_filter and discipline_filter != 'all':
        discipline_map = {
            'cycling': ['cycling', 'bike'],
            'running': ['running', 'run'],
            'rowing': ['rowing', 'row']
        }
        disciplines = discipline_map.get(discipline_filter, [])
        if disciplines:
            all_workouts = all_workouts.filter(ride_detail__fitness_discipline__in=disciplines)
    
    # Calculate Eddington data
    eddington_data = _calculate_eddington_data(all_workouts)
    
    # Get breakdown by discipline
    discipline_breakdown = _get_discipline_breakdown(request.user)
    
    context = {
        "has_workouts": True,
        "discipline_filter": discipline_filter,
        "eddington_data": eddington_data,
        "discipline_breakdown": discipline_breakdown,
    }
    
    return render(request, "plans/eddington.html", context)


def _get_discipline_breakdown(user):
    """Get Eddington scores broken down by discipline"""
    from workouts.models import Workout
    
    all_workouts = Workout.objects.filter(
        user=user,
        details__distance__isnull=False,
        details__distance__gt=0
    ).select_related('ride_detail', 'details').order_by("completed_date")
    
    breakdown = {}
    
    # Cycling
    cycling_workouts = all_workouts.filter(ride_detail__fitness_discipline__in=['cycling', 'bike'])
    if cycling_workouts.exists():
        breakdown['cycling'] = _calculate_eddington_data(cycling_workouts)
        breakdown['cycling']['name'] = 'Cycling'
        breakdown['cycling']['workout_count'] = cycling_workouts.count()
    
    # Running
    running_workouts = all_workouts.filter(ride_detail__fitness_discipline__in=['running', 'run'])
    if running_workouts.exists():
        breakdown['running'] = _calculate_eddington_data(running_workouts)
        breakdown['running']['name'] = 'Running'
        breakdown['running']['workout_count'] = running_workouts.count()
    
    # Rowing
    rowing_workouts = all_workouts.filter(ride_detail__fitness_discipline__in=['rowing', 'row'])
    if rowing_workouts.exists():
        breakdown['rowing'] = _calculate_eddington_data(rowing_workouts)
        breakdown['rowing']['name'] = 'Rowing'
        breakdown['rowing']['workout_count'] = rowing_workouts.count()
    
    return breakdown


def _calculate_eddington_data(workouts):
    """Calculate Eddington number and related statistics for a set of workouts.
    
    Eddington number E: the maximum number such that the athlete has covered 
    at least E km on at least E days.
    """
    from collections import defaultdict
    from datetime import timedelta
    from workouts.models import WorkoutDetails
    from django.core.exceptions import ObjectDoesNotExist
    
    # Helper function to safely get workout details
    def get_workout_details_safe(workout):
        """Safely get workout details, returning None if it doesn't exist"""
        try:
            return workout.details
        except (WorkoutDetails.DoesNotExist, AttributeError, ObjectDoesNotExist):
            return None
    
    # Get daily distances in km
    daily_distances = defaultdict(list)  # date -> list of distances (km) for that day
    
    for workout in workouts:
        workout_date = workout.completed_date
        
        # Get distance in km (convert from miles)
        distance_km = None
        details = get_workout_details_safe(workout)
        if details and details.distance:
            distance_km = details.distance * 1.60934  # Convert miles to km
        
        if distance_km and distance_km > 0:
            daily_distances[workout_date].append(distance_km)
    
    # For each day, take the maximum distance (in case of multiple workouts)
    daily_max_distances = {}
    for date, distances in daily_distances.items():
        daily_max_distances[date] = max(distances)
    
    # Count how many times each distance threshold is completed
    # times_completed[E] = number of days with at least E km
    times_completed = defaultdict(int)
    max_distance = 0
    
    for date, distance_km in daily_max_distances.items():
        # Round distance down to nearest integer
        distance_int = int(distance_km)
        max_distance = max(max_distance, distance_int)
        
        # For each integer distance from 1 to distance_int, increment count
        for E in range(1, distance_int + 1):
            times_completed[E] += 1
    
    # Calculate current Eddington number
    # Eddington number E is the maximum E where times_completed[E] >= E
    eddington_number = 0
    for E in sorted(times_completed.keys(), reverse=True):
        if times_completed[E] >= E:
            eddington_number = E
            break
    
    # Generate times completed data for chart (up to max_distance + 20)
    times_completed_data = []
    chart_max_distance = max(max_distance, eddington_number + 20)
    
    for E in range(1, min(chart_max_distance + 1, 200)):  # Cap at 200km for chart
        count = times_completed.get(E, 0)
        times_completed_data.append({
            'distance': E,
            'times_completed': count
        })
    
    # Calculate history of Eddington number over time
    # Process workouts chronologically and track Eddington number at each point
    eddington_history = []
    
    # Sort dates chronologically
    sorted_dates = sorted(daily_max_distances.keys())
    
    # Track cumulative times_completed as we process dates
    cumulative_times = defaultdict(int)
    current_max_distance = 0
    
    for date in sorted_dates:
        distance_km = daily_max_distances[date]
        distance_int = int(distance_km)
        current_max_distance = max(current_max_distance, distance_int)
        
        # Update cumulative times for all distances up to this one
        for E in range(1, distance_int + 1):
            cumulative_times[E] += 1
        
        # Calculate Eddington number at this point
        eddington_at_date = 0
        for E in range(1, min(current_max_distance + 1, 200)):
            if cumulative_times[E] >= E:
                eddington_at_date = E
            else:
                break
        
        eddington_history.append({
            'date': date.isoformat(),
            'eddington_number': eddington_at_date
        })
    
    # Calculate days needed for next Eddington numbers
    days_needed = {}
    current_eddington = eddington_number
    
    # For each potential Eddington number from current+1 to current+30
    for target_E in range(current_eddington + 1, min(current_eddington + 30, 200)):
        current_count = times_completed.get(target_E, 0)
        needed_count = target_E
        
        if current_count >= needed_count:
            # Already achieved
            days_needed[target_E] = 0
        else:
            # Calculate how many more days needed
            days_needed[target_E] = needed_count - current_count
    
    # Convert days_needed dict to sorted list for template
    days_needed_list = sorted(
        [{'distance': k, 'days_needed': v} for k, v in days_needed.items()],
        key=lambda x: x['distance']
    )
    
    return {
        'current_eddington': eddington_number,
        'times_completed': times_completed_data,
        'history': eddington_history,
        'days_needed': days_needed,
        'days_needed_list': days_needed_list,  # Sorted list for template
        'total_days': len(daily_max_distances),
        'max_distance': max_distance,
    }