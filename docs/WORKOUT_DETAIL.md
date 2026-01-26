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

#### Other Workout Types

For non-power zone workouts:
- **Cycling**: Output line (watts)
- **Running**: Speed line (mph)
- **Other**: Heart rate line (bpm)

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
     - **Target Line**: Calculated from class plan segments (preferred) or API fallback
     - **Zone Ranges**: Calculated from user's FTP at workout date
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

### Zone Range Calculation

Power zone ranges are calculated based on user's FTP at workout date:

```python
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

Re-fetches and updates performance graph data for a specific workout without full re-sync.

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

## Browser Compatibility

- **Chart.js**: v4.4.0 (CDN)
- **Tailwind CSS**: Via CDN with dark mode support
- **Alpine.js**: For interactive elements (from base template)

## Related Documentation

- [Peloton API Integration](./peloton.md) - API integration details
- [Sync Strategy](./SYNC_STRATEGY.md) - Workout syncing process
- [Class Library](./CLASS_LIBRARY.md) - Class library features
