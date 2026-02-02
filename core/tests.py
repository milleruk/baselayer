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


class ChallengeServiceTests(TestCase):
    """Tests for ChallengeService."""
    
    def setUp(self):
        """Set up test data for challenge tests."""
        from django.contrib.auth import get_user_model
        from challenges.models import Challenge
        from datetime import date, timedelta
        
        User = get_user_model()
        
        # Create test users
        self.user1 = User.objects.create_user(email='user1@test.com', password='testpass123')
        self.user2 = User.objects.create_user(email='user2@test.com', password='testpass123')
        
        # Create test challenges
        today = date.today()
        
        # Active challenge (currently running)
        self.active_challenge = Challenge.objects.create(
            name='Active Challenge',
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=7),
            challenge_type='mini',
            is_active=True,
            is_visible=True
        )
        
        # Future challenge (can signup)
        self.future_challenge = Challenge.objects.create(
            name='Future Challenge',
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=20),
            signup_opens_date=today,  # Signup is open now
            challenge_type='mini',
            is_active=True,
            is_visible=True
        )
        
        # Past challenge
        self.past_challenge = Challenge.objects.create(
            name='Past Challenge',
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=10),
            challenge_type='mini',
            is_active=False,
            is_visible=True
        )
    
    def test_get_active_challenge_none(self):
        """Test getting active challenge when user has none."""
        from core.services import ChallengeService
        
        result = ChallengeService.get_active_challenge(self.user1)
        self.assertIsNone(result)
    
    def test_get_active_challenge_exists(self):
        """Test getting active challenge when user has one."""
        from core.services import ChallengeService
        from challenges.models import ChallengeInstance
        
        # Create an active challenge instance
        instance = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=self.active_challenge,
            is_active=True
        )
        
        result = ChallengeService.get_active_challenge(self.user1)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, instance.id)
        self.assertEqual(result.challenge.id, self.active_challenge.id)
    
    def test_has_current_week_plan_false(self):
        """Test has_current_week_plan returns False when no plan exists."""
        from core.services import ChallengeService, DateRangeService
        
        week_start = DateRangeService.sunday_of_current_week(date.today())
        result = ChallengeService.has_current_week_plan(self.user1, week_start)
        self.assertFalse(result)
    
    def test_has_current_week_plan_true(self):
        """Test has_current_week_plan returns True when plan exists."""
        from core.services import ChallengeService, DateRangeService
        from tracker.models import WeeklyPlan
        
        week_start = DateRangeService.sunday_of_current_week(date.today())
        
        # Create a weekly plan
        WeeklyPlan.objects.create(
            user=self.user1,
            week_start=week_start,
            template_name='Test Template'
        )
        
        result = ChallengeService.has_current_week_plan(self.user1, week_start)
        self.assertTrue(result)
    
    def test_get_challenge_involvement_summary_no_involvement(self):
        """Test challenge involvement summary with no involvement."""
        from core.services import ChallengeService
        
        summary = ChallengeService.get_challenge_involvement_summary(self.user1)
        
        self.assertIsNone(summary['active_challenge'])
        self.assertEqual(summary['completed_challenges_count'], 0)
        self.assertFalse(summary['has_involvement'])
    
    def test_get_challenge_involvement_summary_with_active(self):
        """Test challenge involvement summary with active challenge."""
        from core.services import ChallengeService
        from challenges.models import ChallengeInstance
        
        # Create active instance
        instance = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=self.active_challenge,
            is_active=True
        )
        
        summary = ChallengeService.get_challenge_involvement_summary(self.user1)
        
        self.assertIsNotNone(summary['active_challenge'])
        self.assertEqual(summary['active_challenge'].id, instance.id)
        self.assertTrue(summary['has_involvement'])
    
    def test_can_join_challenge_active_running(self):
        """Test can join when challenge is running and signup is not allowed."""
        from core.services import ChallengeService
        
        # Active/running challenges cannot be joined after they start
        can_join, error = ChallengeService.can_join_challenge(self.user1, self.active_challenge)
        self.assertFalse(can_join)
        self.assertIsNotNone(error)
    
    def test_can_join_challenge_future(self):
        """Test can join when challenge is in the future."""
        from core.services import ChallengeService
        
        can_join, error = ChallengeService.can_join_challenge(self.user1, self.future_challenge)
        self.assertTrue(can_join)
        self.assertIsNone(error)
    
    def test_can_join_challenge_past(self):
        """Test can join/retake when challenge is in the past."""
        from core.services import ChallengeService
        
        can_join, error = ChallengeService.can_join_challenge(self.user1, self.past_challenge)
        # Past challenges are retakeable
        self.assertTrue(can_join)
        self.assertIsNone(error)
    
    def test_can_join_challenge_already_active(self):
        """Test cannot join same challenge twice with different error scenarios."""
        from core.services import ChallengeService
        from challenges.models import ChallengeInstance, Challenge
        
        # Create a future challenge we can actually join
        future_challenge = Challenge.objects.create(
            name='Future Test Challenge',
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=20),
            signup_opens_date=date.today(),
            challenge_type='mini',
            is_active=True,
            is_visible=True
        )
        
        # User joins the future challenge
        instance = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=future_challenge,
            is_active=True
        )
        
        # Try to join same challenge again
        can_join, error = ChallengeService.can_join_challenge(self.user1, future_challenge)
        self.assertFalse(can_join)
        self.assertIn('already signed up', error)
    
    def test_get_all_user_challenge_instances(self):
        """Test getting all challenge instances for user."""
        from core.services import ChallengeService
        from challenges.models import ChallengeInstance
        
        # Create multiple instances
        instance1 = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=self.active_challenge,
            is_active=True
        )
        instance2 = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=self.future_challenge,
            is_active=True
        )
        
        # Create inactive instance
        instance3 = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=self.past_challenge,
            is_active=False
        )
        
        # Get active only
        result = ChallengeService.get_all_user_challenge_instances(self.user1, include_inactive=False)
        self.assertEqual(len(result), 2)
        active_ids = [r.id for r in result]
        self.assertIn(instance1.id, active_ids)
        self.assertIn(instance2.id, active_ids)
        self.assertNotIn(instance3.id, active_ids)
        
        # Get all
        result_all = ChallengeService.get_all_user_challenge_instances(self.user1, include_inactive=True)
        self.assertEqual(len(result_all), 3)
    
    def test_deactivate_challenge_success(self):
        """Test successfully deactivating a challenge instance."""
        from core.services import ChallengeService
        from challenges.models import ChallengeInstance
        
        instance = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=self.past_challenge,  # Past challenge can be left
            is_active=True
        )
        
        success, message = ChallengeService.deactivate_challenge(self.user1, instance)
        self.assertTrue(success)
        
        # Verify instance is deactivated
        instance.refresh_from_db()
        self.assertFalse(instance.is_active)
    
    def test_deactivate_challenge_wrong_user(self):
        """Test cannot deactivate another user's challenge."""
        from core.services import ChallengeService
        from challenges.models import ChallengeInstance
        
        instance = ChallengeInstance.objects.create(
            user=self.user1,
            challenge=self.past_challenge,
            is_active=True
        )
        
        # Try to deactivate as different user
        success, message = ChallengeService.deactivate_challenge(self.user2, instance)
        self.assertFalse(success)
        self.assertEqual(message, "Permission denied")
        
        # Verify instance is still active
        instance.refresh_from_db()
        self.assertTrue(instance.is_active)

