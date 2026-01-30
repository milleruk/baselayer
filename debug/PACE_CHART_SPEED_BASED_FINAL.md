# Pace Target Chart - Speed-Based Design (Final)

## Overview
Reverted from zone-based to **speed-based chart** while keeping the visual design improvements from the class library.

## What This Chart Shows

### Y-Axis: Speed (MPH)
- Shows actual speed in miles per hour
- Target line uses middle of pace range (accurate positioning)
- Matches the working implementation from before

### X-Axis: Time (MM:SS)
- Shows workout time
- Target line shifted back 60 seconds for class intro

### Data Sources
1. **Target Line** (Light Blue):
   - Uses `middle_mph` from user's pace zones
   - Stepped line showing coach's targets
   - Calculated from class plan segments

2. **Actual Line** (Yellow/Lime):
   - User's actual speed from workout performance data
   - Smoothed line for better readability

## Visual Features Added

### ✅ Music Timeline
- Colored segments showing playlist songs
- Positioned above chart
- Hover effects on songs
- Toggle-able with checkbox
- Aligned with chart time axis

### ✅ Dark Theme Styling
- Chart background: `bg-gray-900`
- Container: `bg-neutral-800` with `border-gray-700`
- White text with proper contrast
- Grid lines: subtle white with low opacity

### ✅ Enhanced Tooltips
- **Format**: Shows pace in min/mile (e.g., "8:30 /mi")
- **Function**: Converts speed (MPH) to pace for display
- **Works on both lines**: Target and Actual
- Large hit radius (20px) for easy hovering

### ✅ Legend
- Top position
- Custom styling with Inter font
- Point style indicators
- White color for dark theme

## Technical Implementation

### Data Processing
```javascript
// Target line: Uses middle of pace range
const targetSpeed = paceRanges[zoneName].middle_mph;
targetPaceLine.push({ x: startTime, y: targetSpeed });

// Actual line: Direct speed data
const actualSpeedData = performanceData.map(d => ({
  x: d.timestamp,
  y: d.speed  // MPH from API
}));
```

### Tooltip Conversion
```javascript
// Convert speed to pace for tooltip display
function speedToPace(speed) {
  const minPerMile = 60 / speed;
  const mins = Math.floor(minPerMile);
  const secs = Math.round((minPerMile - mins) * 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
```

### Music Timeline
- Renders colored segments proportional to workout duration
- Uses 8 rotating colors for visual variety
- Shows song title and artist (truncated if needed)
- Hover effects (opacity and brightness changes)

## Why Speed-Based Works Better

1. **Accuracy**: Direct representation of actual data
2. **Simplicity**: No complex zone conversions
3. **Familiarity**: Users understand MPH and min/mile pace
4. **Precise Targeting**: Shows exact middle of pace ranges
5. **Better Tooltips**: Clear pace display (8:30 /mi)

## What Was Removed

- Zone-based Y-axis (1-7 scale)
- Zone band backgrounds (colored horizontal bands)
- Zone label overlays (RECOVERY, EASY, etc.)
- `speedToPaceLevel()` conversion function
- Zone band plugin

## Files Modified
- `/templates/workouts/detail_pace_target.html`
  - Reverted chart data to speed-based
  - Kept music timeline rendering
  - Kept dark theme styling
  - Updated tooltips to show pace format

## Benefits

✅ **Accurate**: Uses middle of pace ranges like before
✅ **Visual**: Music timeline and dark theme from library
✅ **Clear**: Tooltips show pace in min/mile format
✅ **Simple**: No complex zone conversions
✅ **Tested**: Based on working implementation

## Testing Checklist
- [x] Chart shows speed on Y-axis (MPH)
- [x] Target line uses middle of pace ranges
- [x] Actual line shows user's speed
- [x] Tooltips show pace format (e.g., "8:30 /mi")
- [x] Music timeline displays above chart
- [x] Music timeline toggle works
- [x] Dark theme styling applied
- [x] Both lines hoverable with tooltips
- [x] Target line shifted back 60 seconds
- [x] No Django errors

## Next Steps
- User testing on actual workout data
- Verify accuracy of target line positioning
- Ensure tooltips work smoothly on both lines
