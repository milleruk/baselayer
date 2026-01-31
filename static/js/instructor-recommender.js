(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function buildSuggestionButton(item) {
    const name = escapeHtml(item.name || '');
    const img = item.image_url ? `<img src="${escapeHtml(item.image_url)}" class="h-8 w-8 rounded-full object-cover border border-gray-200 dark:border-gray-700" alt="">` : '';
    const fallback = !item.image_url
      ? `<div class="h-8 w-8 rounded-full bg-primary/10 dark:bg-primary/20 border border-primary/20 flex items-center justify-center text-primary font-bold text-sm">${name.slice(
          0,
          1
        )}</div>`
      : '';

    return `
      <button type="button" class="w-full text-left px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/70 transition-colors flex items-center gap-3" data-id="${escapeHtml(
        item.id
      )}" data-name="${name}">
        ${img || fallback}
        <div class="min-w-0">
          <div class="text-sm text-gray-900 dark:text-white truncate">${name}</div>
        </div>
      </button>
    `;
  }

  function initPicker(opts) {
    const input = qs(opts.inputSel);
    const idInput = qs(opts.idSel);
    const wrap = qs(opts.wrapSel);
    const list = qs(opts.listSel);
    const disciplineSel = qs('#discipline-select');
    if (!input || !idInput || !wrap || !list) return;

    let timer = null;
    let lastQ = '';

    function hide() {
      wrap.classList.add('hidden');
      list.innerHTML = '';
    }

    async function fetchSuggestions(q) {
      try {
        const base = (window.__INSTRUCTOR_RECOMMENDER__ && window.__INSTRUCTOR_RECOMMENDER__.suggestUrl) || '';
        const url = new URL(base, window.location.origin);
        url.searchParams.set('q', q);
        const discipline = (disciplineSel && disciplineSel.value) || (window.__INSTRUCTOR_RECOMMENDER__ && window.__INSTRUCTOR_RECOMMENDER__.discipline) || '';
        if (discipline) url.searchParams.set('discipline', discipline);

        const resp = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        if (!resp.ok) return [];
        const data = await resp.json();
        return data && Array.isArray(data.results) ? data.results : [];
      } catch (e) {
        return [];
      }
    }

    function render(items) {
      if (!Array.isArray(items) || items.length === 0) {
        hide();
        return;
      }
      list.innerHTML = items.map(buildSuggestionButton).join('');
      wrap.classList.remove('hidden');

      list.querySelectorAll('button[data-id]').forEach((btn) => {
        btn.addEventListener('mousedown', (e) => {
          // prevent blur hiding before click
          e.preventDefault();
          const id = btn.getAttribute('data-id') || '';
          const name = btn.getAttribute('data-name') || '';
          idInput.value = id;
          input.value = name;
          hide();
        });
      });
    }

    input.addEventListener('input', () => {
      const q = (input.value || '').trim();
      lastQ = q;
      idInput.value = ''; // invalidate until selected
      if (timer) window.clearTimeout(timer);
      if (q.length < 2) {
        hide();
        return;
      }
      timer = window.setTimeout(async () => {
        const items = await fetchSuggestions(q);
        if (lastQ !== q) return;
        render(items);
      }, 160);
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') hide();
    });

    document.addEventListener('click', (e) => {
      if (!wrap.contains(e.target) && e.target !== input) hide();
    });

    // Clear any typed text when discipline changes (keeps suggestions consistent)
    if (disciplineSel) {
      disciplineSel.addEventListener('change', () => {
        idInput.value = '';
        hide();
      });
    }

    // If we already have an ID (from query params), keep input as-is;
    // user can re-select if needed.
  }

  function init() {
    initPicker({
      inputSel: '#love-1-input',
      idSel: '#love-1-id',
      wrapSel: '#love-1-suggestions',
      listSel: '#love-1-suggestions-list',
    });
    initPicker({
      inputSel: '#love-2-input',
      idSel: '#love-2-id',
      wrapSel: '#love-2-suggestions',
      listSel: '#love-2-suggestions-list',
    });
    initPicker({
      inputSel: '#exclude-input',
      idSel: '#exclude-id',
      wrapSel: '#exclude-suggestions',
      listSel: '#exclude-suggestions-list',
    });

    // Ensure we don't submit with typed-but-unselected instructor names.
    const form = qs('#instructorRecommenderForm');
    if (form) {
      form.addEventListener('submit', (e) => {
        const love1 = qs('#love-1-id')?.value;
        const love2 = qs('#love-2-id')?.value;
        if (!love1 || !love2) {
          e.preventDefault();
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

