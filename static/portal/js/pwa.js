(() => {
  'use strict';

  const buttons = [document.getElementById('nv-install-app')].filter(Boolean);

  const standalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;

  if (standalone) {
    buttons.forEach((button) => {
      button.hidden = true;
    });
  }

  let installPrompt = null;

  const isAppleMobile = () => {
    const ua = navigator.userAgent || '';
    return (
      /iPhone|iPad|iPod/i.test(ua) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
    );
  };

  const showInstallHelp = () => {
    const message = isAppleMobile()
      ? 'برای نصب در آیفون یا آیپد، سایت را در Safari باز کنید، دکمهٔ Share را بزنید و گزینهٔ Add to Home Screen (افزودن به صفحهٔ اصلی) را انتخاب کنید.'
      : 'اگر گزینهٔ نصب نمایش داده نمی‌شود، سایت را با آخرین نسخهٔ Chrome یا Edge باز کنید و از منوی مرورگر گزینهٔ Install app یا نصب برنامه را انتخاب کنید. در موبایل نیز می‌توانید از منوی مرورگر گزینهٔ Add to Home screen را بزنید.';
    window.alert(message);
  };

  if (!standalone) {
    buttons.forEach((button) => {
      button.hidden = false;
      button.addEventListener('click', async () => {
        if (!installPrompt) {
          showInstallHelp();
          return;
        }

        try {
          await installPrompt.prompt();
          await installPrompt.userChoice;
        } catch {
          showInstallHelp();
        } finally {
          installPrompt = null;
        }
      });
    });

    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      installPrompt = event;
    });

    window.addEventListener('appinstalled', () => {
      installPrompt = null;
      buttons.forEach((button) => {
        button.hidden = true;
      });
    });
  }

  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener(
      'load',
      () => {
        (async () => {
          try {
            // Remove the former admin-only worker so both areas are controlled
            // by the same root-scoped public-site worker.
            const registrations = await navigator.serviceWorker.getRegistrations();
            await Promise.all(
              registrations
                .filter(
                (registration) => registration.scope === `${window.location.origin}/admin/`
              )
                .map((registration) => registration.unregister())
            );
            await navigator.serviceWorker.register('/service-worker.js', {
              scope: '/',
            });
          } catch {
            if (window.location.hostname === 'localhost') {
              console.warn(
                'Service worker registration failed; PWA features may be unavailable.'
              );
            }
          }
        })();
      },
      { once: true }
    );
  }
})();
