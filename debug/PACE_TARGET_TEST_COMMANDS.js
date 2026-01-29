// Pace Target Metrics Debugging - Browser Console Commands
// Use these commands in the browser console on https://chase.haresign.dev/workouts/library/2695/

// ============================================================================
// STEP 1: Verify Data is Loaded Correctly
// ============================================================================

console.log("=== STEP 1: Check Data Structures ===");

// Check if targetLineData is loaded
console.log("targetLineData exists?", !!window.targetLineData);
console.log("targetLineData length:", window.targetLineData?.length);
console.log("First 3 entries:", window.targetLineData?.slice(0, 3));

// Check if targetMetricsJson is loaded
console.log("\ntargetMetricsJson exists?", !!window.targetMetricsJson);
console.log("Segments count:", window.targetMetricsJson?.segments?.length);
console.log("First segment:", window.targetMetricsJson?.segments?.[0]);

// ============================================================================
// STEP 2: Test getCurrentTargetForTime Function
// ============================================================================

console.log("\n=== STEP 2: Test getCurrentTargetForTime ===");

// Create array of test times
const testTimes = [0, 60, 300, 600, 900, 1200, 1800];

testTimes.forEach(time => {
  if (typeof getCurrentTargetForTime === 'function') {
    const target = getCurrentTargetForTime(time);
    console.log(`Time ${time}s (${Math.floor(time/60)}:${String(time%60).padStart(2,'0')}): target level = ${target}`);
  }
});

// ============================================================================
// STEP 3: Monitor Metrics Box Updates
// ============================================================================

console.log("\n=== STEP 3: Monitor Metrics Box ===");

// Create observer to watch metrics changes
const targetEl = document.getElementById('current-target');
const intervalEl = document.getElementById('interval-time');
const timeLeftEl = document.getElementById('time-left');

if (targetEl && intervalEl && timeLeftEl) {
  console.log("Current Target:", targetEl.textContent);
  console.log("Time in Target:", intervalEl.textContent);
  console.log("Time Left:", timeLeftEl.textContent);
  
  // Set up observer to watch for changes
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList' || mutation.type === 'characterData') {
        console.log("METRICS UPDATED:");
        console.log("  Current Target:", targetEl.textContent);
        console.log("  Time in Target:", intervalEl.textContent);
        console.log("  Time Left:", timeLeftEl.textContent);
        console.log("  Chart time (estimated):", window.chartCurrentTime || 'unknown');
      }
    });
  });
  
  observer.observe(targetEl, { characterData: true, subtree: true });
  observer.observe(intervalEl, { characterData: true, subtree: true });
  observer.observe(timeLeftEl, { characterData: true, subtree: true });
  
  console.log("Observer started - drag the slider to see metrics updates logged above");
} else {
  console.error("Metrics elements not found!");
}

// ============================================================================
// STEP 4: Manual Slider Test
// ============================================================================

console.log("\n=== STEP 4: Test Slider Movement ===");

const slider = document.getElementById('progress-slider');
if (slider) {
  console.log("Slider found, you can now test:");
  console.log("1. Drag the slider left and right");
  console.log("2. Watch the metrics update in the console above");
  console.log("3. Verify that:");
  console.log("   - Current Target changes at appropriate times");
  console.log("   - Time in Target resets when entering new pace level");
  console.log("   - Time Left decreases correctly");
  
  // Log slider position changes
  slider.addEventListener('input', (e) => {
    const progress = parseFloat(e.target.value);
    const totalDuration = window.workoutDuration;
    const currentTime = (progress / 100) * totalDuration;
    const target = typeof getCurrentTargetForTime === 'function' ? getCurrentTargetForTime(currentTime) : 'unknown';
    
    console.log(`SLIDER MOVED: ${progress}% = ${currentTime.toFixed(0)}s, Target: ${target}`);
  });
  
  console.log("Slider event listener attached!");
} else {
  console.error("Slider not found!");
}

// ============================================================================
// STEP 5: Compare with Power Zone Class (working reference)
// ============================================================================

console.log("\n=== STEP 5: Comparison Command ===");
console.log("To compare with working Power Zone class:");
console.log("1. Open https://chase.haresign.dev/workouts/library/2668/ in another tab");
console.log("2. Drag slider there and watch metrics update");
console.log("3. Return to Pace Target (2695) and verify same behavior");

// ============================================================================
// STEP 6: Check for Errors
// ============================================================================

console.log("\n=== STEP 6: Error Check ===");

// Check console for any errors
console.log("If you see red errors above, note:");
console.log("- 'getCurrentTargetForTime is not defined' = function not loaded");
console.log("- 'targetLineData is undefined' = data not passed from server");
console.log("- 'Cannot read property' = data structure mismatch");

// Try calling the function
try {
  const testResult = getCurrentTargetForTime(300);
  console.log("✓ getCurrentTargetForTime works, returned:", testResult);
} catch (e) {
  console.error("✗ ERROR calling getCurrentTargetForTime:", e.message);
}

console.log("\n=== DEBUGGING COMPLETE ===");
console.log("Now drag the slider on the chart and watch the metrics update!");
