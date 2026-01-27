// Video modal functionality
document.addEventListener('DOMContentLoaded', function() {
  const videoModal = document.getElementById('videoModal');
  const videoModalOverlay = document.getElementById('videoModalOverlay');
  const videoModalClose = document.getElementById('videoModalClose');
  const videoModalFrame = document.getElementById('videoModalFrame');

  function convertYouTubeUrl(url) {
    if (!url) return null;
    url = url.trim();
    
    if (url.includes('youtube.com/embed/')) {
      const embedMatch = url.match(/youtube\.com\/embed\/([^?&]+)/);
      if (embedMatch) {
        return `https://www.youtube.com/embed/${embedMatch[1]}`;
      }
      return url;
    }
    
    let videoId = '';
    const watchMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
    if (watchMatch) {
      videoId = watchMatch[1];
    }
    
    const shortMatch = url.match(/youtu\.be\/([^&\n?#]+)/);
    if (shortMatch) {
      videoId = shortMatch[1];
    }
    
    if (videoId) {
      videoId = videoId.split('&')[0].split('?')[0].split('#')[0];
      return `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`;
    }
    
    return null;
  }

  function openVideoModal(videoUrl) {
    const embedUrl = convertYouTubeUrl(videoUrl);
    if (embedUrl && videoModalFrame) {
      videoModalFrame.src = '';
      setTimeout(() => {
        videoModalFrame.src = embedUrl;
        if (videoModal) videoModal.classList.add('active');
        document.body.style.overflow = 'hidden';
      }, 10);
    } else {
      window.open(videoUrl, '_blank');
    }
  }

  function closeVideoModal() {
    if (videoModal) videoModal.classList.remove('active');
    if (videoModalFrame) {
      videoModalFrame.src = '';
    }
    document.body.style.overflow = '';
  }

  document.addEventListener('click', function(e) {
    const videoLink = e.target.closest('[data-video-url]');
    if (videoLink) {
      e.preventDefault();
      const videoUrl = videoLink.getAttribute('data-video-url');
      openVideoModal(videoUrl);
    }
  });

  if (videoModalOverlay) {
    videoModalOverlay.addEventListener('click', closeVideoModal);
  }
  
  if (videoModalClose) {
    videoModalClose.addEventListener('click', closeVideoModal);
  }

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && videoModal && videoModal.classList.contains('active')) {
      closeVideoModal();
    }
  });
});
