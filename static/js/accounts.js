// Accounts page functionality (profile page)
function openPaceModal(activityType) {
  const modal = document.getElementById('paceModal');
  const activitySelect = document.getElementById('pace_activity_type');
  if (activitySelect) {
    activitySelect.value = activityType;
  }
  modal.classList.remove('hidden');
}

function openPaceLevelModal(activityType) {
  const modal = document.getElementById('paceLevelModal');
  const activitySelect = document.getElementById('pace_level_activity_type');
  if (activitySelect) {
    activitySelect.value = activityType;
  }
  modal.classList.remove('hidden');
}

function formatPace(paceValue) {
  if (!paceValue) return 'Not set';
  const minutes = Math.floor(paceValue);
  const seconds = Math.round((paceValue - minutes) * 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')} min/mile`;
}

function switchTab(tabName, event) {
  if (event) {
    event.preventDefault();
  }
  
  // Hide all tab contents
  document.querySelectorAll('.settings-tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  
  // Remove active class from all tabs
  document.querySelectorAll('.settings-tab').forEach(tab => {
    tab.classList.remove('border-lime-400', 'text-lime-400');
    tab.classList.add('border-transparent', 'text-white');
  });
  
  // Show selected tab content
  const tabContent = document.getElementById('tab-' + tabName);
  if (tabContent) {
    tabContent.classList.remove('hidden');
  }
  
  // Add active class to selected tab
  const activeTab = document.querySelector(`.settings-tab[data-tab="${tabName}"]`);
  if (activeTab) {
    activeTab.classList.add('border-lime-400', 'text-lime-400');
    activeTab.classList.remove('border-transparent', 'text-white');
  }
  
  // Update URL hash without scrolling
  if (history.pushState) {
    history.pushState(null, null, '#tab-' + tabName);
  } else {
    window.location.hash = '#tab-' + tabName;
  }
  
  return false;
}

// Handle page load with hash
document.addEventListener('DOMContentLoaded', function() {
  const hash = window.location.hash;
  if (hash) {
    const tabName = hash.replace('#tab-', '');
    if (tabName) {
      switchTab(tabName);
    } else {
      // Default to profile tab if hash is present but invalid
      switchTab('profile');
    }
  } else {
    // Default to profile tab if no hash is present
    switchTab('profile');
  }
  
  // Handle browser back/forward buttons
  window.addEventListener('hashchange', function() {
    const hash = window.location.hash;
    if (hash) {
      const tabName = hash.replace('#tab-', '');
      if (tabName) {
        switchTab(tabName);
      } else {
        // Default to profile tab if hash is present but invalid
        switchTab('profile');
      }
    } else {
      // Default to profile tab if hash is removed
      switchTab('profile');
    }
  });
});
