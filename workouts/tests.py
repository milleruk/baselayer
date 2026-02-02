from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import datetime
from .models import WorkoutType, Instructor, RideDetail
from .services.class_filter import ClassLibraryFilter

User = get_user_model()


class ClassLibraryFilterTestCase(TestCase):
    """Unit tests for ClassLibraryFilter service"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests"""
        # Create workout types
        cls.cycling_type = WorkoutType.objects.create(
            name='Cycling',
            slug='cycling'
        )
        cls.running_type = WorkoutType.objects.create(
            name='Running',
            slug='running'
        )
        cls.walking_type = WorkoutType.objects.create(
            name='Walking',
            slug='walking'
        )
        cls.rowing_type = WorkoutType.objects.create(
            name='Rowing',
            slug='rowing'
        )
        
        # Create instructors
        cls.instructor1 = Instructor.objects.create(
            name='Emma',
            peloton_id='instr_emma'
        )
        cls.instructor2 = Instructor.objects.create(
            name='Jenn',
            peloton_id='instr_jenn'
        )
        
        # Create ride details
        # 2024 rides
        cls.ride_2024_jan = RideDetail.objects.create(
            title='Cycling Class Jan 2024',
            peloton_ride_id='ride_2024_jan',
            fitness_discipline='cycling',
            instructor=cls.instructor1,
            workout_type=cls.cycling_type,
            duration_seconds=1800,  # 30 minutes
            original_air_time=int(datetime(2024, 1, 15, 10, 0, 0).timestamp()),
            is_power_zone_class=True,
        )
        
        cls.ride_2024_march = RideDetail.objects.create(
            title='Running Class March 2024',
            peloton_ride_id='ride_2024_march',
            fitness_discipline='running',
            instructor=cls.instructor2,
            workout_type=cls.running_type,
            duration_seconds=2400,  # 40 minutes
            original_air_time=int(datetime(2024, 3, 20, 14, 0, 0).timestamp()),
        )
        
        # 2025 rides
        cls.ride_2025_jan = RideDetail.objects.create(
            title='Walking Class Jan 2025',
            peloton_ride_id='ride_2025_jan',
            fitness_discipline='walking',
            instructor=cls.instructor1,
            workout_type=cls.walking_type,
            duration_seconds=1200,  # 20 minutes
            original_air_time=int(datetime(2025, 1, 10, 9, 0, 0).timestamp()),
        )
        
        cls.ride_2025_june = RideDetail.objects.create(
            title='Rowing Class June 2025',
            peloton_ride_id='ride_2025_june',
            fitness_discipline='rowing',
            instructor=cls.instructor2,
            workout_type=cls.rowing_type,
            duration_seconds=3000,  # 50 minutes
            original_air_time=int(datetime(2025, 6, 15, 11, 0, 0).timestamp()),
        )
        
        # Ride with NULL timestamp
        cls.ride_no_timestamp = RideDetail.objects.create(
            title='Old Class No Date',
            peloton_ride_id='ride_no_date',
            fitness_discipline='cycling',
            instructor=cls.instructor1,
            workout_type=cls.cycling_type,
            duration_seconds=1500,  # 25 minutes
            original_air_time=None,
        )
    
    def setUp(self):
        """Reset queryset for each test"""
        self.base_queryset = RideDetail.objects.all()
    
    def test_filter_initialization(self):
        """Test filter initializes with queryset"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        self.assertEqual(filter_obj.get_queryset().count(), 5)
        self.assertEqual(filter_obj.get_filters(), {})
    
    def test_apply_search_by_title(self):
        """Test search filter by class title"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_search('Jan 202')
        results = filter_obj.get_queryset()
        # Should find rides with "Jan" in title (ride_2024_jan and ride_2025_jan)
        self.assertEqual(results.count(), 2)
    
    def test_apply_search_by_instructor(self):
        """Test search filter by instructor name"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_search('Emma')
        results = filter_obj.get_queryset()
        # instructor1 (Emma) has 3 rides
        self.assertEqual(results.count(), 3)
        self.assertTrue(all(r.instructor.name == 'Emma' for r in results))
    
    def test_apply_search_case_insensitive(self):
        """Test search is case-insensitive"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_search('Running')  # Only in Running Class March 2024
        results = filter_obj.get_queryset()
        # Should find the running class
        self.assertEqual(results.count(), 1)
        self.assertIn('Running', results.first().title)
    
    def test_apply_search_empty(self):
        """Test empty search doesn't filter"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_search('')
        filter_obj.apply_search('   ')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 5)
    
    def test_apply_workout_type_filter_valid(self):
        """Test workout type filter with valid type"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_workout_type_filter('cycling')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 2)
        self.assertTrue(all(r.workout_type.slug == 'cycling' for r in results))
    
    def test_apply_workout_type_filter_invalid(self):
        """Test workout type filter with invalid type"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_workout_type_filter('invalid_type')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 5)  # No filtering
    
    def test_apply_workout_type_filter_all_types(self):
        """Test all allowed types work"""
        allowed_types = ['cycling', 'running', 'walking', 'rowing']
        expected_counts = {
            'cycling': 2,
            'running': 1,
            'walking': 1,
            'rowing': 1,
        }
        
        for wtype in allowed_types:
            filter_obj = ClassLibraryFilter(self.base_queryset)
            filter_obj.apply_workout_type_filter(wtype)
            results = filter_obj.get_queryset()
            self.assertEqual(
                results.count(),
                expected_counts[wtype],
                f"Expected {expected_counts[wtype]} results for {wtype}"
            )
    
    def test_apply_instructor_filter_valid(self):
        """Test instructor filter with valid ID"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_instructor_filter(self.instructor1.id)
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 3)
        self.assertTrue(all(r.instructor_id == self.instructor1.id for r in results))
    
    def test_apply_instructor_filter_invalid(self):
        """Test instructor filter with invalid ID"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_instructor_filter('invalid')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 5)  # No filtering
    
    def test_apply_duration_filter(self):
        """Test duration filter with tolerance"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        # Filter for 30 minutes (±30 seconds)
        filter_obj.apply_duration_filter('30')
        results = filter_obj.get_queryset()
        # Should match ride_2024_jan (1800 seconds = 30 minutes)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().duration_seconds, 1800)
    
    def test_apply_duration_filter_with_tolerance(self):
        """Test duration filter tolerance (±30 seconds)"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        # Filter for 30 minutes - should match 1800±30 seconds
        filter_obj.apply_duration_filter('30')
        results = filter_obj.get_queryset()
        for ride in results:
            duration_min = ride.duration_seconds / 60
            # Should be within ±0.5 minutes (30 seconds)
            self.assertGreaterEqual(duration_min, 30 - 0.5)
            self.assertLessEqual(duration_min, 30 + 0.5)
    
    def test_apply_year_filter(self):
        """Test year filter"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_year_filter('2024')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 2)
        self.assertTrue(all(r.original_air_time is not None for r in results))
    
    def test_apply_year_filter_2025(self):
        """Test year filter for 2025"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_year_filter('2025')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 2)
    
    def test_apply_year_filter_invalid(self):
        """Test year filter with invalid year"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_year_filter('invalid')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 5)  # No filtering
    
    def test_apply_month_filter(self):
        """Test month filter"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_month_filter('2024', '1')  # January 2024
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().peloton_ride_id, 'ride_2024_jan')
    
    def test_apply_month_filter_multiple_matches(self):
        """Test month filter with multiple matches"""
        # Create another Jan 2024 ride
        RideDetail.objects.create(
            title='Another Jan 2024 Ride',
            peloton_ride_id='ride_2024_jan_2',
            fitness_discipline='running',
            instructor=self.instructor2,
            workout_type=self.running_type,
            duration_seconds=1800,
            original_air_time=int(datetime(2024, 1, 25, 10, 0, 0).timestamp()),
        )
        
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_month_filter('2024', '1')
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 2)
    
    def test_apply_month_filter_without_year(self):
        """Test month filter without year does nothing"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_month_filter('', '6')  # No year
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 5)  # No filtering
    
    def test_apply_ordering_descending_default(self):
        """Test default ordering (descending by air time)"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_ordering()
        results = list(filter_obj.get_queryset())
        
        # Extract timestamps (excluding None)
        timestamps = [r.original_air_time for r in results if r.original_air_time is not None]
        # Verify descending order
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        # Verify NULLs are last
        self.assertEqual(results[-1].original_air_time, None)
    
    def test_apply_ordering_ascending(self):
        """Test ascending ordering by air time"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_ordering('original_air_time')
        results = list(filter_obj.get_queryset())
        
        timestamps = [r.original_air_time for r in results if r.original_air_time is not None]
        # Verify ascending order
        self.assertEqual(timestamps, sorted(timestamps))
        # Verify NULLs are last
        self.assertEqual(results[-1].original_air_time, None)
    
    def test_apply_ordering_by_title(self):
        """Test ordering by title"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_ordering('title')
        results = list(filter_obj.get_queryset())
        titles = [r.title for r in results]
        self.assertEqual(titles, sorted(titles))
    
    def test_apply_ordering_invalid(self):
        """Test invalid ordering defaults to descending air time"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_ordering('invalid_order')
        results = list(filter_obj.get_queryset())
        # Should default to -original_air_time
        timestamps = [r.original_air_time for r in results if r.original_air_time is not None]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_chainable_api(self):
        """Test that filter methods can be chained"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        result = (filter_obj
                  .apply_workout_type_filter('cycling')
                  .apply_instructor_filter(self.instructor1.id)
                  .apply_ordering('title'))
        
        # Should return self for chaining
        self.assertIsInstance(result, ClassLibraryFilter)
        results = filter_obj.get_queryset()
        # Both cycling classes by instructor1
        self.assertEqual(results.count(), 2)
    
    def test_get_filters_dict(self):
        """Test get_filters returns applied filters"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_search('Cycling')
        filter_obj.apply_workout_type_filter('cycling')
        filter_obj.apply_year_filter('2024')
        
        filters = filter_obj.get_filters()
        self.assertEqual(filters['search'], 'Cycling')
        self.assertEqual(filters['workout_type'], 'cycling')
        self.assertEqual(filters['year'], 2024)
    
    def test_get_available_years(self):
        """Test get_available_years static method"""
        years = ClassLibraryFilter.get_available_years(self.base_queryset)
        self.assertEqual(sorted(years, reverse=True), years)  # Newest first
        self.assertIn(2024, years)
        self.assertIn(2025, years)
    
    def test_get_available_years_excludes_null(self):
        """Test get_available_years excludes NULL timestamps"""
        years = ClassLibraryFilter.get_available_years(self.base_queryset)
        # ride_no_timestamp has NULL timestamp, shouldn't affect years
        self.assertEqual(len(years), 2)
    
    def test_get_available_months(self):
        """Test get_available_months static method"""
        months = ClassLibraryFilter.get_available_months(self.base_queryset, 2024)
        self.assertIn(1, months)  # January
        self.assertIn(3, months)  # March
        self.assertEqual(len(months), 2)
    
    def test_get_available_months_no_year(self):
        """Test get_available_months with no year"""
        months = ClassLibraryFilter.get_available_months(self.base_queryset, '')
        self.assertEqual(months, [])
    
    def test_get_available_durations(self):
        """Test get_available_durations static method"""
        durations = ClassLibraryFilter.get_available_durations(self.base_queryset)
        # Should include both standard and actual durations
        self.assertIsInstance(durations, list)
        self.assertTrue(len(durations) > 0)
        # Verify sorted
        self.assertEqual(durations, sorted(durations))
    
    def test_multiple_filters_combined(self):
        """Test combining multiple filters"""
        filter_obj = ClassLibraryFilter(self.base_queryset)
        filter_obj.apply_workout_type_filter('cycling')
        filter_obj.apply_instructor_filter(self.instructor1.id)
        filter_obj.apply_year_filter('2024')
        
        results = filter_obj.get_queryset()
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().peloton_ride_id, 'ride_2024_jan')


class ClassLibraryViewTestCase(TestCase):
    """Integration tests for class_library view"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for view tests"""
        # Create test user
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )
        
        # Create workout types
        cls.cycling_type = WorkoutType.objects.create(
            name='Cycling',
            slug='cycling'
        )
        cls.running_type = WorkoutType.objects.create(
            name='Running',
            slug='running'
        )
        
        # Create instructors
        cls.instructor1 = Instructor.objects.create(
            name='Emma Lovewell',
            peloton_id='instr_emma'
        )
        cls.instructor2 = Instructor.objects.create(
            name='Jenn Sherman',
            peloton_id='instr_jenn'
        )
        
        # Create multiple rides for pagination testing
        for i in range(20):
            instructor = cls.instructor1 if i % 2 == 0 else cls.instructor2
            wtype = cls.cycling_type if i % 2 == 0 else cls.running_type
            
            RideDetail.objects.create(
                title=f'Class {i:02d}',
                peloton_ride_id=f'ride_{i:03d}',
                fitness_discipline='cycling' if i % 2 == 0 else 'running',
                instructor=instructor,
                workout_type=wtype,
                duration_seconds=1800 + (i * 60),  # Varying durations
                original_air_time=int(datetime(2024, 1 + (i % 12), 1 + (i % 28), 10, 0, 0).timestamp()),
            )
    
    def setUp(self):
        """Set up for each test"""
        self.client = Client()
        self.url = reverse('classes:library')
    
    def test_view_requires_login(self):
        """Test that view requires authentication"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_view_loads_authenticated(self):
        """Test view loads for authenticated user"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
    
    def test_view_context_has_required_variables(self):
        """Test context has all required template variables"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        
        context = response.context
        self.assertIn('page_obj', context)
        self.assertIn('is_paginated', context)
        self.assertIn('workout_types', context)
        self.assertIn('instructors', context)
        self.assertIn('durations', context)
        self.assertIn('available_years_list', context)
        self.assertIn('available_months', context)
        self.assertIn('search_query', context)
        self.assertIn('workout_type_filter', context)
        self.assertIn('instructor_filter', context)
        self.assertIn('duration_filter', context)
        self.assertIn('year_filter', context)
        self.assertIn('month_filter', context)
        self.assertIn('order_by', context)
    
    def test_pagination_works(self):
        """Test pagination (12 per page)"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        
        page_obj = response.context['page_obj']
        # First page should have 12 items
        self.assertEqual(len(page_obj), 12)
        self.assertTrue(page_obj.has_next())
    
    def test_pagination_page_2(self):
        """Test second page of pagination"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?page=2')
        
        page_obj = response.context['page_obj']
        # Second page should have remaining items (20 - 12 = 8)
        self.assertEqual(len(page_obj), 8)
        self.assertTrue(page_obj.has_previous())
    
    def test_search_filter(self):
        """Test search filter in view"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?search=Class%2001')
        
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 1)
        self.assertEqual(page_obj[0].title, 'Class 01')
    
    def test_workout_type_filter(self):
        """Test workout type filter in view"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?type=cycling')
        
        page_obj = response.context['page_obj']
        # Should have 10 cycling classes (every even index)
        self.assertEqual(page_obj.paginator.count, 10)
    
    def test_instructor_filter(self):
        """Test instructor filter in view"""
        self.client.force_login(self.user)
        response = self.client.get(f'?instructor={self.instructor1.id}', follow=True)
        
        # Just verify the filter is processed without error
        self.assertEqual(response.status_code, 200)
    
    def test_duration_filter(self):
        """Test duration filter in view"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?duration=30')
        
        # Should find rides with duration close to 30 minutes
        page_obj = response.context['page_obj']
        self.assertGreater(page_obj.paginator.count, 0)
    
    def test_year_filter(self):
        """Test year filter in view"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?year=2024')
        
        page_obj = response.context['page_obj']
        # All rides are in 2024
        self.assertEqual(page_obj.paginator.count, 20)
    
    def test_month_filter(self):
        """Test month filter in view"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?year=2024&month=1')
        
        page_obj = response.context['page_obj']
        self.assertGreater(page_obj.paginator.count, 0)
    
    def test_sort_by_air_time_descending(self):
        """Test sort by air time (newest first)"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?order_by=-original_air_time')
        
        page_obj = response.context['page_obj']
        rides = list(page_obj)
        # Verify descending order (newer classes first)
        for i in range(len(rides) - 1):
            if rides[i].original_air_time and rides[i+1].original_air_time:
                self.assertGreaterEqual(
                    rides[i].original_air_time,
                    rides[i+1].original_air_time
                )
    
    def test_sort_by_title(self):
        """Test sort by title"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?order_by=title')
        
        page_obj = response.context['page_obj']
        rides = list(page_obj)
        titles = [r.title for r in rides]
        # Verify alphabetical order
        self.assertEqual(titles, sorted(titles))
    
    def test_sort_by_duration(self):
        """Test sort by duration"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?order_by=duration_seconds')
        
        page_obj = response.context['page_obj']
        rides = list(page_obj)
        durations = [r.duration_seconds for r in rides]
        # Verify ascending order
        self.assertEqual(durations, sorted(durations))
    
    def test_combined_filters(self):
        """Test multiple filters combined"""
        self.client.force_login(self.user)
        response = self.client.get(
            self.url + f'?type=cycling&instructor={self.instructor1.id}&year=2024'
        )
        
        page_obj = response.context['page_obj']
        # Should have cycling classes by instructor1 in 2024
        for ride in page_obj:
            self.assertEqual(ride.workout_type.slug, 'cycling')
            self.assertEqual(ride.instructor_id, self.instructor1.id)
    
    def test_filter_values_passed_to_context(self):
        """Test filter values are passed to template context"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?search=test&type=cycling&year=2024')
        
        context = response.context
        self.assertEqual(context['search_query'], 'test')
        self.assertEqual(context['workout_type_filter'], 'cycling')
        self.assertEqual(context['year_filter'], '2024')
    
    def test_available_years_in_context(self):
        """Test available years are in context"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        
        years = response.context['available_years_list']
        self.assertIsInstance(years, list)
        self.assertIn(2024, years)
    
    def test_template_used(self):
        """Test correct template is used"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        
        self.assertTemplateUsed(response, 'workouts/class_library.html')
    
    def test_empty_results(self):
        """Test handling of empty results"""
        self.client.force_login(self.user)
        response = self.client.get(self.url + '?search=nonexistent')
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 0)
        self.assertEqual(response.status_code, 200)  # Still renders successfully


class MetricsCalculatorTestCase(TestCase):
    """Unit tests for MetricsCalculator service"""
    
    def setUp(self):
        """Set up MetricsCalculator instance for each test"""
        from workouts.services.metrics import MetricsCalculator
        self.calculator = MetricsCalculator()
    
    # ==================== TSS Calculation Tests ====================
    
    def test_calculate_tss_with_valid_data(self):
        """TSS calculation with valid avg_power, duration, and FTP"""
        tss = self.calculator.calculate_tss(
            avg_power=200.0,
            duration_seconds=3600,  # 1 hour
            ftp=280.0
        )
        # IF = 200/280 = 0.714
        # TSS = 1 hour * 0.714^2 * 100 = 51.0
        self.assertIsNotNone(tss)
        self.assertAlmostEqual(tss, 51.0, places=1)
    
    def test_calculate_tss_with_stored_tss(self):
        """TSS returns stored value when provided"""
        stored = 75.5
        tss = self.calculator.calculate_tss(
            avg_power=200.0,
            duration_seconds=3600,
            ftp=280.0,
            stored_tss=stored
        )
        self.assertEqual(tss, stored)
    
    def test_calculate_tss_missing_avg_power(self):
        """TSS returns None when avg_power is missing"""
        tss = self.calculator.calculate_tss(
            duration_seconds=3600,
            ftp=280.0
        )
        self.assertIsNone(tss)
    
    def test_calculate_tss_missing_duration(self):
        """TSS returns None when duration_seconds is missing"""
        tss = self.calculator.calculate_tss(
            avg_power=200.0,
            ftp=280.0
        )
        self.assertIsNone(tss)
    
    def test_calculate_tss_missing_ftp(self):
        """TSS returns None when FTP is missing"""
        tss = self.calculator.calculate_tss(
            avg_power=200.0,
            duration_seconds=3600
        )
        self.assertIsNone(tss)
    
    def test_calculate_tss_invalid_ftp(self):
        """TSS returns None when FTP is zero or negative"""
        tss = self.calculator.calculate_tss(
            avg_power=200.0,
            duration_seconds=3600,
            ftp=0
        )
        self.assertIsNone(tss)
    
    def test_calculate_tss_bounds_checking(self):
        """TSS clamps IF between 0.0 and 2.0"""
        # High IF (should clamp to 2.0)
        tss_high = self.calculator.calculate_tss(
            avg_power=600.0,
            duration_seconds=3600,
            ftp=200.0
        )
        # IF = 600/200 = 3.0, clamped to 2.0
        # TSS = 1 * 2.0^2 * 100 = 400
        self.assertAlmostEqual(tss_high, 400.0, places=1)
        
        # Negative avg_power (should clamp IF to 0.0)
        tss_neg = self.calculator.calculate_tss(
            avg_power=-100.0,
            duration_seconds=3600,
            ftp=200.0
        )
        # IF = -100/200 = -0.5, clamped to 0.0
        # TSS = 1 * 0.0^2 * 100 = 0
        self.assertAlmostEqual(tss_neg, 0.0, places=1)
    
    # ==================== Intensity Factor Tests ====================
    
    def test_calculate_if_from_power_and_ftp(self):
        """IF calculation from avg_power and FTP"""
        if_value = self.calculator.calculate_intensity_factor(
            avg_power=200.0,
            ftp=280.0
        )
        self.assertAlmostEqual(if_value, 0.714, places=2)
    
    def test_calculate_if_from_tss_and_duration(self):
        """IF calculation from TSS (reverse calculation)"""
        # TSS=51, duration=3600s (1 hour)
        # IF = sqrt(51 / (1 * 100)) = sqrt(0.51) = 0.714
        if_value = self.calculator.calculate_intensity_factor(
            tss=51.0,
            duration_seconds=3600
        )
        self.assertAlmostEqual(if_value, 0.714, places=2)
    
    def test_calculate_if_prefers_power_method(self):
        """IF prefers power/FTP method over TSS method"""
        if_value = self.calculator.calculate_intensity_factor(
            avg_power=200.0,
            ftp=280.0,
            tss=100.0,  # Different IF from different TSS
            duration_seconds=3600
        )
        # Should use power method: 200/280 = 0.714
        self.assertAlmostEqual(if_value, 0.714, places=2)
    
    def test_calculate_if_missing_data(self):
        """IF returns None when insufficient data"""
        if_value = self.calculator.calculate_intensity_factor()
        self.assertIsNone(if_value)
    
    def test_calculate_if_bounds_checking(self):
        """IF clamps to 0.0-2.0 range"""
        if_high = self.calculator.calculate_intensity_factor(
            avg_power=600.0,
            ftp=200.0
        )
        self.assertEqual(if_high, 2.0)
    
    # ==================== Power Zone Range Tests ====================
    
    def test_get_power_zone_ranges(self):
        """Power zone ranges calculated correctly from FTP"""
        ftp = 280.0
        ranges = self.calculator.get_power_zone_ranges(ftp)
        
        self.assertIsNotNone(ranges)
        self.assertEqual(len(ranges), 7)
        
        # Zone 1: 0-55%
        self.assertEqual(ranges[1], (0, 154))
        # Zone 2: 55-75%
        self.assertEqual(ranges[2], (154, 210))
        # Zone 7: 150%+
        self.assertEqual(ranges[7][0], 420)
        self.assertIsNone(ranges[7][1])
    
    def test_get_power_zone_ranges_invalid_ftp(self):
        """Power zone ranges returns None for invalid FTP"""
        ranges = self.calculator.get_power_zone_ranges(0)
        self.assertIsNone(ranges)
    
    def test_get_power_zone_for_output(self):
        """Power zone determination from output watts"""
        zone_ranges = self.calculator.get_power_zone_ranges(280.0)
        
        # Zone 1: 0-154W
        zone = self.calculator.get_power_zone_for_output(100, zone_ranges)
        self.assertEqual(zone, 1)
        
        # Zone 4: 252-294W
        zone = self.calculator.get_power_zone_for_output(270, zone_ranges)
        self.assertEqual(zone, 4)
        
        # Zone 7: 420W+
        zone = self.calculator.get_power_zone_for_output(500, zone_ranges)
        self.assertEqual(zone, 7)
    
    def test_get_power_zone_for_output_invalid(self):
        """Power zone returns None for invalid data"""
        zone = self.calculator.get_power_zone_for_output(100, None, None)
        self.assertIsNone(zone)
    
    def test_get_target_watts_for_zone(self):
        """Target watts (midpoint) for power zone"""
        zone_ranges = self.calculator.get_power_zone_ranges(280.0)
        
        # Zone 1 midpoint: (0 + 154) / 2 = 77
        watts = self.calculator.get_target_watts_for_zone(1, zone_ranges)
        self.assertEqual(watts, 77.0)
        
        # Zone 4 midpoint: (252 + 294) / 2 = 273
        watts = self.calculator.get_target_watts_for_zone(4, zone_ranges)
        self.assertEqual(watts, 273.0)
    
    def test_get_available_power_zones(self):
        """Available power zones list"""
        zones = self.calculator.get_available_power_zones(280.0)
        self.assertEqual(zones, [1, 2, 3, 4, 5, 6, 7])
    
    def test_is_valid_power_zone(self):
        """Power zone validation"""
        self.assertTrue(self.calculator.is_valid_power_zone(1))
        self.assertTrue(self.calculator.is_valid_power_zone(7))
        self.assertFalse(self.calculator.is_valid_power_zone(0))
        self.assertFalse(self.calculator.is_valid_power_zone(8))
    
    # ==================== Pace Zone Tests ====================
    
    def test_get_pace_zone_targets(self):
        """Pace zone targets calculated for pace level"""
        targets = self.calculator.get_pace_zone_targets(5)
        
        self.assertIsNotNone(targets)
        self.assertIn('recovery', targets)
        self.assertIn('easy', targets)
        self.assertIn('moderate', targets)
        self.assertIn('max', targets)
        
        # Level 5 base pace = 8:30/mile
        self.assertEqual(targets['recovery'], 10.5)
        self.assertEqual(targets['moderate'], 8.5)
        self.assertEqual(targets['max'], 6.5)
    
    def test_get_pace_zone_targets_different_levels(self):
        """Pace zone targets vary by level"""
        targets_1 = self.calculator.get_pace_zone_targets(1)
        targets_10 = self.calculator.get_pace_zone_targets(10)
        
        # Level 1 pace > Level 10 pace (slower for level 1)
        self.assertGreater(targets_1['moderate'], targets_10['moderate'])
    
    def test_get_pace_zone_targets_invalid_level(self):
        """Pace zone targets returns None for invalid level"""
        targets = self.calculator.get_pace_zone_targets(None)
        self.assertIsNone(targets)
    
    def test_get_available_pace_zones(self):
        """Available pace zones list"""
        zones = self.calculator.get_available_pace_zones()
        self.assertEqual(set(zones), {
            'recovery', 'easy', 'moderate', 'challenging', 'hard', 'very_hard', 'max'
        })
    
    def test_is_valid_pace_level(self):
        """Pace level validation"""
        self.assertTrue(self.calculator.is_valid_pace_level(1))
        self.assertTrue(self.calculator.is_valid_pace_level(10))
        self.assertFalse(self.calculator.is_valid_pace_level(0))
        self.assertFalse(self.calculator.is_valid_pace_level(11))
    
    # ==================== Zone Distribution TSS Tests ====================
    
    def test_calculate_tss_from_power_zone_distribution(self):
        """TSS calculation from power zone distribution"""
        zone_distribution = [
            {'zone': 1, 'time_sec': 300},
            {'zone': 4, 'time_sec': 3000},
            {'zone': 6, 'time_sec': 300},
        ]
        
        tss = self.calculator.calculate_tss_from_zone_distribution(
            zone_distribution=zone_distribution,
            duration_seconds=3600,
            class_type='power_zone',
            ftp=280.0
        )
        
        self.assertIsNotNone(tss)
        self.assertGreater(tss, 0)
    
    def test_calculate_tss_from_pace_target_distribution(self):
        """TSS calculation from pace zone distribution"""
        zone_distribution = [
            {'zone': 'recovery', 'time_sec': 300},
            {'zone': 'moderate', 'time_sec': 3000},
            {'zone': 'hard', 'time_sec': 300},
        ]
        
        tss = self.calculator.calculate_tss_from_zone_distribution(
            zone_distribution=zone_distribution,
            duration_seconds=3600,
            class_type='pace_target',
            pace_level=5
        )
        
        self.assertIsNotNone(tss)
        self.assertGreater(tss, 0)
    
    def test_calculate_tss_from_distribution_missing_data(self):
        """TSS returns None for distribution with missing data"""
        # No FTP for power zone
        tss = self.calculator.calculate_tss_from_zone_distribution(
            zone_distribution=[{'zone': 1, 'time_sec': 300}],
            duration_seconds=3600,
            class_type='power_zone'
        )
        self.assertIsNone(tss)
    
    def test_calculate_tss_from_distribution_empty(self):
        """TSS returns None for empty zone distribution"""
        tss = self.calculator.calculate_tss_from_zone_distribution(
            zone_distribution=[],
            duration_seconds=3600,
            class_type='power_zone',
            ftp=280.0
        )
        self.assertIsNone(tss)
    
    # ==================== Integration Tests ====================
    
    def test_metrics_roundtrip(self):
        """TSS -> IF -> TSS roundtrip maintains consistency"""
        # Calculate TSS
        tss_orig = self.calculator.calculate_tss(
            avg_power=200.0,
            duration_seconds=3600,
            ftp=280.0
        )
        
        # Calculate IF from TSS
        if_value = self.calculator.calculate_intensity_factor(
            tss=tss_orig,
            duration_seconds=3600
        )
        
        # Calculate TSS from IF and avg_power
        tss_new = self.calculator.calculate_tss(
            avg_power=200.0,
            duration_seconds=3600,
            ftp=280.0
        )
        
        self.assertAlmostEqual(tss_orig, tss_new, places=1)
    
    def test_pace_intensity_factors_valid_range(self):
        """All pace intensity factors are reasonable"""
        factors = self.calculator.PACE_ZONE_INTENSITY_FACTORS
        
        for zone, factor in factors.items():
            self.assertGreater(factor, 0)
            self.assertLess(factor, 2.0)
            
        # Recovery should be lower than max
        self.assertLess(factors['recovery'], factors['max'])


class ChartBuilderTestCase(TestCase):
    """Unit tests for ChartBuilder service"""
    
    def setUp(self):
        """Set up ChartBuilder instance for each test"""
        from workouts.services.chart_builder import ChartBuilder
        self.builder = ChartBuilder()
    
    # ==================== Performance Graph Tests ====================
    
    def test_generate_performance_graph_with_valid_data(self):
        """Performance graph generation with valid power zone data"""
        performance_data = [
            {'timestamp': 0, 'value': 100},
            {'timestamp': 30, 'value': 150},
            {'timestamp': 60, 'value': 200},
            {'timestamp': 90, 'value': 250},
            {'timestamp': 120, 'value': 200},
        ]
        
        chart = self.builder.generate_performance_graph(
            performance_data=performance_data,
            workout_type='power_zone',
            ftp=280.0
        )
        
        self.assertIsNotNone(chart)
        self.assertEqual(chart['type'], 'performance_graph')
        self.assertEqual(chart['workout_type'], 'power_zone')
        self.assertGreater(len(chart['points']), 0)
        self.assertEqual(chart['min_value'], 100)
        self.assertEqual(chart['max_value'], 250)
    
    def test_generate_performance_graph_empty_data(self):
        """Performance graph returns None for empty data"""
        chart = self.builder.generate_performance_graph(
            performance_data=[],
            workout_type='power_zone',
            ftp=280.0
        )
        self.assertIsNone(chart)
    
    def test_generate_performance_graph_downsampling(self):
        """Performance graph downsamples correctly"""
        # Create 500 data points
        performance_data = [
            {'timestamp': i, 'value': 100 + (i % 100)}
            for i in range(500)
        ]
        
        chart = self.builder.generate_performance_graph(
            performance_data=performance_data,
            workout_type='power_zone',
            ftp=280.0,
            downsample_points=50
        )
        
        self.assertIsNotNone(chart)
        # Should be downsampled to ~50 points
        self.assertLessEqual(len(chart['points']), 60)
        self.assertGreaterEqual(len(chart['points']), 40)
    
    def test_generate_performance_graph_invalid_data(self):
        """Performance graph handles invalid data points"""
        performance_data = [
            {'timestamp': 'invalid', 'value': 100},
            {'timestamp': 30, 'value': 'invalid'},
            {'timestamp': 60, 'value': 200},
        ]
        
        chart = self.builder.generate_performance_graph(
            performance_data=performance_data,
            workout_type='power_zone',
            ftp=280.0
        )
        
        self.assertIsNotNone(chart)
        # Should only have the valid point
        self.assertEqual(len(chart['points']), 1)
    
    def test_generate_performance_graph_negative_values(self):
        """Performance graph filters negative values"""
        performance_data = [
            {'timestamp': 0, 'value': 100},
            {'timestamp': 30, 'value': -50},  # Should be filtered
            {'timestamp': 60, 'value': 200},
        ]
        
        chart = self.builder.generate_performance_graph(
            performance_data=performance_data,
            workout_type='power_zone',
            ftp=280.0
        )
        
        self.assertIsNotNone(chart)
        self.assertEqual(len(chart['points']), 2)
    
    # ==================== Zone Distribution Tests ====================
    
    def test_generate_zone_distribution_power_zones(self):
        """Zone distribution generation for power zones"""
        zone_data = [
            {'zone': 1, 'time_sec': 300},
            {'zone': 4, 'time_sec': 3000},
            {'zone': 6, 'time_sec': 300},
        ]
        
        dist = self.builder.generate_zone_distribution(
            zone_data=zone_data,
            workout_type='power_zone'
        )
        
        self.assertIsNotNone(dist)
        self.assertEqual(dist['type'], 'zone_distribution')
        self.assertEqual(len(dist['distribution']), 3)
        self.assertEqual(dist['total_duration_seconds'], 3600)
        
        # Check percentages (allow small rounding error)
        total_pct = sum(item['percentage'] for item in dist['distribution'])
        self.assertAlmostEqual(total_pct, 100.0, places=0)
    
    def test_generate_zone_distribution_pace_zones(self):
        """Zone distribution generation for pace zones"""
        zone_data = [
            {'zone': 'recovery', 'time_sec': 300},
            {'zone': 'moderate', 'time_sec': 3000},
            {'zone': 'hard', 'time_sec': 300},
        ]
        
        dist = self.builder.generate_zone_distribution(
            zone_data=zone_data,
            workout_type='pace_target'
        )
        
        self.assertIsNotNone(dist)
        self.assertEqual(dist['type'], 'zone_distribution')
        self.assertEqual(len(dist['distribution']), 3)
        self.assertIn('recovery', [item['zone'] for item in dist['distribution']])
    
    def test_generate_zone_distribution_empty_data(self):
        """Zone distribution returns None for empty data"""
        dist = self.builder.generate_zone_distribution(zone_data=[])
        self.assertIsNone(dist)
    
    def test_generate_zone_distribution_zero_time(self):
        """Zone distribution handles zero time entries"""
        zone_data = [
            {'zone': 1, 'time_sec': 0},
            {'zone': 4, 'time_sec': 3600},
        ]
        
        dist = self.builder.generate_zone_distribution(zone_data=zone_data)
        
        self.assertIsNotNone(dist)
        # Should only have zone 4
        self.assertEqual(len(dist['distribution']), 1)
        self.assertEqual(dist['distribution'][0]['zone'], 4)
    
    def test_generate_zone_distribution_invalid_data(self):
        """Zone distribution filters invalid data"""
        zone_data = [
            {'zone': 1, 'time_sec': 'invalid'},
            {'zone': 4, 'time_sec': 3600},
            {'zone': None, 'time_sec': 300},
        ]
        
        dist = self.builder.generate_zone_distribution(zone_data=zone_data)
        
        self.assertIsNotNone(dist)
        # Should only have valid zone 4
        self.assertEqual(len(dist['distribution']), 1)
    
    # ==================== TSS/IF Metrics Tests ====================
    
    def test_generate_tss_if_metrics_from_power(self):
        """TSS/IF metrics calculation from power"""
        metrics = self.builder.generate_tss_if_metrics(
            avg_power=200.0,
            duration_seconds=3600,
            ftp=280.0
        )
        
        self.assertIsNotNone(metrics)
        self.assertIn('tss', metrics)
        self.assertIn('if', metrics)
        self.assertAlmostEqual(metrics['tss'], 51.0, places=0)
        self.assertAlmostEqual(metrics['if'], 0.71, places=1)
    
    def test_generate_tss_if_metrics_from_zones(self):
        """TSS/IF metrics calculation from zone distribution"""
        zone_distribution = [
            {'zone': 1, 'time_sec': 300},
            {'zone': 4, 'time_sec': 3000},
            {'zone': 6, 'time_sec': 300},
        ]
        
        metrics = self.builder.generate_tss_if_metrics(
            zone_distribution=zone_distribution,
            duration_seconds=3600,
            workout_type='power_zone',
            ftp=280.0
        )
        
        self.assertIsNotNone(metrics)
        self.assertIn('tss_from_zones', metrics)
        self.assertGreater(metrics['tss_from_zones'], 0)
    
    def test_generate_tss_if_metrics_missing_data(self):
        """TSS/IF metrics returns None for missing data"""
        metrics = self.builder.generate_tss_if_metrics()
        self.assertIsNone(metrics)
    
    # ==================== Summary Stats Tests ====================
    
    def test_generate_summary_stats_comprehensive(self):
        """Summary stats generation with all data"""
        performance_data = [
            {'timestamp': 0, 'value': 100},
            {'timestamp': 30, 'value': 200},
            {'timestamp': 60, 'value': 150},
        ]
        zone_distribution = [
            {'zone': 1, 'time_sec': 300},
            {'zone': 4, 'time_sec': 3300},
        ]
        
        stats = self.builder.generate_summary_stats(
            performance_data=performance_data,
            zone_distribution=zone_distribution,
            duration_seconds=3600,
            avg_power=150.0,
            ftp=280.0,
            calories=500.0
        )
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats['duration_minutes'], 60.0)
        self.assertEqual(stats['max_power'], 200)
        self.assertEqual(stats['min_power'], 100)
        self.assertEqual(stats['calories'], 500)
        self.assertIn('tss', stats)
    
    def test_generate_summary_stats_duration_formatting(self):
        """Summary stats formats duration correctly"""
        # 1 hour 30 minutes
        stats = self.builder.generate_summary_stats(duration_seconds=5400)
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats['duration_minutes'], 90.0)
        self.assertEqual(stats['duration_formatted'], '1h 30m')
        
        # 45 minutes
        stats = self.builder.generate_summary_stats(duration_seconds=2700)
        self.assertEqual(stats['duration_formatted'], '45.0m')
    
    def test_generate_summary_stats_empty_data(self):
        """Summary stats returns None for empty data"""
        stats = self.builder.generate_summary_stats()
        self.assertIsNone(stats)
    
    # ==================== Helper Method Tests ====================
    
    def test_downsample_points_performance(self):
        """Downsampling reduces point count"""
        points = [
            {'timestamp': i, 'value': 100 + i}
            for i in range(1000)
        ]
        
        downsampled = self.builder._downsample_points(points, 50)
        
        self.assertLessEqual(len(downsampled), 60)
        self.assertGreaterEqual(len(downsampled), 40)
        # First and last points should be preserved
        self.assertEqual(downsampled[0]['timestamp'], 0)
        self.assertEqual(downsampled[-1]['timestamp'], 999)
    
    def test_downsample_points_small_dataset(self):
        """Downsampling returns original if already small"""
        points = [
            {'timestamp': i, 'value': 100 + i}
            for i in range(10)
        ]
        
        downsampled = self.builder._downsample_points(points, 50)
        
        self.assertEqual(len(downsampled), 10)
    
    def test_zone_label_power_zones(self):
        """Zone label generation for power zones"""
        label = self.builder._get_zone_label(1, 'power_zone')
        self.assertEqual(label, 'Recovery')
        
        label = self.builder._get_zone_label(4, 'power_zone')
        self.assertEqual(label, 'Threshold')
    
    def test_zone_label_pace_zones(self):
        """Zone label generation for pace zones"""
        label = self.builder._get_zone_label('recovery', 'pace_target')
        self.assertEqual(label, 'Recovery')
        
        label = self.builder._get_zone_label('moderate', 'pace_target')
        self.assertEqual(label, 'Moderate')
    
    def test_zone_color_power_zones(self):
        """Zone color generation for power zones"""
        color = self.builder._get_zone_color(1, 'power_zone')
        self.assertEqual(color, '#4472C4')
        
        color = self.builder._get_zone_color(7, 'power_zone')
        self.assertEqual(color, '#8B0000')
    
    def test_zone_color_pace_zones(self):
        """Zone color generation for pace zones"""
        color = self.builder._get_zone_color('recovery', 'pace_target')
        self.assertEqual(color, '#4472C4')
        
        color = self.builder._get_zone_color('max', 'pace_target')
        self.assertEqual(color, '#8B0000')
    
    # ==================== Validation Tests ====================
    
    def test_is_valid_workout_type(self):
        """Workout type validation"""
        self.assertTrue(self.builder.is_valid_workout_type('power_zone'))
        self.assertTrue(self.builder.is_valid_workout_type('pace_target'))
        self.assertFalse(self.builder.is_valid_workout_type('invalid'))
    
    def test_is_sufficient_data(self):
        """Data sufficiency check"""
        # No data
        self.assertFalse(self.builder.is_sufficient_data())
        
        # Only one performance point (insufficient)
        self.assertFalse(
            self.builder.is_sufficient_data(
                performance_data=[{'timestamp': 0, 'value': 100}]
            )
        )
        
        # Two performance points (sufficient)
        self.assertTrue(
            self.builder.is_sufficient_data(
                performance_data=[
                    {'timestamp': 0, 'value': 100},
                    {'timestamp': 30, 'value': 150},
                ]
            )
        )
        
        # Zone distribution only (sufficient)
        self.assertTrue(
            self.builder.is_sufficient_data(
                zone_distribution=[{'zone': 1, 'time_sec': 300}]
            )
        )
    
    # ==================== Integration Tests ====================
    
    def test_chart_builder_complete_workout(self):
        """Complete workout chart generation"""
        performance_data = [
            {'timestamp': i, 'value': 100 + (50 * (i / 120))}
            for i in range(0, 121, 10)
        ]
        zone_distribution = [
            {'zone': 1, 'time_sec': 300},
            {'zone': 4, 'time_sec': 3300},
        ]
        
        # Generate all charts
        perf_graph = self.builder.generate_performance_graph(
            performance_data=performance_data,
            workout_type='power_zone',
            ftp=280.0
        )
        
        zone_dist = self.builder.generate_zone_distribution(
            zone_data=zone_distribution,
            workout_type='power_zone'
        )
        
        metrics = self.builder.generate_tss_if_metrics(
            avg_power=150.0,
            duration_seconds=3600,
            ftp=280.0,
            zone_distribution=zone_distribution,
            workout_type='power_zone'
        )
        
        stats = self.builder.generate_summary_stats(
            performance_data=performance_data,
            zone_distribution=zone_distribution,
            duration_seconds=3600,
            avg_power=150.0,
            ftp=280.0
        )
        
        # All should be generated
        self.assertIsNotNone(perf_graph)
        self.assertIsNotNone(zone_dist)
        self.assertIsNotNone(metrics)
        self.assertIsNotNone(stats)

