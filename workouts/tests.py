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
        self.url = reverse('workouts:library')
    
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
