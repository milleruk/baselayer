// Content wrapper placement logic
document.addEventListener('DOMContentLoaded', function() {
  const contentWrapper = document.getElementById('content-wrapper');
  if (!contentWrapper) return;
  
  // Check if this is a landing page (has main.flex-1.w-full)
  const landingMain = document.querySelector('main.flex-1.w-full');
  if (landingMain) {
    // Landing page - place content directly in main
    landingMain.appendChild(contentWrapper);
    contentWrapper.style.display = 'block';
  } else {
    // Check if authenticated layout exists (has sidebar)
    const authenticatedMain = document.querySelector('.flex-1.overflow-y-auto.bg-gray-50');
    if (authenticatedMain) {
      // Non-landing page - find the flex container and then the content div
      const flexContainer = authenticatedMain.querySelector('.flex-1.flex.flex-col');
      if (flexContainer) {
        // Find the inner div that should contain content (has pb-12 class)
        const contentDiv = flexContainer.querySelector('.flex-1.pb-12');
        if (contentDiv) {
          contentDiv.appendChild(contentWrapper);
          contentWrapper.style.display = 'block';
        } else {
          // Fallback: find first .flex-1 inside the flex container
          const fallbackDiv = flexContainer.querySelector('.flex-1');
          if (fallbackDiv) {
            fallbackDiv.appendChild(contentWrapper);
            contentWrapper.style.display = 'block';
          }
        }
      } else {
        // Fallback to old structure
        const contentDiv = authenticatedMain.querySelector('.flex-1');
        if (contentDiv) {
          contentDiv.appendChild(contentWrapper);
          contentWrapper.style.display = 'block';
        }
      }
    } else {
      // Non-authenticated layout - move content to non-authenticated main
      const main = document.querySelector('main');
      if (main) {
        main.appendChild(contentWrapper);
        contentWrapper.style.display = 'block';
      }
    }
  }
});
