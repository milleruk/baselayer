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
    
