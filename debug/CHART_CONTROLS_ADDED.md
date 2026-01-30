# Chart Control Buttons Added

## Overview
Added interactive chart control buttons below the Pace Target Timeline chart, matching the controls seen in the class library screenshots.

## Buttons Added

### 1. **Show Speed Graph**
- **Function**: Toggle between pace (min/mile) and speed (mph) display
- **Status**: Button added, placeholder alert (TODO: implement full functionality)
- **Toggle Text**: "Show Speed Graph" ↔ "Show Pace Graph"

### 2. **Show Kilometers**
- **Function**: Toggle between miles and kilometers
- **Status**: Button added, placeholder alert (TODO: implement full functionality)
- **Toggle Text**: "Show Kilometers" ↔ "Show Miles"

### 3. **Hide Target**
- **Function**: Show/hide the target pace line on the chart
- **Status**: ✅ Fully functional
- **Toggle Text**: "Hide Target" ↔ "Show Target"
- **Implementation**: Toggles the `hidden` property on the target dataset

### 4. **Bring Actual Forward**
- **Function**: Swap the rendering order of Actual and Target lines (bring one to front)
- **Status**: ✅ Fully functional
- **Toggle Text**: "Bring Actual Forward" ↔ "Bring Target Forward"
- **Implementation**: Swaps dataset order in the chart

### 5. **Save** (with share icon)
- **Function**: Download the chart as a PNG image
- **Status**: ✅ Fully functional
- **Icon**: Share/export SVG icon
- **Implementation**: Uses Chart.js `toBase64Image()` method

### 6. **Zone Colors** (checkbox)
- **Function**: Toggle the colored zone background bands on/off
- **Status**: ✅ Fully functional (checkbox, checked by default)
- **Implementation**: Updates chart plugin options and re-renders

## Visual Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                    [Chart displayed here]                         │
└──────────────────────────────────────────────────────────────────┘
  [Show Speed Graph] [Show Kilometers] [Hide Target] 
  [Bring Actual Forward] [🔗 Save] [✓ Zone Colors]
```

## Styling

**Button Classes:**
```html
class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 
       bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 
       rounded-lg transition-colors border border-gray-300 dark:border-gray-600"
```

**Features:**
- Responsive flex wrap layout
- Right-aligned on desktop
- Consistent sizing and spacing
- Dark mode support
- Hover effects
- Border styling matching theme

## JavaScript Implementation

### Chart Instance
```javascript
let paceChartInstance = null;
if (ctx) {
  paceChartInstance = new Chart(ctx, { ... });
}
```

### Event Handlers

**Hide/Show Target:**
```javascript
toggleTargetBtn.addEventListener('click', function() {
  const targetDataset = paceChartInstance.data.datasets.find(ds => ds.label === 'Target');
  if (targetDataset) {
    targetDataset.hidden = !targetDataset.hidden;
    this.textContent = targetDataset.hidden ? 'Show Target' : 'Hide Target';
    paceChartInstance.update();
  }
});
```

**Zone Colors Toggle:**
```javascript
toggleZoneColorsCheckbox.addEventListener('change', function() {
  paceChartInstance.options.plugins.zoneBackgrounds = { enabled: this.checked };
  paceChartInstance.update();
});
```

**Save Chart:**
```javascript
saveChartBtn.addEventListener('click', function() {
  const url = paceChartInstance.toBase64Image();
  const link = document.createElement('a');
  link.download = 'pace-target-chart.png';
  link.href = url;
  link.click();
});
```

**Bring Actual Forward:**
```javascript
bringActualForwardBtn.addEventListener('click', function() {
  const datasets = paceChartInstance.data.datasets;
  if (datasets.length >= 2) {
    [datasets[0], datasets[1]] = [datasets[1], datasets[0]];
    this.textContent = datasets[0].label === 'Actual' ? 'Bring Target Forward' : 'Bring Actual Forward';
    paceChartInstance.update();
  }
});
```

## Files Modified
- `/templates/workouts/detail_pace_target.html`
  - Added button HTML after chart canvas
  - Added JavaScript event handlers
  - Stored chart instance as `paceChartInstance` for button access

## Future Enhancements

### Show Speed Graph (TODO)
- Convert pace data (min/mile) to speed (mph)
- Update Y-axis labels and scale
- Update tooltip formatting
- Persist user preference

### Show Kilometers (TODO)
- Convert miles to kilometers
- Update axis labels and tooltips
- Convert pace from min/mile to min/km
- Persist user preference

## Testing Checklist
- [x] Hide Target button toggles target line visibility
- [x] Hide Target button text updates correctly
- [x] Zone Colors checkbox toggles background bands
- [x] Save button downloads chart as PNG
- [x] Bring Actual Forward swaps line rendering order
- [x] Bring Actual Forward button text updates correctly
- [x] All buttons styled consistently
- [x] Dark mode styling works
- [x] Responsive layout on mobile
- [ ] Speed Graph toggle (placeholder)
- [ ] Kilometers toggle (placeholder)

## Notes
- Chart controls match the style and functionality of the class library screenshots
- All core interactive features are working
- Speed Graph and Kilometers toggles need full implementation (currently show alert placeholders)
- Buttons are right-aligned and wrap on smaller screens
- All buttons have proper hover states and transitions
