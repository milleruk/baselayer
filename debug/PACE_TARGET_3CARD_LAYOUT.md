# Pace Target Workout - 3-Card Layout Added

## Overview
Added a 3-card layout to the pace target workout detail page, matching the class library design.

## New Layout Structure

### Grid Layout (3 Cards)
```
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│  Main Set Pace Targets  │     Class Notes         │      Pace Level         │
│  • Overall achievement  │  • Hard — 0:28 total    │      [Circle: 8]        │
│  • Zone progress bars   │  • Challenging — 18:26  │   YOUR PACE LEVEL       │
│  • Time in each zone    │  • Moderate — 0:29      │  Based on your profile  │
│                         │  • Easy — 1:29          │                         │
│                         │  • Recovery — 8:52      │                         │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

## Card 1: Main Set Pace Targets

**Purpose:** Shows how well you achieved the pace targets for each zone

**Features:**
- **Overall Achievement Bar**: Gradient cyan-to-teal progress bar showing overall performance
- **Percentage Display**: Large number showing achievement percentage
- **Zone Breakdown**: Individual progress bars for each zone with:
  - Zone name (Recovery, Easy, Moderate, etc.)
  - Time spent in zone
  - Percentage of total time
  - Color-coded bars matching zone colors:
    - Recovery: Purple `bg-purple-500`
    - Easy: Blue `bg-blue-500`
    - Moderate: Sky `bg-sky-500`
    - Challenging: Green `bg-green-500`
    - Hard: Orange `bg-orange-500`
    - Very Hard: Dark Orange `bg-orange-600`
    - Max: Red `bg-red-500`

**Data Source:** `zone_distribution` context variable

## Card 2: Class Notes

**Purpose:** Shows the workout structure from the class plan

**Features:**
- Lists each section of the workout
- Shows section name and duration
- Shows number of blocks in each section
- Format: `[Zone] • [Zone] — [duration] total ([X] block[s])`

**Example:**
```
Hard • Hard — 0:28 total (1 block)
Challenging • Challenging — 18:26 total (5 blocks)
Moderate • Moderate — 0:29 total (1 block)
Easy • Easy — 1:29 total (1 block)
Recovery • Recovery — 8:52 total (8 blocks)
```

**Data Source:** `class_sections` context variable

## Card 3: Pace Level

**Purpose:** Shows the user's current pace level setting

**Features:**
- Large circular badge with gradient background
  - Gradient: `from-blue-400 to-blue-600`
  - Size: 128px x 128px
- Large number displaying pace level (1-10)
- Label: "YOUR PACE LEVEL"
- Explanation text: "Based on your profile settings. Adjust in your profile to change pace targets."

**Data Source:** `user_pace_level` context variable

## Playlist Styling

**Updated to match class library design:**

**Features:**
- Numbered badges (1, 2, 3...) on the left
- Album artwork (if available)
- Song title (bold)
- Artist names (smaller, gray)
- Song title repeated (even smaller, lighter gray)
- Duration/timestamp on the right
- Hover effect: light background change
- Clean, minimal spacing

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ Class Playlist                       12 songs   │
├─────────────────────────────────────────────────┤
│ [1] [Album] Song Title            01:00         │
│             Artist Name                          │
│             Song Title                           │
├─────────────────────────────────────────────────┤
│ [2] [Album] Next Song             04:04         │
│             Artist Name                          │
│             Song Title                           │
└─────────────────────────────────────────────────┘
```

## Responsive Design

**Desktop (lg and up):** 3-column grid
```css
grid-cols-1 lg:grid-cols-3
```

**Tablet/Mobile:** Single column stack
- Main Set Pace Targets (full width)
- Class Notes (full width)
- Pace Level (full width)

## Styling Details

### Cards
- Background: `bg-white dark:bg-gray-800`
- Border: `border border-gray-200 dark:border-gray-700`
- Padding: `p-6`
- Shadow: `shadow-sm`
- Rounded: `rounded-lg`
- Gap between cards: `gap-6`

### Typography
- Card titles: `text-lg font-semibold`
- Zone names: `text-sm font-medium`
- Time/percentage: `text-xs`
- Pace level number: `text-5xl font-bold`

### Colors (Dark Theme)
- Text: `text-gray-900 dark:text-white`
- Subtext: `text-gray-700 dark:text-gray-300`
- Muted text: `text-gray-500 dark:text-gray-400`

## Context Variables Required

From Django view (`workout_detail`):

1. **`zone_distribution`** (list)
   - Each item contains:
     - `zone`: string (e.g., "moderate")
     - `zone_display`: string (e.g., "Moderate")
     - `time_str`: string (e.g., "18:26")
     - `percentage`: float (e.g., 94.9)

2. **`class_sections`** (dict)
   - Keys: section identifiers
   - Values: dict containing:
     - `name`: string
     - `duration`: int (seconds)
     - `segments`: list

3. **`user_pace_level`** (int)
   - User's current pace level (1-10)

4. **`playlist`** (object)
   - `songs`: QuerySet/list
     - Each song has:
       - `title`: string
       - `artists`: list with `artist_name`
       - `album_image_url`: string (optional)
       - `start_time_offset`: int (optional)

## Files Modified
- `/templates/workouts/detail_pace_target.html`
  - Added 3-card grid layout
  - Updated playlist styling
  - Maintained existing dark/light theme support

## Benefits

1. **Better UX**: Quick overview of workout performance
2. **Visual Clarity**: Color-coded progress bars for each zone
3. **Context**: See what pace level was used for the workout
4. **Class Structure**: Understand workout breakdown at a glance
5. **Consistent Design**: Matches class library aesthetic

## Next Steps
- Verify `class_sections` context variable is passed from view
- Test responsiveness on mobile/tablet
- Ensure `zone_distribution` calculation is correct
- Verify playlist data includes all necessary fields
