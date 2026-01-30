// Global HTMX configuration
document.body.addEventListener('htmx:configRequest', (event) => {
  // Add CSRF token to all requests
  event.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
});

// Show loading indicators
document.body.addEventListener('htmx:beforeRequest', (event) => {
  event.target.classList.add('htmx-loading');
});

document.body.addEventListener('htmx:afterRequest', (event) => {
  event.target.classList.remove('htmx-loading');
});

// Helper to get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
