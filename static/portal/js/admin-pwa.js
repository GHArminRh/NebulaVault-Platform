(() => {
  'use strict';
  const button = document.getElementById('nv-admin-install');
  let deferredPrompt = null;

  const standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  if (button && !standalone) {
    button.hidden = false;
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault();
      deferredPrompt = event;
      button.dataset.nativeInstall = 'true';
    });
    button.addEventListener('click', async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        await deferredPrompt.userChoice;
        deferredPrompt = null;
        return;
      }
      const ua = navigator.userAgent || '';
      const ios = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
      window.alert(ios
        ? 'برای نصب پنل در iPhone یا iPad، این صفحه را در Safari باز کنید، Share را بزنید و Add to Home Screen را انتخاب کنید.'
        : 'برای نصب پنل، از منوی مرورگر گزینهٔ Install app یا نصب برنامه را انتخاب کنید. در موبایل نیز می‌توانید Add to Home Screen را بزنید.');
    });
    window.addEventListener('appinstalled', () => { button.hidden = true; });
  } else if (button) {
    button.hidden = true;
  }

  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/admin/service-worker.js', { scope: '/admin/' }).catch(() => {});
    }, { once: true });
  }

  const initializeAppSections = () => {
    if (!document.body.classList.contains('dashboard')) return;
    document.querySelectorAll('#content-main .app').forEach((app, index) => {
      const heading = app.querySelector(':scope > table caption, :scope > h2, :scope > caption');
      const table = app.querySelector(':scope > table');
      if (!heading || !table || app.dataset.nvCollapsible === 'true') return;
      app.dataset.nvCollapsible = 'true';
      table.hidden = true;
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'nv-admin-app-toggle';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = 'نمایش بخش';
      toggle.addEventListener('click', () => {
        const open = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', String(!open));
        table.hidden = open;
        toggle.textContent = open ? 'نمایش بخش' : 'بستن بخش';
      });
      heading.appendChild(toggle);
    });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeAppSections, { once: true });
  else initializeAppSections();
})();
