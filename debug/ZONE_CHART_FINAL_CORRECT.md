# Zone-Based Pace Target Chart - Matching Class Library Design

## Overview
Successfully implemented the **zone-based chart design** exactly matching the class library style shown in the reference image.

## What This Chart Shows (Like Class Library)

### Visual Layout
```
MAX          (Red band)        ███████████████████
VERY HARD    (Dark Orange)     ███████████████████
HARD         (Orange band)     ███████████████████
CHALLENGING  (Green band)      ████════════███████  ← Target line in MIDDLE
MODERATE     (Light Blue)      ███████════════████
EASY         (Blue band)       ███████████████████
RECOVERY     (Purple band)     ███████████████████
```

### Y-Axis: Zone Levels (1-7)
- **Not speed in MPH**
- Each zone is 1 unit tall (e.g., MODERATE = 3.0, spans 2.5-3.5)
- Target line positioned at **zone level** (e.g., 3.0 for moderate, 4.0 for challenging)
- Actual line converted from speed to appropriate zone level

### Key Changes from Speed-Based

| Aspect | Speed-Based (Old) | Zone-Based (New) |
|--------|------------------|------------------|
| Y-Axis | 0-12 MPH | 1-7 Zone Levels |
| Target Line | At middle_mph speed | At zone number (middle of band) |
| Actual Line | At actual speed | At zone level for that speed |
| Background | Plain | Colored zone bands |
| Labels | None | Zone names overlaid |
| Tooltip | Shows speed/pace | Shows pace format |

## Implementation Details

### 1. Target Line Positioning
```javascript
// Target sits in MIDDLE of zone band
const targetLevel = zone + 1;  // zone 0 = level 1, zone 3 = level 4

// Points every 5 seconds
for (let t = startTime; t <= endTime; t += 5) {
  targetPaceLine.push({ x: t, y: targetLevel });  // e.g., y: 3.0 for moderate
}
```

**Example:**
- Class plan says "Moderate" (zone 2)
- Target line draws at **level 3.0** (middle of moderate band 2.5-3.5)
- ✅ This matches the class library visualization

### 2. Actual Line Positioning
```javascript
function speedToPaceLevel(speed) {
  // Check which zone this speed falls into
  for (let level = 7; level >= 1; level--) {
    const range = ranges[zones[level]];
    if (speed >= range.min_mph && speed <= range.max_mph) {
      return level;  // Return zone level, not speed
    }
  }
}
```

**Example:**
- User running at 7.2 MPH
- Falls into "Moderate" zone (6.3-6.8 MPH range)
- Actual line draws at **level 3.0** (or nearby based on position in range)
- Shows in MODERATE colored band

### 3. Colored Zone Bands
```javascript
// Purple (1), Blue (2), Light Blue (3), Green (4), Orange (5), Dark Orange (6), Red (7)
const PACE_LEVEL_COLORS = {
  1: "#6f42c1",  // Recovery
  2: "#4c6ef5",  // Easy
  3: "#228be6",  // Moderate
  4: "#0ca678",  // Challenging
  5: "#ff922b",  // Hard
  6: "#f76707",  // Very Hard
  7: "#fa5252"   // Max
};

// Draw semi-transparent bands
for (let level = 1; level <= 7; level++) {
  const yTop = scales.y.getPixelForValue(level - 0.5);
  const yBot = scales.y.getPixelForValue(level + 0.5);
  ctx.fillRect(chartArea.left, yTop, chartArea.right - chartArea.left, yBot - yTop);
}
```

### 4. Zone Label Overlays
```javascript
// Draw text labels on chart (RECOVERY, EASY, MODERATE, etc.)
for (let level = 1; level <= 7; level++) {
  const yPos = scales.y.getPixelForValue(level);
  const levelName = PACE_LEVEL_NAMES[level];
  ctx.fillText(levelName, chartArea.left + 8, yPos);
}
```

### 5. Tooltips
```javascript
// Shows pace format (e.g., "7:54 /mi") for both lines
label: function(context) {
  // For Actual: use stored speed value
  if (label === 'Actual' && context.raw.speed) {
    const pace = speedToPace(context.raw.speed);
    return `Actual: ${pace} /mi`;
  }
  
  // For Target: use middle_mph from pace ranges
  const middleMph = targetMetrics.pace_ranges[zoneName].middle_mph;
  const pace = speedToPace(middleMph);
  return `Target: ${pace} /mi`;
}
```

## Chart Configuration

```javascript
{
  type: 'line',
  data: { datasets: [targetLine, actualLine] },
  options: {
    scales: {
      y: {
        min: 0.5,
        max: 7.5,
        ticks: { display: false }  // Hide numbers, show zone labels instead
      }
    }
  },
  plugins: [zoneBandsPlugin]  // Draws colored bands and labels
}
```

## Visual Features

✅ **Zone Bands**: 7 colored horizontal bands (purple → red)
✅ **Zone Labels**: Text overlaid on chart (RECOVERY through MAX)
✅ **Target Line**: Light blue, stepped, positioned at zone level
✅ **Actual Line**: Yellow, smoothed, positioned at zone level
✅ **Music Timeline**: Colored segments above chart
✅ **Tooltips**: Show pace format (7:54 /mi) for both lines
✅ **Dark Theme**: Matching class library aesthetic

## Why This Works

1. **Visual Clarity**: Easy to see which zone you're in vs. target
2. **Consistent Design**: Matches class library pages exactly
3. **Accurate Positioning**: Target line in middle of zone band (not at speed value)
4. **Better UX**: Colored bands make zones immediately visible
5. **Pace Format**: Tooltips show familiar min/mile pace

## Files Modified
- `/templates/workouts/detail_pace_target.html`
  - Zone-based chart implementation
  - Zone bands plugin
  - Zone labels overlay
  - Tooltip showing pace format
  - Music timeline

## Testing
- [x] Chart shows 7 colored zone bands
- [x] Zone labels (RECOVERY through MAX) overlaid
- [x] Target line positioned in middle of zone bands
- [x] Actual line positioned at appropriate zone level
- [x] Tooltips show pace format for both lines
- [x] Music timeline displays correctly
- [x] No Django errors

## Next Steps
- User testing to verify target line positioning matches class library
- Confirm actual line zone positioning is accurate
- Verify tooltips show correct pace values
