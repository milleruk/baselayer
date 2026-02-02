"""Unit tests for core services."""
from datetime import date, timedelta
from django.test import TestCase

from core.services import DateRangeService, FormattingService


class DateRangeServiceTests(TestCase):
    """Tests for DateRangeService."""
    
    def test_sunday_of_current_week_on_sunday(self):
        """Test that Sunday returns itself."""
        sunday = date(2026, 2, 1)  # Sunday
        result = DateRangeService.sunday_of_current_week(sunday)
        self.assertEqual(result, sunday)
    
    def test_sunday_of_current_week_on_monday(self):
        """Test Monday returns previous Sunday."""
        monday = date(2026, 2, 2)  # Monday
        expected_sunday = date(2026, 2, 1)  # Previous Sunday
        result = DateRangeService.sunday_of_current_week(monday)
        self.assertEqual(result, expected_sunday)
    
    def test_sunday_of_current_week_on_saturday(self):
        """Test Saturday returns previous Sunday."""
        saturday = date(2026, 2, 7)  # Saturday
        expected_sunday = date(2026, 2, 1)  # Previous Sunday
        result = DateRangeService.sunday_of_current_week(saturday)
        self.assertEqual(result, expected_sunday)
    
    def test_sunday_of_current_week_midweek(self):
        """Test Wednesday returns previous Sunday."""
        wednesday = date(2026, 2, 4)  # Wednesday
        expected_sunday = date(2026, 2, 1)  # Previous Sunday
        result = DateRangeService.sunday_of_current_week(wednesday)
        self.assertEqual(result, expected_sunday)
    
    def test_get_period_dates_7d(self):
        """Test 7 day period calculation."""
        today = date(2026, 2, 2)
        result = DateRangeService.get_period_dates('7d', today)
        
        self.assertEqual(result['start_date'], date(2026, 1, 26))
        self.assertEqual(result['end_date'], today)
        self.assertEqual(result['comparison_start'], date(2026, 1, 19))
        self.assertEqual(result['comparison_end'], date(2026, 1, 26))
        self.assertEqual(result['period_label'], 'Last 7 Days')
        self.assertEqual(result['period_description'], 'last 7 days')
        self.assertEqual(result['comparison_label'], 'previous 7 days')
    
    def test_get_period_dates_30d(self):
        """Test 30 day period calculation."""
        today = date(2026, 2, 2)
        result = DateRangeService.get_period_dates('30d', today)
        
        self.assertEqual(result['start_date'], date(2026, 1, 3))
        self.assertEqual(result['end_date'], today)
        self.assertEqual(result['comparison_start'], date(2025, 12, 4))
        self.assertEqual(result['comparison_end'], date(2026, 1, 3))
        self.assertEqual(result['period_label'], 'Last 30 Days')
    
    def test_get_period_dates_90d(self):
        """Test 90 day period calculation."""
        today = date(2026, 2, 2)
        result = DateRangeService.get_period_dates('90d', today)
        
        self.assertEqual(result['start_date'], date(2025, 11, 4))
        self.assertEqual(result['end_date'], today)
        self.assertEqual(result['comparison_start'], date(2025, 8, 6))
        self.assertEqual(result['period_label'], 'Last 90 Days')
    
    def test_get_period_dates_all(self):
        """Test all time period returns None for dates."""
        today = date(2026, 2, 2)
        result = DateRangeService.get_period_dates('all', today)
        
        self.assertIsNone(result['start_date'])
        self.assertEqual(result['end_date'], today)
        self.assertIsNone(result['comparison_start'])
        self.assertIsNone(result['comparison_end'])
        self.assertEqual(result['period_label'], 'All Time')
    
    def test_get_period_dates_default_today(self):
        """Test that default today parameter works."""
        result = DateRangeService.get_period_dates('7d')
        self.assertIsNotNone(result['start_date'])
        self.assertEqual(result['end_date'], date.today())
    
    def test_get_period_dates_invalid_period(self):
        """Test invalid period defaults to 7d."""
        today = date(2026, 2, 2)
        result = DateRangeService.get_period_dates('invalid', today)
        
        # Should default to 7d
        self.assertEqual(result['start_date'], date(2026, 1, 26))
        self.assertEqual(result['period_label'], 'Last 7 Days')
    
    def test_get_week_boundaries(self):
        """Test get_week_boundaries returns Sunday."""
        wednesday = date(2026, 2, 4)
        result = DateRangeService.get_week_boundaries(wednesday)
        self.assertEqual(result, date(2026, 2, 1))
    
    def test_get_week_boundaries_default_today(self):
        """Test get_week_boundaries with default today."""
        result = DateRangeService.get_week_boundaries()
        # Should return a date (Sunday of current week)
        self.assertIsInstance(result, date)
        # Verify it's a Sunday (weekday() == 6)
        self.assertEqual(result.weekday(), 6)
    
    def test_get_month_boundaries(self):
        """Test month boundaries calculation."""
        reference = date(2026, 2, 15)
        result = DateRangeService.get_month_boundaries(reference)
        
        self.assertEqual(result['month_start'], date(2026, 2, 1))
        self.assertEqual(result['previous_month_start'], date(2026, 1, 1))
        self.assertEqual(result['previous_month_end'], date(2026, 1, 31))
    
    def test_get_month_boundaries_january(self):
        """Test month boundaries for January (year rollover)."""
        reference = date(2026, 1, 15)
        result = DateRangeService.get_month_boundaries(reference)
        
        self.assertEqual(result['month_start'], date(2026, 1, 1))
        self.assertEqual(result['previous_month_start'], date(2025, 12, 1))
        self.assertEqual(result['previous_month_end'], date(2025, 12, 31))
    
    def test_get_month_boundaries_february(self):
        """Test month boundaries for February."""
        reference = date(2026, 3, 15)
        result = DateRangeService.get_month_boundaries(reference)
        
        self.assertEqual(result['month_start'], date(2026, 3, 1))
        self.assertEqual(result['previous_month_start'], date(2026, 2, 1))
        self.assertEqual(result['previous_month_end'], date(2026, 2, 28))


class FormattingServiceTests(TestCase):
    """Tests for FormattingService."""
    
    def test_format_time_seconds_under_hour(self):
        """Test formatting time under an hour."""
        result = FormattingService.format_time_seconds(3665)
        self.assertEqual(result, '01:01:05')
    
    def test_format_time_seconds_with_days(self):
        """Test formatting time with days."""
        result = FormattingService.format_time_seconds(90000)
        self.assertEqual(result, '1d 01:00:00')
    
    def test_format_time_seconds_zero(self):
        """Test formatting zero seconds."""
        result = FormattingService.format_time_seconds(0)
        self.assertEqual(result, '00:00:00')
    
    def test_format_time_seconds_float(self):
        """Test formatting with float input."""
        result = FormattingService.format_time_seconds(3665.7)
        self.assertEqual(result, '01:01:05')
    
    def test_decimal_to_mmss(self):
        """Test decimal minutes to MM:SS conversion."""
        result = FormattingService.decimal_to_mmss(8.5)
        self.assertEqual(result, '8:30')
    
    def test_decimal_to_mmss_quarter_minute(self):
        """Test decimal minutes with .25 (15 seconds)."""
        result = FormattingService.decimal_to_mmss(12.25)
        self.assertEqual(result, '12:15')
    
    def test_decimal_to_mmss_whole_minute(self):
        """Test whole minute conversion."""
        result = FormattingService.decimal_to_mmss(10.0)
        self.assertEqual(result, '10:00')
    
    def test_pace_str_from_mph_valid(self):
        """Test MPH to pace conversion."""
        result = FormattingService.pace_str_from_mph(6.0)
        self.assertEqual(result, '10:00/mi')
    
    def test_pace_str_from_mph_decimal(self):
        """Test MPH to pace with decimal speed."""
        result = FormattingService.pace_str_from_mph(7.5)
        self.assertEqual(result, '8:00/mi')
    
    def test_pace_str_from_mph_zero(self):
        """Test MPH with zero returns None."""
        result = FormattingService.pace_str_from_mph(0)
        self.assertIsNone(result)
    
    def test_pace_str_from_mph_negative(self):
        """Test MPH with negative returns None."""
        result = FormattingService.pace_str_from_mph(-5)
        self.assertIsNone(result)
    
    def test_pace_str_from_mph_invalid(self):
        """Test MPH with invalid input returns None."""
        result = FormattingService.pace_str_from_mph('invalid')
        self.assertIsNone(result)
    
    def test_format_distance_miles(self):
        """Test distance formatting in miles."""
        result = FormattingService.format_distance(3.14159)
        self.assertEqual(result, '3.14 mi')
    
    def test_format_distance_kilometers(self):
        """Test distance formatting in kilometers."""
        result = FormattingService.format_distance(5.0, 'km')
        self.assertEqual(result, '5.00 km')
    
    def test_format_percentage_default(self):
        """Test percentage formatting with default decimals."""
        result = FormattingService.format_percentage(0.755)
        self.assertEqual(result, '75.5%')
    
    def test_format_percentage_two_decimals(self):
        """Test percentage formatting with two decimals."""
        result = FormattingService.format_percentage(0.9999, 2)
        self.assertEqual(result, '99.99%')
    
    def test_format_percentage_zero(self):
        """Test percentage formatting with zero."""
        result = FormattingService.format_percentage(0.0)
        self.assertEqual(result, '0.0%')
    
    def test_format_number_integer(self):
        """Test number formatting without decimals."""
        result = FormattingService.format_number(1234567)
        self.assertEqual(result, '1,234,567')
    
    def test_format_number_with_decimals(self):
        """Test number formatting with decimals."""
        result = FormattingService.format_number(1234.5678, 2)
        self.assertEqual(result, '1,234.57')
    
    def test_format_number_zero(self):
        """Test number formatting with zero."""
        result = FormattingService.format_number(0)
        self.assertEqual(result, '0')
