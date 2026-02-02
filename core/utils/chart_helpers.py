"""
Chart and data visualization helpers for workout data.

Extracted from workouts/views.py for reuse across applications.
Handles downsampling, normalization, and SVG point generation for workout charts.
"""
from typing import List, Dict, Tuple, Optional, Any


def downsample_points(values: List[float], max_points: int = 48) -> List[float]:
    """
    Downsample a list of numeric values to at most max_points, preserving shape.
    
    Args:
        values: List of numeric values to downsample
        max_points: Maximum number of points to return
        
    Returns:
        Downsampled list of values
        
    Example:
        >>> values = list(range(100))
        >>> downsampled = downsample_points(values, max_points=10)
        >>> len(downsampled)
        10
    """
    if not isinstance(values, list):
        return []
    cleaned = [v for v in values if isinstance(v, (int, float))]
    if len(cleaned) <= max_points:
        return cleaned
    if max_points < 2:
        return cleaned[:1]
    step = (len(cleaned) - 1) / float(max_points - 1)
    out = []
    for i in range(max_points):
        idx = int(round(i * step))
        if idx < 0:
            idx = 0
        if idx >= len(cleaned):
            idx = len(cleaned) - 1
        out.append(cleaned[idx])
    return out


def downsample_series(series: List[Dict], max_points: int = 48) -> List[Dict]:
    """
    Downsample a list of dict points (must include 'v') to at most max_points.
    
    Args:
        series: List of dict points with 'v' key (value)
        max_points: Maximum number of points to return
        
    Returns:
        Downsampled list of dict points
        
    Example:
        >>> series = [{'v': i, 't': i} for i in range(100)]
        >>> downsampled = downsample_series(series, max_points=10)
        >>> len(downsampled)
        10
    """
    if not isinstance(series, list):
        return []
    cleaned = [p for p in series if isinstance(p, dict) and isinstance(p.get('v'), (int, float))]
    if len(cleaned) <= max_points:
        return cleaned
    if max_points < 2:
        return cleaned[:1]
    step = (len(cleaned) - 1) / float(max_points - 1)
    out = []
    for i in range(max_points):
        idx = int(round(i * step))
        if idx < 0:
            idx = 0
        if idx >= len(cleaned):
            idx = len(cleaned) - 1
        out.append(cleaned[idx])
    return out


def normalize_series_to_svg_points(
    series: List[Dict],
    width: int = 360,
    height: int = 120,
    left_pad: int = 34,
    right_pad: int = 10,
    top_pad: int = 8,
    bottom_pad: int = 8,
    *,
    preserve_full_series: bool = False,
    max_points: int = 120,
    scaled_min: Optional[float] = None,
    scaled_max: Optional[float] = None,
) -> Tuple[Optional[str], Tuple[float, float, float, float], List[Dict], Optional[float], Optional[float]]:
    """
    Convert a series of dict points (with 'v' and optional 't'/'z') into SVG points.
    
    Args:
        series: List of dict points with 'v' key (value) and optional 't' (timestamp), 'z' (zone)
        width: SVG width in pixels
        height: SVG height in pixels
        left_pad: Left padding in pixels
        right_pad: Right padding in pixels
        top_pad: Top padding in pixels
        bottom_pad: Bottom padding in pixels
        preserve_full_series: If True, don't downsample (use for zone-based charts)
        max_points: Maximum points if downsampling
        scaled_min: Minimum value for scaling (e.g., 0.5 for zone charts)
        scaled_max: Maximum value for scaling (e.g., 7.5 for zone charts)
        
    Returns:
        Tuple of (points_str, plot_box, points_list, vmin, vmax)
        - points_str: SVG polyline points string or None if insufficient data
        - plot_box: (x0, y0, x1, y1) plot area coordinates
        - points_list: List of point dicts with x, y, t, v keys
        - vmin: Minimum value in series
        - vmax: Maximum value in series
        
    Example:
        >>> series = [{'v': 100, 't': 0}, {'v': 150, 't': 60}, {'v': 120, 't': 120}]
        >>> points_str, box, points, vmin, vmax = normalize_series_to_svg_points(series)
        >>> print(points_str)
        '34.0,112.0 180.0,8.0 326.0,88.0'
    """
    plot_x0 = left_pad
    plot_x1 = max(left_pad + 10, width - right_pad)
    plot_y0 = top_pad
    plot_y1 = max(top_pad + 10, height - bottom_pad)
    plot_box = (plot_x0, plot_y0, plot_x1, plot_y1)

    cleaned = [p for p in series if isinstance(p, dict) and isinstance(p.get('v'), (int, float))] if isinstance(series, list) else []
    if len(cleaned) < 2:
        return None, plot_box, [], None, None

    if preserve_full_series:
        ds = cleaned
    else:
        ds = downsample_series(cleaned, max_points=max_points)
    if len(ds) < 2:
        return None, plot_box, [], None, None

    # Allow plotting in "scaled value" space (e.g. zone 1-7) while keeping raw v for tooltips.
    uses_scaled = any(isinstance(p.get('sv'), (int, float)) for p in ds) or any(isinstance(p.get('stv'), (int, float)) for p in ds)

    def _v_for_plot(p):
        sv = p.get('sv')
        if isinstance(sv, (int, float)):
            return float(sv)
        return float(p['v'])

    vals = [_v_for_plot(p) for p in ds]
    # Include target values in scaling if present
    for p in ds:
        stv = p.get('stv')
        if isinstance(stv, (int, float)):
            vals.append(float(stv))
            continue
        tv = p.get('tv')
        if isinstance(tv, (int, float)):
            vals.append(float(tv))

    # For zone-based plots, keep fixed padding so the line sits nicely in the bands.
    if uses_scaled:
        vmin = float(scaled_min) if isinstance(scaled_min, (int, float)) else 0.5
        vmax = float(scaled_max) if isinstance(scaled_max, (int, float)) else 7.5
    else:
        vmin = min(vals)
        vmax = max(vals)
    if vmax == vmin:
        vmax = vmin + 1.0

    n = len(ds)
    xs = []
    if n == 1:
        xs = [plot_x0]
    else:
        span = (plot_x1 - plot_x0)
        xs = [plot_x0 + (span * i / float(n - 1)) for i in range(n)]

    def y_for(v):
        norm = (v - vmin) / float(vmax - vmin)
        return plot_y1 - norm * (plot_y1 - plot_y0)

    points = []
    pts = []
    for i in range(n):
        raw_v = float(ds[i]['v'])
        v = _v_for_plot(ds[i])
        x = float(xs[i])
        y = float(y_for(v))
        point = {
            'x': round(x, 1),
            'y': round(y, 1),
            't': int(ds[i].get('t', 0) or 0),
            'v': raw_v,
        }
        tv = ds[i].get('tv')
        if isinstance(tv, (int, float)):
            point['tv'] = float(tv)
        stv = ds[i].get('stv')
        if isinstance(stv, (int, float)):
            point['stv'] = float(stv)
        if ds[i].get('z') is not None:
            point['z'] = ds[i].get('z')
        pts.append(f"{point['x']:.1f},{point['y']:.1f}")
        points.append(point)

    return " ".join(pts), plot_box, points, vmin, vmax


def scaled_zone_value_from_output(output_watts: float, zone_ranges: Dict) -> Optional[float]:
    """
    Map an output value onto the zone axis so the line can flow within each band.
    
    Args:
        output_watts: Power output in watts
        zone_ranges: Dict mapping zone number to (lower, upper) bounds
        
    Returns:
        Scaled value (e.g., 2.7 for 70% through zone 3) or None if invalid
        
    Example:
        >>> zone_ranges = {1: (0, 100), 2: (100, 150), 3: (150, 200)}
        >>> scaled_zone_value_from_output(125, zone_ranges)
        2.5  # Midpoint of zone 2
    """
    if not isinstance(output_watts, (int, float)):
        return None
    if not isinstance(zone_ranges, dict) or not zone_ranges:
        return None

    # First determine which zone this output falls into
    zone = None
    for z in sorted(zone_ranges.keys()):
        lo, hi = zone_ranges.get(z, (None, None))
        if not isinstance(lo, (int, float)):
            continue
        hi_val = float(hi) if isinstance(hi, (int, float)) else float(lo) + max(float(lo) * 0.25, 25.0)
        if float(output_watts) <= hi_val + 1e-6:
            zone = z
            break
    
    if zone is None:
        zone = max(zone_ranges.keys())
    
    if not isinstance(zone, int):
        return None

    lo, hi = zone_ranges.get(zone, (None, None))
    if not isinstance(lo, (int, float)):
        return float(zone)

    lo = float(lo)
    hi_val = float(hi) if isinstance(hi, (int, float)) else None
    if hi_val is None:
        hi_val = lo + max(lo * 0.25, 25.0)

    span = hi_val - lo
    if span <= 0:
        span = max(lo * 0.25, 25.0)

    value = float(output_watts)
    clamped = min(max(value, lo), lo + span)
    frac = (clamped - lo) / span
    frac = max(0.0, min(frac, 1.0))

    return (zone - 0.5) + frac
