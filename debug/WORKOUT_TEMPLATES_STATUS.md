# Workout Detail Templates - Creation Status

## Overview
Splitting the monolithic 1688-line `detail.html` into 3 focused templates.

## Progress

### ✅ COMPLETED: detail_general.html (269 lines)
**File**: `/opt/projects/pelvicplanner/templates/workouts/detail_general.html`

**For**: General workouts (cycling, strength, yoga, meditation, etc.)

**Includes**:
- Common workout header (title, instructor, duration, badges, action buttons)
- Workout dates (recorded, completed)
- Basic metrics card (output, speed, distance, HR, calories, cadence, resistance)
- Simple dual-axis performance chart (Output + Heart Rate)
- Playlist section with song details
- Description section
- Clean Chart.js implementation (no zone complexity)

**Testing**: Ready to test

---

### 🔨 IN PROGRESS: detail_power_zone.html
**Target**: ~350-400 lines

**Structure** (what needs to be included):
1. Common header (same as general)
2. Power Zone-specific metrics:
   - TSS (Training Stress Score) + TSS Target
   - Average Output, Max Output
   - Time in each zone
3. **Power Zone Timeline Chart**:
   - Zone color bands (7 zones)
   - Target power line overlay
   - Music timeline (optional toggle)
   - Chart controls (Hide/Show Target, Save, Zone Colors toggle)
4. **Power Profile Card**:
   - 5-second peak power
   - 1-minute peak power
   - 5-minute peak power
   - 20-minute peak power
5. **Zone Targets Card**:
   - Overall completion percentage
   - Time spent in each target zone
   - Visual progress bars per zone
6. **Class Notes Card**:
   - Segment breakdown by zone
   - Block count per zone
7. Playlist (same as general)
8. Description (same as general)

**JavaScript Needs**:
- Power zone chart with 7-zone color mapping
- Target line calculation from segments
- Zone band rendering
- Music timeline integration
- Chart controls event listeners

**Unique CSS Classes**:
- `.power-zone-chart`
- `.zone-band-z1` through `.zone-band-z7`
- `.power-profile-card`

---

### 🔨 IN PROGRESS: detail_pace_target.html
**Target**: ~300-350 lines

**Structure** (what needs to be included):
1. Common header (same as general)
2. Pace-specific metrics:
   - Average pace (min/mile)
   - Average speed (mph)
   - Distance
   - Time in each pace zone
3. **Pace Target Timeline Chart**:
   - Pace zone color bands (7 for running, 5 for walking)
   - Target pace line overlay
   - Music timeline (optional toggle)
   - Chart controls
4. **Pace Targets Card**:
   - Overall completion percentage
   - Time spent in each target pace zone
   - Visual progress bars per zone
5. **Pace Class Notes Card**:
   - Segment breakdown by pace zone
   - Block count per zone
6. **User Pace Level Card**:
   - Display user's pace level (1-10)
   - Note about profile settings
7. Playlist (same as general)
8. Description (same as general)

**JavaScript Needs**:
- Pace zone chart with dynamic zone count (running=7, walking=5)
- Pace zone color mapping (different from power zones)
- Target pace line calculation
- Min/mile pace formatting
- Walking vs Running detection

**Unique CSS Classes**:
- `.pace-target-chart`
- `.pace-zone-recovery` through `.pace-zone-max`
- `.pace-level-card`

---

## Next Steps

### Immediate (Current Session):
1. Create `detail_power_zone.html` template
2. Create `detail_pace_target.html` template
3. Update `workout_detail()` view to route to correct template
4. Test basic rendering of all 3 templates

### Testing Phase (Next Session):
1. Test with real power zone workout
2. Test with running workout
3. Test with walking workout
4. Test with general cycling workout
5. Verify charts render correctly
6. Check for JS errors
7. Verify music timelines work
8. Test chart controls

### Cleanup:
1. Rename `detail.html` to `detail_old.html`
2. Update any references
3. Remove unused CSS/JS
4. Document changes

## Key Considerations

### Common Elements to Extract (DRY):
- Header section (title, instructor, dates, badges)
- Playlist section (identical across all)
- Description section (identical across all)
- Base Chart.js setup

### Template-Specific Elements:
- **Power Zone**: Zone calculations, FTP-based targets, power profile
- **Pace Target**: Pace calculations, min/mile formatting, running vs walking zones
- **General**: Simplified metrics, basic charts

### JavaScript Organization:
Each template will have its own `<script>` block with:
- Performance data initialization
- Chart configuration specific to workout type
- Event listeners for controls
- No shared JS variables that could conflict

## Benefits Recap

1. **Clarity**: Each template is ~250-400 lines vs 1688
2. **No Conflicts**: Separate JS/CSS namespaces
3. **Maintainability**: Easy to modify one workout type
4. **Performance**: Load only relevant code
5. **Debugging**: Isolate issues by workout type
6. **Future-proof**: Easy to add new workout types (e.g., rowing, bootcamp)

## File Sizes Comparison

```
Before:
detail.html: 1688 lines

After:
detail_general.html: 269 lines ✅
detail_power_zone.html: ~350 lines (estimated) 🔨
detail_pace_target.html: ~300 lines (estimated) 🔨
TOTAL: ~919 lines (45% reduction)
```

Plus better organization and zero conflicts!
