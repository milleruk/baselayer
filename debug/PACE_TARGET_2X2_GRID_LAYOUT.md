# Pace Target Workout - 2x2 Grid Layout Update

## Overview
Replaced the 3-card layout with a **2x2 grid layout** matching the class library detail pages design.

## Layout Structure

### 2x2 Grid (Desktop: 2 columns, Mobile: 1 column)
```
┌─────────────────────────────────────┬─────────────────────────────────────┐
│         CLASS INFO                  │          INSTRUCTOR                 │
│  • Discipline: Running              │  [Photo] Instructor Name            │
│  • Type: Pace Target                │                                     │
│  • TSS: 67                          │                                     │
│  • IF: 0.85                         │                                     │
│  • Your Pace Level: 8               │                                     │
├─────────────────────────────────────┼─────────────────────────────────────┤
│      ZONE DISTRIBUTION              │       CLASS DETAILS                 │
│  ■ Recovery    8:52 (91.2%)         │  🔥 Hard — 0:28      [▼]            │
│  ■ Easy        1:29 (100.0%)        │  💪 Challenging — 18:26 [▼]         │
│  ■ Moderate    0:29 (100.0%)        │  🏃 Moderate — 0:29  [▼]            │
│  ■ Challenging 18:26 (94.9%)        │  🚶 Easy — 1:29      [▼]            │
│  ■ Hard        0:28 (100.0%)        │  😌 Recovery — 8:52  [▼]            │
└─────────────────────────────────────┴─────────────────────────────────────┘
```

## Card 1: Class Info (Top-Left)

**Purpose:** Display class metadata and user pace settings

**Fields:**
- **Discipline**: Running / Walking (from `ride.workout_type.name` or `ride.fitness_discipline_display_name`)
- **Type**: Always shows "Pace Target"
- **TSS** (optional): Training Stress Score - `{{ tss|floatformat:0 }}`
- **IF** (optional): Intensity Factor - `{{ if_value }}`
- **Your Pace Level**: User's current pace level setting (1-10)

**Styling:**
- Label: `text-sm text-gray-600 dark:text-gray-400`
- Value: `text-lg font-bold text-gray-900 dark:text-white`

## Card 2: Instructor (Top-Right)

**Purpose:** Show instructor information with photo

**Content:**
- Instructor photo (circular, 48x48px)
- Fallback emoji if no photo: 👤
- Instructor name

**Conditional Display:**
- If `ride.instructor` exists: Shows photo + name
- If no instructor: Shows "No instructor information"

## Card 3: Zone Distribution (Bottom-Left)

**Purpose:** Show time spent in each pace zone with colored indicators

**Features:**
- **Colored squares** (16x16px) matching zone colors:
  - Recovery: `#6f42c1` (Purple)
  - Easy: `#4c6ef5` (Blue)
  - Moderate: `#228be6` (Sky Blue)
  - Challenging: `#0ca678` (Teal/Green)
  - Hard: `#ff922b` (Orange)
  - Very Hard: `#f76707` (Dark Orange)
  - Max: `#fa5252` (Red)
- Zone name (e.g., "Recovery", "Challenging")
- Time in zone (formatted as `MM:SS`)
- Percentage of total workout time

**Layout:**
```html
<div class="flex items-center justify-between">
  <div class="flex items-center gap-2">
    <div class="w-4 h-4 rounded" style="background-color: #color;"></div>
    <span>Zone Name</span>
  </div>
  <div>8:52 (91.2%)</div>
</div>
```

## Card 4: CLASS DETAILS (Bottom-Right)

**Purpose:** Show workout structure with collapsible sections

**Features:**
- **Collapsible sections** (one per workout section)
- Each section button shows:
  - Icon (emoji like 🔥, 💪, 🏃, 🚶, 😌)
  - Section name (e.g., "Hard", "Challenging")
  - Duration (formatted as `MM:SS`)
  - Chevron icon (rotates when expanded)
- **Expanded content** shows:
  - Optional description
  - List of segments with:
    - Segment name
    - Segment duration

**JavaScript Interaction:**
- Click button to expand/collapse
- Chevron rotates 180° when expanded
- `aria-expanded` attribute toggles between `true`/`false`
- Content has `.hidden` class when collapsed

**Styling:**
- Button: Hover effect with `hover:bg-gray-50 dark:hover:bg-gray-700/50`
- Expanded content: Different background `bg-gray-50 dark:bg-gray-900/50`
- Segments: White/gray background with rounded corners

## Responsive Behavior

### Desktop (md and up)
- 2-column grid: `grid-cols-1 md:grid-cols-2`
- Cards side-by-side

### Mobile/Tablet
- Single column stack
- Full-width cards
- Reduced padding: `p-4 sm:p-6`
- Smaller gaps: `gap-4 sm:gap-6`

## JavaScript Features

### Collapsible Sections Toggle
```javascript
const sectionToggles = document.querySelectorAll('.section-toggle');
sectionToggles.forEach(toggle => {
  toggle.addEventListener('click', function() {
    const content = this.nextElementSibling;
    const chevron = this.querySelector('.section-chevron');
    const isExpanded = this.getAttribute('aria-expanded') === 'true';
    
    if (isExpanded) {
      content.classList.add('hidden');
      this.setAttribute('aria-expanded', 'false');
      chevron.style.transform = 'rotate(0deg)';
    } else {
      content.classList.remove('hidden');
      this.setAttribute('aria-expanded', 'true');
      chevron.style.transform = 'rotate(180deg)';
    }
  });
});
```

## Context Variables Required

From Django view (`workout_detail`):

1. **`ride`** (Workout object)
   - `workout_type.name`: Discipline
   - `fitness_discipline_display_name`: Fallback discipline
   - `instructor`: Instructor object
     - `image_url`: Photo URL
     - `name`: Instructor name

2. **`tss`** (float, optional): Training Stress Score

3. **`if_value`** (float, optional): Intensity Factor

4. **`user_pace_level`** (int): User's pace level (1-10)

5. **`zone_distribution`** (list)
   - Each item:
     - `zone`: string (e.g., "moderate")
     - `zone_display`: string (e.g., "Moderate")
     - `time_str`: string (e.g., "18:26")
     - `percentage`: float (e.g., 94.9)

6. **`class_sections`** (dict)
   - Keys: section identifiers
   - Values: dict
     - `name`: string
     - `icon`: string (emoji)
     - `duration`: int (seconds)
     - `description`: string (optional)
     - `segments`: list
       - Each segment:
         - `name`: string
         - `duration_str`: string (e.g., "2:30")

## Styling Consistency

### Card Base
```html
class="rounded-lg border border-gray-200 dark:border-gray-700 
       bg-white dark:bg-gray-800 p-4 sm:p-6 shadow-sm"
```

### Headings
```html
class="text-lg font-semibold text-gray-900 dark:text-white mb-4"
```

### Body Text
- Labels: `text-sm text-gray-600 dark:text-gray-400`
- Values: `text-lg font-bold text-gray-900 dark:text-white`
- Regular text: `text-sm text-gray-700 dark:text-gray-300`

### Grid
```html
class="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 mb-6"
```

## Files Modified
- `/templates/workouts/detail_pace_target.html`
  - Replaced 3-card layout with 2x2 grid
  - Added collapsible sections with JavaScript
  - Maintained chart section (unchanged)
  - Kept existing playlist styling

## Benefits Over 3-Card Layout

1. **Better Information Architecture**: 
   - Groups related info (class metadata vs instructor vs performance vs structure)
   
2. **More Detailed Class Structure**: 
   - Collapsible sections allow viewing segment-by-segment breakdown
   - Expandable design prevents information overload
   
3. **Visual Hierarchy**: 
   - Colored squares for zones match chart colors
   - Icons make sections easily scannable
   
4. **Instructor Prominence**: 
   - Dedicated card for instructor builds connection
   
5. **TSS/IF Metrics**: 
   - Important training metrics now visible
   
6. **Consistency**: 
   - Matches class library design patterns
   - Familiar layout for users

## Design Match with Class Library

This 2x2 grid layout **exactly matches** the design in `/templates/workouts/partials/pace_target_content.html` (class library detail pages), including:

✅ Same card structure and order  
✅ Same colored zone indicators  
✅ Same collapsible CLASS DETAILS with segments  
✅ Same typography and spacing  
✅ Same responsive breakpoints  
✅ Same hover effects and transitions

## Next Steps

The layout is complete and functional. To enhance further:
- Verify `class_sections` data includes all necessary fields
- Test collapsible sections on mobile devices
- Ensure `tss` and `if_value` calculations are accurate
- Consider adding animation to chevron rotation
