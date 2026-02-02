# Core Services

This app contains shared services and utilities used across the PelvicPlanner project.

## Purpose

The `core` app provides reusable business logic, calculations, and utilities that are used by multiple apps (tracker, plans, challenges, workouts, etc.). This follows the DRY (Don't Repeat Yourself) principle and makes the codebase more maintainable.

## Services

### DateRangeService

Located in: `core/services/date_utils.py`

Provides date-related calculations and utilities:

- `sunday_of_current_week(d)` - Get the Sunday of the current week
- `get_period_dates(period, today)` - Get start/end dates for periods (7d, 30d, 90d, all)
- `get_week_boundaries(reference_date)` - Get current week start (Sunday)
- `get_month_boundaries(reference_date)` - Get current and previous month boundaries

**Usage:**
```python
from core.services import DateRangeService

# Get Sunday of current week
sunday = DateRangeService.sunday_of_current_week(date.today())

# Get 7-day period dates
dates = DateRangeService.get_period_dates('7d')
# Returns: {'start_date': ..., 'end_date': ..., 'comparison_start': ..., ...}
```

### FormattingService

Located in: `core/services/formatting.py`

Provides formatting utilities for common data transformations:

- `format_time_seconds(seconds)` - Format seconds as HH:MM:SS or Dd HH:MM:SS
- `decimal_to_mmss(decimal_minutes)` - Convert decimal minutes to MM:SS format
- `pace_str_from_mph(mph)` - Convert MPH to pace string (MM:SS/mi)
- `format_distance(distance, unit)` - Format distance with unit
- `format_percentage(value, decimals)` - Format value as percentage
- `format_number(value, decimals)` - Format number with thousands separator

**Usage:**
```python
from core.services import FormattingService

# Format time
time_str = FormattingService.format_time_seconds(3665)  # "01:01:05"

# Format pace
pace = FormattingService.pace_str_from_mph(6.0)  # "10:00/mi"

# Format percentage
pct = FormattingService.format_percentage(0.755)  # "75.5%"
```

## Testing

All services have comprehensive unit tests in `core/tests.py`.

Run tests:
```bash
python manage.py test core
```

## Future Services

As part of the refactoring plan, these services will be added:

- **ChallengeService** - Challenge-related operations (Phase 3)
- **ZoneCalculatorService** - Cycling and running zone calculations (Phase 4)
- **ActivityToggleService** - Activity completion toggle logic (Phase 5)
- **PlanProcessorService** - Weekly plan processing and display logic (Phase 6)
- **WorkoutStatsService** - Workout statistics calculations (Phase 7)

## Design Principles

1. **Stateless** - Services don't maintain state
2. **Pure Functions** - Same input always produces same output
3. **No Side Effects** - Services don't modify global state or external systems
4. **Well Tested** - Comprehensive unit tests for all methods
5. **Well Documented** - Clear docstrings with examples
6. **Type Hints** - All methods have type annotations

## Import Convention

Import services from the package level:

```python
from core.services import DateRangeService, FormattingService
```

Not from individual modules:
```python
# Don't do this
from core.services.date_utils import DateRangeService
```
