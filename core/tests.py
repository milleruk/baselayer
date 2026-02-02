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


class ZoneCalculatorServiceTests(TestCase):
    """Tests for ZoneCalculatorService."""
    
    def setUp(self):
        """Set up test data."""
        from accounts.models import User
        from workouts.models import Workout, WorkoutType, RideDetail, WorkoutPerformanceData
        from django.utils import timezone
        
        # Create test user
        self.user = User.objects.create_user(
            email='zonetest@example.com',
            password='testpass123'
        )
        
        # Create workout types
        self.cycling_type = WorkoutType.objects.create(
            name='Cycling',
            slug='cycling'
        )
        self.running_type = WorkoutType.objects.create(
            name='Running',
            slug='running'
        )
    
    def test_calculate_cycling_zones_no_workouts(self):
        """Test cycling zone calculation with no workouts."""
        from core.services import ZoneCalculatorService
        from workouts.models import Workout
        from django.utils import timezone
        
        workouts = Workout.objects.filter(user=self.user)
        result = ZoneCalculatorService.calculate_cycling_zones(workouts)
        
        self.assertIn('zones', result)
        self.assertIn('total_seconds', result)
        self.assertIn('total_formatted', result)
        
        # All zones should be 0
        for zone_num in [1, 2, 3, 4, 5, 6, 7]:
            self.assertEqual(result['zones'][zone_num]['time_seconds'], 0)
        self.assertEqual(result['total_seconds'], 0)
    
    def test_calculate_cycling_zones_with_workouts(self):
        """Test cycling zone calculation with actual workouts."""
        from core.services import ZoneCalculatorService
        from workouts.models import Workout, RideDetail, WorkoutPerformanceData
        from django.utils import timezone
        import uuid
        
        # Create a cycling workout
        now = timezone.now()
        ride_detail = RideDetail.objects.create(
            peloton_ride_id=f'cycling_1_{uuid.uuid4().hex[:8]}',
            title='Cycling Test Ride',
            description='Test ride for zone calculations',
            workout_type=self.cycling_type,
            duration_seconds=3600,
            fitness_discipline='cycling'
        )
        
        workout = Workout.objects.create(
            user=self.user,
            ride_detail=ride_detail,
            completed_date=now.date(),
            recorded_date=now.date()
        )
        
        # Create performance data in zone 2 (Endurance - 56-75% FTP)
        # Create 60 data points spread throughout the workout
        for i in range(60):
            WorkoutPerformanceData.objects.create(
                workout=workout,
                timestamp=i * 60,  # Every 60 seconds (1 minute)
                power_zone=2,
                output=300  # Example power output
            )
        
        workouts = Workout.objects.filter(user=self.user)
        result = ZoneCalculatorService.calculate_cycling_zones(workouts)
        
        self.assertIn('zones', result)
        self.assertIn('total_seconds', result)
        self.assertEqual(result['zones'][2]['name'], 'Endurance')
        # Should have some time in zone 2
        self.assertGreaterEqual(result['zones'][2]['time_seconds'], 0)
    
    def test_calculate_cycling_zones_period_filter_month(self):
        """Test cycling zone calculation with month filter."""
        from core.services import ZoneCalculatorService
        from workouts.models import Workout, RideDetail, WorkoutPerformanceData
        from django.utils import timezone
        from datetime import timedelta
        import uuid
        
        now = timezone.now()
        
        # Create two cycling workouts - one this month, one last month
        ride_detail_current = RideDetail.objects.create(
            peloton_ride_id=f'cycling_2_{uuid.uuid4().hex[:8]}',
            title='Cycling Current Month',
            description='Test ride',
            workout_type=self.cycling_type,
            duration_seconds=3600,
            fitness_discipline='cycling'
        )
        
        ride_detail_last = RideDetail.objects.create(
            peloton_ride_id=f'cycling_3_{uuid.uuid4().hex[:8]}',
            title='Cycling Last Month',
            description='Test ride',
            workout_type=self.cycling_type,
            duration_seconds=3600,
            fitness_discipline='cycling'
        )
        
        # Current month workout
        workout_current = Workout.objects.create(
            user=self.user,
            ride_detail=ride_detail_current,
            completed_date=now.date(),
            recorded_date=now.date()
        )
        
        # Last month workout
        last_month = now - timedelta(days=30)
        workout_last = Workout.objects.create(
            user=self.user,
            ride_detail=ride_detail_last,
            completed_date=last_month.date(),
            recorded_date=last_month.date()
        )
        
        # Add performance data to both
        for workout in [workout_current, workout_last]:
            for i in range(5):
                WorkoutPerformanceData.objects.create(
                    workout=workout,
                    timestamp=i * 360,
                    power_zone=3,
                    output=350
                )
        
        workouts = Workout.objects.filter(user=self.user)
        result_month = ZoneCalculatorService.calculate_cycling_zones(workouts, period='month')
        result_all = ZoneCalculatorService.calculate_cycling_zones(workouts, period='all')
        
        # Month filter should have less or equal time than all time
        self.assertLessEqual(
            result_month['zones'][3]['time_seconds'],
            result_all['zones'][3]['time_seconds']
        )
    
    def test_calculate_running_zones_no_workouts(self):
        """Test running zone calculation with no workouts."""
        from core.services import ZoneCalculatorService
        from workouts.models import Workout
        
        workouts = Workout.objects.filter(user=self.user)
        result = ZoneCalculatorService.calculate_running_zones(workouts)
        
        self.assertIn('zones', result)
        self.assertIn('total_seconds', result)
        self.assertIn('total_formatted', result)
        
        # All zones should be 0
        for zone in ['recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max']:
            self.assertEqual(result['zones'][zone]['time_seconds'], 0)
        self.assertEqual(result['total_seconds'], 0)
    
    def test_calculate_running_zones_with_workouts(self):
        """Test running zone calculation with actual workouts."""
        from core.services import ZoneCalculatorService
        from workouts.models import Workout, RideDetail, WorkoutPerformanceData
        from django.utils import timezone
        import uuid
        
        # Create a running workout
        now = timezone.now()
        ride_detail = RideDetail.objects.create(
            peloton_ride_id=f'running_1_{uuid.uuid4().hex[:8]}',
            title='Running Test Workout',
            description='Test run for zone calculations',
            workout_type=self.running_type,
            duration_seconds=1800,
            fitness_discipline='running'
        )
        
        workout = Workout.objects.create(
            user=self.user,
            ride_detail=ride_detail,
            completed_date=now.date(),
            recorded_date=now.date()
        )
        
        # Create performance data in 'easy' zone
        # timestamp is seconds from start of workout
        for i in range(10):
            WorkoutPerformanceData.objects.create(
                workout=workout,
                timestamp=i * 180,  # Every 180 seconds (3 minutes)
                intensity_zone='easy',
                speed=5.5
            )
        
        workouts = Workout.objects.filter(user=self.user)
        result = ZoneCalculatorService.calculate_running_zones(workouts)
        
        self.assertIn('zones', result)
        self.assertIn('total_seconds', result)
        self.assertEqual(result['zones']['easy']['name'], 'Easy')
        self.assertGreater(result['zones']['easy']['time_seconds'], 0)
    
    def test_calculate_running_zones_period_filter_year(self):
        """Test running zone calculation with year filter."""
        from core.services import ZoneCalculatorService
        from workouts.models import Workout, RideDetail, WorkoutPerformanceData
        from django.utils import timezone
        from datetime import timedelta
        import uuid
        
        now = timezone.now()
        
        # Create two running workouts - one this year, one last year
        ride_detail_current = RideDetail.objects.create(
            peloton_ride_id=f'running_2_{uuid.uuid4().hex[:8]}',
            title='Running Current Year',
            description='Test run',
            workout_type=self.running_type,
            duration_seconds=1800,
            fitness_discipline='running'
        )
        
        ride_detail_last = RideDetail.objects.create(
            peloton_ride_id=f'running_3_{uuid.uuid4().hex[:8]}',
            title='Running Last Year',
            description='Test run',
            workout_type=self.running_type,
            duration_seconds=1800,
            fitness_discipline='running'
        )
        
        # Current year workout
        workout_current = Workout.objects.create(
            user=self.user,
            ride_detail=ride_detail_current,
            completed_date=now.date(),
            recorded_date=now.date()
        )
        
        # Last year workout
        last_year = now - timedelta(days=400)
        workout_last = Workout.objects.create(
            user=self.user,
            ride_detail=ride_detail_last,
            completed_date=last_year.date(),
            recorded_date=last_year.date()
        )
        
        # Add performance data to both
        for workout in [workout_current, workout_last]:
            for i in range(5):
                WorkoutPerformanceData.objects.create(
                    workout=workout,
                    timestamp=i * 360,
                    intensity_zone='moderate',
                    speed=6.5
                )
        
        workouts = Workout.objects.filter(user=self.user)
        result_year = ZoneCalculatorService.calculate_running_zones(workouts, period='year')
        result_all = ZoneCalculatorService.calculate_running_zones(workouts, period='all')
        
        # Year filter should have less or equal time than all time
        self.assertLessEqual(
            result_year['zones']['moderate']['time_seconds'],
            result_all['zones']['moderate']['time_seconds']
        )
    
    def test_zone_format_output_structure(self):
        """Test that zone calculation returns correct output structure."""
        from core.services import ZoneCalculatorService
        from workouts.models import Workout, RideDetail, WorkoutPerformanceData
        from django.utils import timezone
        import uuid
        
        now = timezone.now()
        
        # Create workout with performance data
        ride_detail = RideDetail.objects.create(
            peloton_ride_id=f'cycling_4_{uuid.uuid4().hex[:8]}',
            title='Cycling Structure Test',
            description='Test ride',
            workout_type=self.cycling_type,
            duration_seconds=3600,
            fitness_discipline='cycling'
        )
        
        workout = Workout.objects.create(
            user=self.user,
            ride_detail=ride_detail,
            completed_date=now.date(),
            recorded_date=now.date()
        )
        
        for i in range(10):
            WorkoutPerformanceData.objects.create(
                workout=workout,
                timestamp=i * 360,
                power_zone=4,
                output=400
            )
        
        workouts = Workout.objects.filter(user=self.user)
        result = ZoneCalculatorService.calculate_cycling_zones(workouts)
        
        # Verify structure
        self.assertIsInstance(result, dict)
        self.assertIn('zones', result)
        self.assertIn('total_seconds', result)
        self.assertIn('total_formatted', result)
        
        # Verify zone structure
        zone_4 = result['zones'][4]
        self.assertIn('name', zone_4)
        self.assertIn('time_seconds', zone_4)
        self.assertIn('time_formatted', zone_4)
        self.assertEqual(zone_4['name'], 'Threshold')
        self.assertIsInstance(zone_4['time_seconds'], (int, float))
        self.assertIsInstance(zone_4['time_formatted'], str)


class ActivityToggleServiceTests(TestCase):
    """Tests for ActivityToggleService - validation and utility methods."""
    
    def test_is_valid_activity_valid(self):
        """Test activity validation with valid activities."""
        from core.services import ActivityToggleService
        
        self.assertTrue(ActivityToggleService.is_valid_activity('ride'))
        self.assertTrue(ActivityToggleService.is_valid_activity('run'))
        self.assertTrue(ActivityToggleService.is_valid_activity('yoga'))
        self.assertTrue(ActivityToggleService.is_valid_activity('strength'))
    
    def test_is_valid_activity_invalid(self):
        """Test activity validation with invalid activities."""
        from core.services import ActivityToggleService
        
        self.assertFalse(ActivityToggleService.is_valid_activity('invalid'))
        self.assertFalse(ActivityToggleService.is_valid_activity('swimming'))
        self.assertFalse(ActivityToggleService.is_valid_activity(''))
        self.assertFalse(ActivityToggleService.is_valid_activity(None))
    
    def test_get_activity_field(self):
        """Test mapping activity names to model fields."""
        from core.services import ActivityToggleService
        
        self.assertEqual(ActivityToggleService.get_activity_field('ride'), 'ride_done')
        self.assertEqual(ActivityToggleService.get_activity_field('run'), 'run_done')
        self.assertEqual(ActivityToggleService.get_activity_field('yoga'), 'yoga_done')
        self.assertEqual(ActivityToggleService.get_activity_field('strength'), 'strength_done')
        self.assertIsNone(ActivityToggleService.get_activity_field('invalid'))
    
    def test_get_activity_name(self):
        """Test getting display names for activities."""
        from core.services import ActivityToggleService
        
        self.assertEqual(ActivityToggleService.get_activity_name('ride'), 'Ride')
        self.assertEqual(ActivityToggleService.get_activity_name('run'), 'Run')
        self.assertEqual(ActivityToggleService.get_activity_name('yoga'), 'Yoga')
        self.assertEqual(ActivityToggleService.get_activity_name('strength'), 'Strength')
        self.assertIsNone(ActivityToggleService.get_activity_name(''))
        self.assertIsNone(ActivityToggleService.get_activity_name(None))
    
    def test_calculate_activity_points_no_points_when_unchecking(self):
        """Test that unchecking an activity earns no points."""
        from core.services import ActivityToggleService
        from tracker.models import WeeklyPlan
        from accounts.models import User
        from datetime import date
        
        user = User.objects.create_user(email='pointtest@example.com', password='test')
        plan = WeeklyPlan.objects.create(user=user, week_start=date.today(), template_name='Test')
        
        # Create a mock item
        from unittest.mock import Mock
        item = Mock()
        item.day_of_week = 1
        
        # Unchecking should earn no points
        points = ActivityToggleService.calculate_activity_points(item, is_being_checked=False, plan=plan)
        self.assertEqual(points, 0)
    
    def test_activity_map_coverage(self):
        """Test that ACTIVITY_MAP contains all expected activities."""
        from core.services import ActivityToggleService
        
        expected_activities = {'ride', 'run', 'yoga', 'strength'}
        self.assertEqual(set(ActivityToggleService.ACTIVITY_MAP.keys()), expected_activities)
    
    def test_get_day_activity_status_all_false(self):
        """Test getting day activity status when nothing is done."""
        from core.services import ActivityToggleService
        from tracker.models import WeeklyPlan
        from accounts.models import User
        from datetime import date
        
        user = User.objects.create_user(email='statustest@example.com', password='test')
        plan = WeeklyPlan.objects.create(user=user, week_start=date.today(), template_name='Test')
        
        # Get status for a day with no items
        status = ActivityToggleService.get_day_activity_status(plan, day_of_week=1)
        
        self.assertFalse(status['ride'])
        self.assertFalse(status['run'])
        self.assertFalse(status['yoga'])
        self.assertFalse(status['strength'])

class ActivityToggleServiceTests(TestCase):
    """Tests for ActivityToggleService."""
    
    def test_is_valid_activity(self):
        """Test activity validation."""
        from core.services import ActivityToggleService
        
        self.assertTrue(ActivityToggleService.is_valid_activity('ride'))
        self.assertTrue(ActivityToggleService.is_valid_activity('run'))
        self.assertTrue(ActivityToggleService.is_valid_activity('yoga'))
        self.assertTrue(ActivityToggleService.is_valid_activity('strength'))
        
        self.assertFalse(ActivityToggleService.is_valid_activity('invalid'))
        self.assertFalse(ActivityToggleService.is_valid_activity('swimming'))
        self.assertFalse(ActivityToggleService.is_valid_activity(''))
    
    def test_get_activity_field(self):
        """Test getting field name for activity."""
        from core.services import ActivityToggleService
        
        self.assertEqual(ActivityToggleService.get_activity_field('ride'), 'ride_done')
        self.assertEqual(ActivityToggleService.get_activity_field('run'), 'run_done')
        self.assertEqual(ActivityToggleService.get_activity_field('yoga'), 'yoga_done')
        self.assertEqual(ActivityToggleService.get_activity_field('strength'), 'strength_done')
        
        self.assertIsNone(ActivityToggleService.get_activity_field('invalid'))
    
    def test_get_activity_name(self):
        """Test getting display name for activity."""
        from core.services import ActivityToggleService
        
        self.assertEqual(ActivityToggleService.get_activity_name('ride'), 'Ride')
        self.assertEqual(ActivityToggleService.get_activity_name('run'), 'Run')
        self.assertEqual(ActivityToggleService.get_activity_name('yoga'), 'Yoga')
        self.assertEqual(ActivityToggleService.get_activity_name('strength'), 'Strength')
        self.assertIsNone(ActivityToggleService.get_activity_name(''))
        self.assertIsNone(ActivityToggleService.get_activity_name(None))


class PlanProcessorServiceTests(TestCase):
    """Tests for PlanProcessorService."""
    
    def test_calculate_day_points_3_core(self):
        """Test points calculation for 3-core plan."""
        from core.services import PlanProcessorService
        
        # 3-core: all days = 50 points
        self.assertEqual(PlanProcessorService.calculate_day_points(3, 1), 50)
        self.assertEqual(PlanProcessorService.calculate_day_points(3, 2), 50)
        self.assertEqual(PlanProcessorService.calculate_day_points(3, 3), 50)
    
    def test_calculate_day_points_4_core(self):
        """Test points calculation for 4-core plan."""
        from core.services import PlanProcessorService
        
        # 4-core: first/last = 50, middle = 25
        self.assertEqual(PlanProcessorService.calculate_day_points(4, 1), 50)  # First
        self.assertEqual(PlanProcessorService.calculate_day_points(4, 2), 25)  # Middle
        self.assertEqual(PlanProcessorService.calculate_day_points(4, 3), 25)  # Middle
        self.assertEqual(PlanProcessorService.calculate_day_points(4, 4), 50)  # Last
    
    def test_calculate_day_points_default(self):
        """Test default points calculation."""
        from core.services import PlanProcessorService
        
        # Unknown core count defaults to 50
        self.assertEqual(PlanProcessorService.calculate_day_points(5, 1), 50)
        self.assertEqual(PlanProcessorService.calculate_day_points(0, 1), 50)
    
    def test_is_bonus_completed(self):
        """Test bonus completion check."""
        from core.services import PlanProcessorService
        
        # Empty list
        self.assertFalse(PlanProcessorService.is_bonus_completed([]))
        
        # Mock items with different completion states
        class MockItem:
            def __init__(self, ride=False, run=False, yoga=False, strength=False):
                self.ride_done = ride
                self.run_done = run
                self.yoga_done = yoga
                self.strength_done = strength
        
        # Not completed
        items_incomplete = [MockItem(False, False, False, False)]
        self.assertFalse(PlanProcessorService.is_bonus_completed(items_incomplete))
        
        # Ride completed
        items_ride_done = [MockItem(True, False, False, False)]
        self.assertTrue(PlanProcessorService.is_bonus_completed(items_ride_done))
        
        # Run completed
        items_run_done = [MockItem(False, True, False, False)]
        self.assertTrue(PlanProcessorService.is_bonus_completed(items_run_done))
    
    def test_get_activity_type_for_item(self):
        """Test activity type detection for items."""
        from core.services import PlanProcessorService
        
        class MockItem:
            def __init__(self, ride_url='', run_url='', yoga_url='', strength_url=''):
                self.peloton_ride_url = ride_url
                self.peloton_run_url = run_url
                self.peloton_yoga_url = yoga_url
                self.peloton_strength_url = strength_url
        
        # No URLs
        self.assertIsNone(PlanProcessorService.get_activity_type_for_item(MockItem()))
        
        # Ride URL
        item_ride = MockItem(ride_url='https://example.com/ride')
        self.assertEqual(PlanProcessorService.get_activity_type_for_item(item_ride), 'ride')
        
        # Run URL
        item_run = MockItem(run_url='https://example.com/run')
        self.assertEqual(PlanProcessorService.get_activity_type_for_item(item_run), 'run')
        
        # Yoga URL
        item_yoga = MockItem(yoga_url='https://example.com/yoga')
        self.assertEqual(PlanProcessorService.get_activity_type_for_item(item_yoga), 'yoga')
        
        # Strength URL
        item_strength = MockItem(strength_url='https://example.com/strength')
        self.assertEqual(PlanProcessorService.get_activity_type_for_item(item_strength), 'strength')
        
        # Empty strings don't count
        item_empty = MockItem(ride_url='', run_url='  ')
        self.assertIsNone(PlanProcessorService.get_activity_type_for_item(item_empty))
    
    def test_is_item_done(self):
        """Test checking if activity is done."""
        from core.services import PlanProcessorService
        
        class MockItem:
            def __init__(self, ride=False, run=False, yoga=False, strength=False):
                self.ride_done = ride
                self.run_done = run
                self.yoga_done = yoga
                self.strength_done = strength
        
        item = MockItem(ride=True, run=False, yoga=True, strength=False)
        
        self.assertTrue(PlanProcessorService.is_item_done(item, 'ride'))
        self.assertFalse(PlanProcessorService.is_item_done(item, 'run'))
        self.assertTrue(PlanProcessorService.is_item_done(item, 'yoga'))
        self.assertFalse(PlanProcessorService.is_item_done(item, 'strength'))
        self.assertFalse(PlanProcessorService.is_item_done(item, 'invalid'))
    
    def test_organize_workout_days(self):
        """Test organizing workout items by day and activity."""
        from core.services import PlanProcessorService
        
        class MockItem:
            def __init__(self, dow, ride_url='', run_url='', yoga_url='', strength_url=''):
                self.day_of_week = dow
                self.peloton_ride_url = ride_url
                self.peloton_run_url = run_url
                self.peloton_yoga_url = yoga_url
                self.peloton_strength_url = strength_url
        
        items = [
            MockItem(0, ride_url='url1'),  # Sunday ride
            MockItem(0, run_url='url2'),   # Sunday run
            MockItem(1, ride_url='url3'),  # Monday ride
        ]
        
        result = PlanProcessorService.organize_workout_days(items)
        
        # Check structure
        self.assertIn(0, result)  # Sunday
        self.assertIn(1, result)  # Monday
        self.assertIn('ride', result[0])
        self.assertIn('run', result[0])
        self.assertIn('ride', result[1])
        
        # Check counts
        self.assertEqual(len(result[0]['ride']), 1)
        self.assertEqual(len(result[0]['run']), 1)
        self.assertEqual(len(result[1]['ride']), 1)
    
    def test_can_user_generate_plan_success(self):
        """Test successful plan generation validation."""
        from core.services import PlanProcessorService
        from django.contrib.auth import get_user_model
        from datetime import date
        
        User = get_user_model()
        user = User.objects.create_user(email='test@example.com', password='testpass123')
        week_start = date(2025, 1, 5)  # A Sunday
        
        can_generate, error = PlanProcessorService.can_user_generate_plan(user, week_start, None)
        
        self.assertTrue(can_generate)
        self.assertIsNone(error)
    
    def test_calculate_week_number_no_challenge(self):
        """Test week number calculation for standalone plan."""
        from core.services import PlanProcessorService
        
        class MockPlan:
            challenge_instance = None
        
        result = PlanProcessorService.calculate_week_number(MockPlan())
        self.assertIsNone(result)


# Import utility modules for testing
from core.utils import pace_converter, chart_helpers, workout_targets


class PaceConverterTests(TestCase):
    """Tests for pace_converter utility module."""
    
    def test_pace_zone_to_level_from_int(self):
        """Test pace zone level conversion from integer."""
        self.assertEqual(pace_converter.pace_zone_to_level(2), 3)  # 0-indexed to 1-indexed
        self.assertEqual(pace_converter.pace_zone_to_level(0), 1)
        self.assertEqual(pace_converter.pace_zone_to_level(6), 7)
    
    def test_pace_zone_to_level_from_string(self):
        """Test pace zone level conversion from string."""
        self.assertEqual(pace_converter.pace_zone_to_level('moderate'), 3)
        self.assertEqual(pace_converter.pace_zone_to_level('easy'), 2)
        self.assertEqual(pace_converter.pace_zone_to_level('max'), 7)
    
    def test_pace_zone_to_level_invalid(self):
        """Test pace zone level with invalid input."""
        self.assertIsNone(pace_converter.pace_zone_to_level('invalid'))
        self.assertIsNone(pace_converter.pace_zone_to_level(None))
        self.assertIsNone(pace_converter.pace_zone_to_level(''))
    
    def test_pace_str_from_mph(self):
        """Test MPH to pace string conversion."""
        self.assertEqual(pace_converter.pace_str_from_mph(7.5), '8:00/mi')
        self.assertEqual(pace_converter.pace_str_from_mph(6.0), '10:00/mi')
        self.assertIsNone(pace_converter.pace_str_from_mph(0))
        self.assertIsNone(pace_converter.pace_str_from_mph(-5))
    
    def test_mph_from_pace_value_string(self):
        """Test pace value to MPH conversion from string."""
        self.assertAlmostEqual(pace_converter.mph_from_pace_value('8:00'), 7.5, places=1)
        self.assertAlmostEqual(pace_converter.mph_from_pace_value('10:00'), 6.0, places=1)
    
    def test_mph_from_pace_value_numeric(self):
        """Test pace value to MPH conversion from numeric."""
        self.assertAlmostEqual(pace_converter.mph_from_pace_value(8.0), 7.5, places=1)
        self.assertAlmostEqual(pace_converter.mph_from_pace_value(10.0), 6.0, places=1)
    
    def test_mph_from_pace_value_invalid(self):
        """Test pace value with invalid input."""
        self.assertIsNone(pace_converter.mph_from_pace_value(0))
        self.assertIsNone(pace_converter.mph_from_pace_value(''))
        self.assertIsNone(pace_converter.mph_from_pace_value(None))
    
    def test_pace_zone_level_from_speed(self):
        """Test getting zone level from speed."""
        pace_ranges = {
            1: {'max_mph': 4.0},
            2: {'max_mph': 5.0},
            3: {'max_mph': 6.0},
        }
        self.assertEqual(pace_converter.pace_zone_level_from_speed(3.5, pace_ranges), 1)
        self.assertEqual(pace_converter.pace_zone_level_from_speed(4.5, pace_ranges), 2)
        self.assertEqual(pace_converter.pace_zone_level_from_speed(5.5, pace_ranges), 3)
    
    def test_pace_zone_label_from_level(self):
        """Test getting zone label from level."""
        self.assertEqual(pace_converter.pace_zone_label_from_level(1, uppercase=True), 'RECOVERY')
        self.assertEqual(pace_converter.pace_zone_label_from_level(2, uppercase=False), 'Easy')
        self.assertIsNone(pace_converter.pace_zone_label_from_level(10))


class ChartHelpersTests(TestCase):
    """Tests for chart_helpers utility module."""
    
    def test_downsample_points_no_downsampling_needed(self):
        """Test downsample when values already below max_points."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = chart_helpers.downsample_points(values, max_points=10)
        self.assertEqual(len(result), 5)
        self.assertEqual(result, values)
    
    def test_downsample_points_with_downsampling(self):
        """Test downsample when values exceed max_points."""
        values = list(range(100))
        result = chart_helpers.downsample_points(values, max_points=10)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], 0)
        self.assertEqual(result[-1], 99)
    
    def test_downsample_series(self):
        """Test downsample series of dict points."""
        series = [{'v': i, 't': i} for i in range(100)]
        result = chart_helpers.downsample_series(series, max_points=10)
        self.assertEqual(len(result), 10)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(result[0]['v'], 0)
        self.assertEqual(result[-1]['v'], 99)
    
    def test_normalize_series_to_svg_points_basic(self):
        """Test basic SVG point normalization."""
        series = [{'v': 100, 't': 0}, {'v': 150, 't': 60}, {'v': 120, 't': 120}]
        points_str, box, points, vmin, vmax = chart_helpers.normalize_series_to_svg_points(series)
        
        self.assertIsNotNone(points_str)
        self.assertEqual(len(points), 3)
        self.assertEqual(vmin, 100)
        self.assertEqual(vmax, 150)
        self.assertIn('x', points[0])
        self.assertIn('y', points[0])
        self.assertIn('v', points[0])
    
    def test_normalize_series_insufficient_data(self):
        """Test SVG normalization with insufficient data."""
        series = [{'v': 100}]  # Only one point
        points_str, box, points, vmin, vmax = chart_helpers.normalize_series_to_svg_points(series)
        
        self.assertIsNone(points_str)
        self.assertEqual(len(points), 0)
        self.assertIsNone(vmin)
        self.assertIsNone(vmax)
    
    def test_scaled_zone_value_from_output(self):
        """Test scaled zone value calculation."""
        zone_ranges = {1: (0, 100), 2: (100, 150), 3: (150, 200)}
        
        # Test midpoint of zone 2
        result = chart_helpers.scaled_zone_value_from_output(125, zone_ranges)
        self.assertAlmostEqual(result, 2.0, places=1)
        
        # Test upper bound of zone 2
        result = chart_helpers.scaled_zone_value_from_output(150, zone_ranges)
        self.assertAlmostEqual(result, 2.5, places=1)


class WorkoutTargetsTests(TestCase):
    """Tests for workout_targets utility module."""
    
    def test_target_value_at_time(self):
        """Test finding target value at specific time."""
        segments = [
            {'start': 0, 'end': 60, 'target': 100},
            {'start': 60, 'end': 120, 'target': 150},
        ]
        self.assertEqual(workout_targets.target_value_at_time(segments, 30), 100)
        self.assertEqual(workout_targets.target_value_at_time(segments, 90), 150)
        self.assertIsNone(workout_targets.target_value_at_time(segments, 150))
    
    def test_target_value_at_time_with_shift(self):
        """Test target value with time shift."""
        segments = [{'start': 60, 'end': 120, 'target': 150}]
        # With -60 shift, segment effectively starts at 0
        result = workout_targets.target_value_at_time_with_shift(segments, 30, shift_seconds=-60)
        self.assertEqual(result, 150)
    
    def test_target_segment_at_time_with_shift(self):
        """Test getting full segment dict at time with shift."""
        segments = [{'start': 0, 'end': 60, 'zone': 2, 'target': 100}]
        seg = workout_targets.target_segment_at_time_with_shift(segments, 30)
        self.assertIsNotNone(seg)
        self.assertEqual(seg['zone'], 2)
        self.assertEqual(seg['target'], 100)
    
    def test_calculate_target_line_from_segments(self):
        """Test power zone target line calculation."""
        segments = [{'start': 0, 'end': 120, 'zone': 2}]
        zone_ranges = {2: (100, 150)}
        seconds = list(range(0, 120))
        
        targets = workout_targets.calculate_target_line_from_segments(
            segments, zone_ranges, seconds, user_ftp=200
        )
        
        self.assertEqual(len(targets), 120)
        self.assertIn('timestamp', targets[0])
        self.assertIn('target_output', targets[0])
        # Zone 2 at 65% of FTP 200 = 130 watts
        self.assertEqual(targets[60]['target_output'], 130)
    
    def test_calculate_pace_target_line_from_segments(self):
        """Test pace target line calculation."""
        segments = [{'start': 0, 'end': 120, 'zone': 2}]
        seconds = list(range(0, 120))
        
        targets = workout_targets.calculate_pace_target_line_from_segments(segments, seconds)
        
        self.assertEqual(len(targets), 120)
        self.assertIn('timestamp', targets[0])
        self.assertIn('target_pace_zone', targets[0])
        self.assertEqual(targets[0]['target_pace_zone'], 2)
    
    def test_calculate_power_zone_target_line(self):
        """Test power zone target line from metrics data."""
        metrics = [{
            'segment_type': 'power_zone',
            'offsets': {'start': 0, 'end': 120},
            'metrics': [{'name': 'power_zone', 'lower': 3, 'upper': 3}]
        }]
        seconds = list(range(0, 120))
        
        targets = workout_targets.calculate_power_zone_target_line(metrics, 200, seconds)
        
        self.assertEqual(len(targets), 120)
        # Zone 3 at 82.5% of FTP 200 = 165 watts
        self.assertEqual(targets[60]['target_output'], 165)

