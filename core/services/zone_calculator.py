"""Zone calculation services for workouts (cycling and running)."""
from typing import Dict, Any, Optional
from datetime import date
from collections import defaultdict


class ZoneCalculatorService:
    """Service for calculating workout zones (power zones for cycling, intensity zones for running)."""
    
    @staticmethod
    def calculate_cycling_zones(workouts, period: Optional[str] = None, current_ftp: Optional[Any] = None) -> Dict[str, Any]:
        """Calculate time spent in each power zone (1-7) for cycling workouts.
        
        Args:
            workouts: QuerySet of Workout objects
            period: Time period filter - 'month', 'year', or None for all time
            current_ftp: FTP (Functional Threshold Power) entry object for zone calculations
            
        Returns:
            Dictionary with zone breakdown including times and formatted strings
            
        Example:
            >>> zones = ZoneCalculatorService.calculate_cycling_zones(all_workouts, period='month')
            >>> print(zones['zones'][3]['name'])  # 'Tempo'
            >>> print(zones['total_formatted'])   # 'Formatted total time'
        """
        from django.utils import timezone
        from django.db.models import Q
        from workouts.models import WorkoutPerformanceData
        
        today = timezone.now().date()
        
        # Filter workouts by period
        if period == 'month':
            month_start = today.replace(day=1)
            workouts = workouts.filter(completed_date__gte=month_start)
        elif period == 'year':
            year_start = today.replace(month=1, day=1)
            workouts = workouts.filter(completed_date__gte=year_start)
        # period == 'all' or None means all time
        
        # Filter to cycling workouts only - try multiple ways to detect cycling
        cycling_workout_ids = workouts.filter(
            Q(ride_detail__fitness_discipline__in=['cycling', 'ride']) |
            Q(ride_detail__workout_type__slug__in=['cycling', 'ride']) |
            Q(ride_detail__workout_type__name__icontains='cycle') |
            Q(ride_detail__workout_type__name__icontains='bike')
        ).values_list('id', flat=True)
        
        if not cycling_workout_ids:
            # Return empty zones if no workouts
            zone_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        else:
            # Initialize zone times (in seconds)
            zone_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
            
            # Get user's FTP for calculating zones if power_zone is not set
            user_ftp = None
            if current_ftp:
                user_ftp = float(current_ftp.ftp_value)
            
            # Get performance data in bulk - only fetch what we need
            perf_data_qs = WorkoutPerformanceData.objects.filter(
                workout_id__in=cycling_workout_ids
            ).select_related('workout', 'workout__ride_detail').order_by('workout_id', 'timestamp').only(
                'workout_id', 'timestamp', 'power_zone', 'output', 'workout__ride_detail__duration_seconds'
            )
            
            # Group by workout for efficient processing
            perf_by_workout = defaultdict(list)
            for perf in perf_data_qs:
                perf_by_workout[perf.workout_id].append(perf)
            
            # Process workouts in batches
            for workout_id, perf_list in perf_by_workout.items():
                if not perf_list:
                    continue
                
                # Sort by timestamp
                perf_list.sort(key=lambda x: x.timestamp)
                
                # Calculate time interval (assume consistent intervals)
                if len(perf_list) > 1:
                    time_interval = perf_list[1].timestamp - perf_list[0].timestamp
                else:
                    # Single data point - use workout duration if available
                    duration = perf_list[0].workout.ride_detail.duration_seconds if perf_list[0].workout.ride_detail else None
                    time_interval = duration if duration else 5
                
                # Process data points - sample every Nth point if too many to speed up
                sample_rate = 1
                if len(perf_list) > 1000:  # If more than 1000 points, sample every 2nd
                    sample_rate = 2
                elif len(perf_list) > 2000:  # If more than 2000 points, sample every 3rd
                    sample_rate = 3
                
                for i in range(0, len(perf_list), sample_rate):
                    perf = perf_list[i]
                    zone = None
                    
                    # First try to use power_zone field if available
                    if perf.power_zone and perf.power_zone in zone_times:
                        zone = perf.power_zone
                    # Otherwise, calculate zone from output and FTP
                    elif perf.output and user_ftp:
                        percentage = perf.output / user_ftp
                        if percentage < 0.55:
                            zone = 1
                        elif percentage < 0.75:
                            zone = 2
                        elif percentage < 0.90:
                            zone = 3
                        elif percentage < 1.05:
                            zone = 4
                        elif percentage < 1.20:
                            zone = 5
                        elif percentage < 1.50:
                            zone = 6
                        else:
                            zone = 7
                    
                    if zone and zone in zone_times:
                        # Calculate time for this data point
                        if i + sample_rate < len(perf_list):
                            # Time until next sampled point
                            time_spent = (perf_list[i + sample_rate].timestamp - perf.timestamp) * sample_rate
                        else:
                            # Last data point - use average interval
                            time_spent = time_interval * sample_rate
                        
                        # Ensure time is positive and reasonable
                        if time_spent > 0 and time_spent < 300:  # Max 5 minutes per interval
                            zone_times[zone] += time_spent
        
        # Convert to formatted time strings and return
        total_seconds = sum(zone_times.values())
        
        return {
            'zones': {
                1: {'name': 'Recovery', 'time_seconds': zone_times[1], 'time_formatted': ZoneCalculatorService._format_time(zone_times[1])},
                2: {'name': 'Endurance', 'time_seconds': zone_times[2], 'time_formatted': ZoneCalculatorService._format_time(zone_times[2])},
                3: {'name': 'Tempo', 'time_seconds': zone_times[3], 'time_formatted': ZoneCalculatorService._format_time(zone_times[3])},
                4: {'name': 'Threshold', 'time_seconds': zone_times[4], 'time_formatted': ZoneCalculatorService._format_time(zone_times[4])},
                5: {'name': 'VO2 Max', 'time_seconds': zone_times[5], 'time_formatted': ZoneCalculatorService._format_time(zone_times[5])},
                6: {'name': 'Anaerobic', 'time_seconds': zone_times[6], 'time_formatted': ZoneCalculatorService._format_time(zone_times[6])},
                7: {'name': 'Neuromuscular', 'time_seconds': zone_times[7], 'time_formatted': ZoneCalculatorService._format_time(zone_times[7])},
            },
            'total_seconds': total_seconds,
            'total_formatted': ZoneCalculatorService._format_time(total_seconds)
        }
    
    @staticmethod
    def calculate_running_zones(workouts, period: Optional[str] = None) -> Dict[str, Any]:
        """Calculate time spent in each intensity zone for running workouts.
        
        Args:
            workouts: QuerySet of Workout objects
            period: Time period filter - 'month', 'year', or None for all time
            
        Returns:
            Dictionary with zone breakdown including times and formatted strings
            
        Example:
            >>> zones = ZoneCalculatorService.calculate_running_zones(all_workouts, period='month')
            >>> print(zones['zones']['easy']['name'])  # 'Easy'
            >>> print(zones['total_formatted'])        # 'Formatted total time'
        """
        from django.utils import timezone
        from django.db.models import Q
        from workouts.models import WorkoutPerformanceData, Workout
        
        today = timezone.now().date()
        
        # Filter workouts by period
        if period == 'month':
            month_start = today.replace(day=1)
            workouts = workouts.filter(completed_date__gte=month_start)
        elif period == 'year':
            year_start = today.replace(month=1, day=1)
            workouts = workouts.filter(completed_date__gte=year_start)
        # period == 'all' or None means all time
        
        # Filter to running workouts only - try multiple ways to detect running
        running_workout_ids = workouts.filter(
            Q(ride_detail__fitness_discipline__in=['running', 'run', 'walking']) |
            Q(ride_detail__fitness_discipline__isnull=True, ride_detail__workout_type__slug__in=['running', 'run', 'walking']) |
            Q(ride_detail__workout_type__slug__in=['running', 'run', 'walking']) |
            Q(ride_detail__workout_type__name__icontains='run') |
            Q(ride_detail__workout_type__name__icontains='walk') |
            Q(ride_detail__workout_type__name__icontains='tread')
        ).values_list('id', flat=True).distinct()
        
        # Initialize zone times (in seconds)
        zone_times = {
            'recovery': 0,
            'easy': 0,
            'moderate': 0,
            'challenging': 0,
            'hard': 0,
            'very_hard': 0,
            'max': 0
        }
        
        if not running_workout_ids:
            # Return empty zones if no workouts
            pass
        else:
            # Get performance data in bulk - only fetch what we need
            perf_data_qs = WorkoutPerformanceData.objects.filter(
                workout_id__in=running_workout_ids
            ).select_related('workout', 'workout__ride_detail').order_by('workout_id', 'timestamp').only(
                'workout_id', 'timestamp', 'intensity_zone', 'speed', 'heart_rate', 'workout__ride_detail__duration_seconds'
            )
            
            # Group by workout for efficient processing
            perf_by_workout = defaultdict(list)
            workouts_without_data = set(running_workout_ids)
            
            for perf in perf_data_qs:
                perf_by_workout[perf.workout_id].append(perf)
                workouts_without_data.discard(perf.workout_id)
            
            # Handle workouts without performance data
            if workouts_without_data:
                workouts_no_data = Workout.objects.filter(
                    id__in=workouts_without_data
                ).select_related('ride_detail').only('id', 'ride_detail__duration_seconds')
                
                for workout in workouts_no_data:
                    if workout.ride_detail and workout.ride_detail.duration_seconds:
                        duration = workout.ride_detail.duration_seconds
                        # Rough estimate: most running is in easy/moderate zones
                        zone_times['easy'] += duration * 0.3
                        zone_times['moderate'] += duration * 0.4
                        zone_times['challenging'] += duration * 0.2
                        zone_times['hard'] += duration * 0.1
            
            # Process workouts with performance data
            for workout_id, perf_list in perf_by_workout.items():
                if not perf_list:
                    continue
                
                # Sort by timestamp
                perf_list.sort(key=lambda x: x.timestamp)
                
                # Calculate time interval
                if len(perf_list) > 1:
                    time_interval = perf_list[1].timestamp - perf_list[0].timestamp
                else:
                    duration = perf_list[0].workout.ride_detail.duration_seconds if perf_list[0].workout.ride_detail else None
                    time_interval = duration if duration else 5
                
                # Process data points - sample every Nth point if too many to speed up
                sample_rate = 1
                if len(perf_list) > 1000:  # If more than 1000 points, sample every 2nd
                    sample_rate = 2
                elif len(perf_list) > 2000:  # If more than 2000 points, sample every 3rd
                    sample_rate = 3
                
                for i in range(0, len(perf_list), sample_rate):
                    perf = perf_list[i]
                    zone = None
                    
                    # First try to use intensity_zone field if available
                    if perf.intensity_zone and perf.intensity_zone in zone_times:
                        zone = perf.intensity_zone
                    # Fallback: try to calculate zone from speed or heart rate if available
                    elif perf.speed:
                        avg_speed = perf.speed
                        if avg_speed < 4.0:
                            zone = 'recovery'
                        elif avg_speed < 5.5:
                            zone = 'easy'
                        elif avg_speed < 7.0:
                            zone = 'moderate'
                        elif avg_speed < 8.5:
                            zone = 'challenging'
                        elif avg_speed < 10.0:
                            zone = 'hard'
                        elif avg_speed < 12.0:
                            zone = 'very_hard'
                        else:
                            zone = 'max'
                    elif perf.heart_rate:
                        hr = perf.heart_rate
                        if hr < 120:
                            zone = 'recovery'
                        elif hr < 140:
                            zone = 'easy'
                        elif hr < 160:
                            zone = 'moderate'
                        elif hr < 175:
                            zone = 'challenging'
                        elif hr < 185:
                            zone = 'hard'
                        elif hr < 195:
                            zone = 'very_hard'
                        else:
                            zone = 'max'
                    
                    if zone and zone in zone_times:
                        # Calculate time for this data point
                        if i + sample_rate < len(perf_list):
                            time_spent = (perf_list[i + sample_rate].timestamp - perf.timestamp) * sample_rate
                        else:
                            time_spent = time_interval * sample_rate
                        
                        # Ensure time is positive and reasonable
                        if time_spent > 0 and time_spent < 300:  # Max 5 minutes per interval
                            zone_times[zone] += time_spent
        
        total_seconds = sum(zone_times.values())
        
        return {
            'zones': {
                'recovery': {'name': 'Recovery', 'time_seconds': zone_times['recovery'], 'time_formatted': ZoneCalculatorService._format_time(zone_times['recovery'])},
                'easy': {'name': 'Easy', 'time_seconds': zone_times['easy'], 'time_formatted': ZoneCalculatorService._format_time(zone_times['easy'])},
                'moderate': {'name': 'Moderate', 'time_seconds': zone_times['moderate'], 'time_formatted': ZoneCalculatorService._format_time(zone_times['moderate'])},
                'challenging': {'name': 'Challenging', 'time_seconds': zone_times['challenging'], 'time_formatted': ZoneCalculatorService._format_time(zone_times['challenging'])},
                'hard': {'name': 'Hard', 'time_seconds': zone_times['hard'], 'time_formatted': ZoneCalculatorService._format_time(zone_times['hard'])},
                'very_hard': {'name': 'Very Hard', 'time_seconds': zone_times['very_hard'], 'time_formatted': ZoneCalculatorService._format_time(zone_times['very_hard'])},
                'max': {'name': 'Max', 'time_seconds': zone_times['max'], 'time_formatted': ZoneCalculatorService._format_time(zone_times['max'])},
            },
            'total_seconds': total_seconds,
            'total_formatted': ZoneCalculatorService._format_time(total_seconds)
        }
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS or Dd HH:MM:SS.
        
        Args:
            seconds: Number of seconds to format
            
        Returns:
            Formatted time string
        """
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if days > 0:
            return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
