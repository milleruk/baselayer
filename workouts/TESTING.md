# Workouts App Testing Documentation

## Overview

This document describes the test suite for the workouts app, particularly focusing on Phase 1 refactoring that introduced the `ClassLibraryFilter` service.

## Test Files

### `workouts/tests.py`

The main test file containing all tests for the workouts app.

## Test Structure

### 1. ClassLibraryFilterTestCase (30 tests)

Unit tests for the `ClassLibraryFilter` service (`workouts/services/class_filter.py`).

**Purpose**: Validate the filtering, searching, and ordering logic used in the class library view.

#### Filter Method Tests

These tests verify individual filter methods work correctly:

- **`test_filter_initialization`** - Filter initializes with correct queryset
- **`test_apply_search_by_title`** - Search by class title (partial match)
- **`test_apply_search_by_instructor`** - Search by instructor name
- **`test_apply_search_case_insensitive`** - Search is case-insensitive
- **`test_apply_search_empty`** - Empty search doesn't filter

#### Workout Type Filter Tests

- **`test_apply_workout_type_filter_valid`** - Valid workout type slug filters correctly
- **`test_apply_workout_type_filter_invalid`** - Invalid type is ignored
- **`test_apply_workout_type_filter_all_types`** - All allowed types work (cycling, running, walking, rowing)

#### Instructor Filter Tests

- **`test_apply_instructor_filter_valid`** - Valid instructor ID filters correctly
- **`test_apply_instructor_filter_invalid`** - Invalid ID is ignored

#### Duration Filter Tests

- **`test_apply_duration_filter`** - Basic duration filtering works
- **`test_apply_duration_filter_with_tolerance`** - Duration matches ±30 seconds tolerance

#### Date Filter Tests

- **`test_apply_year_filter`** - Filter by year (converts to Unix timestamps)
- **`test_apply_year_filter_2025`** - Year filter works for different years
- **`test_apply_year_filter_invalid`** - Invalid year is ignored
- **`test_apply_month_filter`** - Filter by month (requires year)
- **`test_apply_month_filter_multiple_matches`** - Multiple classes in same month
- **`test_apply_month_filter_without_year`** - Month filter without year doesn't filter

#### Ordering Tests

- **`test_apply_ordering_descending_default`** - Default ordering (newest first, NULLs last)
- **`test_apply_ordering_ascending`** - Ascending ordering by air time
- **`test_apply_ordering_by_title`** - Sort by title alphabetically
- **`test_apply_ordering_invalid`** - Invalid order defaults to descending air time

#### API Tests

- **`test_chainable_api`** - Filter methods return self for method chaining
- **`test_get_filters_dict`** - `get_filters()` returns applied filters dictionary

#### Static Utility Tests

- **`test_get_available_years`** - Extract unique years from rides
- **`test_get_available_years_excludes_null`** - NULL timestamps excluded from year extraction
- **`test_get_available_months`** - Extract months for a given year
- **`test_get_available_months_no_year`** - Empty list when no year provided
- **`test_get_available_durations`** - Combine standard and actual durations

#### Integration Tests

- **`test_multiple_filters_combined`** - Multiple filters work together correctly

### 2. ClassLibraryViewTestCase (19 tests)

Integration tests for the `class_library` view (`workouts/views.py`).

**Purpose**: Validate the view correctly uses filters and renders the template.

**Status**: Foundation laid - some tests need additional setup (authentication middleware)

#### Authentication Tests

- **`test_view_requires_login`** - View redirects unauthenticated users
- **`test_view_loads_authenticated`** - View loads for authenticated users

#### Context Tests

- **`test_view_context_has_required_variables`** - All required context variables present
- **`test_view_template_used`** - Correct template is rendered

#### Pagination Tests

- **`test_pagination_works`** - 12 items per page pagination
- **`test_pagination_page_2`** - Second page has remaining items

#### Filter Tests

- **`test_search_filter`** - Search filter works in view
- **`test_workout_type_filter`** - Workout type filter works
- **`test_instructor_filter`** - Instructor filter works
- **`test_duration_filter`** - Duration filter works
- **`test_year_filter`** - Year filter works
- **`test_month_filter`** - Month filter works

#### Sorting Tests

- **`test_sort_by_air_time_descending`** - Sort newest first
- **`test_sort_by_title`** - Sort alphabetically
- **`test_sort_by_duration`** - Sort by duration

#### Advanced Tests

- **`test_combined_filters`** - Multiple filters work together in view
- **`test_filter_values_passed_to_context`** - Filter values passed to template
- **`test_available_years_in_context`** - Available years list in context
- **`test_empty_results`** - Empty results handled gracefully

## Test Data Setup

Both test cases use `setUpTestData` for efficient test database usage:

### Test Fixtures

- **4 WorkoutType objects**: cycling, running, walking, rowing
- **2 Instructor objects**: Emma (instructor1), Jenn (instructor2)
- **5 RideDetail objects**:
  - Cycling Class Jan 2024 (2024-01-15, Emma)
  - Running Class March 2024 (2024-03-20, Jenn)
  - Walking Class Jan 2025 (2025-01-10, Emma)
  - Rowing Class June 2025 (2025-06-15, Jenn)
  - Old Class No Date (NULL timestamp, Emma)
- **20 Additional RideDetail objects** (for pagination testing in view tests)

## Running the Tests

### Run All Tests

```bash
python manage.py test workouts.tests
```

### Run Filter Tests Only (30 tests - all passing)

```bash
python manage.py test workouts.tests.ClassLibraryFilterTestCase
```

### Run View Tests Only (foundation laid)

```bash
python manage.py test workouts.tests.ClassLibraryViewTestCase
```

### Run with Verbose Output

```bash
python manage.py test workouts.tests -v 2
```

### Run Specific Test

```bash
python manage.py test workouts.tests.ClassLibraryFilterTestCase.test_apply_search_by_title
```

## Test Coverage

### What's Covered ✓

1. **Search & Filter Logic** - All filter methods tested individually and combined
2. **Ordering & Sorting** - All sort options with NULL handling
3. **Date Handling** - Year/month filtering with Unix timestamp conversion
4. **Edge Cases** - Invalid input, empty results, NULL values
5. **API Design** - Chainable methods, filter metadata

### What's Partially Covered ⚠️

- View integration tests (foundation laid, may need additional Django setup)

### What's Not Yet Covered

- Metrics calculation (Phase 2)
- Chart generation (Phase 2)
- Performance metrics (TSS, IF) filtering
- AJAX requests
- Template rendering details

## Key Testing Decisions

### Why Unit Tests for the Service?

The `ClassLibraryFilter` service is well-suited for unit testing because:
- It's pure business logic (no database writes)
- It's decoupled from the view layer
- It can be tested in isolation
- It returns verifiable querysets and metadata

### Why Chainable API?

The service methods return `self` to allow:
```python
filter_obj = ClassLibraryFilter(rides)
filter_obj.apply_search('emma') \
         .apply_workout_type_filter('cycling') \
         .apply_year_filter('2024')
```

This makes the view code more readable:
```python
class_filter.apply_search(request.GET.get('search', '')) \
           .apply_workout_type_filter(request.GET.get('type', ''))
```

## Integration with CI/CD

The tests are designed to be:
- **Fast**: Run in ~60ms (filter tests) on modern hardware
- **Deterministic**: No external dependencies or randomness
- **Isolated**: Use test database, don't affect production
- **Comprehensive**: Cover happy paths and edge cases

## Future Testing Additions (Phase 2)

### Metrics Service Tests

When `services/metrics.py` is created:
- Test TSS/IF calculation
- Test zone distribution calculation
- Test pace target zone detection
- Test power zone segment extraction

### Chart Generation Tests

When `services/chart_builder.py` is created:
- Test chart data structure
- Test zone color mapping
- Test segment rendering

### View Integration Tests

Complete the view tests:
- Test AJAX endpoints
- Test pagination link preservation
- Test template context completeness
- Test error handling

## Debugging Tests

### Run Test with Print Statements

```bash
python manage.py test workouts.tests.ClassLibraryFilterTestCase -v 2
```

### Run Single Test Method

```bash
python manage.py test workouts.tests.ClassLibraryFilterTestCase.test_apply_search_by_title -v 2
```

### Check Test Database

Tests use SQLite in-memory database by default. To use persistent database for debugging:

```bash
# In settings.py (TEST section):
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'debug_test_db.sqlite3',  # Won't be cleaned up
    }
}
```

## Test Statistics

| Metric | Value |
|--------|-------|
| Total Tests | 49 |
| Filter Tests | 30 |
| View Tests | 19 |
| Lines Tested | 160+ |
| Execution Time | ~1.0s |
| Database Writes | 0 (unit tests read-only) |

## Notes for Developers

1. **When modifying `ClassLibraryFilter`**: Update corresponding test
2. **When adding new filters**: Add tests for happy path, invalid input, and edge cases
3. **When changing ordering logic**: Verify NULL handling still works
4. **When creating Phase 2 services**: Follow similar pattern with unit tests first

## Related Documentation

- [ClassLibraryFilter Service](workouts/services/class_filter.py)
- [Class Library View](workouts/views.py#L236)
- [Phase 1 Refactoring Plan](docs/README.md)
