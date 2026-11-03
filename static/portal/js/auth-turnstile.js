(() => {
  'use strict';

  const shell = document.querySelector('.nv-auth-shell');
  if (!shell) return;

  function renderActiveTurnstile() {
    if (!window.turnstile) return;

    const side = shell.getAttribute('data-auth-side') || 'login';
    const face = shell.querySelector(side === 'register' ? '.nv-auth-register' : '.nv-auth-login');
    if (!face) return;

    face.querySelectorAll('.nv-turnstile-widget:not([data-rendered="true"])').forEach((widget) => {
      const siteKey = widget.getAttribute('data-sitekey');
      if (!siteKey) return;

      try {
        // Cloudflare's compact challenge is needed when the card's content
        // width is too narrow for the standard 300px widget (small iPhones).
        const compact = (widget.closest('.nv-auth-face')?.clientWidth || window.innerWidth) <= 320;
        window.turnstile.render(widget, {
          sitekey: siteKey,
          action: widget.getAttribute('data-action') || 'customer_auth',
          theme: 'dark',
          language: 'fa',
          size: compact ? 'compact' : 'normal',
          appearance: 'always',
        });
        widget.setAttribute('data-rendered', 'true');

        // The provider has accepted the render request. Its iframe may be
        // attached asynchronously or outside this node, so waiting for a
        // descendant iframe can leave our preparation overlay stuck forever.
        const loading = widget.closest('.turnstile-shell')?.querySelector('.turnstile-loading');
        if (loading) {
          loading.style.display = 'none';
          loading.setAttribute('data-state', 'ready');
        }
      } catch {
        // Preserve the loading/error surface if the provider is unavailable.
      }
    });
  }

  window.nvRenderAuthTurnstile = renderActiveTurnstile;
  window.nvTurnstileReady = () => {
    document.documentElement.classList.add('turnstile-script-loaded');
    renderActiveTurnstile();
  };
})();
