/**
 * Mobile navbar scroll behavior
 * Hides navbar on scroll down, shows on scroll up (mobile only)
 */
(function() {
  'use strict';
  
  // Check if we're on mobile
  function isMobile() {
    return window.innerWidth < 768; // md breakpoint
  }
  
  let lastScrollTop = 0;
  let ticking = false;
  
  // Find navbars by checking for the backdrop-blur class which is common to both navbars
  // Tailwind classes with slashes are escaped, so we check the classList string representation
  function getNavbars() {
    return Array.from(document.querySelectorAll('nav')).filter(nav => {
      const classList = nav.className;
      // Check for backdrop-blur-sm which both navbars have
      return classList.includes('backdrop-blur-sm');
    });
  }
  
  let navbars = [];
  
  function handleScroll() {
    if (!isMobile() || navbars.length === 0) {
      return;
    }
    
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    navbars.forEach(nav => {
      if (scrollTop > lastScrollTop && scrollTop > 50) {
        // Scrolling down - hide navbar
        nav.style.transform = 'translateY(-100%)';
        nav.style.transition = 'transform 0.3s ease-in-out';
      } else {
        // Scrolling up - show navbar
        nav.style.transform = 'translateY(0)';
        nav.style.transition = 'transform 0.3s ease-in-out';
      }
    });
    
    lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    ticking = false;
  }
  
  function requestTick() {
    if (!ticking) {
      window.requestAnimationFrame(handleScroll);
      ticking = true;
    }
  }
  
  // Initialize on load
  document.addEventListener('DOMContentLoaded', function() {
    navbars = getNavbars();
    
    // Set initial position for mobile
    if (isMobile() && navbars.length > 0) {
      const firstNav = navbars[0];
      const navHeight = firstNav.offsetHeight;
      
      navbars.forEach(nav => {
        nav.style.position = 'fixed';
        nav.style.top = '0';
        nav.style.left = '0';
        nav.style.right = '0';
        nav.style.zIndex = '50';
        nav.style.width = '100%';
      });
      
      // Add padding to body to account for fixed navbar (only on mobile)
      document.body.style.paddingTop = navHeight + 'px';
    }
    
    // Listen for scroll events
    window.addEventListener('scroll', requestTick, { passive: true });
    
    // Handle resize to reset on desktop
    window.addEventListener('resize', function() {
      navbars = getNavbars();
      if (!isMobile()) {
        navbars.forEach(nav => {
          nav.style.position = '';
          nav.style.transform = '';
          nav.style.transition = '';
          nav.style.top = '';
          nav.style.left = '';
          nav.style.right = '';
          nav.style.zIndex = '';
          nav.style.width = '';
        });
        document.body.style.paddingTop = '';
      } else if (navbars.length > 0) {
        const firstNav = navbars[0];
        const navHeight = firstNav.offsetHeight;
        navbars.forEach(nav => {
          nav.style.position = 'fixed';
          nav.style.top = '0';
          nav.style.left = '0';
          nav.style.right = '0';
          nav.style.zIndex = '50';
          nav.style.width = '100%';
        });
        document.body.style.paddingTop = navHeight + 'px';
      }
    }, { passive: true });
  });
})();
