# Pace Target Zone-Based Chart Implementation - Complete

## Overview
Successfully converted the pace target workout detail page from a speed-based chart to a **zone-based chart** design matching the class library style.

## What Changed

### 1. Chart Type: Speed → Zone Scale
**Before:** Y-axis showed speed in MPH (0-12 mph)
**After:** Y-axis shows pace levels 1-7 (Recovery through Max)

### 2. Visual Design
- **Zone Bands**: Semi-transparent colored bands for each pace level (1-7)
- **Zone Labels**: Text labels overlaid on the chart (RECOVERY, EASY, MODERATE, etc.)
- **Music Timeline**: Colored song segments above the chart showing playlist
- **Dark Theme**: Consistent with class library aesthetic

### 3. Data Conversion
- **Target Line**: Uses segments from class plan, converts zones (0-6) to display levels (1-7), stepped line style
- **Actual Performance**: Converts user's speed data (MPH) to pace levels based on their custom pace ranges
- **Time Shift**: Target line shifted back 60 seconds to account for class intro

### 4. Chart Features
- **Zone Band Colors**:
  - Level 1 (Recovery): Purple `#6f42c1`
  - Level 2 (Easy): Blue `#4c6ef5`
  - Level 3 (Moderate): Light Blue `#228be6`
  - Level 4 (Challenging): Green `#0ca678`
  - Level 5 (Hard): Orange `#ff922b`
  - Level 6 (Very Hard): Dark Orange `#f76707`
  - Level 7 (Max): Red `#fa5252`

- **Target Line**: Light blue `#93c5fd`, stepped (not smoothed)
- **Actual Line**: Yellow/lime `#e0fe48`, slightly smoothed

### 5. Music Timeline
- Displays playlist songs as colored horizontal segments
- Shows song title and artist
- Hover effects for better UX
- Toggle-able via checkbox
- Aligned with chart time axis

### 6. Tooltips
- Show time (MM:SS format)
- Display pace level names (e.g., "RECOVERY", "HARD")
- Clean, dark-themed design

## Technical Implementation

### Chart.js Configuration
```javascript
type: 'line'
data: { datasets: [targetLine, actualLine] }
scales: {
  x: { type: 'linear', min: 0, max: workoutDuration }
  y: { type: 'linear', min: 0.5, max: 7.5 }  // Zone scale
}
plugins: [zoneBandsPlugin]  // Custom plugin for bands and labels
```

### Data Processing
1. **Target Metrics**: Uses `segment.zone` from class plan
2. **Actual Speed**: Converts MPH to pace level using `pace_ranges` from user profile
3. **Pace Ranges**: Min/Max MPH for each zone from user's pace level settings

### Helper Functions
- `speedToPaceLevel(speed)`: Converts MPH to zone level (1-7)
- `formatTime(seconds)`: Converts seconds to MM:SS format
- `zoneBandsPlugin`: Custom Chart.js plugin for zone backgrounds and labels

## Files Modified
- `/templates/workouts/detail_pace_target.html`
  - Chart HTML structure (added music timeline)
  - Complete JavaScript rewrite for zone-based rendering
  - CSS updates for music timeline

## Benefits
1. **Visual Clarity**: Easier to see which pace zone user was in vs. target
2. **Consistent Design**: Matches class library pages exactly
3. **Better UX**: Music timeline provides context for class sections
4. **Accurate Mapping**: Uses user's custom pace zones from profile

## Testing Checklist
- [ ] View a pace target workout (running or walking)
- [ ] Verify chart shows 7 horizontal zone bands with labels
- [ ] Confirm target line (stepped, light blue) displays correctly
- [ ] Confirm actual performance line (smoothed, yellow) displays correctly
- [ ] Check music timeline shows songs above chart
- [ ] Test music timeline toggle checkbox
- [ ] Hover over chart to see tooltips (should show zone names)
- [ ] Verify time axis matches workout duration
- [ ] Test with different pace levels (1-10)

## Known Limitations
- Requires performance data to show actual line
- Requires target metrics (segments) from class plan for target line
- Pace range conversion assumes user has pace settings configured

## Next Steps
- User testing and feedback
- Consider adding similar design to walking workouts
- Potentially add zone distribution summary (time in each zone)
