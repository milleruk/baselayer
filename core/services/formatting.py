"""Formatting utilities for common data transformations."""
from typing import Union, Optional


class FormattingService:
    """Service for common formatting operations."""
    
    @staticmethod
    def format_time_seconds(seconds: Union[int, float]) -> str:
        """Format seconds as HH:MM:SS or Dd HH:MM:SS.
        
        Args:
            seconds: Number of seconds to format
            
        Returns:
            Formatted time string
            
        Example:
            >>> FormattingService.format_time_seconds(3665)
            '01:01:05'
            >>> FormattingService.format_time_seconds(90000)
            '1d 01:00:00'
        """
        seconds = int(seconds)
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if days > 0:
            return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def decimal_to_mmss(decimal_minutes: float) -> str:
        """Convert decimal minutes to MM:SS format.
        
        Args:
            decimal_minutes: Minutes in decimal format (e.g., 8.5 = 8 minutes 30 seconds)
            
        Returns:
            Formatted time string as MM:SS
            
        Example:
            >>> FormattingService.decimal_to_mmss(8.5)
            '8:30'
            >>> FormattingService.decimal_to_mmss(12.25)
            '12:15'
        """
        minutes = int(decimal_minutes)
        seconds = int((decimal_minutes - minutes) * 60)
        return f"{minutes}:{seconds:02d}"
    
    @staticmethod
    def pace_str_from_mph(mph: float) -> Optional[str]:
        """Convert MPH to pace string (MM:SS/mi).
        
        Args:
            mph: Speed in miles per hour
            
        Returns:
            Pace string in MM:SS/mi format, or None if invalid
            
        Example:
            >>> FormattingService.pace_str_from_mph(6.0)
            '10:00/mi'
            >>> FormattingService.pace_str_from_mph(7.5)
            '8:00/mi'
        """
        try:
            mph = float(mph)
            if mph <= 0:
                return None
            
            pace_min_per_mile = 60.0 / mph
            minutes = int(pace_min_per_mile)
            seconds = int(round((pace_min_per_mile - minutes) * 60.0))
            
            # Handle rounding edge case
            if seconds == 60:
                minutes += 1
                seconds = 0
                
            return f"{minutes}:{seconds:02d}/mi"
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    
    @staticmethod
    def format_distance(distance: float, unit: str = 'mi') -> str:
        """Format distance with unit.
        
        Args:
            distance: Distance value
            unit: Unit of measurement ('mi' or 'km')
            
        Returns:
            Formatted distance string
            
        Example:
            >>> FormattingService.format_distance(3.14159)
            '3.14 mi'
            >>> FormattingService.format_distance(5.0, 'km')
            '5.00 km'
        """
        return f"{distance:.2f} {unit}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """Format value as percentage.
        
        Args:
            value: Decimal value (0.0 to 1.0)
            decimals: Number of decimal places
            
        Returns:
            Formatted percentage string
            
        Example:
            >>> FormattingService.format_percentage(0.755)
            '75.5%'
            >>> FormattingService.format_percentage(0.9999, 2)
            '99.99%'
        """
        return f"{value * 100:.{decimals}f}%"
    
    @staticmethod
    def format_number(value: Union[int, float], decimals: int = 0) -> str:
        """Format number with thousands separator.
        
        Args:
            value: Number to format
            decimals: Number of decimal places
            
        Returns:
            Formatted number string
            
        Example:
            >>> FormattingService.format_number(1234567)
            '1,234,567'
            >>> FormattingService.format_number(1234.5678, 2)
            '1,234.57'
        """
        if decimals == 0:
            return f"{int(value):,}"
        else:
            return f"{value:,.{decimals}f}"
