(function () {
  const loader = document.getElementById('global-loader');
  if (!loader) return;

  let timer = null;

  function showDelayed() {
    // avoid flash for fast requests
    clearTimeout(timer);
    timer = setTimeout(() => loader.classList.remove('hidden'), 180);
  }

  function hideNow() {
    clearTimeout(timer);
    loader.classList.add('hidden');
  }

  document.body.addEventListener('htmx:beforeRequest', (e) => {
    // only show for dashboard swaps (adjust if you want global-global)
    const t = e.detail?.target;
    if (t && t.id === 'dashboard-content') showDelayed();
  });

  document.body.addEventListener('htmx:afterSwap', (e) => {
    const t = e.detail?.target;
    if (t && t.id === 'dashboard-content') hideNow();
  });

  document.body.addEventListener('htmx:responseError', hideNow);
})();