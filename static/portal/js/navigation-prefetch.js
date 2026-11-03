(() => {
  'use strict';

  // Prefetch only safe, same-origin document links after clear user intent.
  // Authentication, account, cart, payment, admin and API routes are excluded.
  const MAX_PREFETCHES = 6;
  const prefetched = new Set();
  const excludedPath = /\/(?:admin|api|login|logout|register|cart|checkout|payment|account|dashboard)(?:\/|$)/i;

  const canPrefetch = (anchor) => {
    if (
      !anchor ||
      anchor.hasAttribute('download') ||
      anchor.target === '_blank' ||
      anchor.relList.contains('nofollow') ||
      anchor.dataset.noPrefetch !== undefined
    ) {
      return null;
    }

    let url;
    try {
      url = new URL(anchor.href, window.location.href);
    } catch {
      return null;
    }

    if (
      url.origin !== window.location.origin ||
      url.username ||
      url.password ||
      url.pathname === window.location.pathname ||
      excludedPath.test(url.pathname) ||
      url.pathname.startsWith('/.well-known/')
    ) {
      return null;
    }

    // Ignore fragment-only changes and non-HTML-looking endpoints.
    if (url.pathname === window.location.pathname && url.search === window.location.search) {
      return null;
    }

    return url;
  };

  const prefetch = (anchor) => {
    if (
      document.visibilityState !== 'visible' ||
      prefetched.size >= MAX_PREFETCHES ||
      navigator.connection?.saveData ||
      /^(?:slow-2g|2g)$/.test(navigator.connection?.effectiveType || '')
    ) {
      return;
    }

    const url = canPrefetch(anchor);
    if (!url) return;

    const key = url.href;
    if (prefetched.has(key)) return;
    prefetched.add(key);

    const hint = document.createElement('link');
    hint.rel = 'prefetch';
    hint.as = 'document';
    hint.href = key;
    hint.referrerPolicy = 'same-origin';
    document.head.append(hint);
  };

  // Pointer intent is useful on desktop; keyboard focus gets the same benefit.
  document.addEventListener('pointerover', (event) => {
    if (event.pointerType === 'touch') return;
    const anchor = event.target.closest?.('a[href]');
    if (anchor) prefetch(anchor);
  }, { passive: true });

  document.addEventListener('focusin', (event) => {
    const anchor = event.target.closest?.('a[href]');
    if (anchor) prefetch(anchor);
  });
})();
