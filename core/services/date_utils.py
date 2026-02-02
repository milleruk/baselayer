"""Date range and week calculation utilities."""
from datetime import date, timedelta
from typing import Dict, Optional


class DateRangeService:
    """Service for date range and week calculations."""
    
    @staticmethod
    def sunday_of_current_week(d: date) -> date:
        """Get the Sunday of the current week (week starts on Sunday).
        
        Args:
            d: Reference date
            
        Returns:
            Date object representing the Sunday of the week containing d
            
        Example:
            >>> DateRangeService.sunday_of_current_week(date(2026, 2, 4))  # Wednesday
            date(2026, 2, 2)  # Previous Sunday
        """
        # weekday() returns 0=Monday, 6=Sunday
        # We want Sunday to be day 0, so we adjust
        days_since_sunday = (d.weekday() + 1) % 7
        return d - timedelta(days=days_since_sunday)
    
    @staticmethod
    def get_period_dates(period: str = '7d', today: Optional[date] = None) -> Dict:
        """Get start and end dates for a period with comparison dates.
        
        Args:
            period: One of '7d', '30d', '90d', 'all'
            today: Reference date (defaults to today)
        
        Returns:
            Dictionary with:
                - start_date: Start of the period
                - end_date: End of the period (typically today)
                - comparison_start: Start of comparison period
                - comparison_end: End of comparison period
                - period_label: Human-readable label
                - period_description: Description text
                - comparison_label: Comparison period label
                
        Example:
            >>> dates = DateRangeService.get_period_dates('7d', date(2026, 2, 2))
            >>> dates['start_date']
            date(2026, 1, 26)  # 7 days ago
            >>> dates['comparison_start']
            date(2026, 1, 19)  # 14 days ago
        """
        if today is None:
            today = date.today()
        
        period_configs = {
            '7d': {
                'start_offset': 7,
                'comparison_offset': 14,
                'label': 'Last 7 Days',
                'description': 'last 7 days'
            },
            '30d': {
                'start_offset': 30,
                'comparison_offset': 60,
                'label': 'Last 30 Days',
                'description': 'last 30 days'
            },
            '90d': {
                'start_offset': 90,
                'comparison_offset': 180,
                'label': 'Last 90 Days',
                'description': 'last 90 days'
            },
            'all': {
                'start_offset': None,
                'comparison_offset': None,
                'label': 'All Time',
                'description': 'all time'
            }
        }
        
        config = period_configs.get(period, period_configs['7d'])
        
        if config['start_offset'] is None:
            return {
                'start_date': None,
                'end_date': today,
                'comparison_start': None,
                'comparison_end': None,
                'period_label': config['label'],
                'period_description': config['description'],
                'comparison_label': 'N/A'
            }
        
        start_date = today - timedelta(days=config['start_offset'])
        comparison_start = today - timedelta(days=config['comparison_offset'])
        comparison_end = start_date
        
        return {
            'start_date': start_date,
            'end_date': today,
            'comparison_start': comparison_start,
            'comparison_end': comparison_end,
            'period_label': config['label'],
            'period_description': config['description'],
            'comparison_label': f"previous {config['start_offset']} days"
        }
    
    @staticmethod
    def get_week_boundaries(reference_date: Optional[date] = None) -> date:
        """Get current week start (Sunday).
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            Date object representing the Sunday of the week
            
        Example:
            >>> DateRangeService.get_week_boundaries(date(2026, 2, 4))
            date(2026, 2, 2)  # Sunday
        """
        if reference_date is None:
            reference_date = date.today()
        return DateRangeService.sunday_of_current_week(reference_date)
    
    @staticmethod
    def get_month_boundaries(reference_date: Optional[date] = None) -> Dict:
        """Get current and previous month boundaries.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            Dictionary with:
                - month_start: First day of current month
                - previous_month_start: First day of previous month
                - previous_month_end: Last day of previous month
                
        Example:
            >>> bounds = DateRangeService.get_month_boundaries(date(2026, 2, 15))
            >>> bounds['month_start']
            date(2026, 2, 1)
            >>> bounds['previous_month_start']
            date(2026, 1, 1)
        """
        if reference_date is None:
            reference_date = date.today()
        
        month_start = reference_date.replace(day=1)
        
        # Calculate previous month
        if month_start.month == 1:
            previous_month_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            previous_month_start = month_start.replace(month=month_start.month - 1)
        
        # Calculate last day of previous month
        if previous_month_start.month == 12:
            previous_month_end = previous_month_start.replace(
                year=previous_month_start.year + 1, 
                month=1, 
                day=1
            ) - timedelta(days=1)
        else:
            previous_month_end = previous_month_start.replace(
                month=previous_month_start.month + 1, 
                day=1
            ) - timedelta(days=1)
        
        return {
            'month_start': month_start,
            'previous_month_start': previous_month_start,
            'previous_month_end': previous_month_end,
        }
