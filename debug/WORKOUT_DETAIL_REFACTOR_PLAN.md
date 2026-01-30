# Workout Detail Page Refactor Plan

## Current Problem
- Single `detail.html` template: **1688 lines**
- Massive conditionals for 3 workout types
- JS and CSS overlapping causing conflicts
- Difficult to maintain and debug

## Solution: 3 Separate Templates

### 1. **detail_general.html** (✅ Created - 269 lines)
**For:** General cycling workouts, strength, yoga, meditation, etc.

**Features:**
- Common header (title, instructor, duration, dates)
- Basic workout metrics (output, speed, distance, HR, calories)
- Simple performance chart (output + heart rate)
- Playlist
- Clean Chart.js implementation

**When to use:** All non-power-zone, non-pace-target workouts

---

### 2. **detail_power_zone.html** (To Create)
**For:** Power Zone cycling classes

**Features:**
- Common header
- Power Zone specific metrics (TSS, FTP-based zones, time in zones)
- Power Zone timeline chart with:
  - Target power line overlay
  - Zone color bands
  - Music timeline integration
  - Chart controls (hide/show target, save, zone colors)
- Power Profile (5s, 1m, 5m, 20m peaks)
- Zone Distribution breakdown
- Zone Targets vs Actual comparison
- Performance notes specific to power training

**Dedicated JS/CSS:**
- Power zone chart configuration
- Zone color management
- Target line calculations
- No conflicts with pace target code

---

### 3. **detail_pace_target.html** (To Create)
**For:** Running and Walking classes

**Features:**
- Common header
- Pace-specific metrics (avg pace, distance, elevation)
- Pace Target timeline chart with:
  - Target pace overlay
  - Pace zone color bands
  - Music timeline integration
- Pace Distribution (time in each zone)
- Pace Targets vs Actual
- Running/Walking specific analysis

**Dedicated JS/CSS:**
- Pace chart configuration
- Pace zone management (running vs walking)
- Min/mile pace calculations
- No conflicts with power zone code

---

## View Logic Update

```python
def workout_detail(request, pk):
    # ... existing logic ...
    
    # Determine workout type and template
    template_name = 'workouts/detail_general.html'  # default
    
    if workout.ride_detail:
        ride_detail = workout.ride_detail
        
        # Power Zone Class
        if ride_detail.is_power_zone_class or ride_detail.class_type == 'power_zone':
            template_name = 'workouts/detail_power_zone.html'
        
        # Pace Target Class (Running/Walking)
        elif ride_detail.fitness_discipline in ['running', 'walking', 'run', 'walk']:
            template_name = 'workouts/detail_pace_target.html'
    
    # ... existing context ...
    
    return render(request, template_name, context)
```

## Benefits

1. **Maintainability**: Each template is ~250-350 lines instead of 1688
2. **No JS Conflicts**: Dedicated Chart.js configs per workout type
3. **No CSS Conflicts**: Unique class names and styles per type
4. **Performance**: Load only relevant JS/CSS for workout type
5. **Clarity**: Easy to find and modify specific workout type features
6. **Debugging**: Simpler to isolate issues
7. **Future-proof**: Easy to add new workout types

## File Structure

```
templates/workouts/
├── detail.html (backup/rename to detail_old.html)
├── detail_general.html ✅ (269 lines)
├── detail_power_zone.html 🔨 (to create ~350 lines)
└── detail_pace_target.html 🔨 (to create ~300 lines)
```

## Migration Strategy

1. ✅ Create `detail_general.html` template
2. 🔨 Create `detail_power_zone.html` template
3. 🔨 Create `detail_pace_target.html` template
4. 🔨 Update `workouts/views.py` workout_detail() to route to correct template
5. 🧪 Test all 3 workout types
6. 🗑️ Rename old `detail.html` to `detail_old.html` (keep as backup)
7. ✅ Commit changes

## Testing Checklist

- [ ] General workout displays correctly (Cycling, Strength, Yoga)
- [ ] Power Zone workout shows correct zones and target line
- [ ] Running workout shows pace zones correctly
- [ ] Walking workout shows walking-specific pace zones
- [ ] Charts render without errors
- [ ] Music timeline works on all types
- [ ] No JS console errors
- [ ] Performance data loads correctly
- [ ] Playlists display properly

## Timeline

Total estimated lines: ~900-950 (vs current 1688)
Reduction: **~44% code reduction** with clearer separation!
