# Quick Test Reference

## Run Tests

```bash
# All tests
python manage.py test workouts.tests

# Filter service tests only (all passing)
python manage.py test workouts.tests.ClassLibraryFilterTestCase

# View tests 
python manage.py test workouts.tests.ClassLibraryViewTestCase

# Verbose output
python manage.py test workouts.tests -v 2

# Single test
python manage.py test workouts.tests.ClassLibraryFilterTestCase.test_apply_search_by_title
```

## Test Stats

- **Total Tests**: 49
- **Filter Tests**: 30 ✅ (all passing)
- **View Tests**: 19 (foundation laid)
- **Execution Time**: ~1 second

## What Gets Tested

### ClassLibraryFilter Service (workouts/services/class_filter.py)

| Category | Tests | Status |
|----------|-------|--------|
| Search/Filter | 5 | ✅ |
| Workout Type | 3 | ✅ |
| Instructor | 2 | ✅ |
| Duration | 2 | ✅ |
| Date (Year/Month) | 6 | ✅ |
| Ordering | 4 | ✅ |
| API Methods | 2 | ✅ |
| Static Utils | 5 | ✅ |
| Combined | 1 | ✅ |

### Class Library View (workouts/views.py)

| Category | Tests | Status |
|----------|-------|--------|
| Authentication | 2 | 🏗️ |
| Context | 2 | 🏗️ |
| Pagination | 2 | 🏗️ |
| Filters | 6 | 🏗️ |
| Sorting | 3 | 🏗️ |
| Advanced | 4 | 🏗️ |

✅ = All passing | 🏗️ = Foundation laid

## Test Examples

### Running a Search Filter Test

```python
def test_apply_search_by_instructor(self):
    filter_obj = ClassLibraryFilter(self.base_queryset)
    filter_obj.apply_search('Emma')
    results = filter_obj.get_queryset()
    self.assertEqual(results.count(), 3)
```

### Running Combined Filter Test

```python
def test_multiple_filters_combined(self):
    filter_obj = ClassLibraryFilter(self.base_queryset)
    filter_obj.apply_workout_type_filter('cycling')
    filter_obj.apply_instructor_filter(self.instructor1.id)
    filter_obj.apply_year_filter('2024')
    
    results = filter_obj.get_queryset()
    self.assertEqual(results.count(), 2)
```

## Adding New Tests

1. Add test method to appropriate TestCase class
2. Follow naming: `test_<feature>_<scenario>`
3. Use setUpTestData for shared fixtures
4. Test happy path + edge cases
5. Run with `-v 2` for detailed output

## Common Test Patterns

```python
# Basic filter test
filter_obj = ClassLibraryFilter(self.base_queryset)
filter_obj.apply_search('query')
results = filter_obj.get_queryset()
self.assertEqual(results.count(), expected_count)

# Chained filters
filter_obj = ClassLibraryFilter(self.base_queryset)
(filter_obj
 .apply_workout_type_filter('cycling')
 .apply_year_filter('2024')
 .apply_ordering('-original_air_time'))
results = filter_obj.get_queryset()

# Check filters returned
filters = filter_obj.get_filters()
self.assertEqual(filters['search'], 'query')
```

## Test Data Available

- **4 Workout Types**: cycling, running, walking, rowing
- **2 Instructors**: Emma (3 rides), Jenn (2 rides)
- **5 Base Rides**: various years (2024, 2025), durations, instructors
- **20 Additional Rides**: for pagination testing

Access in tests via:
```python
self.base_queryset = RideDetail.objects.all()
self.instructor1  # Emma
self.instructor2  # Jenn
self.cycling_type
self.running_type
```

## Debugging Tips

```bash
# Verbose output shows each test
python manage.py test workouts.tests -v 2

# Stop at first failure
python manage.py test workouts.tests --failfast

# Run with pdb on failure
python manage.py test workouts.tests --pdb

# Keep test database for inspection
python manage.py test workouts.tests --keepdb
```

## Phase 2 Test Plans

- [ ] Metrics service tests (TSS, IF calculation)
- [ ] Chart generation tests
- [ ] View integration test completion
- [ ] Performance tests for large datasets
- [ ] Cache invalidation tests
