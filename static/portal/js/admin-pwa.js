(() => {
  'use strict';

  const button = document.getElementById('nv-admin-install');
  let deferredPrompt = null;

  const standalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;

  if (button && !standalone) {
    button.hidden = false;
    window.addEventListener('beforeinstallprompt', (event) => {
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
      const ios =
        /iPhone|iPad|iPod/i.test(ua) ||
        (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

      window.alert(
        ios
          ? 'برای نصب پنل در iPhone یا iPad، این صفحه را در Safari باز کنید، Share را بزنید و Add to Home Screen را انتخاب کنید.'
          : 'برای نصب پنل، از منوی مرورگر گزینهٔ Install app یا نصب برنامه را انتخاب کنید. در موبایل نیز می‌توانید Add to Home Screen را بزنید.'
      );
    });

    window.addEventListener('appinstalled', () => {
      button.hidden = true;
    });
  } else if (button) {
    button.hidden = true;
  }

  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener(
      'load',
      () => {
        navigator.serviceWorker
          .register('/admin/service-worker.js', { scope: '/admin/' })
          .catch(() => {});
      },
      { once: true }
    );
  }

  const initializeAppSections = () => {
    if (!document.body.classList.contains('dashboard')) return;

    // Django's stock admin index renders one .module per app, each containing
    // a table whose caption is the app heading. Do not depend on app labels
    // or alter the table/model markup itself.
    document.querySelectorAll('#content-main .module').forEach((module) => {
      const table = module.querySelector(':scope > table');
      const heading = table && table.querySelector(':scope > caption');
      if (!table || !heading || module.dataset.nvCollapsible === 'true') return;

      module.dataset.nvCollapsible = 'true';
      const contentRows = Array.from(table.rows).filter(
        (row) => !row.closest('thead')
      );
      contentRows.forEach((row) => {
        row.hidden = true;
      });

      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'nv-admin-app-toggle';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = 'نمایش بخش';
      toggle.setAttribute('aria-label', 'نمایش یا بستن مدل‌های این اپ');

      toggle.addEventListener('click', () => {
        const open = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', String(!open));
        contentRows.forEach((row) => {
          row.hidden = open;
        });
        toggle.textContent = open ? 'نمایش بخش' : 'بستن بخش';
      });

      heading.appendChild(toggle);
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAppSections, {
      once: true,
    });
  } else {
    initializeAppSections();
  }
})();
