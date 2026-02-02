"""
Metrics Service for Pelvic Planner Workouts

Encapsulates all workout metrics calculations:
- TSS (Training Stress Score)
- IF (Intensity Factor)
- Power zones and zone ranges
- Pace zones and zone targets
"""

import logging
from typing import Optional, Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculates workout metrics including TSS, IF, and zone-based metrics.
    
    Supports both power zone and pace target workouts.
    """

    # Zone-based intensity factors for pace targets
    PACE_ZONE_INTENSITY_FACTORS = {
        'recovery': 0.5,
        'easy': 0.7,
        'moderate': 1.0,
        'challenging': 1.15,
        'hard': 1.3,
        'very_hard': 1.5,
        'max': 1.8,
    }

    # Base paces by level for pace zone targets
    BASE_PACES_BY_LEVEL = {
        1: 12.0,   # 12:00/mile
        2: 11.0,   # 11:00/mile
        3: 10.0,   # 10:00/mile
        4: 9.0,    # 9:00/mile
        5: 8.5,    # 8:30/mile
        6: 8.0,    # 8:00/mile
        7: 7.5,    # 7:30/mile
        8: 7.0,    # 7:00/mile
        9: 6.5,    # 6:30/mile
        10: 6.0,   # 6:00/mile
    }

    # Power zone percentages (% of FTP) for normalized power calculation
    ZONE_POWER_PERCENTAGES = {
        1: 0.45,   # Peloton Z1 target (active recovery ~45% FTP)
        2: 0.65,   # Z2 midpoint of 55-75%
        3: 0.825,  # Z3 midpoint of 75-90%
        4: 0.975,  # Z4 midpoint of 90-105%
        5: 1.125,  # Z5 midpoint of 105-120%
        6: 1.35,   # Z6 midpoint of 120-150%
        7: 1.60,   # Z7 sprint target (~160% FTP)
    }

    def get_power_zone_target_watts(self, ftp: Optional[float]) -> Optional[Dict[int, int]]:
        """Return Peloton-style target wattage for each power zone."""
        try:
            ftp_val = float(ftp)
        except (TypeError, ValueError):
            return None

        if ftp_val <= 0:
            return None

        targets = {}
        for zone, percentage in self.ZONE_POWER_PERCENTAGES.items():
            targets[zone] = int(round(ftp_val * percentage))
        return targets

    def calculate_tss(
        self,
        avg_power: Optional[float] = None,
        duration_seconds: Optional[int] = None,
        ftp: Optional[float] = None,
        stored_tss: Optional[float] = None,
    ) -> Optional[float]:
        """
        Calculate TSS (Training Stress Score) for cycling workouts.

        Formula: TSS = (duration_hours) × IF² × 100
        Where IF = avg_power / FTP

        Args:
            avg_power: Average power in watts
            duration_seconds: Duration of workout in seconds
            ftp: Functional Threshold Power in watts
            stored_tss: Pre-calculated TSS from source (returned if available)

        Returns:
            TSS value or None if insufficient data
        """
        # Return stored TSS if available
        if stored_tss is not None:
            try:
                return float(stored_tss)
            except (TypeError, ValueError):
                pass

        # Validate required data
        if (
            avg_power is None
            or duration_seconds is None
            or ftp is None
        ):
            return None

        try:
            avg_power = float(avg_power)
            duration_seconds = int(duration_seconds)
            ftp = float(ftp)
        except (TypeError, ValueError):
            return None

        if ftp <= 0 or duration_seconds <= 0:
            return None

        # Calculate IF with bounds checking
        intensity_factor = avg_power / ftp
        intensity_factor = max(0.0, min(intensity_factor, 2.0))

        # Calculate TSS
        hours = duration_seconds / 3600.0
        tss = hours * (intensity_factor ** 2) * 100.0

        return tss

    def calculate_intensity_factor(
        self,
        avg_power: Optional[float] = None,
        ftp: Optional[float] = None,
        tss: Optional[float] = None,
        duration_seconds: Optional[int] = None,
    ) -> Optional[float]:
        """
        Calculate IF (Intensity Factor).

        Can be calculated from:
        1. IF = avg_power / FTP (direct)
        2. IF = sqrt(TSS / (duration_hours × 100)) (from TSS)

        Args:
            avg_power: Average power in watts
            ftp: Functional Threshold Power
            tss: Training Stress Score (for reverse calculation)
            duration_seconds: Duration (needed if calculating from TSS)

        Returns:
            IF value or None if insufficient data
        """
        # Method 1: Direct calculation from avg_power and FTP
        if avg_power is not None and ftp is not None:
            try:
                avg_power = float(avg_power)
                ftp = float(ftp)
                if ftp > 0:
                    if_value = avg_power / ftp
                    return max(0.0, min(if_value, 2.0))
            except (TypeError, ValueError):
                pass

        # Method 2: Reverse calculation from TSS and duration
        if tss is not None and duration_seconds is not None:
            try:
                tss = float(tss)
                duration_seconds = int(duration_seconds)
                if duration_seconds > 0:
                    hours = duration_seconds / 3600.0
                    if hours > 0:
                        return (tss / (hours * 100.0)) ** 0.5
            except (TypeError, ValueError):
                pass

        return None

    def calculate_tss_from_zone_distribution(
        self,
        zone_distribution: List[Dict[str, Any]],
        duration_seconds: int,
        class_type: str,
        ftp: Optional[float] = None,
        pace_level: Optional[int] = None,
    ) -> Optional[float]:
        """
        Calculate TSS from zone distribution and class type.

        For power zone classes: uses weighted average of zone powers
        For pace target classes: uses weighted average of pace zone intensities

        Args:
            zone_distribution: List of zone info dicts with 'zone' and 'time_sec'
            duration_seconds: Total workout duration in seconds
            class_type: 'power_zone' or 'pace_target'
            ftp: FTP value (required for power zone)
            pace_level: Pace level 1-10 (required for pace target)

        Returns:
            TSS value or None if insufficient data
        """
        if not zone_distribution or duration_seconds <= 0:
            return None

        if class_type == 'power_zone':
            return self._calculate_power_zone_tss(
                zone_distribution, duration_seconds, ftp
            )
        elif class_type == 'pace_target':
            return self._calculate_pace_target_tss(
                zone_distribution, duration_seconds, pace_level
            )

        return None

    def _calculate_power_zone_tss(
        self,
        zone_distribution: List[Dict[str, Any]],
        duration_seconds: int,
        ftp: Optional[float] = None,
    ) -> Optional[float]:
        """Calculate TSS for power zone classes using normalized power."""
        if not ftp or ftp <= 0:
            return None

        try:
            ftp = float(ftp)
        except (TypeError, ValueError):
            return None

        # Calculate weighted average power from zones
        total_weighted_power = 0.0
        total_time = 0.0

        for zone_info in zone_distribution:
            zone = zone_info.get('zone')
            time_sec = zone_info.get('time_sec', 0)

            if not zone or time_sec <= 0:
                continue

            try:
                zone = int(zone)
                time_sec = float(time_sec)
            except (TypeError, ValueError):
                continue

            if zone in self.ZONE_POWER_PERCENTAGES:
                zone_power = ftp * self.ZONE_POWER_PERCENTAGES[zone]
                total_weighted_power += zone_power * time_sec
                total_time += time_sec

        if total_time <= 0:
            return None

        # Calculate normalized power and IF
        normalized_power = total_weighted_power / total_time
        if_value = normalized_power / ftp

        # Calculate TSS
        hours = duration_seconds / 3600.0
        tss = hours * (if_value ** 2) * 100.0

        return tss

    def _calculate_pace_target_tss(
        self,
        zone_distribution: List[Dict[str, Any]],
        duration_seconds: int,
        pace_level: Optional[int] = None,
    ) -> Optional[float]:
        """Calculate TSS for pace target classes using zone intensity factors."""
        if pace_level is None:
            return None

        # Calculate weighted average intensity factor
        total_weighted_intensity = 0.0
        total_time = 0.0

        for zone_info in zone_distribution:
            zone_key = zone_info.get('zone')
            time_sec = zone_info.get('time_sec', 0)

            if not zone_key or time_sec <= 0:
                continue

            try:
                time_sec = float(time_sec)
            except (TypeError, ValueError):
                continue

            # Map zone key to intensity factor
            zone_if = self._get_pace_zone_intensity_factor(zone_key)

            if zone_if is not None:
                total_weighted_intensity += zone_if * time_sec
                total_time += time_sec

        if total_time <= 0:
            return None

        # Calculate IF as weighted average
        if_value = total_weighted_intensity / total_time

        # Calculate TSS
        hours = duration_seconds / 3600.0
        tss = hours * (if_value ** 2) * 100.0

        return tss

    def _get_pace_zone_intensity_factor(self, zone_key: Any) -> Optional[float]:
        """
        Get intensity factor for a pace zone key.

        Handles string zone names, numeric indices, and zone_display values.
        """
        if isinstance(zone_key, str):
            zone_lower = zone_key.lower()
            if zone_lower in self.PACE_ZONE_INTENSITY_FACTORS:
                return self.PACE_ZONE_INTENSITY_FACTORS[zone_lower]

        elif isinstance(zone_key, int):
            # Map numeric index to zone name
            zone_map = {
                0: 'recovery',
                1: 'easy',
                2: 'moderate',
                3: 'challenging',
                4: 'hard',
                5: 'very_hard',
                6: 'max',
            }
            zone_name = zone_map.get(zone_key, 'moderate')
            return self.PACE_ZONE_INTENSITY_FACTORS.get(zone_name, 1.0)

        return None

    def get_power_zone_ranges(self, ftp: Optional[float]) -> Optional[Dict[int, Tuple[int, Optional[int]]]]:
        """
        Get power zone ranges (low, high) in watts for a given FTP.

        Returns dict mapping zone number (1-7) to (low_watts, high_watts) tuple.
        High watts is None for zone 7 (unbounded).

        Args:
            ftp: Functional Threshold Power in watts

        Returns:
            Dict of zone ranges or None if FTP is invalid
        """
        try:
            ftp_val = float(ftp)
        except (TypeError, ValueError):
            return None

        if ftp_val <= 0:
            return None

        # Peloton power zone ranges
        return {
            1: (0, int(ftp_val * 0.55)),
            2: (int(ftp_val * 0.55), int(ftp_val * 0.75)),
            3: (int(ftp_val * 0.75), int(ftp_val * 0.90)),
            4: (int(ftp_val * 0.90), int(ftp_val * 1.05)),
            5: (int(ftp_val * 1.05), int(ftp_val * 1.20)),
            6: (int(ftp_val * 1.20), int(ftp_val * 1.50)),
            7: (int(ftp_val * 1.50), None),
        }

    def get_power_zone_for_output(
        self,
        output_watts: float,
        zone_ranges: Optional[Dict[int, Tuple[int, Optional[int]]]] = None,
        ftp: Optional[float] = None,
    ) -> Optional[int]:
        """
        Get power zone (1-7) for a given output value.

        Args:
            output_watts: Power output in watts
            zone_ranges: Pre-calculated zone ranges (or provide FTP)
            ftp: FTP to calculate zone ranges (if zone_ranges not provided)

        Returns:
            Zone number 1-7 or None if invalid
        """
        if zone_ranges is None:
            if ftp is None:
                return None
            zone_ranges = self.get_power_zone_ranges(ftp)

        if zone_ranges is None:
            return None

        try:
            w = float(output_watts)
        except (TypeError, ValueError):
            return None

        for z in range(1, 8):
            lo, hi = zone_ranges.get(z, (None, None))
            if lo is None:
                continue
            if hi is None:
                if w >= lo:
                    return z
            else:
                if w >= lo and w < hi:
                    return z

        return None

    def get_pace_zone_targets(
        self,
        pace_level: Optional[int],
    ) -> Optional[Dict[str, float]]:
        """
        Get pace zone targets (min/mile) for a given pace level.

        Args:
            pace_level: Pace level 1-10

        Returns:
            Dict mapping zone names to pace targets (min/mile), or None if invalid
        """
        try:
            lvl = int(pace_level)
        except (TypeError, ValueError):
            return None

        base_pace = float(self.BASE_PACES_BY_LEVEL.get(lvl, 8.0))

        return {
            'recovery': base_pace + 2.0,
            'easy': base_pace + 1.0,
            'moderate': base_pace,
            'challenging': base_pace - 0.5,
            'hard': base_pace - 1.0,
            'very_hard': base_pace - 1.5,
            'max': base_pace - 2.0,
        }

    def get_target_watts_for_zone(
        self,
        zone_num: int,
        zone_ranges: Optional[Dict[int, Tuple[int, Optional[int]]]] = None,
        ftp: Optional[float] = None,
    ) -> Optional[float]:
        """
        Get target watts for a power zone using Peloton zone target percentages.

        Args:
            zone_num: Power zone 1-7
            zone_ranges: Pre-calculated zone ranges (or provide FTP)
            ftp: FTP to calculate zone ranges (if zone_ranges not provided)

        Returns:
            Target watts or None if invalid
        """
        if not isinstance(zone_num, int) or zone_num not in self.ZONE_POWER_PERCENTAGES:
            return None

        # Get FTP value
        ftp_val = ftp
        if ftp_val is None and zone_ranges:
            # Extract FTP from zone 1 upper bound (55% FTP)
            zone_1_range = zone_ranges.get(1)
            if zone_1_range and zone_1_range[1] is not None:
                ftp_val = zone_1_range[1] / 0.55

        if ftp_val is None:
            return None

        try:
            ftp_val = float(ftp_val)
        except (TypeError, ValueError):
            return None

        if ftp_val <= 0:
            return None

        # Use proper Peloton zone target percentages (not range midpoints)
        target_percentage = self.ZONE_POWER_PERCENTAGES[zone_num]
        return float(ftp_val * target_percentage)

    def get_available_power_zones(self, ftp: Optional[float] = None) -> Optional[List[int]]:
        """
        Get list of available power zones (1-7).

        Args:
            ftp: FTP (validates that FTP is available for zone calculations)

        Returns:
            List [1, 2, 3, 4, 5, 6, 7] if FTP is valid, None otherwise
        """
        if ftp is not None:
            try:
                ftp = float(ftp)
                if ftp <= 0:
                    return None
            except (TypeError, ValueError):
                return None

        return list(range(1, 8))

    def get_available_pace_zones(self) -> List[str]:
        """Get list of available pace zone names."""
        return sorted(self.PACE_ZONE_INTENSITY_FACTORS.keys())

    def is_valid_power_zone(self, zone: int) -> bool:
        """Check if zone number is valid power zone (1-7)."""
        return isinstance(zone, int) and 1 <= zone <= 7

    def is_valid_pace_level(self, level: int) -> bool:
        """Check if pace level is valid (1-10)."""
        return isinstance(level, int) and 1 <= level <= 10
