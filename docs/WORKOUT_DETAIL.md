# Workout Detail Page

## Overview

The workout detail page (`/workouts/{id}/`) displays comprehensive information about a completed workout, including performance graphs, metrics, and class details. The page features interactive Chart.js visualizations for power zone classes, pace target classes, and other workout types.

## Features

### 1. Workout Header

Displays essential workout information:
- **Duration**: Workout length in minutes
- **Workout Type**: Class type badge (cycling, running, etc.)
- **Title**: Workout/class title
- **Instructor**: Instructor name (if available)
- **Action Buttons**: 
  - "View Workout" - Link to Peloton workout page
  - "View Class" - Link to Peloton class page
- **Dates**: Recorded and completed dates

### 2. Workout Metrics Section

Displays key performance metrics in a grid layout:
- **Training Stress Score (TSS)**: With target if available
- **Average Output**: In watts
- **Total Output**: In kilojoules
- **Max Output**: Peak watts
- **Average Speed**: In mph (for running workouts)
- **Max Speed**: Peak speed (for running workouts)
- **Distance**: In miles
- **Average Heart Rate**: In bpm
- **Max Heart Rate**: Peak bpm
- **Calories**: Total calories burned

### 3. Performance Graph

Interactive Chart.js visualization showing workout performance over time.

#### Power Zone Classes

For power zone cycling classes, the graph includes:

- **Power Zone Timeline**: Title and description
- **Music Timeline Toggle**: Checkbox to show/hide music overlay (top-right)
- **Music Timeline Overlay**: Horizontal band above chart showing song segments with:
  - Song titles and artists
  - Color-coded segments
  - Hover effects for details
- **Chart Features**:
  - **Actual Output Line**: Blue smooth curve showing actual watts
  - **Target Output Line**: Blue dashed stepped line showing target watts (from class plan)
  - **Zone Background Bands**: Colored zones 1-7 with opacity
  - **Custom Legend**: Zone names with watt ranges (Z7 to Z1)
  - **Readout Display**: Shows "Time • Output X w • Target Y w" on hover
- **Zone Colors**:
  - Zone 1: Purple (#6f42c1) - Active Recovery
  - Zone 2: Teal (#17a2b8) - Endurance
  - Zone 3: Green (#28a745) - Tempo
  - Zone 4: Yellow (#ffc107) - Threshold
  - Zone 5: Orange (#fd7e14) - VO2 Max
  - Zone 6: Red (#dc3545) - Anaerobic
  - Zone 7: Dark Purple (#6610f2) - Neuromuscular

#### Pace Target Classes

For running and walking pace target classes, the graph includes:

- **Pace Target Timeline**: Title and description
- **Music Timeline Toggle**: Checkbox to show/hide music overlay (top-right)
- **Music Timeline Overlay**: Horizontal band above chart showing song segments (same as power zone)
- **Chart Features**:
  - **Actual Pace Line**: Yellow smooth curve showing actual pace level (1-7) based on speed
  - **Target Pace Line**: Blue stepped line showing target pace zones (from class plan)
  - **Zone Background Bands**: Colored zones 1-7 with opacity
  - **Custom Legend**: Zone names (Max to Recovery)
  - **Readout Display**: Shows "Time • Pace Level X • Target Y" on hover
- **Zone Colors** (matching power zone):
  - Recovery: Purple - Zone 1
  - Easy: Teal - Zone 2
  - Moderate: Green - Zone 3
  - Challenging: Yellow - Zone 4
  - Hard: Orange - Zone 5
  - Very Hard: Red - Zone 6
  - Max: Pink - Zone 7
- **Target Line Offset**: Target pace line is offset by -60 seconds (starts 60s earlier) to match power zone behavior

#### Other Workout Types

For non-power zone, non-pace target workouts:
- **Cycling**: Output line (watts)
- **Running/Walking (non-pace target)**: Speed line (mph)
- **Other**: Heart rate line (bpm)

#### Classes Without Performance Data

For classes where Peloton returned no performance metrics:
- Displays message: "Peloton returned no performance metrics for this class"
- No chart is rendered

#### Unsupported Class Types

For class types that don't support performance graphs (e.g., yoga, strength, meditation):
- Displays message: "Performance data is not available for this class type"

### 4. Power Profile and Zone Cards (Power Zone Classes Only)

For power zone cycling classes, three additional cards are displayed below the performance graph:

#### Power Profile Card

Displays peak power output for different time intervals:
- **5 Second Power**: Maximum average power over 5 seconds
- **1 Minute Power**: Maximum average power over 1 minute
- **5 Minute Power**: Maximum average power over 5 minutes
- **20 Minute Power**: Maximum average power over 20 minutes

Each metric is displayed in a purple gradient card with the duration prominently shown, followed by the wattage value below.

#### Main Set Zone Targets Card

Shows compliance with class zone targets:
- **Overall Progress Bar**: Large horizontal bar showing overall completion percentage (orange-yellow gradient)
- **Individual Zone Progress**: For each zone (Z7 to Z1) with target time:
  - Zone label (e.g., "Z5 • VO2 Max")
  - Colored progress bar showing actual vs target time
  - Target time and completion percentage
  - Zone colors match the chart zones:
    - Z5: Orange
    - Z4: Yellow
    - Z3: Green
    - Z2: Teal
    - Z1: Purple
    - Z6: Red
    - Z7: Pink

#### Class Notes Card

Displays zone breakdown summary:
- **Zone List**: Each zone (Z7 to Z1) with:
  - Zone label and name (e.g., "Z5 • VO2 Max")
  - Total time in that zone
  - Number of blocks (consecutive segments in same zone)

### 5. Playlist Section

Displays class playlist if available:
- **Song List**: Numbered list with:
  - Song number badge
  - Album art (or placeholder)
  - Song title and artists
  - Album name
  - Start time offset
  - Spotify search link (hover to reveal)
  - Explicit rating badge
- **Top Artists**: Summary of most featured artists

## Technical Implementation

### Template Structure

**File**: `templates/workouts/detail.html`

#### Key Sections:

1. **Back Button**: Link to workout history
2. **Workout Header**: Title, badges, dates, action buttons
3. **Metrics Section**: Grid of workout metrics
4. **Performance Graph**: Conditional rendering based on workout type
5. **Playlist Section**: Song list and top artists

### Data Flow

#### Backend (`workouts/views.py`)

1. **`workout_detail` view**:
   - Fetches workout with related data (ride_detail, performance_data)
   - Determines workout type (power zone, pace target, other)
   - Calculates target metrics:
     - **Power Zone**: Uses `ride_detail.get_power_zone_segments()` with user's FTP at workout date
     - **Pace Target**: Uses `ride_detail.get_pace_segments()` with user's pace level at workout date
     - **Target Line**: Calculated from class plan segments (preferred) or API fallback
     - **Zone Ranges**: 
       - Power Zone: Calculated from user's FTP at workout date
       - Pace Target: Calculated from user's pace level at workout date (activity-specific: running or walking)
   - Calculates power profile (5s, 1m, 5m, 20m peak power):
     - Uses rolling averages over performance data
     - Calculates segment_length from timestamp intervals
     - Finds maximum average power for each duration window
   - Calculates zone targets and compliance:
     - Extracts target zone times from class plan segments
     - Calculates actual time in each zone from performance data
     - Compares actual vs target for compliance percentage
     - Counts zone blocks (consecutive segments in same zone)
   - Prepares JSON data for frontend:
     - `target_metrics_json`: Zone ranges and segments
     - `target_line_data`: Target output line data points
     - `playlist`: Song data for music timeline
     - `power_profile`: Peak power for different durations
     - `zone_targets`: Zone compliance data with progress bars
     - `class_notes`: Zone breakdown summary

#### Frontend JavaScript

1. **Chart Initialization**:
   - Checks for Chart.js library
   - Validates data availability
   - Determines workout type and power zone status
   - Prepares datasets based on workout type

2. **Power Zone Chart**:
   - Builds zone bands from `zoneRanges`
   - Creates actual and target output datasets
   - Configures Chart.js with:
     - Linear x-axis (time-based)
     - Custom y-axis range with padding
     - Zone bands plugin for background
     - External tooltip for readout

3. **Music Timeline**:
   - Renders song segments as positioned divs
   - Calculates positions based on workout duration
   - Handles checkbox toggle to show/hide
   - Applies color palette for visual distinction

### Target Line Calculation

The target line is calculated using two methods (in priority order):

1. **Class Plan Segments** (`_calculate_target_line_from_segments`):
   - Uses segments from `ride_detail.get_power_zone_segments()`
   - Calculates target watts as middle of each zone's range
   - Applies -60 second time shift (target line starts 60s earlier)
   - Aligns with performance data timestamps

2. **API Fallback** (`_calculate_power_zone_target_line`):
   - Fetches `target_metrics_performance_data` from Peloton API
   - Calculates target watts from zone percentages
   - Applies -60 second time shift
   - Used when class plan segments unavailable

### Historical Data Lookup

The system uses **historical values** (FTP and pace levels) that were active when the workout was recorded, not current values. This ensures accurate zone calculations and target displays for past workouts.

#### FTP Lookup

Power zone ranges are calculated based on user's FTP at workout date:

```python
workout_date = workout.completed_date or workout.recorded_date
user_ftp = user_profile.get_ftp_at_date(workout_date)

zone_ranges = {
    1: (0, int(user_ftp * 0.55)),           # Zone 1: 0-55% FTP
    2: (int(user_ftp * 0.55), int(user_ftp * 0.75)),  # Zone 2: 55-75% FTP
    3: (int(user_ftp * 0.75), int(user_ftp * 0.90)),  # Zone 3: 75-90% FTP
    4: (int(user_ftp * 0.90), int(user_ftp * 1.05)),  # Zone 4: 90-105% FTP
    5: (int(user_ftp * 1.05), int(user_ftp * 1.20)),  # Zone 5: 105-120% FTP
    6: (int(user_ftp * 1.20), int(user_ftp * 1.50)),  # Zone 6: 120-150% FTP
    7: (int(user_ftp * 1.50), None)              # Zone 7: 150%+ FTP
}
```

The `get_ftp_at_date()` method:
- Finds the most recent FTP entry with `recorded_date <= workout_date`
- Falls back to current FTP if no historical entry found

#### Pace Level Lookup

Pace target zones are calculated based on user's pace level at workout date (activity-specific):

```python
workout_date = workout.completed_date or workout.recorded_date
activity_type = 'running' if ride_detail.fitness_discipline in ['running', 'run'] else 'walking'
user_pace_level = user_profile.get_pace_at_date(workout_date, activity_type=activity_type)

# Calculate pace zones based on level (1-10)
base_paces = {
    1: 12.0, 2: 11.0, 3: 10.0, 4: 9.0, 5: 8.5, 6: 8.0, 7: 7.5, 8: 7.0, 9: 6.5, 10: 6.0
}
base_pace = base_paces.get(user_pace_level, 8.0)

pace_zones = {
    'recovery': base_pace + 2.0,      # Recovery: +2:00/mile
    'easy': base_pace + 1.0,          # Easy: +1:00/mile
    'moderate': base_pace,            # Moderate: base pace
    'challenging': base_pace - 0.5,   # Challenging: -0:30/mile
    'hard': base_pace - 1.0,          # Hard: -1:00/mile
    'very_hard': base_pace - 1.5,     # Very Hard: -1:30/mile
    'max': base_pace - 2.0            # Max: -2:00/mile
}
```

The `get_pace_at_date()` method:
- Finds the most recent PaceEntry with `recorded_date <= workout_date` for the specific activity type (running or walking)
- Falls back to current active pace if no historical entry found
- Supports separate pace levels for running and walking activities

### Styling

The template uses Tailwind CSS classes for consistent styling:

- **Cards**: `rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm`
- **Headings**: `text-lg font-semibold text-gray-900 dark:text-white`
- **Text**: `text-sm text-gray-600 dark:text-gray-400`
- **Spacing**: Consistent `mb-6` between sections

#### Mobile Responsiveness

The workout detail page is fully responsive with mobile-optimized layouts:

- **Chart Card**: 
  - Reduced padding on mobile (`p-3` vs `p-6` on desktop)
  - Smaller chart height on mobile (`min-h-[240px]` vs `min-h-[320px]`)
  - Responsive text sizes (`text-base sm:text-lg`)
  - Stacked header layout on mobile
- **Chart Controls**: 
  - Centered on mobile, right-aligned on desktop
  - Smaller buttons and text on mobile
  - Touch-friendly spacing
- **Power Profile Cards**: 
  - 2-column grid on mobile, 3-column on desktop
  - Responsive card sizing
- **Zone Targets Card**: 
  - Full-width on mobile, responsive grid on desktop
  - Scrollable content if needed

### Chart.js Configuration

#### Power Zone Chart:

```javascript
{
  type: 'line',
  data: {
    labels: timeSeconds,  // Linear scale timestamps
    datasets: [
      {
        label: 'Actual',
        data: outputData,
        borderColor: '#5b7cfa',
        borderWidth: 2.8,
        cubicInterpolationMode: 'monotone'
      },
      {
        label: 'Target',
        data: targetOutputData,
        borderColor: '#5b7cfa',
        borderWidth: 2.8,
        borderDash: [5, 4],
        stepped: 'before'
      }
    ]
  },
  options: {
    scales: {
      x: {
        type: 'linear',
        min: 0,
        max: workoutDuration
      },
      y: {
        min: ymin,
        max: ymax
      }
    },
    plugins: [zoneBandsPlugin]
  }
}
```

## Management Commands

### Refresh Workout Performance

**Command**: `python manage.py refresh_workout_performance <workout_id>`

Re-fetches and updates performance graph data for a specific workout without full re-sync. This command correctly extracts speed data from the `pace` metric's `alternatives` array for running/walking workouts.

**Options**:
- `--username`: Peloton username (if not workout owner)
- `--every-n`: Sampling interval in seconds (default: 5)
- `--django-id`: Treat workout_id as Django workout ID

**Usage**:
```bash
# Using Peloton workout ID
python manage.py refresh_workout_performance c29be4c7e31441d9964ec1cd34a497a2

# Using Django workout ID
python manage.py refresh_workout_performance 936 --django-id
```

### Refresh All Running/Walking Workouts

**Command**: `python manage.py refresh_all_running_walking`

Bulk refreshes performance data for all running and walking workouts. Useful after fixing speed extraction logic or updating performance data processing.

**Options**:
- `--username`: Peloton username (if not provided, processes all users)
- `--every-n`: Sampling interval in seconds (default: 5)
- `--limit`: Limit the number of workouts to process (for testing)
- `--dry-run`: Show what would be processed without actually updating

**Usage**:
```bash
# Refresh all running/walking workouts
python manage.py refresh_all_running_walking

# Test with first 10 workouts
python manage.py refresh_all_running_walking --limit 10

# Dry run to see what would be processed
python manage.py refresh_all_running_walking --dry-run
```

**Features**:
- Correctly extracts speed data from `pace` metric's `alternatives` array
- Groups workouts by user to minimize API client creation
- Provides detailed progress output with success/failure counts
- Skips workouts with no performance data available from Peloton

### Download Workout JSONs

**Command**: `python manage.py download_workout_jsons <workout_id1> [workout_id2] ...`

Downloads performance graph JSON files for inspection/testing.

**Usage**:
```bash
python manage.py download_workout_jsons c29be4c7e31441d9964ec1cd34a497a2 f30afa54730a45b89f2f3ec98959a5b9
```

Files are saved to `./jsons/` directory (gitignored).

## Data Models

### WorkoutPerformanceData

Stores time-series performance data:
- `workout`: Foreign key to Workout
- `timestamp`: Time offset in seconds
- `output`: Watts
- `cadence`: RPM
- `resistance`: Percentage
- `speed`: MPH
- `heart_rate`: BPM

### Target Metrics Structure

For power zone classes:
```json
{
  "type": "power_zone",
  "segments": [
    {
      "zone": 1,
      "start": 0,
      "end": 300
    }
  ],
  "zone_ranges": {
    "1": [0, 105],
    "2": [105, 143],
    ...
  }
}
```

For pace target classes:
```json
{
  "type": "pace",
  "segments": [
    {
      "zone": 3,
      "pace_level": 3,
      "start": 60,
      "end": 300
    }
  ],
  "pace_zones": {
    "recovery": 10.0,
    "easy": 9.0,
    "moderate": 8.5,
    "challenging": 8.0,
    "hard": 7.5,
    "very_hard": 7.0,
    "max": 6.5
  }
}
```

## Browser Compatibility

- **Chart.js**: v4.4.0 (CDN)
- **Tailwind CSS**: Via CDN with dark mode support
- **Alpine.js**: For interactive elements (from base template)

## Related Documentation

- [Peloton API Integration](./peloton.md) - API integration details
- [Sync Strategy](./SYNC_STRATEGY.md) - Workout syncing process
- [Class Library](./CLASS_LIBRARY.md) - Class library features
