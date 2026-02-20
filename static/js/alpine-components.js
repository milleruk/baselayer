// Alpine.js Components for reusability and better state management
document.addEventListener('alpine:init', () => {
  
  // Notification/Toast Store
  Alpine.store('notifications', {
    items: [],
    
    add(message, type = 'info', duration = 3000) {
      const id = Date.now();
      this.items.push({ id, message, type });
      
      if (duration > 0) {
        setTimeout(() => this.remove(id), duration);
      }
      
      return id;
    },
    
    remove(id) {
      this.items = this.items.filter(item => item.id !== id);
    },
    
    clear() {
      this.items = [];
    }
  });
  
  // Workout Filters Component (with persistence)
  Alpine.data('workoutFilters', () => ({
    search: Alpine.$persist('').as('workout-search'),
    instructor: Alpine.$persist('').as('workout-instructor'),
    duration: Alpine.$persist('').as('workout-duration'),
    tss: Alpine.$persist('').as('workout-tss'),
    workoutType: Alpine.$persist('').as('workout-type'),
    
    init() {
      // Apply saved filters on load (if they exist)
      this.syncFormToData();
    },
    
    syncFormToData() {
      // Sync form inputs with Alpine data
      const form = this.$el.closest('form');
      if (!form) return;
      
      const elements = form.elements;
      if (elements['search']) elements['search'].value = this.search;
      if (elements['instructor']) elements['instructor'].value = this.instructor;
      if (elements['duration']) elements['duration'].value = this.duration;
      if (elements['tss']) elements['tss'].value = this.tss;
      if (elements['type']) elements['type'].value = this.workoutType;
    },
    
    updateFromForm() {
      // Update Alpine data from form inputs
      const form = this.$el.closest('form');
      if (!form) return;
      
      const elements = form.elements;
      this.search = elements['search']?.value || '';
      this.instructor = elements['instructor']?.value || '';
      this.duration = elements['duration']?.value || '';
      this.tss = elements['tss']?.value || '';
      this.workoutType = elements['type']?.value || '';
    },
    
    clearFilters() {
      this.search = '';
      this.instructor = '';
      this.duration = '';
      this.tss = '';
      this.workoutType = '';
      
      // Clear form inputs
      const form = this.$el.closest('form');
      if (form) {
        const elements = form.elements;
        if (elements['search']) elements['search'].value = '';
        if (elements['instructor']) elements['instructor'].value = '';
        if (elements['duration']) elements['duration'].value = '';
        if (elements['tss']) elements['tss'].value = '';
        if (elements['type']) elements['type'].value = '';
        
        // Trigger HTMX request
        htmx.trigger(form, 'submit');
      }
    },
    
    applyFilters() {
      // Update data from form, then trigger HTMX
      this.updateFromForm();
      const form = this.$el.closest('form');
      if (form) {
        htmx.trigger(form, 'submit');
      }
    }
  }));
  
  // Sidebar Management Component
  Alpine.data('sidebar', () => ({
    open: false,
    
    init() {
      // On desktop, restore state from localStorage
      if (window.innerWidth >= 1024) {
        const saved = localStorage.getItem('sidebar-open');
        this.open = saved !== null ? saved === 'true' : false;
      }
      
      // Watch for changes and save to localStorage (desktop only)
      this.$watch('open', value => {
        if (window.innerWidth >= 1024) {
          localStorage.setItem('sidebar-open', value);
        }
      });
      
      // Handle window resize
      window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024) {
          const saved = localStorage.getItem('sidebar-open');
          if (saved !== null) {
            this.open = saved === 'true';
          }
        } else {
          // On mobile, always closed by default
          this.open = false;
        }
      });
    },
    
    toggle() {
      this.open = !this.open;
    },
    
    close() {
      // Only close on mobile (on desktop, let user manage)
      if (window.innerWidth < 1024) {
        this.open = false;
      }
    }
  }));
  
  // Modal Component
  Alpine.data('modal', (initialOpen = false) => ({
    open: initialOpen,
    
    show() {
      this.open = true;
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    },
    
    hide() {
      this.open = false;
      // Restore body scroll
      document.body.style.overflow = '';
    },
    
    toggle() {
      this.open ? this.hide() : this.show();
    }
  }));
  
  // Dropdown Component
  Alpine.data('dropdown', () => ({
    open: false,
    
    toggle() {
      this.open = !this.open;
    },
    
    close() {
      this.open = false;
    }
  }));
  
  // Tabs Component
  Alpine.data('tabs', (defaultTab = 0) => ({
    activeTab: defaultTab,
    
    setTab(index) {
      this.activeTab = index;
    },
    
    isActive(index) {
      return this.activeTab === index;
    }
  }));
  
  // Accordion Component
  Alpine.data('accordion', (initialOpen = false) => ({
    open: initialOpen,
    
    toggle() {
      this.open = !this.open;
    }
  }));
  
  // Confirmation Dialog Component
  Alpine.data('confirmDialog', () => ({
    showing: false,
    message: '',
    confirmCallback: null,
    cancelCallback: null,
    
    show(message, onConfirm, onCancel = null) {
      this.message = message;
      this.confirmCallback = onConfirm;
      this.cancelCallback = onCancel;
      this.showing = true;
    },
    
    confirm() {
      if (this.confirmCallback) {
        this.confirmCallback();
      }
      this.showing = false;
    },
    
    cancel() {
      if (this.cancelCallback) {
        this.cancelCallback();
      }
      this.showing = false;
    }
  }));
});

// HTMX Event Listeners for notifications
document.body.addEventListener('htmx:afterRequest', (event) => {
  // Show success notification after successful requests (optional)
  if (event.detail.successful && event.detail.xhr.status === 200) {
    // Check if there's a success message in the response
    const successMsg = event.detail.xhr.getResponseHeader('X-Success-Message');
    if (successMsg) {
      Alpine.store('notifications').add(successMsg, 'success', 3000);
    }
  }
});

document.body.addEventListener('htmx:responseError', (event) => {
  // Show error notification on failed requests
  Alpine.store('notifications').add('An error occurred. Please try again.', 'error', 5000);
});

document.body.addEventListener('htmx:sendError', (event) => {
  // Show error notification on network errors
  Alpine.store('notifications').add('Network error. Please check your connection.', 'error', 5000);
});

function layoutRoot() {
  return {
    sidebarOpen: false,
    sidebarCollapsed: Alpine.$persist(false).as('ctz_sidebar_collapsed'),
    darkMode: Alpine.$persist(true).as('ctz_dark'),

    init() {
      document.documentElement.classList.toggle('dark', this.darkMode);

      const mq = window.matchMedia('(min-width: 1024px)');
      const onChange = () => { if (mq.matches) this.sidebarOpen = false; };
      mq.addEventListener?.('change', onChange);
      onChange();

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.sidebarOpen = false;
      });
    },

    toggleDark() {
      this.darkMode = !this.darkMode;
      document.documentElement.classList.toggle('dark', this.darkMode);
    },

    toggleSidebar() { this.sidebarOpen = !this.sidebarOpen; },
    toggleCollapse() { this.sidebarCollapsed = !this.sidebarCollapsed; },
  };
}