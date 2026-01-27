// Ensure Chart.js is fully loaded before any chart initialization
window.chartJsReady = false;
if (typeof Chart !== 'undefined') {
  window.chartJsReady = true;
} else {
  // Fallback: wait for script to load
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
      if (typeof Chart !== 'undefined') {
        window.chartJsReady = true;
        window.dispatchEvent(new Event('chartjsready'));
      }
    }, 100);
  });
}
