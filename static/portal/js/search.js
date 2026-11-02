(() => {
  const normalizeQuery = (value) =>
    String(value || '')
      .normalize('NFKC')
      .replace(/[يى]/g, 'ی')
      .replace(/ك/g, 'ک')
      .replace(/[ۀة]/g, 'ه')
      .replace(/ـ/g, '')
      .replace(/[\u064b-\u065f\u0670]/g, '')
      .replace(/[\u200c\u200d]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

  const safeUrl = (value) => {
    try {
      const url = new URL(value, window.location.origin);
      return url.origin === window.location.origin ? url.href : null;
    } catch {
      return null;
    }
  };

  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const renderResults = (container, payload) => {
    container.replaceChildren();
    const groups = [
      { label: 'محصولات', hits: payload.results?.[0]?.hits || [] },
      { label: 'مقالات', hits: payload.results?.[1]?.hits || [] },
    ];
    let count = 0;
    groups.forEach((group) => {
      if (!group.hits.length) return;
      const section = element('section', 'nv-search-group');
      section.append(element('div', 'nv-search-group-title', group.label));
      group.hits.forEach((hit) => {
        const href = safeUrl(hit.url);
        if (!href) return;
        count += 1;
        const link = element('a', 'nv-search-hit');
        link.href = href;
        link.append(element('strong', '', hit.title || hit.name || 'بدون عنوان'));
        const summary = hit.excerpt || hit.description || hit.content || '';
        if (summary) link.append(element('p', '', summary.slice(0, 190)));
        const metadata = [
          hit.category,
          ...(hit.platforms || []).slice(0, 2),
          ...(hit.tags || []).slice(0, 2),
        ]
          .filter(Boolean)
          .join(' · ');
        if (metadata) link.append(element('small', '', metadata));
        section.append(link);
      });
      if (section.childElementCount > 1) container.append(section);
    });
    if (!count)
      container.append(element('div', 'nv-search-empty', 'نتیجه‌ای برای این عبارت پیدا نشد.'));
  };

  const runSearch = async (root, query, sequence) => {
    const status = root.querySelector('[data-algolia-status]');
    const results = root.querySelector('[data-algolia-results]');
    if (!results || !query) return;
    if (status) status.textContent = 'در حال جست‌وجو…';
    const appId = root.dataset.algoliaAppId;
    const apiKey = root.dataset.algoliaSearchKey;
    const controller = new AbortController();
    root._algoliaController?.abort();
    root._algoliaController = controller;
    try {
      const response = await fetch(
        'https://' + encodeURIComponent(appId) + '-dsn.algolia.net/1/indexes/*/queries',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Algolia-Application-Id': appId,
            'X-Algolia-API-Key': apiKey,
          },
          body: JSON.stringify({
            requests: [
              {
                indexName: root.dataset.algoliaProductsIndex,
                params: new URLSearchParams({
                  query,
                  hitsPerPage: root.dataset.fullSearch === 'true' ? '8' : '4',
                }).toString(),
              },
              {
                indexName: root.dataset.algoliaArticlesIndex,
                params: new URLSearchParams({
                  query,
                  hitsPerPage: root.dataset.fullSearch === 'true' ? '8' : '4',
                }).toString(),
              },
            ],
          }),
          signal: controller.signal,
        }
      );
      if (!response.ok) throw new Error('Algolia request failed: ' + response.status);
      const payload = await response.json();
      if (sequence !== root._algoliaSequence) return;
      renderResults(results, payload);
      const total = (payload.results || []).reduce((sum, item) => sum + (item.nbHits || 0), 0);
      if (status)
        status.textContent = total ? total + ' نتیجه در محصولات و مقالات' : 'نتیجه‌ای پیدا نشد.';
    } catch (error) {
      if (error.name === 'AbortError') return;
      if (status)
        status.textContent = 'ارتباط با سرویس جست‌وجو برقرار نشد. کمی بعد دوباره تلاش کن.';
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-algolia-search]').forEach((root) => {
      const input = root.querySelector('[data-algolia-search-input]');
      if (!input) return;
      const params = new URLSearchParams(window.location.search);
      if (root.dataset.fullSearch === 'true' && params.get('q')) input.value = params.get('q');
      let timer = 0;
      const search = () => {
        const query = normalizeQuery(input.value);
        const sequence = (root._algoliaSequence || 0) + 1;
        root._algoliaSequence = sequence;
        window.clearTimeout(timer);
        if (query.length < 2) {
          root._algoliaController?.abort();
          root.querySelector('[data-algolia-results]')?.replaceChildren();
          const status = root.querySelector('[data-algolia-status]');
          if (status) status.textContent = 'حداقل دو نویسه وارد کن.';
          return;
        }
        timer = window.setTimeout(() => runSearch(root, query, sequence), 260);
      };
      input.addEventListener('input', search);
      if (input.value.length >= 2) search();
    });

    const dialog = document.getElementById('nv-search-dialog');
    const openButton = document.getElementById('nv-search-open');
    if (dialog && openButton) {
      openButton.addEventListener('click', () => {
        if (typeof dialog.showModal === 'function') dialog.showModal();
        else dialog.setAttribute('open', '');
        dialog.querySelector('[data-algolia-search-input]')?.focus();
      });
      dialog.querySelector('[data-search-close]')?.addEventListener('click', () => dialog.close());
      dialog.addEventListener('click', (event) => {
        if (event.target === dialog) dialog.close();
      });
    }
  });
})();
