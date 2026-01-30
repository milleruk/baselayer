# Pace Target Chart - Library Design Implementation

## Overview
Updated the Pace Target workout detail page to match the class library's modern dark theme design while maintaining Chart.js functionality.

## Design Changes Applied

### 1. **Container Styling**
**Before:**
```html
<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
```

**After:**
```html
<div class="bg-neutral-800 shadow-sm p-6 sm:p-8 border-2 border-gray-700 rounded-lg">
```

**Changes:**
- Dark background: `bg-neutral-800` (always dark, no conditional)
- Thicker border: `border-2` instead of `border`
- Consistent border color: `border-gray-700`
- Responsive padding: `p-6 sm:p-8`

### 2. **Typography**
**Before:**
```html
<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
```

**After:**
```html
<h2 class="text-xl sm:text-xl md:text-2xl font-semibold text-white leading-tight mb-6">
```

**Changes:**
- Larger, responsive font sizes
- Always white text
- Better leading and spacing

### 3. **Chart Container**
**Before:**
```html
<div class="h-80">
  <canvas id="paceChart"></canvas>
</div>
```

**After:**
```html
<div class="h-64">
  <canvas id="paceChart"></canvas>
</div>
```

**Changes:**
- Reduced height from `h-80` (320px) to `h-64` (256px) to match library
- Added subtitle/description area above chart

### 4. **Chart.js Styling**

#### Color Theme
```javascript
// Before: Dynamic dark mode detection
const isDark = document.documentElement.classList.contains('dark');
const textColor = isDark ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.8)';
const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

// After: Fixed dark theme
const textColor = 'rgba(255, 255, 255, 0.8)';
const gridColor = 'rgba(255, 255, 255, 0.1)';
```

#### Legend
```javascript
legend: {
  display: true,
  position: 'top',
  labels: {
    color: textColor,
    font: {
      size: 14,
      family: "'Inter', sans-serif"
    },
    padding: 15,
    usePointStyle: true
  }
}
```

#### Tooltip
```javascript
tooltip: {
  backgroundColor: 'rgba(30, 30, 30, 0.9)',
  titleColor: '#ffffff',
  bodyColor: '#ffffff',
  borderColor: 'rgba(255, 255, 255, 0.2)',
  borderWidth: 1,
  padding: 12,
  displayColors: false,
  titleFont: {
    size: 14,
    weight: 'bold'
  },
  bodyFont: {
    size: 13
  }
}
```

#### Axes
```javascript
x: {
  // ... existing config
  ticks: {
    color: textColor,
    font: {
      size: 12
    }
  },
  grid: {
    color: gridColor,
    drawBorder: false  // Remove border line
  },
  border: {
    display: false  // No axis border
  }
}
```

### 5. **Metrics Cards**
**Before:**
```html
<div>
  <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg Speed</div>
  <div class="text-xl font-bold text-gray-900 dark:text-white">7.5 mph</div>
</div>
```

**After:**
```html
<div class="flex flex-col items-center justify-center p-3 bg-neutral-700/50 rounded-lg">
  <div class="text-2xl font-bold text-white">7.5</div>
  <div class="text-xs text-white/60 mt-1">Avg Speed (mph)</div>
</div>
```

**Changes:**
- Centered layout
- Darker card background with 50% opacity: `bg-neutral-700/50`
- Larger value text: `text-2xl`
- Inverted hierarchy (value on top, label below)

### 6. **Progress Bars**
**Before:**
```html
<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4">
  <div class="h-full rounded-full pace-color-3" style="width: 75%"></div>
</div>
```

**After:**
```html
<div class="w-full bg-neutral-700 rounded-full h-5">
  <div class="h-full rounded-full pace-color-3" style="width: 75%"></div>
</div>
```

**Changes:**
- Darker background: `bg-neutral-700`
- Slightly taller: `h-5` instead of `h-4`
- Larger text and spacing

### 7. **Playlist Items**
**Before:**
```html
<div class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
  <span class="text-sm font-semibold text-gray-900 dark:text-white">
```

**After:**
```html
<div class="flex items-center gap-3 p-3 bg-neutral-700/50 rounded-lg hover:bg-neutral-700 transition-colors">
  <span class="text-sm font-semibold text-white">
```

**Changes:**
- Consistent dark background
- Hover effect
- Always white text

## Color Palette

### Background Colors
- **Main container**: `bg-neutral-800` (#262626)
- **Cards/metrics**: `bg-neutral-700/50` (50% opacity)
- **Progress bars**: `bg-neutral-700` (#404040)

### Border Colors
- **Primary border**: `border-gray-700` (#374151)
- **Border width**: `border-2`

### Text Colors
- **Primary text**: `text-white` (#ffffff)
- **Secondary text**: `text-white/60` (60% opacity)
- **Muted text**: `text-white/60`

### Chart Colors
- **Target Pace line**: `#76bbf7` (blue, dashed)
- **Actual Speed line**: `#e0fe48` (yellow/lime)
- **Grid lines**: `rgba(255, 255, 255, 0.1)`
- **Text**: `rgba(255, 255, 255, 0.8)`

## Typography
- **Font family**: Inter, sans-serif
- **Heading sizes**: `text-xl` → `text-2xl` (responsive)
- **Body text**: `text-sm` → `text-base`
- **Label text**: `text-xs`
- **Values**: `text-2xl` (bold)

## Spacing
- **Container padding**: `p-6 sm:p-8` (24px → 32px)
- **Section margins**: `mb-6` (24px)
- **Grid gaps**: `gap-4` → `gap-6`
- **Item spacing**: `space-y-3` → `space-y-4`

## Responsive Breakpoints
- **Headings**: Scale from `text-xl` → `text-2xl` at `md` breakpoint
- **Padding**: Increases at `sm` breakpoint (640px+)
- **Grid columns**: Adjust at `md` (768px) and `lg` (1024px)

## Browser Compatibility
- Uses modern Tailwind utilities
- Chart.js v4.4.6
- CSS gradients for zone colors
- Backdrop filters not used (for better compatibility)

## Benefits
1. **Consistent Design**: Matches class library aesthetic across the app
2. **Better Readability**: Higher contrast, larger text
3. **Modern Look**: Dark theme with subtle gradients
4. **Performance**: No dynamic theme switching
5. **Maintainability**: Simplified color logic

## Files Modified
- `/opt/projects/pelvicplanner/templates/workouts/detail_pace_target.html`

## Next Steps
Consider applying similar styling to:
1. `detail_power_zone.html` - Power Zone workout template
2. `detail_general.html` - General workout template
3. Other workout detail pages that need modernization
