# Pace Target Cards Data Fix

## Issue
The 2x2 grid cards were empty because the template was looking for `zone_distribution` and `class_sections`, but pace target workouts store this data in `pace_targets` and `pace_class_notes`.

## Variables Fixed

### 1. Class Info Card (Top-Left)
**Changed:**
- `{{ ride.workout_type.name }}` → `{{ workout.fitness_discipline }}`

**Now shows:**
- Discipline: Running/Walking
- Type: Pace Target
- TSS (if available)
- IF - Intensity Factor (if available)  
- Your Pace Level: Level 9

### 2. Instructor Card (Top-Right)
**Changed:**
- `{% if ride.instructor %}` → `{% if workout.instructor_name %}`
- `{{ ride.instructor.name }}` → `{{ workout.instructor_name }}`
- Removed instructor image URL (not available on workout object)

**Now shows:**
- Instructor name with emoji avatar (👤)
- Or "No instructor information" if none

### 3. Zone Distribution Card (Bottom-Left)
**Changed:**
- `{% if zone_distribution %}` → `{% if pace_targets.zones %}`
- Loop: `{% for zone_info in zone_distribution %}` → `{% for zone_info in pace_targets.zones|dictsortreversed:"zone" %}`
- Zone check: `zone_info.zone == 'recovery'` → `zone_info.zone == 1 or zone_info.name == 'Recovery'`
- Display: `{{ zone_info.zone_display }}` → `{{ zone_info.name }}`
- Time: `{{ zone_info.time_str }}` → `{{ zone_info.target_time_str }}`
- Percentage: `{{ zone_info.percentage }}%` → `{{ zone_info.blocks }} block(s)`

**Data source:** `pace_targets.zones`
```python
[
    {'zone': 4, 'name': 'Challenging', 'target_time_str': '1:05', 'blocks': 1},
    {'zone': 3, 'name': 'Moderate', 'target_time_str': '16:36', 'blocks': 3},
    {'zone': 2, 'name': 'Easy', 'target_time_str': '8:26', 'blocks': 4},
    {'zone': 1, 'name': 'Recovery', 'target_time_str': '3:30', 'blocks': 2}
]
```

**Now shows:**
- Colored square (matching zone color)
- Zone name (Challenging, Moderate, Easy, Recovery)
- Duration (e.g., "1:05")
- Number of blocks (e.g., "1 block", "3 blocks")
- **Ordered from highest to lowest zone**

### 4. CLASS DETAILS Card (Bottom-Right)
**Changed:**
- `{% if class_sections %}` → `{% if pace_class_notes %}`
- Loop: `{% for section_key, section in class_sections.items %}` → `{% for note in pace_class_notes|dictsortreversed:"zone" %}`
- Removed collapsible button/content structure
- Simplified to static list items with icons
- Duration: `{{ section.duration|format_duration_seconds }}` → `{{ note.total_time_str }}`
- Blocks: Added `{{ note.blocks }} block(s)`

**Data source:** `pace_class_notes`
```python
[
    {'zone': 4, 'zone_label': 'Challenging', 'name': 'Challenging', 'total_time_str': '1:05', 'blocks': 1},
    {'zone': 3, 'zone_label': 'Moderate', 'name': 'Moderate', 'total_time_str': '16:36', 'blocks': 3},
    {'zone': 2, 'zone_label': 'Easy', 'name': 'Easy', 'total_time_str': '8:26', 'blocks': 4},
    {'zone': 1, 'zone_label': 'Recovery', 'name': 'Recovery', 'total_time_str': '3:30', 'blocks': 2}
]
```

**Now shows:**
- Icon emoji (🔥 💪 ⚡ 🏃 🚴 🚶 😌 based on zone)
- Zone name
- Duration (e.g., "1:05")
- Number of blocks (e.g., "1 block", "3 blocks")
- **Ordered from highest to lowest zone**

## Zone Number to Name/Color Mapping

| Zone | Name | Color | Icon |
|------|------|-------|------|
| 7 | Max | `#fa5252` (Red) | 🔥 |
| 6 | Very Hard | `#f76707` (Dark Orange) | 💪 |
| 5 | Hard | `#ff922b` (Orange) | ⚡ |
| 4 | Challenging | `#0ca678` (Teal/Green) | 🏃 |
| 3 | Moderate | `#228be6` (Sky Blue) | 🚴 |
| 2 | Easy | `#4c6ef5` (Blue) | 🚶 |
| 1 | Recovery | `#6f42c1` (Purple) | 😌 |

## Order Fix

Added `|dictsortreversed:"zone"` filter to both loops so zones display from **highest to lowest**:
- Challenging (zone 4)
- Moderate (zone 3)
- Easy (zone 2)
- Recovery (zone 1)

This matches the visual order in the class library design.

## Context Variables Used

From `workouts.views.workout_detail`:

✅ `workout` - Workout model instance
✅ `workout.fitness_discipline` - e.g., "Running"
✅ `workout.instructor_name` - Instructor name string
✅ `user_pace_level` - User's pace level (1-10)
✅ `tss` - Training Stress Score (optional)
✅ `if_value` - Intensity Factor (optional)
✅ `pace_targets` - Dict with `zones` list
✅ `pace_class_notes` - List of zone info

❌ `ride` - (Not available, use `workout`)
❌ `zone_distribution` - (Empty for pace target, use `pace_targets.zones`)
❌ `class_sections` - (Empty for pace target, use `pace_class_notes`)

## Files Modified
- `/templates/workouts/detail_pace_target.html`
  - Updated all 4 cards to use correct variables
  - Changed from `ride` to `workout`
  - Changed from `zone_distribution` to `pace_targets.zones`
  - Changed from `class_sections` to `pace_class_notes`
  - Added reversed sorting for zone order
  - Simplified CLASS DETAILS from collapsible to static list

## Result

All 4 cards now show data correctly:
1. ✅ Class Info: Shows discipline, type, pace level, TSS, IF
2. ✅ Instructor: Shows instructor name
3. ✅ Zone Distribution: Shows colored zones with time and blocks
4. ✅ CLASS DETAILS: Shows zones with icons, time, and blocks

Order is corrected to show zones from high to low (Challenging → Recovery).
