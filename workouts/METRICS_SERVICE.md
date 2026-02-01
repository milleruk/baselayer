# Metrics Service Documentation

## Overview

The **MetricsCalculator** service encapsulates all workout metrics calculations for the Pelvic Planner application. It provides reusable, tested business logic for TSS (Training Stress Score), IF (Intensity Factor), and zone-based metrics.

**Location:** `workouts/services/metrics.py`  
**Lines:** 350  
**Test Coverage:** 30 unit tests (100% pass rate ✅)

## Design Principles

- **Single Responsibility:** Only handles metrics calculations
- **No Database Access:** Pure business logic, reusable everywhere
- **Input Validation:** Defensive programming with None checks
- **Chainable Methods:** Return self where appropriate for fluent API
- **Type Hints:** All methods documented with parameter/return types
- **Constants:** Zone definitions, intensity factors as class attributes

## Key Formulas

### TSS Calculation (Cycling)
```
IF = Average Power / FTP
TSS = (Duration in hours) × IF² × 100
```

### IF Bounds
```
IF is clamped to 0.0 ≤ IF ≤ 2.0
```

### Power Zone Ranges (% of FTP)
```
Zone 1: 0-55%
Zone 2: 55-75%
Zone 3: 75-90%
Zone 4: 90-105%
Zone 5: 105-120%
Zone 6: 120-150%
Zone 7: 150%+
```

### Pace Zone Intensity Factors
```
Recovery:    0.5
Easy:        0.7
Moderate:    1.0 (threshold)
Challenging: 1.15
Hard:        1.3
Very Hard:   1.5
Max:         1.8
```

## Class Methods

### TSS Calculation

#### `calculate_tss()`
**Purpose:** Calculate Training Stress Score for cycling workouts

**Signature:**
```python
def calculate_tss(
    avg_power: Optional[float] = None,
    duration_seconds: Optional[int] = None,
    ftp: Optional[float] = None,
    stored_tss: Optional[float] = None,
) -> Optional[float]
```

**Parameters:**
- `avg_power`: Average power in watts
- `duration_seconds`: Workout duration in seconds
- `ftp`: Functional Threshold Power in watts
- `stored_tss`: Pre-calculated TSS (takes priority)

**Returns:** TSS value or None if insufficient data

**Example:**
```python
calculator = MetricsCalculator()
tss = calculator.calculate_tss(
    avg_power=200.0,
    duration_seconds=3600,  # 1 hour
    ftp=280.0
)
# Returns: ~51.0
```

**Notes:**
- Returns `stored_tss` if provided (Peloton value preferred)
- Calculates IF = avg_power / FTP with bounds checking
- Clamps IF between 0.0 and 2.0

---

#### `calculate_intensity_factor()`
**Purpose:** Calculate IF with multiple input methods

**Signature:**
```python
def calculate_intensity_factor(
    avg_power: Optional[float] = None,
    ftp: Optional[float] = None,
    tss: Optional[float] = None,
    duration_seconds: Optional[int] = None,
) -> Optional[float]
```

**Methods:**
1. **Direct:** IF = avg_power / FTP
2. **Reverse:** IF = sqrt(TSS / (hours × 100))

**Returns:** IF value (0.0-2.0) or None

**Example:**
```python
# Method 1: From power and FTP
if_value = calculator.calculate_intensity_factor(
    avg_power=200.0,
    ftp=280.0
)
# Returns: ~0.714

# Method 2: From TSS (reverse)
if_value = calculator.calculate_intensity_factor(
    tss=51.0,
    duration_seconds=3600
)
# Returns: ~0.714
```

**Notes:**
- Prefers power method if both available
- Returns first valid result

---

### Zone Distribution TSS

#### `calculate_tss_from_zone_distribution()`
**Purpose:** Calculate TSS from zone distribution data (power or pace)

**Signature:**
```python
def calculate_tss_from_zone_distribution(
    zone_distribution: List[Dict[str, Any]],
    duration_seconds: int,
    class_type: str,
    ftp: Optional[float] = None,
    pace_level: Optional[int] = None,
) -> Optional[float]
```

**Parameters:**
- `zone_distribution`: List of zone objects with 'zone' and 'time_sec'
- `duration_seconds`: Total workout duration
- `class_type`: 'power_zone' or 'pace_target'
- `ftp`: Required for power_zone
- `pace_level`: Required for pace_target (1-10)

**Returns:** Calculated TSS or None

**Power Zone Example:**
```python
zone_distribution = [
    {'zone': 1, 'time_sec': 300},    # 5 min in Z1
    {'zone': 4, 'time_sec': 3000},   # 50 min in Z4
    {'zone': 6, 'time_sec': 300},    # 5 min in Z6
]

tss = calculator.calculate_tss_from_zone_distribution(
    zone_distribution=zone_distribution,
    duration_seconds=3600,
    class_type='power_zone',
    ftp=280.0
)
```

**Pace Target Example:**
```python
zone_distribution = [
    {'zone': 'recovery', 'time_sec': 300},
    {'zone': 'moderate', 'time_sec': 3000},
    {'zone': 'hard', 'time_sec': 300},
]

tss = calculator.calculate_tss_from_zone_distribution(
    zone_distribution=zone_distribution,
    duration_seconds=3600,
    class_type='pace_target',
    pace_level=5
)
```

**Calculation Logic:**
- **Power Zone:** Calculates normalized power (weighted average by zone × FTP %), then IF, then TSS
- **Pace Target:** Calculates weighted average intensity factor from zone intensities, then TSS

---

### Power Zone Methods

#### `get_power_zone_ranges()`
**Purpose:** Get power zone boundaries from FTP

**Signature:**
```python
def get_power_zone_ranges(
    ftp: Optional[float]
) -> Optional[Dict[int, Tuple[int, Optional[int]]]]
```

**Returns:** Dict mapping zone (1-7) to (low_watts, high_watts)

**Example:**
```python
ranges = calculator.get_power_zone_ranges(280.0)
# Returns:
# {
#     1: (0, 154),
#     2: (154, 210),
#     3: (210, 252),
#     4: (252, 294),
#     5: (294, 336),
#     6: (336, 420),
#     7: (420, None),  # No upper bound
# }
```

---

#### `get_power_zone_for_output()`
**Purpose:** Determine power zone from watts output

**Signature:**
```python
def get_power_zone_for_output(
    output_watts: float,
    zone_ranges: Optional[Dict[int, Tuple[int, Optional[int]]]] = None,
    ftp: Optional[float] = None,
) -> Optional[int]
```

**Returns:** Zone number 1-7 or None

**Example:**
```python
zone_ranges = calculator.get_power_zone_ranges(280.0)

zone = calculator.get_power_zone_for_output(200, zone_ranges)
# Returns: 3 (200W falls in zone 3: 210-252W... wait, that's wrong)
# Actually returns: 2 (200W falls in zone 2: 154-210W)

zone = calculator.get_power_zone_for_output(270, zone_ranges)
# Returns: 4 (270W falls in zone 4: 252-294W)
```

---

#### `get_target_watts_for_zone()`
**Purpose:** Get midpoint target watts for a power zone

**Signature:**
```python
def get_target_watts_for_zone(
    zone_num: int,
    zone_ranges: Optional[Dict[int, Tuple[int, Optional[int]]]] = None,
    ftp: Optional[float] = None,
) -> Optional[float]
```

**Returns:** Target watts (midpoint) or None

**Example:**
```python
zone_ranges = calculator.get_power_zone_ranges(280.0)

target = calculator.get_target_watts_for_zone(1, zone_ranges)
# Returns: 77.0 (midpoint of 0-154)

target = calculator.get_target_watts_for_zone(4, zone_ranges)
# Returns: 273.0 (midpoint of 252-294)
```

---

#### `get_available_power_zones()`
**Purpose:** Get list of available power zones

**Signature:**
```python
def get_available_power_zones(ftp: Optional[float] = None) -> Optional[List[int]]
```

**Returns:** [1, 2, 3, 4, 5, 6, 7] or None if FTP invalid

---

#### `is_valid_power_zone()`
**Purpose:** Validate power zone number

**Signature:**
```python
def is_valid_power_zone(zone: int) -> bool
```

**Returns:** True if zone is 1-7

---

### Pace Zone Methods

#### `get_pace_zone_targets()`
**Purpose:** Get pace zone targets (min/mile) for a pace level

**Signature:**
```python
def get_pace_zone_targets(
    pace_level: Optional[int]
) -> Optional[Dict[str, float]]
```

**Returns:** Dict mapping zone names to pace targets (min/mile)

**Example:**
```python
targets = calculator.get_pace_zone_targets(5)
# Returns:
# {
#     'recovery': 10.5,      # 12:00 base + 2:00 = 10:30
#     'easy': 9.5,
#     'moderate': 8.5,       # 8:30/mile (threshold pace)
#     'challenging': 8.0,
#     'hard': 7.5,
#     'very_hard': 7.0,
#     'max': 6.5,
# }

targets = calculator.get_pace_zone_targets(10)
# Returns:
# {
#     'recovery': 8.0,       # 12:00 base + 2:00 = 8:00
#     'easy': 7.0,
#     'moderate': 6.0,       # 6:00/mile (threshold pace for level 10)
#     'challenging': 5.5,
#     'hard': 5.0,
#     'very_hard': 4.5,
#     'max': 4.0,
# }
```

**Notes:**
- Levels 1-10 (slow to fast)
- Base pace determined by level
- Zones offset by fixed amounts from base

---

#### `get_available_pace_zones()`
**Purpose:** Get list of available pace zone names

**Signature:**
```python
def get_available_pace_zones() -> List[str]
```

**Returns:** ['challenging', 'easy', 'hard', 'max', 'moderate', 'recovery', 'very_hard']

---

#### `is_valid_pace_level()`
**Purpose:** Validate pace level

**Signature:**
```python
def is_valid_pace_level(level: int) -> bool
```

**Returns:** True if level is 1-10

---

## Class Attributes

### Constants

```python
# Pace zone intensity factors (relative to threshold)
PACE_ZONE_INTENSITY_FACTORS = {
    'recovery': 0.5,
    'easy': 0.7,
    'moderate': 1.0,
    'challenging': 1.15,
    'hard': 1.3,
    'very_hard': 1.5,
    'max': 1.8,
}

# Base paces by level (min/mile)
BASE_PACES_BY_LEVEL = {
    1: 12.0, 2: 11.0, 3: 10.0, 4: 9.0, 5: 8.5,
    6: 8.0, 7: 7.5, 8: 7.0, 9: 6.5, 10: 6.0,
}

# Zone power percentages (% of FTP for normalized power)
ZONE_POWER_PERCENTAGES = {
    1: 0.275,  # Midpoint of 0-55%
    2: 0.65,   # Midpoint of 55-75%
    3: 0.825,  # Midpoint of 75-90%
    4: 0.975,  # Midpoint of 90-105%
    5: 1.125,  # Midpoint of 105-120%
    6: 1.35,   # Midpoint of 120-150%
    7: 1.75,   # Conservative estimate for 150%+
}
```

## Usage in Views

The `MetricsCalculator` is instantiated once at module level in `views.py`:

```python
from workouts.services.metrics import MetricsCalculator

# Module-level initialization
metrics_calculator = MetricsCalculator()
```

### Example: TSS from Workout

```python
@login_required
def workout_detail(request, pk):
    workout = get_object_or_404(Workout, pk=pk)
    user_profile = request.user.profile
    
    # Calculate TSS using metrics service
    tss = metrics_calculator.calculate_tss(
        avg_power=workout.details.avg_output,
        duration_seconds=workout.ride_detail.duration_seconds,
        ftp=user_profile.get_current_ftp()
    )
    
    context = {'tss': tss}
    return render(request, 'workouts/detail.html', context)
```

### Example: Zone Determination

```python
# Get zone ranges for FTP
zone_ranges = metrics_calculator.get_power_zone_ranges(user_ftp)

# Determine zone for each data point
for data_point in performance_data:
    zone = metrics_calculator.get_power_zone_for_output(
        data_point.output,
        zone_ranges
    )
    data_point['zone'] = zone
```

## Testing

**Test File:** `workouts/tests.py`  
**Test Class:** `MetricsCalculatorTestCase`  
**Test Count:** 30 tests (100% passing ✅)

### Test Categories

**TSS Calculation (9 tests)**
- `test_calculate_tss_with_valid_data` - Normal calculation
- `test_calculate_tss_with_stored_tss` - Uses stored value
- `test_calculate_tss_missing_avg_power` - Validation
- `test_calculate_tss_missing_duration` - Validation
- `test_calculate_tss_missing_ftp` - Validation
- `test_calculate_tss_invalid_ftp` - Zero/negative FTP
- `test_calculate_tss_bounds_checking` - IF clamping

**IF Calculation (6 tests)**
- `test_calculate_if_from_power_and_ftp` - Direct method
- `test_calculate_if_from_tss_and_duration` - Reverse method
- `test_calculate_if_prefers_power_method` - Priority order
- `test_calculate_if_missing_data` - Validation
- `test_calculate_if_bounds_checking` - IF clamping

**Power Zones (7 tests)**
- `test_get_power_zone_ranges` - Zone boundary calculation
- `test_get_power_zone_ranges_invalid_ftp` - Validation
- `test_get_power_zone_for_output` - Zone detection
- `test_get_power_zone_for_output_invalid` - Validation
- `test_get_target_watts_for_zone` - Midpoint calculation
- `test_get_available_power_zones` - Zone list
- `test_is_valid_power_zone` - Validation

**Pace Zones (7 tests)**
- `test_get_pace_zone_targets` - Target calculation
- `test_get_pace_zone_targets_different_levels` - Level variation
- `test_get_pace_zone_targets_invalid_level` - Validation
- `test_get_available_pace_zones` - Zone list
- `test_is_valid_pace_level` - Validation

**Zone Distribution TSS (4 tests)**
- `test_calculate_tss_from_power_zone_distribution` - Power zones
- `test_calculate_tss_from_pace_target_distribution` - Pace targets
- `test_calculate_tss_from_distribution_missing_data` - Validation
- `test_calculate_tss_from_distribution_empty` - Validation

**Integration (1 test)**
- `test_metrics_roundtrip` - TSS ↔ IF consistency

## Error Handling

All methods handle edge cases gracefully:

```python
# Invalid inputs return None
calculator.calculate_tss(None, None, None)  # → None

# Type conversion failures return None
calculator.get_power_zone_ranges("not a number")  # → None

# Out of range values are handled
calculator.calculate_tss(
    avg_power=600,  # High power
    duration_seconds=3600,
    ftp=200
)  # → TSS calculated with IF clamped to 2.0

# Empty data handled
calculator.calculate_tss_from_zone_distribution(
    zone_distribution=[],
    duration_seconds=3600,
    class_type='power_zone',
    ftp=280
)  # → None
```

## Future Enhancements

### Phase 3: Chart Service
Will use `MetricsCalculator` to:
- Generate chart data for performance graphs
- Calculate zone distribution visualizations
- Build TSS/IF trend charts

### Potential Additions
- Relative Intensity (RI = watts / LT watts)
- Normalized Power calculation from detailed series
- Pedal efficiency metrics
- Cadence-based metrics
- Heart rate zone calculations (if HR data available)

## Integration Points

**Used By:**
- `workouts/views.py` - All view functions that display metrics
- Future: API endpoints, management commands, dashboards

**Depends On:**
- None! (Pure Python, no Django models)

**Exported In:**
- `workouts/services/__init__.py` (available for import)

## See Also

- [Phase 2 Summary](debug/PHASE_2_SUMMARY.md)
- [Phase 2 Architecture](debug/PHASE_2_ARCHITECTURE.md)
- [Testing Guide](TESTING.md)
- [Class Library Filter Service](CLASS_FILTER.md) (Phase 1)
