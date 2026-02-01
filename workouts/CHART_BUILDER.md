# ChartBuilder Service - Complete API Reference

**Service Location:** `workouts/services/chart_builder.py`  
**Status:** ✅ Production Ready  
**Test Coverage:** 25 tests, 100% passing  

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Methods](#core-methods)
3. [Validation Methods](#validation-methods)
4. [Helper Methods](#helper-methods)
5. [Constants](#constants)
6. [Data Structures](#data-structures)
7. [Error Handling](#error-handling)
8. [Examples](#examples)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```python
from workouts.services.chart_builder import ChartBuilder

# Create instance (do once per application)
chart_builder = ChartBuilder()
```

### Basic Usage

```python
# Generate performance graph
chart_data = chart_builder.generate_performance_graph(
    performance_data=workout.performance_graph,
    workout_type='power_zone',
    ftp=280.0
)

# Use in template
context = {
    'chart_data': chart_data,
}
return render(request, 'template.html', context)
```

### In a View Function

```python
from workouts.services.chart_builder import ChartBuilder

chart_builder = ChartBuilder()  # Module level

def workout_detail(request, workout_id):
    workout = Workout.objects.get(id=workout_id)
    performance_data = json.loads(workout.performance_graph)
    
    # Generate all charts
    graph = chart_builder.generate_performance_graph(
        performance_data=performance_data,
        workout_type=workout.workout_type,
        ftp=request.user.userprofile.ftp
    )
    
    zones = chart_builder.generate_zone_distribution(
        zone_data=json.loads(workout.zone_distribution),
        workout_type=workout.workout_type
    )
    
    stats = chart_builder.generate_summary_stats(
        performance_data=performance_data,
        zone_distribution=json.loads(workout.zone_distribution),
        duration_seconds=workout.duration_seconds,
        avg_power=workout.avg_power,
        ftp=request.user.userprofile.ftp,
        calories=workout.calories
    )
    
    return render(request, 'workout_detail.html', {
        'workout': workout,
        'performance_graph': graph,
        'zone_distribution': zones,
        'summary_stats': stats,
    })
```

---

## Core Methods

### 1. generate_performance_graph()

Generates performance data for line/area charts showing watts/pace over time with zone coloring.

**Signature:**
```python
def generate_performance_graph(
    self,
    performance_data: list[dict],
    workout_type: str = 'power_zone',
    ftp: float = 200.0,
    pace_level: str = None,
    downsample_points: int = 120,
) -> dict:
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `performance_data` | list[dict] | ✓ | — | Array of {timestamp, output} points |
| `workout_type` | str | ✗ | `'power_zone'` | `'power_zone'` or `'pace_target'` |
| `ftp` | float | ✗ | 200.0 | FTP in watts (for power zones only) |
| `pace_level` | str | ✗ | None | Pace level name (for pace workouts) |
| `downsample_points` | int | ✗ | 120 | Max points in output (None = no downsampling) |

**Input Format:**
```python
performance_data = [
    {'timestamp': 0, 'output': 100},      # start of workout
    {'timestamp': 30, 'output': 150},     # 30 seconds in, 150W
    {'timestamp': 60, 'output': 175},     # 1 minute in, 175W
    # ... more points
]
```

**Returns:**
```python
{
    'type': 'performance_graph',
    'workout_type': 'power_zone',
    'points': [
        {
            'timestamp': 0,        # Unix timestamp or seconds
            'value': 100,          # Power in watts or pace
            'zone': 2,             # Zone number (1-7)
        },
        # ... up to ~120 points (downsampled)
    ],
    'zones': {
        1: 'Recovery',
        2: 'Endurance',
        3: 'Tempo',
        4: 'Lactate Threshold',
        5: 'VO2 Max',
        6: 'Anaerobic',
        7: 'Maximum',
    },
    'colors': {
        1: '#4472C4',  # Blue
        2: '#70AD47',  # Green
        3: '#FFC000',  # Yellow
        4: '#FF6600',  # Orange
        5: '#C00000',  # Red
        6: '#7030A0',  # Purple
        7: '#330000',  # Dark Red
    },
    'min_value': 100,     # Minimum watts/pace
    'max_value': 250,     # Maximum watts/pace
    'message': None,      # Error message if applicable
}
```

**Examples:**

**Power Zone Workout:**
```python
chart_data = chart_builder.generate_performance_graph(
    performance_data=[
        {'timestamp': 0, 'output': 100},
        {'timestamp': 30, 'output': 150},
        {'timestamp': 60, 'output': 200},
        # ... many points
    ],
    workout_type='power_zone',
    ftp=280.0
)
# Returns performance graph with zones based on FTP
```

**Pace Target Workout:**
```python
chart_data = chart_builder.generate_performance_graph(
    performance_data=[
        {'timestamp': 0, 'output': 8.5},   # pace in min/mile
        {'timestamp': 30, 'output': 8.2},
        {'timestamp': 60, 'output': 8.0},
        # ... many points
    ],
    workout_type='pace_target',
    pace_level='Moderate'
)
# Returns performance graph with pace zones
```

**Large Dataset (Auto Downsampling):**
```python
# 5000 points input
chart_data = chart_builder.generate_performance_graph(
    performance_data=big_dataset,  # 5000 points
    workout_type='power_zone',
    ftp=280.0
    # downsample_points=120 (default)
)
# Returns ~120 points (downsampled for performance)
```

**Disable Downsampling:**
```python
chart_data = chart_builder.generate_performance_graph(
    performance_data=data,
    workout_type='power_zone',
    ftp=280.0,
    downsample_points=None  # Return ALL points
)
# Returns exact number of valid points
```

**Usage in Template:**
```html
<canvas id="performanceChart"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    const chartData = {{ performance_graph|safe }};
    
    new Chart(document.getElementById('performanceChart'), {
        type: 'line',
        data: {
            labels: chartData.points.map(p => p.timestamp),
            datasets: [{
                label: 'Power Output (Watts)',
                data: chartData.points.map(p => ({
                    x: p.timestamp,
                    y: p.value,
                    zone: p.zone
                })),
                backgroundColor: 'rgba(68, 114, 196, 0.1)',
                borderColor: 'rgba(68, 114, 196, 1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Workout Performance Graph'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    min: chartData.min_value,
                    max: chartData.max_value
                }
            }
        }
    });
</script>
```

---

### 2. generate_zone_distribution()

Generates data for pie/donut charts showing time spent in each zone.

**Signature:**
```python
def generate_zone_distribution(
    self,
    zone_data: dict[int, dict],
    workout_type: str = 'power_zone',
    total_duration_seconds: int = None,
) -> dict:
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `zone_data` | dict[int, dict] | ✓ | — | Zone data: {1: {output: [...], time_sec: 123}, ...} |
| `workout_type` | str | ✗ | `'power_zone'` | Chart type (determines zone names) |
| `total_duration_seconds` | int | ✗ | None | Calculated from zone_data if not provided |

**Input Format:**
```python
zone_data = {
    1: {'output': [100, 105], 'time_sec': 300},  # 5 min in zone 1
    2: {'output': [140, 145], 'time_sec': 1200}, # 20 min in zone 2
    3: {'output': [180, 190], 'time_sec': 900},  # 15 min in zone 3
    # ... zones up to 7
}
```

**Returns:**
```python
{
    'type': 'zone_distribution',
    'workout_type': 'power_zone',
    'distribution': [
        {
            'zone': 1,
            'label': 'Recovery',
            'time_seconds': 300,
            'time_minutes': 5.0,
            'percentage': 8.3,
            'color': '#4472C4',
        },
        {
            'zone': 2,
            'label': 'Endurance',
            'time_seconds': 1200,
            'time_minutes': 20.0,
            'percentage': 33.3,
            'color': '#70AD47',
        },
        # ... one entry per zone with data
    ],
    'total_duration_seconds': 3600,
    'total_duration_minutes': 60.0,
    'message': None,
}
```

**Examples:**

**Basic Usage:**
```python
zone_dist = chart_builder.generate_zone_distribution(
    zone_data=workout.zone_distribution,
    workout_type='power_zone'
)

# Use in pie chart
context = {
    'zone_labels': [z['label'] for z in zone_dist['distribution']],
    'zone_percentages': [z['percentage'] for z in zone_dist['distribution']],
    'zone_colors': [z['color'] for z in zone_dist['distribution']],
}
```

**With Total Duration:**
```python
zone_dist = chart_builder.generate_zone_distribution(
    zone_data=zone_dict,
    workout_type='power_zone',
    total_duration_seconds=3600  # 1 hour
)
```

**Template Usage (Chart.js):**
```html
<canvas id="zoneChart"></canvas>

<script>
    const zoneData = {{ zone_distribution|safe }};
    
    new Chart(document.getElementById('zoneChart'), {
        type: 'doughnut',
        data: {
            labels: zoneData.distribution.map(z => z.label),
            datasets: [{
                data: zoneData.distribution.map(z => z.percentage),
                backgroundColor: zoneData.distribution.map(z => z.color),
            }]
        },
        options: {
            plugins: {
                title: {
                    display: true,
                    text: 'Time in Each Zone'
                },
                legend: {
                    position: 'right'
                }
            }
        }
    });
</script>
```

---

### 3. generate_tss_if_metrics()

Generates TSS (Training Stress Score) and IF (Intensity Factor) metrics.

**Signature:**
```python
def generate_tss_if_metrics(
    self,
    avg_power: float = None,
    duration_seconds: int = None,
    ftp: float = 200.0,
    zone_distribution: dict[int, dict] = None,
    workout_type: str = 'power_zone',
) -> dict:
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `avg_power` | float | ✗ | None | Average power in watts |
| `duration_seconds` | int | ✗ | None | Workout duration in seconds |
| `ftp` | float | ✗ | 200.0 | Functional Threshold Power (watts) |
| `zone_distribution` | dict[int, dict] | ✗ | None | Zone data for TSS calculation |
| `workout_type` | str | ✗ | `'power_zone'` | Workout type (power or pace) |

**Returns:**
```python
{
    'tss': 51.0,               # Training Stress Score
    'if': 0.71,                # Intensity Factor (0.0 - 2.0)
    'estimation_method': 'direct'  # 'direct' or 'from_zones'
}
```

**Calculation Methods:**

**Method 1: Direct (from avg_power)**
```
IF = avg_power / FTP
TSS = (duration_minutes * IF * normalized_power_factor) / 100
```

**Method 2: From Zone Distribution (more accurate)**
```
TSS = sum(zone_tss for each zone)
IF = sqrt(TSS / (duration_minutes * 100)) / 0.75
```

**Examples:**

**Direct Calculation:**
```python
metrics = chart_builder.generate_tss_if_metrics(
    avg_power=175.0,
    duration_seconds=3600,
    ftp=280.0
)
# Returns: {'tss': 51.0, 'if': 0.625, 'estimation_method': 'direct'}
```

**From Zone Distribution (More Accurate):**
```python
metrics = chart_builder.generate_tss_if_metrics(
    zone_distribution={
        1: {'output': [...], 'time_sec': 300},
        2: {'output': [...], 'time_sec': 1200},
        3: {'output': [...], 'time_sec': 2100},
    },
    ftp=280.0
)
# Returns: {'tss': 51.5, 'if': 0.71, 'estimation_method': 'from_zones'}
```

**In Context:**
```python
def workout_detail(request, id):
    workout = Workout.objects.get(id=id)
    
    metrics = chart_builder.generate_tss_if_metrics(
        avg_power=workout.avg_power,
        duration_seconds=workout.duration_seconds,
        ftp=request.user.userprofile.ftp
    )
    
    context = {
        'tss': metrics['tss'],
        'if': metrics['if'],
    }
    return render(request, 'template.html', context)
```

---

### 4. generate_summary_stats()

Generates comprehensive workout summary statistics.

**Signature:**
```python
def generate_summary_stats(
    self,
    performance_data: list[dict],
    zone_distribution: dict[int, dict] = None,
    duration_seconds: int = None,
    avg_power: float = None,
    ftp: float = 200.0,
    calories: float = None,
) -> dict:
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `performance_data` | list[dict] | ✓ | — | Performance points {timestamp, output} |
| `zone_distribution` | dict[int, dict] | ✗ | None | Zone time breakdown |
| `duration_seconds` | int | ✗ | None | Total duration (calculated if None) |
| `avg_power` | float | ✗ | None | Average power (calculated if None) |
| `ftp` | float | ✗ | 200.0 | FTP for calculations |
| `calories` | float | ✗ | None | Energy expended |

**Returns:**
```python
{
    'duration_minutes': 60.0,
    'duration_formatted': '1h 0m',
    'max_power': 250,
    'min_power': 100,
    'avg_power': 175,
    'tss': 51.0,
    'if': 0.71,
    'calories': 500,
    'zone_times': {
        1: 5.0,   # minutes in each zone
        2: 20.0,
        3: 15.0,
        4: 15.0,
        5: 5.0,
    }
}
```

**Examples:**

**Complete Stats:**
```python
stats = chart_builder.generate_summary_stats(
    performance_data=[
        {'timestamp': 0, 'output': 100},
        {'timestamp': 30, 'output': 150},
        # ... many points
    ],
    zone_distribution=workout.zone_distribution,
    avg_power=175.0,
    ftp=280.0,
    calories=500.0
)

# Result:
# {
#     'duration_minutes': 60.0,
#     'duration_formatted': '1h 0m',
#     'max_power': 250,
#     'avg_power': 175,
#     'tss': 51.0,
#     'if': 0.71,
#     'calories': 500,
#     'zone_times': {...}
# }
```

**Minimal Stats (calculates from performance_data):**
```python
stats = chart_builder.generate_summary_stats(
    performance_data=[
        {'timestamp': 0, 'output': 100},
        {'timestamp': 30, 'output': 150},
    ],
    ftp=280.0
)

# Result: Has duration, max, min, avg (calculated)
```

**Template Usage:**
```html
<div class="workout-summary">
    <h2>Workout Summary</h2>
    <p>Duration: {{ stats.duration_formatted }}</p>
    <p>Average Power: {{ stats.avg_power }}W</p>
    <p>Max Power: {{ stats.max_power }}W</p>
    <p>TSS: {{ stats.tss }}</p>
    <p>IF: {{ stats.if }}</p>
    <p>Calories: {{ stats.calories }}</p>
</div>
```

---

## Validation Methods

### 1. is_valid_workout_type()

Checks if the workout type is supported.

**Signature:**
```python
def is_valid_workout_type(self, workout_type: str) -> bool:
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `workout_type` | str | Type to validate |

**Returns:** `bool` - True if type is valid

**Valid Types:**
- `'power_zone'` - Watts-based training
- `'pace_target'` - Pace-based training (running)

**Examples:**

```python
# Valid
chart_builder.is_valid_workout_type('power_zone')    # → True
chart_builder.is_valid_workout_type('pace_target')   # → True

# Invalid
chart_builder.is_valid_workout_type('hr_zone')       # → False
chart_builder.is_valid_workout_type('invalid')       # → False
chart_builder.is_valid_workout_type(None)            # → False
```

**Usage:**
```python
def generate_performance_graph(self, ..., workout_type):
    if not self.is_valid_workout_type(workout_type):
        return {
            'type': 'performance_graph',
            'points': [],
            'message': f'Invalid workout type: {workout_type}'
        }
    # ... continue
```

---

### 2. is_sufficient_data()

Checks if dataset has minimum required points.

**Signature:**
```python
def is_sufficient_data(
    self,
    performance_data: list[dict],
    minimum_points: int = 2,
) -> bool:
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `performance_data` | list[dict] | — | Data to check |
| `minimum_points` | int | 2 | Minimum required points |

**Returns:** `bool` - True if data has enough points

**Examples:**

```python
# Has enough points
chart_builder.is_sufficient_data([{'timestamp': 0, 'output': 100}])
# → True (1 point ≥ 2? No, returns False)

chart_builder.is_sufficient_data(
    [{'timestamp': 0, 'output': 100}, {'timestamp': 30, 'output': 150}]
)
# → True (2 points ≥ 2)

# Doesn't have enough points
chart_builder.is_sufficient_data([])                 # → False
chart_builder.is_sufficient_data(None)               # → False

# Custom minimum
chart_builder.is_sufficient_data(data, minimum_points=10)
```

---

## Helper Methods

### 1. _extract_data_points()

Extracts and validates data points.

**Signature:**
```python
def _extract_data_points(
    self,
    data: list[dict],
    expected_keys: list[str],
) -> list[dict]:
```

**Returns:** List of valid points (skips invalid ones gracefully)

---

### 2. _downsample_points()

Reduces number of points while preserving data shape.

**Signature:**
```python
def _downsample_points(
    self,
    points: list[dict],
    target_points: int = 120,
) -> list[dict]:
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `points` | list[dict] | — | Points to downsample |
| `target_points` | int | 120 | Target number of points |

**Behavior:**
- If points ≤ target_points: returns unchanged
- If points > target_points: selects every nth point
- Always includes first and last point
- Deterministic (same input → same output)

**Example:**
```python
# 1000 points → 120 points
downsampled = chart_builder._downsample_points(big_dataset, 120)
len(downsampled)  # ~120
```

---

### 3. _get_zone_config()

Returns zone definitions for workout type.

**Signature:**
```python
def _get_zone_config(self, workout_type: str) -> dict:
```

**Returns:**
```python
{
    1: {'name': 'Recovery', 'color': '#4472C4'},
    2: {'name': 'Endurance', 'color': '#70AD47'},
    # ... up to 7 zones
}
```

---

### 4. _get_zone_label()

Gets display label for a zone.

**Signature:**
```python
def _get_zone_label(self, zone: int, workout_type: str = 'power_zone') -> str:
```

**Returns:** Zone name (str)

**Examples:**
```python
chart_builder._get_zone_label(1, 'power_zone')    # → 'Recovery'
chart_builder._get_zone_label(4, 'power_zone')    # → 'Lactate Threshold'
chart_builder._get_zone_label(1, 'pace_target')   # → 'Recovery'
```

---

### 5. _get_zone_color()

Gets hex color for a zone.

**Signature:**
```python
def _get_zone_color(self, zone: int, workout_type: str = 'power_zone') -> str:
```

**Returns:** Hex color code (str)

**Examples:**
```python
chart_builder._get_zone_color(1, 'power_zone')    # → '#4472C4' (blue)
chart_builder._get_zone_color(5, 'power_zone')    # → '#C00000' (red)
```

---

## Constants

### ZONE_COLORS

Power zone color mapping.

```python
{
    1: '#4472C4',  # Blue - Recovery
    2: '#70AD47',  # Green - Endurance
    3: '#FFC000',  # Yellow - Tempo
    4: '#FF6600',  # Orange - Threshold
    5: '#C00000',  # Red - VO2 Max
    6: '#7030A0',  # Purple - Anaerobic
    7: '#330000',  # Dark Red - Maximum
}
```

### PACE_ZONE_COLORS

Pace zone color mapping.

```python
{
    1: '#4472C4',  # Blue - Recovery
    2: '#70AD47',  # Green - Easy
    3: '#FFC000',  # Yellow - Moderate
    4: '#FF6600',  # Orange - Challenging
    5: '#C00000',  # Red - Hard
    6: '#7030A0',  # Purple - Very Hard
    7: '#330000',  # Dark Red - Maximum
}
```

### DEFAULT_DOWNSAMPLE_POINTS

Default target for point downsampling: **120 points**

---

## Data Structures

### Performance Data

**Input Format:**
```python
[
    {'timestamp': 0, 'output': 100},
    {'timestamp': 30, 'output': 150},
    {'timestamp': 60, 'output': 175},
    # ... more points
]
```

**Notes:**
- `timestamp`: Seconds or Unix timestamp
- `output`: Watts (power_zone) or pace (pace_target)
- Other fields are ignored

### Zone Distribution Data

**Input Format:**
```python
{
    1: {
        'output': [100, 105, 110],  # samples in zone
        'time_sec': 300,             # total time in zone
    },
    2: {
        'output': [145, 150, 155],
        'time_sec': 1200,
    },
    # ... up to 7 zones
}
```

### Performance Graph Output

**Structure:**
```python
{
    'type': 'performance_graph',
    'workout_type': 'power_zone' | 'pace_target',
    'points': [...],     # Downsampled points with zones
    'zones': {...},      # Zone name mapping
    'colors': {...},     # Zone color mapping
    'min_value': 100,
    'max_value': 250,
    'message': None,
}
```

---

## Error Handling

### Graceful Degradation

All methods fail gracefully (no exceptions):

```python
# Missing required data
chart_data = chart_builder.generate_performance_graph(
    performance_data=None,
    workout_type='power_zone'
)
# Returns: {'type': 'performance_graph', 'points': [], 'message': 'No valid data points found'}

# Invalid type
chart_data = chart_builder.generate_performance_graph(
    performance_data=data,
    workout_type='invalid'
)
# Returns: {'type': 'performance_graph', 'points': [], 'message': 'Invalid workout type: invalid'}

# Empty data
chart_data = chart_builder.generate_performance_graph(
    performance_data=[],
    workout_type='power_zone'
)
# Returns: {'type': 'performance_graph', 'points': [], 'message': '...'}
```

### Error Scenarios

| Scenario | Behavior | Return Value |
|----------|----------|--------------|
| `performance_data=None` | Graceful | Empty dict with message |
| `performance_data=[]` | Graceful | Empty dict with message |
| Invalid `workout_type` | Graceful | Empty dict with message |
| Missing required fields | Graceful | Skip invalid points |
| Type conversion error | Graceful | Skip problematic value |

---

## Examples

### Example 1: Complete Workout Visualization

```python
from workouts.services.chart_builder import ChartBuilder
import json

chart_builder = ChartBuilder()

def workout_detail(request, workout_id):
    workout = Workout.objects.get(id=workout_id)
    user = request.user
    
    perf_data = json.loads(workout.performance_graph)
    zone_data = json.loads(workout.zone_distribution)
    
    # Generate all charts
    performance_graph = chart_builder.generate_performance_graph(
        performance_data=perf_data,
        workout_type=workout.workout_type,
        ftp=user.userprofile.ftp
    )
    
    zone_distribution = chart_builder.generate_zone_distribution(
        zone_data=zone_data,
        workout_type=workout.workout_type
    )
    
    summary_stats = chart_builder.generate_summary_stats(
        performance_data=perf_data,
        zone_distribution=zone_data,
        duration_seconds=workout.duration_seconds,
        avg_power=workout.avg_power,
        ftp=user.userprofile.ftp,
        calories=workout.calories
    )
    
    context = {
        'workout': workout,
        'performance_graph': performance_graph,
        'zone_distribution': zone_distribution,
        'summary_stats': summary_stats,
    }
    
    return render(request, 'workout_detail.html', context)
```

### Example 2: API Endpoint

```python
from django.http import JsonResponse
from rest_framework.decorators import api_view
import json

@api_view(['GET'])
def api_workout_chart(request, workout_id):
    """REST endpoint for workout chart data."""
    workout = Workout.objects.get(id=workout_id)
    
    perf_data = json.loads(workout.performance_graph)
    
    chart_data = chart_builder.generate_performance_graph(
        performance_data=perf_data,
        workout_type=workout.workout_type,
        ftp=request.user.userprofile.ftp
    )
    
    return JsonResponse(chart_data)
```

### Example 3: Dashboard Widget

```python
def dashboard(request):
    """Show recent workouts with chart summaries."""
    recent_workouts = Workout.objects.filter(
        user=request.user
    ).order_by('-date')[:5]
    
    charts = []
    for workout in recent_workouts:
        perf_data = json.loads(workout.performance_graph)
        
        stats = chart_builder.generate_summary_stats(
            performance_data=perf_data,
            duration_seconds=workout.duration_seconds,
            avg_power=workout.avg_power,
            ftp=request.user.userprofile.ftp
        )
        
        charts.append({
            'workout': workout,
            'stats': stats,
        })
    
    context = {'workouts_with_stats': charts}
    return render(request, 'dashboard.html', context)
```

---

## Best Practices

### 1. Initialize Once

```python
# ✅ Good: Module-level initialization
from workouts.services.chart_builder import ChartBuilder

chart_builder = ChartBuilder()

def view1(request):
    graph = chart_builder.generate_performance_graph(...)
    
def view2(request):
    dist = chart_builder.generate_zone_distribution(...)

# ❌ Avoid: Creating new instance each time
def view1(request):
    chart_builder = ChartBuilder()  # Wasteful
    ...
```

### 2. Pass FTP from UserProfile

```python
# ✅ Good: Get FTP from database
ftp = request.user.userprofile.ftp
chart_data = chart_builder.generate_performance_graph(..., ftp=ftp)

# ❌ Avoid: Hardcoding FTP
chart_data = chart_builder.generate_performance_graph(..., ftp=200.0)
```

### 3. Handle Large Datasets

```python
# ✅ Good: Use default downsampling (120 points)
chart_data = chart_builder.generate_performance_graph(data)  # Auto-downsample

# ⚠️ Consider: Explicit downsampling for very large datasets
chart_data = chart_builder.generate_performance_graph(
    data,
    downsample_points=100  # More aggressive
)

# ⚠️ Careful: No downsampling for small datasets only
if len(data) > 500:
    chart_data = chart_builder.generate_performance_graph(data)
```

### 4. Validate Data Before Calling

```python
# ✅ Good: Check data availability
if chart_builder.is_sufficient_data(perf_data):
    graph = chart_builder.generate_performance_graph(perf_data)
else:
    graph = None

# ✅ Good: Check workout type
if chart_builder.is_valid_workout_type(workout_type):
    graph = chart_builder.generate_performance_graph(
        data,
        workout_type=workout_type
    )
```

### 5. Use in Templates Safely

```html
<!-- ✅ Good: Mark as safe for JSON rendering -->
<script>
    const chartData = {{ chart_data|safe }};
    // Use chartData with Chart.js or D3
</script>

<!-- ❌ Avoid: HTML escaping JSON breaks parsing -->
<script>
    const chartData = {{ chart_data }};  <!-- Escapes quotes -->
</script>
```

---

## Troubleshooting

### Problem: Empty Chart Data

**Symptom:** `chart_data['points']` is empty

**Causes:**
- No valid performance data provided
- Invalid `workout_type`
- Data points missing required fields (`timestamp`, `output`)

**Solution:**
```python
# Check data
if not chart_builder.is_sufficient_data(perf_data):
    print("Not enough data points")

# Check format
print(perf_data[0])  # Should be {'timestamp': ..., 'output': ...}

# Check type
if not chart_builder.is_valid_workout_type(workout_type):
    print(f"Invalid type: {workout_type}")

# Check data extraction
points = chart_builder._extract_data_points(
    perf_data,
    ['timestamp', 'output']
)
print(f"Extracted {len(points)} points")
```

### Problem: Wrong Zone Assignment

**Symptom:** Points assigned to wrong zones

**Causes:**
- Incorrect FTP value
- Mismatch between workout_type and data

**Solution:**
```python
# Verify FTP
print(f"Using FTP: {ftp}")

# Test zone calculation
from workouts.services.metrics import MetricsCalculator
calc = MetricsCalculator()
zone = calc.get_power_zone_for_output(watts=150, ftp=280)
print(f"150W at 280 FTP = Zone {zone}")
```

### Problem: Downsampling Too Aggressive

**Symptom:** Chart looks blocky or missing detail

**Solution:**
```python
# Increase downsampling target
chart_data = chart_builder.generate_performance_graph(
    perf_data,
    downsample_points=240  # Instead of default 120
)

# Or disable downsampling
chart_data = chart_builder.generate_performance_graph(
    perf_data,
    downsample_points=None  # All points
)
```

### Problem: Missing Metrics

**Symptom:** `chart_data['tss']` or `chart_data['if']` is None

**Causes:**
- Missing `avg_power` or `zone_distribution`
- Insufficient data to calculate

**Solution:**
```python
# Provide explicit values
metrics = chart_builder.generate_tss_if_metrics(
    avg_power=workout.avg_power,
    duration_seconds=workout.duration_seconds,
    ftp=user_ftp
)

# Or provide zone distribution for more accurate calculation
metrics = chart_builder.generate_tss_if_metrics(
    zone_distribution=zone_data,
    ftp=user_ftp
)
```

---

## See Also

- [Phase 3 Summary](PHASE_3_SUMMARY.md)
- [Phase 3 Architecture](PHASE_3_ARCHITECTURE.md)
- [Metrics Service API](../workouts/METRICS_SERVICE.md)
- [Phase 2 Summary](PHASE_2_SUMMARY.md)

---

**API Reference Status:** ✅ Complete  
**Test Coverage:** 25 tests (100% passing)  
**Last Updated:** February 1, 2026
