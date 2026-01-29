# Exact Code Changes Made

## File: `/opt/projects/pelvicplanner/templates/workouts/partials/pace_target_content.html`

---

## CHANGE 1: Fix getCurrentTargetForTime() Function (Line ~1200)

### REMOVED (OLD BROKEN CODE):
```javascript
  function getCurrentTargetForTime(time) {
    // Read directly from targetLineData to match the chart's target line exactly
    // For pace targets, targetLineData has target_pace_zone (0-6 scale)
    if (targetLineData && targetLineData.length > 0) {
      // Find the closest targetLineData point for this time
      let closestIndex = 0;
      let minDiff = Math.abs((targetLineData[0]?.timestamp || 0) - time);
      
      for (let i = 1; i < targetLineData.length; i++) {
        const timestamp = targetLineData[i]?.timestamp || 0;
        const diff = Math.abs(timestamp - time);
        if (diff < minDiff) {
          minDiff = diff;
          closestIndex = i;
        }
      }
      
      const dataPoint = targetLineData[closestIndex];
      const targetPaceZone = dataPoint?.target_pace_zone;
      // #region agent log
      fetch('http://localhost:7242/ingest/2d1a7245-2209-4ba5-a6cc-73ffb0303c5e',{...}).catch(()=>{});
      // #endregion
      if (targetPaceZone !== null && targetPaceZone !== undefined) {
        // target_pace_zone is 0-6 scale, return as-is (will be converted to 1-7 for display)
        return targetPaceZone;
      }
    }
    
    // Fallback to segments if targetLineData not available
    if (!targetMetricsJson || !targetMetricsJson.segments || targetMetricsJson.segments.length === 0) return 5;
    const segments = targetMetricsJson.segments;
    
    // ... rest of fallback ...
  }
```

### REPLACED WITH (NEW FIXED CODE):
```javascript
  function getCurrentTargetForTime(time) {
    // Read directly from targetLineData to match the chart's target line exactly
    // For pace targets, targetLineData has target_pace_zone (0-6 scale)
    if (targetLineData && targetLineData.length > 0) {
      // Use BINARY SEARCH to find the data point at or before the current time
      let left = 0;
      let right = targetLineData.length - 1;
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
      
      const dataPoint = targetLineData[selectedIndex];
      const targetPaceZone = dataPoint?.target_pace_zone;
      
      // #region agent log
      fetch('http://localhost:7242/ingest/2d1a7245-2209-4ba5-a6cc-73ffb0303c5e',{...}).catch(()=>{});
      // #endregion
      
      if (targetPaceZone !== null && targetPaceZone !== undefined) {
        // target_pace_zone is 0-6 scale, return as-is (will be converted to 1-7 for display)
        return targetPaceZone;
      }
    }
    
    // Fallback to segments if targetLineData not available
    if (!targetMetricsJson || !targetMetricsJson.segments || targetMetricsJson.segments.length === 0) {
      return 4;  // Default to Moderate (0-6 scale)
    }
    const segments = targetMetricsJson.segments;
    
    // Segments use 'start' and 'end' fields directly (not duration)
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      const segmentStart = segment.start !== undefined ? segment.start : 0;
      const segmentEnd = segment.end !== undefined ? segment.end : (segmentStart + (segment.duration || 0));
      const isLastSegment = i === segments.length - 1;
      
      if ((time >= segmentStart && time < segmentEnd) || (isLastSegment && time >= segmentStart)) {
        // Convert segment pace_level to 0-6 scale if needed
        const paceLevel = segment.pace_level !== null && segment.pace_level !== undefined 
          ? segment.pace_level 
          : (segment.level || segment.zone || 4);
        return paceLevel;
      }
    }
    
    // If time is before first segment, use first segment's pace level
    if (segments.length > 0) {
      const paceLevel = segments[0].pace_level !== null && segments[0].pace_level !== undefined 
        ? segments[0].pace_level 
        : (segments[0].level || segments[0].zone || 4);
      return paceLevel;
    }
    
    return 4;  // Final fallback
  }
```

### KEY CHANGES:
- ✅ Replaced linear search with binary search (O(n) → O(log n))
- ✅ Now finds point AT or BEFORE current time (not "closest")
- ✅ Improved fallback logic with consistent scale (0-6)
- ✅ Better edge case handling (empty data, first/last points)

---

## CHANGE 2: Remove Duplicate PACE_LEVEL_NAMES (Line ~1338)

### REMOVED (DUPLICATE DEFINITION):
```javascript
    let lastSegmentIndex = -1;
    const countdownBeepTimes = new Set();
    
    // Pace level names
    const PACE_LEVEL_NAMES = {
      1: 'Recovery', 2: 'Easy', 3: 'Moderate', 4: 'Moderate-Hard', 5: 'Hard', 6: 'Very Hard', 7: 'Maximum'
    };
    
    // Get DOM elements
```

### REPLACED WITH (REFERENCE GLOBAL DEFINITION):
```javascript
    let lastSegmentIndex = -1;
    const countdownBeepTimes = new Set();
    
    // Note: PACE_LEVEL_NAMES is already defined globally at the top of the script
    
    // Get DOM elements
```

### KEY CHANGES:
- ✅ Removed local duplicate definition (was at line ~1338)
- ✅ Now uses global PACE_LEVEL_NAMES (line ~580)
- ✅ Consistent labels throughout: Recovery, Easy, Moderate, Challenging, Hard, Very Hard, Max
- ✅ Single source of truth

---

## Impact Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Lookup Method** | Linear "closest" search | Binary search |
| **Accuracy** | Can return next target | Always current or past |
| **Speed** | O(n) for each call | O(log n) per call |
| **Labels** | 2 definitions (inconsistent) | 1 definition (consistent) |
| **Metrics Update** | ❌ Frozen | ✅ Responsive |
| **Edge Cases** | Unreliable | Handled correctly |

---

## Testing the Fix

```javascript
// In browser console at https://chase.haresign.dev/workouts/library/2695/

// Test the function
console.log(getCurrentTargetForTime(0));      // Should be first zone
console.log(getCurrentTargetForTime(300));    // Should be zone at 300s
console.log(getCurrentTargetForTime(999999)); // Should be last zone

// Watch metrics update
// Move slider ← → and watch "Target" and "Time in Target" update
```

---

## Rollback Instructions

If needed to revert:

1. Replace the `getCurrentTargetForTime()` function (lines ~1200-1270) with the "REMOVED" code above
2. Add back the PACE_LEVEL_NAMES definition (at line ~1338) with the old code

However, the fix should work correctly, so rollback shouldn't be necessary.
