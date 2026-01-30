# Workout Template Refactor - Simplified Approach

## Problem
The current `detail.html` has 1688 lines with massive JavaScript sections that are hard to maintain and debug.

## Solution Strategy

Instead of copying all the complex JS, let's create **clean, modern templates** that:
1. Use the same header/metrics structure
2. Have focused, minimal JavaScript
3. Load Chart.js configurations from external files if needed
4. Focus on readability and maintainability

## Implementation Plan

### Phase 1: Create Templates (Now)
Create 3 template files with:
- ✅ `detail_general.html` (269 lines) - DONE
- 🔨 `detail_power_zone.html` (~350 lines) - Create minimal version
- 🔨 `detail_pace_target.html` (~300 lines) - Create minimal version

### Phase 2: Update View (Now)
Modify `workout_detail()` to route to correct template based on:
```python
if workout.ride_detail.is_power_zone_class:
    template = 'workouts/detail_power_zone.html'
elif workout.ride_detail.fitness_discipline in ['running', 'walking']:
    template = 'workouts/detail_pace_target.html'
else:
    template = 'workouts/detail_general.html'
```

### Phase 3: Test & Debug (Next)
- Test each workout type
- Fix any rendering issues
- Optimize JavaScript
- Add missing features incrementally

## Current Status

**✅ Completed:**
- General workout template created
- Status documentation created
- Plan documented

**🔨 Next Up:**
I need to create 2 more templates. Given token limits, I suggest:

**Option A (Recommended):** Create minimal working versions now, test them, then enhance
**Option B:** Take time to extract all features from original (risk of errors/conflicts)

I recommend **Option A** - let's get the basic structure working, then we can iterate and add the complex features (power profile, zone analysis, etc.) in the next session after testing the basics.

## Minimal Feature Set (Phase 1)

### detail_power_zone.html (Minimal)
- Header
- TSS metric
- Basic power zone chart (7 zones)
- Simple zone distribution
- Playlist

### detail_pace_target.html (Minimal)
- Header
- Pace metrics
- Basic pace zone chart
- Simple pace distribution
- Playlist

**We can add these later** (Phase 2):
- Power profile (5s, 1m, 5m, 20m)
- Detailed zone targets
- Class notes
- Music timeline overlay
- Advanced chart controls

This approach gets us:
1. ✅ Working templates quickly
2. ✅ Can test the routing logic
3. ✅ Can identify issues early
4. ✅ Can add features incrementally

**Should I proceed with minimal templates now, or do you want full-featured templates?**
