"""
Chart Builder Service for Pelvic Planner Workouts

Encapsulates all chart data generation:
- Performance graphs (watts/pace over time with zones)
- Zone distribution (pie/donut charts)
- TSS/IF trends
- Target line charts
"""

import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from .metrics import MetricsCalculator

logger = logging.getLogger(__name__)


class ChartBuilder:
    """
    Generates chart data for workout visualizations.
    
    Uses MetricsCalculator for all metric calculations.
    Handles data downsampling, aggregation, and format conversion.
    """

    # Default settings
    DEFAULT_DOWNSAMPLE_POINTS = 120
    ZONE_COLORS = {
        1: '#4472C4',  # Blue
        2: '#70AD47',  # Green
        3: '#FFC000',  # Yellow
        4: '#FF6B35',  # Orange
        5: '#E74C3C',  # Red
        6: '#C1339E',  # Purple
        7: '#8B0000',  # Dark Red
    }

    PACE_ZONE_COLORS = {
        'recovery': '#4472C4',
        'easy': '#70AD47',
        'moderate': '#FFC000',
        'challenging': '#FF6B35',
        'hard': '#E74C3C',
        'very_hard': '#C1339E',
        'max': '#8B0000',
    }

    def __init__(self):
        """Initialize ChartBuilder with MetricsCalculator."""
        self.metrics = MetricsCalculator()

    def generate_performance_graph(
        self,
        performance_data: List[Dict[str, Any]],
        workout_type: str = 'power_zone',
        ftp: Optional[float] = None,
        pace_level: Optional[int] = None,
        target_segments: Optional[List[Dict[str, Any]]] = None,
        downsample_points: int = DEFAULT_DOWNSAMPLE_POINTS,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate performance graph data with zones.

        Args:
            performance_data: List of performance data points with 'timestamp' and 'value'
            workout_type: 'power_zone' or 'pace_target'
            ftp: FTP for power zone calculations
            pace_level: Pace level for pace target calculations
            target_segments: Optional list of target segments with zone/pace info
            downsample_points: Maximum points in output (for performance)

        Returns:
            Dict with chart data or None if insufficient data
        """
        if not performance_data:
            return None

        # Extract and validate data points
        points = self._extract_data_points(performance_data)
        if not points:
            return None

        # Downsample for performance
        downsampled = self._downsample_points(points, downsample_points)

        # Get zone ranges/targets
        if workout_type == 'power_zone' and ftp:
            zone_ranges = self.metrics.get_power_zone_ranges(ftp)
            if not zone_ranges:
                return None

            # Assign zones to each point
            for point in downsampled:
                zone = self.metrics.get_power_zone_for_output(
                    point['value'], zone_ranges
                )
                point['zone'] = zone
        elif workout_type == 'pace_target' and pace_level:
            pace_targets = self.metrics.get_pace_zone_targets(pace_level)
            if not pace_targets:
                return None

            # Assign pace zones (would need pace value in data)
            # This is simplified - actual implementation depends on data format

        # Build chart data
        return {
            'type': 'performance_graph',
            'workout_type': workout_type,
            'points': downsampled,
            'zones': self._get_zone_config(workout_type),
            'colors': self.ZONE_COLORS if workout_type == 'power_zone' else self.PACE_ZONE_COLORS,
            'min_value': min(p['value'] for p in downsampled),
            'max_value': max(p['value'] for p in downsampled),
        }

    def generate_zone_distribution(
        self,
        zone_data: List[Dict[str, Any]],
        workout_type: str = 'power_zone',
        total_duration_seconds: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate zone distribution chart data (pie/donut).

        Args:
            zone_data: List of zone info with 'zone' and 'time_sec'
            workout_type: 'power_zone' or 'pace_target'
            total_duration_seconds: Total workout duration for validation

        Returns:
            Dict with chart data or None if insufficient data
        """
        if not zone_data:
            return None

        # Aggregate time by zone
        zone_times = defaultdict(float)
        total_time = 0.0

        for zone_info in zone_data:
            zone = zone_info.get('zone')
            time_sec = zone_info.get('time_sec', 0)

            if not zone:
                continue

            try:
                time_sec = float(time_sec)
            except (TypeError, ValueError):
                continue

            if time_sec <= 0:
                continue

            zone_times[zone] += time_sec
            total_time += time_sec

        if total_time <= 0:
            return None

        # Build distribution data
        distribution = []
        for zone in sorted(zone_times.keys()):
            time_sec = zone_times[zone]
            percentage = (time_sec / total_time) * 100
            minutes = time_sec / 60.0

            zone_label = self._get_zone_label(zone, workout_type)
            zone_color = self._get_zone_color(zone, workout_type)

            distribution.append({
                'zone': zone,
                'label': zone_label,
                'time_seconds': time_sec,
                'time_minutes': round(minutes, 1),
                'percentage': round(percentage, 1),
                'color': zone_color,
            })

        return {
            'type': 'zone_distribution',
            'workout_type': workout_type,
            'distribution': distribution,
            'total_duration_seconds': total_time,
            'total_duration_minutes': round(total_time / 60.0, 1),
        }

    def generate_tss_if_metrics(
        self,
        avg_power: Optional[float] = None,
        duration_seconds: Optional[int] = None,
        ftp: Optional[float] = None,
        zone_distribution: Optional[List[Dict[str, Any]]] = None,
        workout_type: str = 'power_zone',
    ) -> Optional[Dict[str, Any]]:
        """
        Generate TSS and IF metrics for display.

        Args:
            avg_power: Average power in watts
            duration_seconds: Duration in seconds
            ftp: FTP in watts
            zone_distribution: Optional zone distribution for detailed calc
            workout_type: 'power_zone' or 'pace_target'

        Returns:
            Dict with TSS and IF metrics or None
        """
        metrics = {}

        # Calculate TSS
        if avg_power and duration_seconds and ftp:
            tss = self.metrics.calculate_tss(
                avg_power=avg_power,
                duration_seconds=duration_seconds,
                ftp=ftp,
            )
            if tss is not None:
                metrics['tss'] = round(tss, 1)

        # Calculate IF
        if avg_power and ftp:
            if_value = self.metrics.calculate_intensity_factor(
                avg_power=avg_power,
                ftp=ftp,
            )
            if if_value is not None:
                metrics['if'] = round(if_value, 2)

        # Calculate from zone distribution if available
        if zone_distribution and duration_seconds:
            if workout_type == 'power_zone' and ftp:
                tss = self.metrics.calculate_tss_from_zone_distribution(
                    zone_distribution=zone_distribution,
                    duration_seconds=duration_seconds,
                    class_type='power_zone',
                    ftp=ftp,
                )
                if tss is not None:
                    metrics['tss_from_zones'] = round(tss, 1)

        return metrics if metrics else None

    def generate_summary_stats(
        self,
        performance_data: Optional[List[Dict[str, Any]]] = None,
        zone_distribution: Optional[List[Dict[str, Any]]] = None,
        duration_seconds: Optional[int] = None,
        avg_power: Optional[float] = None,
        ftp: Optional[float] = None,
        calories: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate summary statistics for workout.

        Args:
            performance_data: Performance data points
            zone_distribution: Zone distribution data
            duration_seconds: Total duration
            avg_power: Average power
            ftp: FTP for calculations
            calories: Calories burned

        Returns:
            Dict with summary stats or None
        """
        stats = {}

        # Duration
        if duration_seconds:
            stats['duration_minutes'] = round(duration_seconds / 60.0, 1)
            hours = duration_seconds / 3600.0
            if hours >= 1:
                hours_val = int(hours)
                mins_val = int((hours - hours_val) * 60)
                stats['duration_formatted'] = f'{hours_val}h {mins_val}m'
            else:
                stats['duration_formatted'] = f'{stats["duration_minutes"]}m'

        # Power stats
        if performance_data and performance_data:
            values = [
                float(p.get('value', 0))
                for p in performance_data
                if isinstance(p.get('value'), (int, float))
            ]
            if values:
                stats['max_power'] = int(max(values))
                stats['min_power'] = int(min(values))
                stats['avg_power'] = int(sum(values) / len(values))

        # Metrics
        if avg_power and ftp and duration_seconds:
            metrics = self.generate_tss_if_metrics(
                avg_power=avg_power,
                duration_seconds=duration_seconds,
                ftp=ftp,
                zone_distribution=zone_distribution,
            )
            if metrics:
                stats.update(metrics)

        # Calories
        if calories:
            stats['calories'] = int(calories)

        # Zone times
        if zone_distribution:
            zone_dist = self.generate_zone_distribution(zone_distribution)
            if zone_dist:
                stats['zone_times'] = {
                    item['zone']: item['time_minutes']
                    for item in zone_dist['distribution']
                }

        return stats if stats else None

    # ==================== Helper Methods ====================

    def _extract_data_points(
        self,
        performance_data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract and validate performance data points."""
        points = []
        for data in performance_data:
            try:
                timestamp = int(data.get('timestamp', 0))
                value = float(data.get('value', 0))

                if value < 0:
                    continue

                points.append({
                    'timestamp': timestamp,
                    'value': value,
                })
            except (TypeError, ValueError):
                continue

        return sorted(points, key=lambda p: p['timestamp'])

    def _downsample_points(
        self,
        points: List[Dict[str, Any]],
        max_points: int,
    ) -> List[Dict[str, Any]]:
        """Downsample points to max_points for performance."""
        if len(points) <= max_points:
            return points

        if max_points < 2:
            return points[:1]

        step = (len(points) - 1) / float(max_points - 1)
        downsampled = []

        for i in range(max_points):
            idx = int(round(i * step))
            if idx < 0:
                idx = 0
            if idx >= len(points):
                idx = len(points) - 1
            downsampled.append(points[idx])

        return downsampled

    def _get_zone_config(self, workout_type: str) -> Dict[str, Any]:
        """Get zone configuration for workout type."""
        if workout_type == 'power_zone':
            return {
                'zones': [1, 2, 3, 4, 5, 6, 7],
                'labels': ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7'],
                'names': [
                    'Recovery',
                    'Endurance',
                    'Tempo',
                    'Threshold',
                    'VO2',
                    'Anaerobic',
                    'Neuromuscular',
                ],
            }
        elif workout_type == 'pace_target':
            return {
                'zones': [
                    'recovery', 'easy', 'moderate', 'challenging', 'hard',
                    'very_hard', 'max'
                ],
                'labels': [
                    'Recovery', 'Easy', 'Moderate', 'Challenging', 'Hard',
                    'Very Hard', 'Max'
                ],
                'names': [
                    'Recovery Pace',
                    'Easy Pace',
                    'Moderate Pace',
                    'Challenging Pace',
                    'Hard Pace',
                    'Very Hard Pace',
                    'Max Pace',
                ],
            }
        return {}

    def _get_zone_label(self, zone: Any, workout_type: str) -> str:
        """Get display label for zone."""
        if workout_type == 'power_zone':
            if isinstance(zone, int) and 1 <= zone <= 7:
                names = [
                    'Recovery', 'Endurance', 'Tempo', 'Threshold', 'VO2',
                    'Anaerobic', 'Neuromuscular'
                ]
                return names[zone - 1]
            return f'Zone {zone}'
        elif workout_type == 'pace_target':
            zone_labels = {
                'recovery': 'Recovery',
                'easy': 'Easy',
                'moderate': 'Moderate',
                'challenging': 'Challenging',
                'hard': 'Hard',
                'very_hard': 'Very Hard',
                'max': 'Max',
            }
            if isinstance(zone, str):
                return zone_labels.get(zone.lower(), zone)
            return str(zone)
        return str(zone)

    def _get_zone_color(self, zone: Any, workout_type: str) -> str:
        """Get display color for zone."""
        if workout_type == 'power_zone':
            if isinstance(zone, int) and zone in self.ZONE_COLORS:
                return self.ZONE_COLORS[zone]
            return '#999999'  # Default gray
        elif workout_type == 'pace_target':
            if isinstance(zone, str):
                zone_lower = zone.lower()
                if zone_lower in self.PACE_ZONE_COLORS:
                    return self.PACE_ZONE_COLORS[zone_lower]
            return '#999999'  # Default gray
        return '#999999'

    def is_valid_workout_type(self, workout_type: str) -> bool:
        """Check if workout type is valid."""
        return workout_type in ['power_zone', 'pace_target']

    def is_sufficient_data(
        self,
        performance_data: Optional[List[Dict[str, Any]]] = None,
        zone_distribution: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Check if sufficient data exists for chart generation."""
        has_perf = performance_data and len(performance_data) >= 2
        has_zones = zone_distribution and len(zone_distribution) > 0
        return has_perf or has_zones
