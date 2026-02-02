"""Helper utilities for workouts views and services."""
import json

from django.utils.safestring import mark_safe

from .metrics import MetricsCalculator
from ..models import Playlist
from core.utils.pace_converter import (
    pace_zone_to_level,
    mph_from_pace_value,
    pace_zone_level_from_speed,
    scaled_pace_zone_value_from_speed,
    pace_zone_label_from_level,
    resolve_pace_context,
    PACE_ZONE_LEVEL_ORDER,
    PACE_ZONE_COLORS,
)
from core.utils.chart_helpers import normalize_series_to_svg_points, scaled_zone_value_from_output
from core.utils.workout_targets import target_segment_at_time_with_shift


metrics_calculator = MetricsCalculator()


def estimate_workout_avg_speed_mph(workout):
    """Estimate avg speed (mph) from details or time-series speed."""
    try:
        details = getattr(workout, "details", None)
        if details and getattr(details, "avg_speed", None) is not None:
            return float(details.avg_speed)
    except Exception:
        pass

    try:
        perf = list(workout.performance_data.all())
    except Exception:
        perf = []
    speeds = []
    for p in perf:
        v = getattr(p, "speed", None)
        if isinstance(v, (int, float)):
            speeds.append(float(v))
    if not speeds:
        return None
    return sum(speeds) / float(len(speeds))


def estimate_workout_if_from_tss(workout):
    """
    Estimate IF from stored TSS + duration when available.

    Delegates to MetricsCalculator service.
    """
    try:
        details = getattr(workout, "details", None)
        tss = getattr(details, "tss", None) if details else None
        if tss is None:
            return None
        ride = getattr(workout, "ride_detail", None)
        duration_seconds = getattr(ride, "duration_seconds", None) if ride else None
        if not isinstance(duration_seconds, int) or duration_seconds <= 0:
            return None

        return metrics_calculator.calculate_intensity_factor(
            tss=tss,
            duration_seconds=duration_seconds,
        )
    except Exception:
        return None


def estimate_workout_tss(workout, user_profile=None):
    """
    Estimate cycling TSS when Peloton didn't provide it.

    Uses a common approximation:
      IF ≈ avg_power / FTP
      TSS ≈ hours * IF^2 * 100

    Delegates to MetricsCalculator service.
    """
    ride = getattr(workout, "ride_detail", None)
    if not ride:
        return None

    discipline = (getattr(ride, "fitness_discipline", "") or "").lower()
    if discipline not in ["cycling", "ride", "bike", "bike_bootcamp", "circuit"]:
        return None

    # Prefer stored avg_output if available
    avg_power = None
    try:
        details = getattr(workout, "details", None)
        if details and getattr(details, "avg_output", None) is not None:
            avg_power = float(details.avg_output)
        if details and getattr(details, "tss", None) is not None:
            return float(details.tss)
    except Exception:
        pass

    try:
        perf = list(workout.performance_data.all())
    except Exception:
        perf = []
    outputs = []
    max_t = None
    for p in perf:
        t = getattr(p, "timestamp", None)
        if isinstance(t, int):
            max_t = t if max_t is None else max(max_t, t)
        v = getattr(p, "output", None)
        if isinstance(v, (int, float)):
            outputs.append(float(v))

    if avg_power is None:
        if not outputs:
            return None
        avg_power = sum(outputs) / float(len(outputs))

    # Duration: prefer class duration; fallback to last timestamp
    duration_seconds = getattr(ride, "duration_seconds", None)
    if not isinstance(duration_seconds, int) or duration_seconds <= 0:
        duration_seconds = (max_t + 1) if isinstance(max_t, int) else None
    if not duration_seconds or duration_seconds <= 0:
        return None

    # FTP at workout date
    ftp = None
    workout_date = getattr(workout, "completed_date", None) or getattr(workout, "recorded_date", None)
    if user_profile and workout_date and hasattr(user_profile, "get_ftp_at_date"):
        try:
            ftp = user_profile.get_ftp_at_date(workout_date)
        except Exception:
            ftp = None
    if not ftp and user_profile and hasattr(user_profile, "get_current_ftp"):
        try:
            ftp = user_profile.get_current_ftp()
        except Exception:
            ftp = None

    # Use MetricsCalculator for TSS calculation
    return metrics_calculator.calculate_tss(
        avg_power=avg_power,
        duration_seconds=duration_seconds,
        ftp=ftp,
    )


def zone_ranges_for_ftp(ftp):
    """
    Return power zone ranges dict from FTP.

    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_power_zone_ranges(ftp)


def power_zone_for_output(output_watts, zone_ranges):
    """
    Return zone number 1-7 for an output value given zone_ranges.

    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_power_zone_for_output(output_watts, zone_ranges)


def pace_zone_targets_for_level(pace_level):
    """
    Build pace zone targets (min/mile) from a pace level (1-10),
    matching Profile.get_pace_zone_targets().

    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_pace_zone_targets(pace_level)


def target_watts_for_zone(zone_ranges, zone_num):
    """
    Get target watts (midpoint) for a power zone.

    Delegates to MetricsCalculator service.
    """
    return metrics_calculator.get_target_watts_for_zone(zone_num, zone_ranges)


def build_workout_card_chart(workout, user_profile=None):
    """
    Build lightweight mini-chart data for workout cards.
    Output is a dict that templates can render as an inline SVG.
    """
    ride = getattr(workout, 'ride_detail', None)
    if not ride:
        return None

    perf = list(getattr(workout, 'performance_data', []).all() if hasattr(workout, 'performance_data') else [])
    if not perf:
        return None

    discipline = (getattr(ride, 'fitness_discipline', '') or '').lower()
    class_type = (getattr(ride, 'class_type', '') or '').lower()
    is_power_zone = bool(getattr(ride, 'is_power_zone_class', False) or class_type == 'power_zone')
    is_pace = class_type == 'pace_target' or discipline in ['running', 'run', 'walking', 'walk']
    is_cycling = discipline in ['cycling', 'ride', 'bike']
    workout_date = getattr(workout, 'completed_date', None) or getattr(workout, 'recorded_date', None)
    user_ftp = None
    if user_profile and workout_date and hasattr(user_profile, "get_ftp_at_date"):
        try:
            user_ftp = user_profile.get_ftp_at_date(workout_date)
        except Exception:
            user_ftp = None
    zone_ranges = zone_ranges_for_ftp(user_ftp) if user_ftp else None
    pace_context = None
    pace_ranges = None
    pace_zone_thresholds = None
    pace_level_value = None
    activity_type = None
    if is_pace:
        pace_context = resolve_pace_context(user_profile, workout_date, discipline)
        if isinstance(pace_context, dict):
            activity_type = pace_context.get('activity_type')
            pace_ranges = pace_context.get('pace_ranges') or None
            pace_zone_thresholds = pace_context.get('pace_zone_thresholds') or None
            pace_level_value = pace_context.get('pace_level')

    # Decide which series to chart
    metric_key = None
    chart_kind = None
    if is_pace:
        metric_key = 'speed'
        chart_kind = 'pace'
        line_color = "rgba(253, 224, 71, 0.95)"  # yellow-300
    elif is_cycling:
        metric_key = 'output'
        chart_kind = 'power_zone' if is_power_zone else 'cycling_output_zones'
        line_color = "rgba(253, 224, 71, 0.95)"  # yellow-300
    else:
        return None

    series = []
    for p in perf:
        t = getattr(p, 'timestamp', None)
        v = getattr(p, metric_key, None)
        if not isinstance(t, int):
            continue
        if not isinstance(v, (int, float)):
            continue
        point = {'t': int(t), 'v': float(v)}
        if chart_kind == 'power_zone':
            z = getattr(p, 'power_zone', None)
            if isinstance(z, int):
                point['z'] = z
            else:
                # Fallback: compute from FTP if power_zone field missing
                zc = power_zone_for_output(point['v'], zone_ranges)
                if isinstance(zc, int):
                    point['z'] = zc
        elif chart_kind == 'pace':
            z = getattr(p, 'intensity_zone', None)
            if isinstance(z, str) and z:
                point['z'] = z
                lvl = pace_zone_to_level(z)
                if isinstance(lvl, int):
                    point['sv'] = float(lvl)
            if pace_ranges:
                sv = scaled_pace_zone_value_from_speed(point['v'], pace_ranges)
                if sv is not None:
                    point['sv'] = sv
                if not point.get('z'):
                    lvl = pace_zone_level_from_speed(point['v'], pace_ranges)
                    label = pace_zone_label_from_level(lvl) if lvl else None
                    if label:
                        point['z'] = label
        elif chart_kind == 'cycling_output_zones':
            # Non–PZ cycling should follow power zones (not pace/intensity bands)
            zc = power_zone_for_output(point['v'], zone_ranges)
            if isinstance(zc, int):
                point['z'] = zc
        if chart_kind in ['power_zone', 'cycling_output_zones']:
            scaled_sv = scaled_zone_value_from_output(point['v'], zone_ranges)
            if scaled_sv is not None:
                point['sv'] = scaled_sv
            elif isinstance(point.get('z'), int):
                point['sv'] = float(point['z'])
        series.append(point)

    scaled_min = None
    scaled_max = None
    display_max_zone = 7
    if chart_kind in ['power_zone', 'cycling_output_zones', 'pace']:
        scaled_min = 0.5
        scaled_max = display_max_zone + 0.5

    # Build target segments (optional)
    target_segments = None
    TARGET_TIME_SHIFT_SECONDS = -60  # intro is within target metrics; shift targets earlier
    try:
        if chart_kind == 'power_zone' and user_ftp and hasattr(ride, 'get_power_zone_segments'):
            pz_segments = ride.get_power_zone_segments(user_ftp=user_ftp)
            target_segments = []
            for seg in (pz_segments or []):
                z = seg.get('zone')
                try:
                    z = int(z)
                except Exception:
                    z = None
                tv = target_watts_for_zone(zone_ranges, z) if z else None
                target_segments.append({
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'target': tv,
                    'zone': z,
                })
        elif chart_kind == 'pace' and hasattr(ride, 'get_pace_segments'):
            pace_zones = pace_zone_thresholds
            if not pace_zones:
                fallback_level = pace_level_value or 5
                pace_zones = pace_zone_targets_for_level(fallback_level)
            pace_segments = ride.get_pace_segments(user_pace_zones=pace_zones)
            target_segments = []
            for seg in (pace_segments or []):
                raw_zone = seg.get('zone') or seg.get('zone_name') or seg.get('pace_level')
                zone_level = pace_zone_to_level(raw_zone)
                tv = None
                for key in ('target_speed_mph', 'target_mph'):
                    value = seg.get(key)
                    if isinstance(value, (int, float)):
                        tv = float(value)
                        break
                if tv is None:
                    tv = mph_from_pace_value(seg.get('pace_range') or seg.get('pace_target'))
                if tv is None and pace_ranges and isinstance(zone_level, int):
                    zone_meta = pace_ranges.get(zone_level)
                    if zone_meta:
                        tv = zone_meta.get('mid_mph')
                target_segments.append({
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'target': tv,
                    'zone': seg.get('zone'),
                    'zone_name': seg.get('zone_name'),
                    'zone_level': zone_level,
                })
    except Exception:
        target_segments = None

    # Attach target values to points (so scaling includes them and tooltip can show them)
    if target_segments:
        for pt in series:
            t = pt.get('t')
            if isinstance(t, int):
                seg = target_segment_at_time_with_shift(target_segments, t, shift_seconds=TARGET_TIME_SHIFT_SECONDS)
                if not isinstance(seg, dict):
                    continue

                tv = seg.get('target')
                if isinstance(tv, (int, float)):
                    pt['tv'] = float(tv)

                # Scaled target for zone-space plotting
                if chart_kind in ['power_zone', 'cycling_output_zones']:
                    stv = scaled_zone_value_from_output(tv, zone_ranges) if isinstance(tv, (int, float)) else None
                    if stv is None:
                        zt = seg.get('zone')
                        try:
                            zt = int(zt) if zt is not None else None
                        except Exception:
                            zt = None
                        if isinstance(zt, int) and 1 <= zt <= 7:
                            stv = float(zt)
                    if isinstance(stv, (int, float)):
                        pt['stv'] = stv
                elif chart_kind == 'pace':
                    stv = None
                    if isinstance(tv, (int, float)) and pace_ranges:
                        stv = scaled_pace_zone_value_from_speed(tv, pace_ranges)
                    if stv is None:
                        lvl = seg.get('zone_level') or pace_zone_to_level(seg.get('zone') or seg.get('zone_name'))
                        if isinstance(lvl, int):
                            stv = float(lvl)
                    if isinstance(stv, (int, float)):
                        pt['stv'] = stv

    if chart_kind in ['power_zone', 'cycling_output_zones', 'pace']:
        zone_cap = 7
        max_zone_hit = 0

        def _apply_zone_candidate(candidate):
            nonlocal max_zone_hit
            if candidate is None:
                return
            if chart_kind == 'pace' and not isinstance(candidate, (int, float)):
                lvl = pace_zone_to_level(candidate)
            else:
                try:
                    lvl = int(round(float(candidate)))
                except Exception:
                    lvl = None
            if isinstance(lvl, int) and 1 <= lvl <= zone_cap:
                max_zone_hit = max(max_zone_hit, lvl)

        for pt in series:
            if isinstance(pt.get('sv'), (int, float)):
                _apply_zone_candidate(pt.get('sv'))
            else:
                _apply_zone_candidate(pt.get('z'))

        if target_segments:
            for seg in target_segments or []:
                candidate = None
                if isinstance(seg, dict):
                    candidate = seg.get('zone_level')
                    if candidate is None:
                        candidate = seg.get('zone') or seg.get('zone_name')
                _apply_zone_candidate(candidate)

        if max_zone_hit > 0:
            display_max_zone = min(zone_cap, max_zone_hit + 2)
        scaled_min = 0.5
        scaled_max = display_max_zone + 0.5

    width = 420
    height = 150
    preserve_full_series = chart_kind in ['power_zone', 'cycling_output_zones', 'pace']
    points_str, plot_box, points_list, vmin, vmax = normalize_series_to_svg_points(
        series,
        width=width,
        height=height,
        left_pad=0,
        right_pad=0,
        top_pad=6,
        bottom_pad=8,
        preserve_full_series=preserve_full_series,
        max_points=120,
        scaled_min=scaled_min,
        scaled_max=scaled_max,
    )
    if not points_str:
        return None

    plot_x0, plot_y0, plot_x1, plot_y1 = plot_box
    plot_w = plot_x1 - plot_x0
    plot_h = plot_y1 - plot_y0
    plot_h = plot_y1 - plot_y0

    bands = []
    labels = []

    if is_pace:
        zone_levels = list(range(display_max_zone, 0, -1)) or list(reversed(PACE_ZONE_LEVEL_ORDER))
        band_h = plot_h / float(len(zone_levels)) if zone_levels else plot_h
        for idx, level in enumerate(zone_levels):
            bands.append({
                'y': plot_y0 + idx * band_h,
                'h': band_h,
                'fill': PACE_ZONE_COLORS.get(level, "rgba(59, 130, 246, 0.55)"),
                'label': pace_zone_label_from_level(level) or f"Zone {level}",
                'label_y': plot_y0 + idx * band_h + band_h / 2.0,
            })

    elif chart_kind in ['power_zone', 'cycling_output_zones']:
        zone_colors = {
            7: "rgba(239, 68, 68, 0.45)",   # red-500
            6: "rgba(249, 115, 22, 0.45)",  # orange-500
            5: "rgba(245, 158, 11, 0.45)",  # amber-500
            4: "rgba(34, 197, 94, 0.45)",   # green-500
            3: "rgba(20, 184, 166, 0.45)",  # teal-500
            2: "rgba(59, 130, 246, 0.45)",  # blue-500
            1: "rgba(124, 58, 237, 0.45)",  # violet-600
        }
        top_zone = display_max_zone or 7
        top_zone = max(1, min(7, top_zone))
        zone_range = list(range(top_zone, 0, -1))
        band_h = plot_h / float(len(zone_range))
        for idx, zone in enumerate(zone_range):
            bands.append({
                'y': plot_y0 + idx * band_h,
                'h': band_h,
                'fill': zone_colors.get(zone, zone_colors[1]),
                'label': f"Zone {zone}",
                'label_y': plot_y0 + idx * band_h + band_h / 2.0,
            })

    # Safe JSON for inline script blocks in templates
    try:
        series_json = mark_safe(json.dumps(points_list))
    except Exception:
        series_json = "[]"

    # Build target polyline string if targets exist (stepped line for 90-degree angles)
    target_points = None
    if points_list and any(isinstance(p.get('tv'), (int, float)) for p in points_list):
        try:
            plot_x0, plot_y0, plot_x1, plot_y1 = plot_box
            if vmax == vmin:
                vmax = (vmin or 0) + 1.0

            def y_for(v):
                norm = (float(v) - float(vmin)) / float(float(vmax) - float(vmin))
                return float(plot_y1) - norm * (float(plot_y1) - float(plot_y0))

            # Build stepped line points: for each segment, add horizontal then vertical point
            target_pts = []
            prev_x = None
            prev_y = None
            prev_tv = None
            prev_stv = None

            for i, p in enumerate(points_list):
                tv = p.get('tv')
                stv = p.get('stv')
                curr_y = y_for(stv) if isinstance(stv, (int, float)) else y_for(tv) if isinstance(tv, (int, float)) else None
                curr_x = float(p['x'])

                if curr_y is None:
                    # Missing target - break the line
                    prev_x = None
                    prev_y = None
                    prev_tv = None
                    prev_stv = None
                    continue

                if prev_x is not None and prev_y is not None:
                    # Add intermediate point for stepped line: horizontal from prev, then vertical to curr
                    target_pts.append(f"{curr_x},{prev_y:.1f}")

                target_pts.append(f"{curr_x},{curr_y:.1f}")

                prev_x = curr_x
                prev_y = curr_y
                prev_tv = tv
                prev_stv = stv

            joined = " ".join([s for s in target_pts if s])
            target_points = joined if joined else None
        except Exception:
            target_points = None

    return {
        'width': width,
        'height': height,
        'plot_x0': plot_x0,
        'plot_x1': plot_x1,
        'plot_y0': plot_y0,
        'plot_y1': plot_y1,
        'plot_w': plot_w,
        'plot_h': plot_h,
        'bands': bands,
        'points': points_str,
        'target_points': target_points,
        'series_json': series_json,
        'kind': chart_kind,
        'vmin': vmin,
        'vmax': vmax,
        'line_color': line_color,
    }


def store_playlist_from_data(playlist_data, ride_detail, logger, workout_num=None, workout_id=None):
    """
    Helper function to store playlist data for a ride.
    playlist_data should come from ride_details response (data['playlist']).
    Returns True if playlist was stored successfully, False otherwise.
    """
    if not playlist_data:
        return False

    try:
        # Extract playlist information
        peloton_playlist_id = playlist_data.get('id')
        songs = playlist_data.get('songs', [])
        top_artists = playlist_data.get('top_artists', [])
        top_albums = playlist_data.get('top_albums', [])
        stream_id = playlist_data.get('stream_id')
        stream_url = playlist_data.get('stream_url')

        # Create or update playlist
        playlist, playlist_created = Playlist.objects.update_or_create(
            ride_detail=ride_detail,
            defaults={
                'peloton_playlist_id': peloton_playlist_id,
                'songs': songs,
                'top_artists': top_artists,
                'top_albums': top_albums,
                'stream_id': stream_id,
                'stream_url': stream_url,
                'is_top_artists_shown': playlist_data.get('is_top_artists_shown', False),
                'is_playlist_shown': playlist_data.get('is_playlist_shown', False),
                'is_in_class_music_shown': playlist_data.get('is_in_class_music_shown', False),
            }
        )
        log_prefix = f"Workout {workout_num} ({workout_id})" if workout_num and workout_id else "Playlist"
        if playlist_created:
            logger.info(f"{log_prefix}: ✓ Created Playlist with {len(songs)} songs")
        else:
            logger.debug(f"{log_prefix}: ↻ Updated Playlist")
        return True
    except Exception as e:
        # Playlist storage is optional - don't fail the whole sync if it fails
        log_prefix = f"Workout {workout_num} ({workout_id})" if workout_num and workout_id else "Playlist"
        logger.debug(f"{log_prefix}: Could not store playlist: {e}")
    return False
