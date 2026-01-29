# Pace Target Metrics Update Fix

## Problem Identified
The metrics boxes (target zone, time in target) were not updating when the slider moved on Pace Target classes. This was due to:

1. **Incorrect lookup logic in `getCurrentTargetForTime()`** - Was using a simple min-distance comparison instead of binary search
2. **Duplicate PACE_LEVEL_NAMES definitions** - One global (correct) and one inside initTimer() with different labels
3. **No proper boundary checking** - Wasn't handling edge cases correctly

## Changes Made

### 1. Fixed `getCurrentTargetForTime()` Function (Line ~1200)
**Before:** Used simple loop to find closest point (could be off by seconds)
```javascript
// OLD: Finding closest point could get wrong zone
let closestIndex = 0;
let minDiff = Math.abs((targetLineData[0]?.timestamp || 0) - time);
for (let i = 1; i < targetLineData.length; i++) {
  // ...find closest...
}
```

**After:** Uses binary search to find exact point at or before current time
```javascript
// NEW: Binary search for exact time position
let left = 0, right = targetLineData.length - 1;
let selectedIndex = 0;
while (left <= right) {
  const mid = Math.floor((left + right) / 2);
  const midTime = targetLineData[mid]?.timestamp || 0;
  if (midTime <= time) {
    selectedIndex = mid;
    left = mid + 1;
  } else {
    right = mid - 1;
  }
}
```

### 2. Removed Duplicate `PACE_LEVEL_NAMES` (Line ~1338)
- Removed the local definition inside `initTimer()` that had incorrect labels
- Now uses the global definition with consistent labels
- Global definition: Recovery, Easy, Moderate, Challenging, Hard, Very Hard, Max

### 3. Improved Fallback Logic
- Better handling of edge cases when targetLineData not available
- Proper scale conversion (0-6 to 1-7 for display)
- More robust segment-based fallback

## Testing Instructions

### In Browser Console (https://chase.haresign.dev/workouts/library/2695/)

1. **Check targetLineData structure:**
```javascript
console.log('targetLineData length:', targetLineData?.length);
console.log('First 3 points:', targetLineData?.slice(0, 3));
console.log('Sample point keys:', targetLineData?.[0] ? Object.keys(targetLineData[0]) : 'none');
```

2. **Test getCurrentTargetForTime with different times:**
```javascript
// Test at various points in the workout
console.log('Target at 0s:', getCurrentTargetForTime(0));
console.log('Target at 300s:', getCurrentTargetForTime(300));
console.log('Target at 600s:', getCurrentTargetForTime(600));
console.log('Target at 1200s:', getCurrentTargetForTime(1200));
```

3. **Watch metrics update as slider moves:**
```javascript
// Open DevTools Elements tab and watch these:
// #current-target (should change as you drag slider)
// #interval-time (should change based on position in current zone)
// #time-left (should count down)
```

4. **Compare with Power Zone class (working reference):**
- Open https://chase.haresign.dev/workouts/library/2668/ (Power Zone)
- Drag slider and watch metrics update
- Then go back to 2695 and verify same behavior

## Expected Behavior After Fix

✅ When slider moves:
- **Current Target** updates to show correct pace level
- **Time in Target** updates to show how long in current pace level
- **Time Left** counts down correctly
- Chart updates to show correct progress position

✅ Metrics match the timeline:
- If slider is on a "Hard" segment, shows "Hard (Level 5)"
- If slider is at start of new segment, time in target resets
- Colors in chart align with metrics box

## Debugging Telemetry

The code includes debug logging that sends to:
`http://localhost:7242/ingest/2d1a7245-2209-4ba5-a6cc-73ffb0303c5e`

This logs:
- `getCurrentTargetForTime` calls with time, selected index, and found pace zone
- `updateProgress` calls showing current time and target
- Slider input events showing progress percentage

You can ignore these if not monitoring, or remove them later by searching for `#region agent log` and removing those fetch calls.

## Files Modified
- `/opt/projects/pelvicplanner/templates/workouts/partials/pace_target_content.html`
  - Fixed `getCurrentTargetForTime()` function (~1200)
  - Removed duplicate `PACE_LEVEL_NAMES` (was at ~1338)
  - Added debug logging for troubleshooting
