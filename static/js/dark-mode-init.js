// Load dark mode preference from localStorage immediately to prevent flash
(function() {
  if (typeof Storage !== 'undefined') {
    const saved = localStorage.getItem('darkMode');
    const isDark = saved !== null ? saved === 'true' : true; // Default to dark mode
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
  } else {
    // Default to dark mode if localStorage not available
    document.documentElement.classList.add('dark');
  }
})();
