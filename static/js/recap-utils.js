// Utility functions for recap page
function getCSRFToken() {
  // Try to get CSRF token from hidden input first
  const hiddenInput = document.querySelector('[name=csrfmiddlewaretoken]');
  if (hiddenInput && hiddenInput.value) {
    return hiddenInput.value;
  }
  
  // Try to get from cookie
  let token = getCookie('csrftoken');
  if (token) return token;
  
  // Try alternative cookie names
  token = getCookie('csrf_token');
  if (token) return token;
  
  // Fallback: try to get from meta tag
  const metaTag = document.querySelector('meta[name=csrf-token]');
  if (metaTag) return metaTag.getAttribute('content');
  
  return null;
}

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

function showShareModal() {
  alert('Share modal functionality coming soon!');
}
