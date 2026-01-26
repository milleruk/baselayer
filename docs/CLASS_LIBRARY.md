# Class Library Documentation

## Overview

The Class Library is a comprehensive browsing and filtering system for Peloton classes that allows users to explore available classes, view detailed information, and access interactive workout previews. The library provides rich visualizations, personalized metrics, and powerful filtering capabilities.

## Features

### 1. Class Browsing

The library displays all available Peloton classes with:
- **Class Cards**: Visual cards showing class information, metrics, and intensity charts
- **Pagination**: 12 classes per page for optimal performance
- **Sorting**: Multiple sorting options (newest first, oldest first, title A-Z/Z-A, duration)

### 2. Filtering System

The library provides comprehensive filtering options matching the workout history page for consistency:

#### Search
- Search by class title or instructor name
- Real-time filtering as you type

#### Workout Type Tabs
- Visual tabs for quick filtering by workout type
- Options: All, Cycling, Running, Walking, Rowing
- Active tab highlighted with primary color

#### Advanced Filters
- **TSS Filter**: Filter classes by Training Stress Score (≥ value)
- **Instructor Filter**: Dropdown to filter by specific instructor
- **Duration Filter**: Filter by class duration (5, 10, 15, 20, 30, 45, 60, 75, 90, 120 minutes)
- **Active Filter Pills**: Visual indicators showing active filters with easy removal

### 3. Class Cards

Each class card displays:

#### Visual Elements
- **Duration Badge**: Yellow badge showing class duration in minutes
- **Activity Icon**: Icon representing workout type (cycling, running, walking, etc.)
- **Class Title**: Full class title with line clamping for long titles
- **Instructor Name**: Class instructor
- **Recorded Date**: Original air date (only shown if valid timestamp)

#### Metrics Display
- **Power Zone Classes**:
  - **TSS** (Training Stress Score): Calculated based on user's FTP and zone distribution
  - **IF** (Intensity Factor): Calculated normalized power / FTP
- **Pace Target Classes**:
  - **Difficulty Rating**: 0-10 scale based on average intensity
- **Other Classes**: Difficulty rating when available

#### Class Plan Chart
- **Mini Chart.js Line Graph**: Shows intensity profile over time
- **Zone Backgrounds**: Colored bands indicating different zones/intensity levels
- **Interactive**: Hover to see time and target values
- **Responsive**: Adapts to card size and screen resolution

#### Action Buttons
- **View Details**: Navigate to detailed class view with interactive player
- **View on Peloton**: External link to Peloton website (if available)

### 4. Class Detail Pages

Detailed class views provide:

#### Interactive Workout Player
- **Power Zone Classes**:
  - Interactive Chart.js visualization with zone bands
  - FTP input for personalized power targets
  - Real-time target display (watts @ zone)
  - Play/pause controls
  - Progress slider with tooltip
  - Fullscreen mode
  - Countdown timer
  - Audio cues for interval changes
  
- **Pace Target Classes**:
  - Interactive Chart.js visualization with pace level bands
  - Pace level selector (1-10) for personalized pace targets
  - Real-time target display (pace @ level)
  - Same interactive features as power zone classes

#### Information Grid (2x2 Layout)
- **Class Info Card**: Discipline, type, TSS, IF
- **Instructor Card**: Instructor photo and name
- **Zone Distribution Card**: Time spent in each zone with percentages
- **Class Details Card**: Expandable sections for Warm Up, Main, Cool Down

#### Header Section
- Compact header with class title
- Instructor and recorded date
- Duration, FTP/Pace level, TSS/IF metrics
- Peloton link button

### 5. Data Calculations

#### TSS (Training Stress Score) Calculation

**Power Zone Classes**:
```
Normalized Power = Weighted average power across all zones
IF = Normalized Power / FTP
TSS = (Duration in hours) × IF² × 100
```

**Pace Target Classes**:
```
Average Intensity = Weighted average of pace zone intensity factors
IF = Average Intensity
TSS = (Duration in hours) × IF² × 100
```

Intensity factors for pace zones:
- Recovery: 0.5
- Easy: 0.7
- Moderate: 1.0
- Challenging: 1.15
- Hard: 1.3
- Very Hard: 1.5
- Max: 1.8

#### Difficulty Rating

For pace target classes:
```
Difficulty = (Average Intensity / 1.8) × 10
```
Results in a 0-10 scale where 1.8 (Max intensity) = 10.0

### 6. Chart Data Generation

#### Power Zone Classes
- Extracts zone segments from `get_power_zone_segments()`
- Maps zones 1-7 to chart zones
- Excludes warm up (first 15%) and cool down (last 10%)
- Generates time series data for Chart.js visualization

#### Pace Target Classes
- Primary: Extracts from `target_metrics_data` → `get_target_metrics_segments()`
- Fallback: Uses `get_pace_segments()` if target_metrics_data unavailable
- Maps zones 0-6 (Recovery to Max) to chart zones
- Excludes warm up and cool down segments
- Generates time series data for Chart.js visualization

### 7. Zone Distribution

#### Power Zone Classes
- Calculates time spent in each zone (1-7)
- Excludes warm up and cool down from calculations
- Displays as percentages of main workout duration
- Ordered from Zone 1 (bottom) to Zone 7 (top) for stacked visualization

#### Pace Target Classes
- Calculates time spent in each pace level (Recovery, Easy, Moderate, Challenging, Hard, Very Hard, Max)
- Excludes warm up and cool down from calculations
- Displays as percentages of main workout duration
- Ordered from Recovery (bottom) to Max (top) for stacked visualization

### 8. Filtering Logic

#### Excluded Classes
- Warm up classes (`class_type == 'warm_up'`)
- Cool down classes (`class_type == 'cool_down'`)
- Classes with "warm up", "warmup", "cool down", or "cooldown" in title

#### Allowed Types
- Cycling
- Running
- Walking
- Rowing

#### Date Filtering
- Only displays classes with valid `original_air_time` (excludes Unix epoch 0 = 01/21/1970)

### 9. Mobile Responsiveness

All library pages are fully responsive:

#### Library Page
- Cards stack vertically on mobile
- Filters wrap appropriately
- Tabs scroll horizontally on mobile
- Active filter pills wrap on small screens

#### Detail Pages
- Header stacks vertically on mobile
- Workout controls wrap on mobile
- Status items stack vertically on mobile
- Charts scale appropriately (300px mobile, 400px desktop)
- Grid layouts stack to single column on mobile
- Card padding adjusts (p-4 mobile, p-6 desktop)

### 10. Interactive Features

#### Chart Hover Tooltips
- **Power Zone Classes**: Shows time and target watts based on user's FTP
- **Pace Target Classes**: Shows time and target pace based on user's pace level
- Tooltip appears near cursor/intersection point
- Updates in real-time as user changes FTP or pace level

#### Chart Interaction
- Hover over chart line to see tooltip
- Progress slider for scrubbing through workout
- Fullscreen mode for immersive experience
- Play/pause controls for workout simulation

## Technical Implementation

### Models

- **RideDetail**: Stores class/ride template information
  - Links to `WorkoutType` and `Instructor`
  - Stores target metrics (Power Zone ranges, pace targets)
  - Stores class metadata (title, duration, difficulty, description)
  - `original_air_time`: Unix timestamp for class recording date
  - `target_metrics_data`: JSON field with class plan segments

### Views

- **`class_library`**: Main library view with filtering and pagination
- **`class_detail`**: Detailed class view with interactive player

### Templates

- **`class_library.html`**: Main library page template
- **`class_detail.html`**: Base detail page template
- **`partials/class_header.html`**: Compact header component
- **`partials/power_zone_content.html`**: Power zone specific layout
- **`partials/pace_target_content.html`**: Pace target specific layout
- **`partials/default_content.html`**: Fallback layout for other class types
- **`partials/power_zone_chart.html`**: Interactive power zone chart component
- **`partials/pace_target_chart.html`**: Interactive pace target chart component

### JavaScript

- **Chart.js v4.4.6**: For data visualization
- **Custom Plugins**:
  - `zoneBands`: Draws colored zone backgrounds
  - `progressLine`: Shows current time indicator
- **Interactive Features**:
  - Play/pause simulation
  - Progress scrubbing
  - Fullscreen mode
  - Audio cues
  - Countdown timer

### Data Flow

1. **Library Page Load**:
   - Fetches `RideDetail` objects with filters applied
   - Calculates TSS/IF for each ride based on user profile
   - Generates chart data for mini visualizations
   - Paginates results (12 per page)

2. **Detail Page Load**:
   - Fetches specific `RideDetail` object
   - Extracts target metrics data
   - Generates full chart data for interactive player
   - Calculates zone distribution
   - Prepares class sections (Warm Up, Main, Cool Down)

3. **Chart Rendering**:
   - Parses chart data from JSON
   - Builds time series arrays
   - Creates Chart.js configuration
   - Renders with zone bands and interactive features

## User Experience

### Library Page
- Clean, card-based layout
- Visual intensity charts on each card
- Quick filtering with tabs and dropdowns
- Active filter indicators
- Responsive design for all screen sizes

### Detail Page
- Interactive workout preview
- Personalized targets based on user settings
- Expandable class details
- Fullscreen mode for focused viewing
- Mobile-optimized controls

## Future Enhancements

Potential improvements:
- Save favorite classes
- Create custom playlists
- Compare classes side-by-side
- Export class plans
- Share classes with other users
- Integration with workout planning

## Related Documentation

- [Peloton API Integration](./peloton.md) - Details on Peloton API integration
- [Sync Strategy](./SYNC_STRATEGY.md) - Workout syncing documentation
- [README](../README.md) - Project overview and setup
