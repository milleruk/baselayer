# Recap and Eddington Pages

## Overview

The Recap and Eddington pages provide users with comprehensive yearly workout summaries and distance-based achievement tracking. These pages offer insights into workout patterns, achievements, and progress over time.

## Yearly Recap Page

### Overview

The Yearly Recap page (`/recap/`) displays a comprehensive summary of a user's workout activity for a selected year, including statistics, top instructors, monthly breakdowns, and shareable public links.

### Features

#### 1. Year Selection

Users can select any year from their workout history:
- **Year Dropdown**: Lists all years with completed workouts
- **Auto-redirect**: Changing the year updates the page automatically
- **Default Year**: Shows the most recent year with workouts

#### 2. Summary Statistics

Displays key metrics in a card-based layout:
- **Total Workouts**: Count of all workouts completed in the year
- **Active Days**: Number of unique days with at least one workout
- **Longest Streak**: Maximum consecutive days with workouts
- **Total Duration**: Sum of all workout durations (in hours/minutes)
- **Total Distance**: Combined distance across all workouts (in miles/km)

#### 3. Performance Metrics

Shows aggregated performance data:
- **Total Output**: Sum of all power output (for cycling workouts)
- **Average Output**: Mean power output across cycling workouts
- **Total Calories**: Combined calories burned
- **Average Heart Rate**: Mean heart rate across all workouts

#### 4. Top Instructors

Lists the most frequently used instructors:
- **Instructor Name**: Display name
- **Workout Count**: Number of classes taken with that instructor
- **Percentage**: Share of total workouts
- **Sorted**: By workout count (descending)

#### 5. Monthly Breakdown

Visual representation of workout activity by month:
- **Bar Chart**: Shows workout count per month
- **Month Labels**: Full month names
- **Color Coding**: Consistent color scheme for visual clarity
- **Interactive**: Chart.js visualization with hover tooltips

#### 6. Shareable Links

Users can create and manage public share links:
- **Create Share Link**: Generates a unique token-based URL
- **View Share Link**: Opens the public recap page in a new tab
- **Disable/Enable**: Toggle share link status
- **Regenerate Token**: Create a new share token (invalidates old link)
- **View Count**: Tracks how many times the shared link has been viewed
- **Last Viewed**: Timestamp of most recent view

### Technical Implementation

#### Backend (`plans/views.py`)

**`recap` view**:
- Fetches all workouts for the selected year
- Groups workouts by date for streak calculation
- Aggregates metrics (total workouts, active days, duration, distance)
- Calculates top instructors with workout counts
- Generates monthly breakdown data
- Handles share link creation/retrieval via `RecapShare` model

**Key calculations**:
- **Longest Streak**: Finds maximum consecutive days with workouts
- **Active Days**: Counts unique dates with at least one workout
- **Monthly Breakdown**: Groups workouts by month and counts them

#### Frontend Template (`templates/plans/recap.html`)

**Structure**:
1. **Header**: Year selector and share link controls
2. **Summary Cards**: Grid layout with key statistics
3. **Performance Metrics**: Additional workout metrics
4. **Top Instructors**: List of most-used instructors
5. **Monthly Chart**: Chart.js bar chart visualization

**JavaScript**:
- **CSRF Token Handling**: Extracts CSRF token for AJAX requests
- **Share Link Management**: 
  - `createShare()`: Creates new share link via AJAX
  - `disableShare()`: Disables existing share link
  - `regenerateToken()`: Creates new token for share link
- **Error Handling**: Displays user-friendly error messages

#### Public Share View (`recap_share`)

**URL Pattern**: `/recap/share/<token>/`

**Features**:
- **Token-based Access**: Public access via unique token
- **View Tracking**: Increments view count on each visit
- **Last Viewed Timestamp**: Updates on each view
- **Read-only**: No user controls (year selection, share management)
- **Same Data**: Displays identical recap data as private view

**Template**: `templates/plans/recap_public.html`

#### Share Management API (`recap_share_manage`)

**URL Pattern**: `/recap/share/manage/`

**Endpoints** (POST requests):
- **Create**: `action=create&year=YYYY`
- **Disable**: `action=disable&year=YYYY`
- **Regenerate**: `action=regenerate&year=YYYY`

**Response Format**:
```json
{
  "success": true,
  "share": {
    "token": "unique-token-string",
    "is_enabled": true,
    "view_count": 0,
    "url": "/recap/share/unique-token-string/"
  }
}
```

### Data Models

#### RecapShare Model (`plans/models.py`)

```python
class RecapShare(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    token = models.CharField(max_length=64, unique=True, db_index=True)
    is_enabled = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Key Methods**:
- `regenerate_token()`: Creates new secure token
- `increment_view_count()`: Updates view statistics
- `is_valid()`: Checks if share link is active
- `get_or_create_for_user_year()`: Class method to get/create share

**Unique Constraint**: One share per user per year

### Styling

Uses Tailwind CSS with dark mode support:
- **Cards**: `bg-white dark:bg-gray-800 rounded-lg shadow p-6`
- **Text**: `text-gray-900 dark:text-white`
- **Buttons**: `bg-primary text-white rounded-lg hover:bg-primary-dark`
- **Responsive**: Grid layouts adapt to screen size

## Eddington Page

### Overview

The Eddington page (`/eddington/`) tracks the Eddington number, a distance-based achievement metric. The Eddington number is the maximum number **E** such that the athlete has covered at least **E km** on at least **E days**.

### Features

#### 1. Eddington Definition

Explains the concept:
- **Definition**: Maximum number E where athlete has done ≥E km on ≥E days
- **Example**: Eddington number of 70 means cycled ≥70 km on ≥70 occasions
- **Progression**: Moving from 70 to 75 requires more than 5 new long-distance workouts

#### 2. Discipline Filtering

Users can filter by workout discipline:
- **All**: Combined data from all disciplines
- **Cycling**: Only cycling workouts
- **Running**: Only running workouts
- **Rowing**: Only rowing workouts
- **Display**: Shows current Eddington number for each discipline

#### 3. Current Eddington Metrics

Three key statistics:
- **Current Eddington Number**: The calculated Eddington number (highlighted in orange)
- **Total Active Days**: Number of days with recorded distance data
- **Maximum Distance**: Longest single-day distance (in km)

#### 4. Times Completed vs. Distance Chart

Interactive Chart.js visualization showing:
- **Bar Chart**: Number of times each distance (km) was completed
- **Eddington Line**: Diagonal line (y = x) showing where times completed equals distance
- **Current Eddington Marker**: Highlighted point on the Eddington line
- **X-axis**: Distance in kilometers
- **Y-axis**: Times completed
- **Visualization**: Helps identify which distances need more completions

#### 5. History Chart

Line chart showing Eddington number progression over time:
- **X-axis**: Date (month/year format)
- **Y-axis**: Eddington number
- **Line**: Smooth curve showing growth over time
- **Tooltip**: Shows full date and Eddington number on hover
- **Fill**: Area under curve for visual emphasis

#### 6. Days Needed Grid

Grid showing how many more days needed for each distance milestone:
- **Distance Labels**: Each card shows distance in km (e.g., "70KM")
- **Days Needed**: Number of additional days required (0 if already achieved)
- **Achieved Indicator**: Checkmark (✓) for completed distances
- **Color Coding**: 
  - Orange: Days still needed
  - Green: Already achieved
- **Filtered Display**: Only shows distances up to current Eddington + 25 km

### Technical Implementation

#### Backend (`plans/views.py`)

**`eddington` view**:
- Filters workouts by discipline (if specified)
- Calculates Eddington data using `_calculate_eddington_data()`
- Generates discipline breakdown for filter tabs
- Handles "all" discipline (combines all disciplines)

**`_calculate_eddington_data(workouts)` function**:
- **Daily Max Distances**: Groups workouts by date, finds max distance per day
- **Eddington Calculation**: 
  - For each distance (km), counts how many days achieved that distance
  - Eddington number is the maximum distance where days ≥ distance
- **Times Completed Data**: For each distance, counts how many days achieved it
- **History Calculation**: 
  - Processes workouts chronologically
  - Calculates Eddington number at each point in time
  - Returns list of {date, eddington_number} objects
- **Days Needed**: For each distance, calculates how many more days needed to reach that distance threshold

**`_get_discipline_breakdown(user)` function**:
- Calculates Eddington data for each discipline separately
- Returns dictionary with discipline keys and their Eddington numbers
- Used to populate discipline filter tabs

#### Frontend Template (`templates/plans/eddington.html`)

**Structure**:
1. **Header**: Title and definition explanation
2. **Discipline Selector**: Filter tabs for discipline selection
3. **Metrics Cards**: Current Eddington, active days, max distance
4. **Times Completed Chart**: Bar chart with Eddington line overlay
5. **History Chart**: Line chart showing progression
6. **Days Needed Grid**: Responsive grid of distance milestones

**JavaScript**:
- **Chart.js Integration**: 
  - Times Completed Chart: Bar chart with line overlay
  - History Chart: Line chart with area fill
- **Dark Mode Support**: Charts automatically adapt to theme
- **Responsive**: Charts maintain aspect ratio on all screen sizes

### Eddington Calculation Algorithm

```python
def calculate_eddington(daily_max_distances):
    """
    Calculate Eddington number from daily max distances.
    
    Args:
        daily_max_distances: Dict mapping date -> max_distance_km
    
    Returns:
        int: Eddington number
    """
    # Count how many days achieved each distance
    distance_counts = defaultdict(int)
    for date, max_distance in daily_max_distances.items():
        # For each distance from 1 to max_distance, increment count
        for distance in range(1, int(max_distance) + 1):
            distance_counts[distance] += 1
    
    # Find maximum distance where count >= distance
    eddington = 0
    for distance in sorted(distance_counts.keys(), reverse=True):
        if distance_counts[distance] >= distance:
            eddington = distance
            break
    
    return eddington
```

### Data Models

Uses existing `Workout` model from `workouts/models.py`:
- **Distance Field**: `distance` (in miles, converted to km for Eddington)
- **Date Field**: `completed_date` or `recorded_date` for grouping
- **Discipline**: Filtered by `fitness_discipline` field

### Styling

Uses Tailwind CSS with dark mode support:
- **Cards**: `bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm p-6`
- **Text**: `text-gray-900 dark:text-white` for headings, `text-gray-600 dark:text-gray-400` for descriptions
- **Eddington Number**: `text-orange-500 dark:text-orange-400` (highlighted)
- **Achieved Milestones**: `text-green-600 dark:text-green-400`
- **Charts**: Dark mode colors adapt automatically
- **Responsive Grid**: `grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3`

### Chart Configuration

#### Times Completed Chart

```javascript
{
  type: 'bar',
  data: {
    labels: distances,  // [1, 2, 3, ..., max_distance]
    datasets: [
      {
        label: 'Times completed',
        data: timesCompleted,  // [count1, count2, ...]
        backgroundColor: 'rgba(249, 115, 22, 0.6)',
        borderColor: 'rgba(249, 115, 22, 1)',
        order: 2
      },
      {
        label: 'Eddington',
        data: eddingtonLineData,  // [1, 2, 3, ...] (y = x)
        type: 'line',
        borderColor: 'rgba(249, 115, 22, 1)',
        order: 1
      }
    ]
  }
}
```

#### History Chart

```javascript
{
  type: 'line',
  data: {
    labels: dates,  // Formatted dates
    datasets: [{
      label: 'Eddington Number',
      data: eddingtonNumbers,  // [e1, e2, e3, ...]
      borderColor: 'rgba(249, 115, 22, 1)',
      backgroundColor: 'rgba(249, 115, 22, 0.1)',
      fill: true,
      tension: 0.4
    }]
  }
}
```

## URL Patterns

### Recap URLs

- `/recap/` - Main recap page (user's view)
- `/recap/share/<token>/` - Public shared recap page
- `/recap/share/manage/` - API endpoint for share management

### Eddington URLs

- `/eddington/` - Main Eddington page
- `/eddington/?discipline=cycling` - Filtered by discipline
- `/eddington/?discipline=running` - Filtered by discipline
- `/eddington/?discipline=rowing` - Filtered by discipline
- `/eddington/?discipline=all` - All disciplines combined

## Admin Integration

### RecapShare Admin

Registered in `plans/admin.py`:
- **List Display**: user, year, is_enabled, view_count, created_at, last_viewed_at
- **List Filters**: year, is_enabled, created_at
- **Search Fields**: user__username, user__email, token
- **Readonly Fields**: token, created_at, updated_at, view_count, last_viewed_at
- **Raw ID Fields**: user (for performance)

## Security Considerations

### Share Links

- **Token Generation**: Uses `secrets.token_urlsafe(32)` for secure random tokens
- **Token Length**: 64 characters (URL-safe base64 encoding)
- **Unique Constraint**: Database-level uniqueness on token field
- **Indexed**: Token field is indexed for fast lookups
- **Disable Capability**: Users can disable share links without deleting them
- **View Tracking**: Tracks views for analytics (doesn't expose sensitive data)

### Access Control

- **Recap Page**: Requires authentication (user can only view their own recap)
- **Public Share**: No authentication required (token-based access)
- **Share Management**: Requires authentication (user can only manage their own shares)

## Performance Considerations

### Query Optimization

- **Recap View**: Uses `select_related()` for efficient related object fetching
- **Eddington View**: Filters workouts by discipline before processing
- **Date Grouping**: Efficient date-based grouping using Django ORM
- **Chart Data**: Pre-calculated in backend, passed as JSON to frontend

### Caching Opportunities

- **Year List**: Could cache available years per user
- **Eddington Calculation**: Could cache per user/discipline combination
- **Monthly Breakdown**: Could cache aggregated monthly data

## Future Enhancements

### Recap Page

- Additional statistics (pace zones, power zones breakdown)
- Comparison between years
- Export to PDF/image
- Social media sharing integration
- Customizable recap sections

### Eddington Page

- Multiple Eddington metrics (time-based, elevation-based)
- Goal setting and tracking
- Achievement badges
- Comparison with other users (anonymized)
- Historical trends by discipline

## Related Documentation

- [Workout Detail Page](./WORKOUT_DETAIL.md) - Individual workout analysis
- [Peloton Integration](./peloton.md) - Peloton API integration
- [Sync Strategy](./SYNC_STRATEGY.md) - Workout syncing process
