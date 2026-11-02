(() => {
  'use strict';

  const body = document.body;
  const measurementId = body?.dataset.ga4Id || '';
  if (!/^G-[A-Z0-9]+$/i.test(measurementId)) return;

  const consentBanner = document.getElementById('nv-analytics-consent');
  const consentCookieName = 'nv_analytics_consent';
  const cookieMaxAge = 60 * 60 * 24 * 180;
  const deniedConsent = {
    analytics_storage: 'denied',
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
  };
  const acceptedConsent = {
    analytics_storage: 'granted',
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
  };

  function readConsent() {
    const entry = document.cookie
      .split('; ')
      .find((part) => part.startsWith(consentCookieName + '='));
    return entry ? decodeURIComponent(entry.split('=').slice(1).join('=')) : '';
  }

  function saveConsent(value) {
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie =
      consentCookieName +
      '=' +
      encodeURIComponent(value) +
      '; Max-Age=' +
      cookieMaxAge +
      '; Path=/; SameSite=Lax' +
      secure;
  }

  function safePageUrl(value) {
    try {
      const url = new URL(value, window.location.origin);
      url.search = '';
      url.hash = '';
      if (/^\/accounts\/verify\//.test(url.pathname)) {
        url.pathname = '/accounts/verify/';
      } else if (/^\/accounts\/password\/reset\//.test(url.pathname)) {
        url.pathname = '/accounts/password/reset/';
      }
      return url.origin + url.pathname;
    } catch {
      return window.location.origin + '/';
    }
  }

  function ensureGoogleTag() {
    if (window.__nvGa4Loaded) {
      window.gtag('consent', 'update', acceptedConsent);
      window.__nvGa4Consent = 'granted';
      sendPendingAuthEvent();
      sendPageContextEvents();
      sendPurchaseEvent();
      return;
    }

    window.dataLayer = window.dataLayer || [];
    window.gtag =
      window.gtag ||
      function gtag() {
        window.dataLayer.push(arguments);
      };
    window.gtag('consent', 'default', deniedConsent);
    window.gtag('consent', 'update', acceptedConsent);
    window.gtag('js', new Date());
    window.gtag('config', measurementId, {
      send_page_view: false,
      page_location: safePageUrl(window.location.href),
      page_referrer: document.referrer ? safePageUrl(document.referrer) : '',
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });

    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(measurementId);
    document.head.appendChild(script);
    window.__nvGa4Loaded = true;
    window.__nvGa4Consent = 'granted';
    window.gtag('event', 'page_view', {
      page_location: safePageUrl(window.location.href),
      page_title: document.title,
    });
    sendPendingAuthEvent();
    sendPageContextEvents();
    sendPurchaseEvent();
  }

  function track(name, params, callback) {
    if (window.__nvGa4Consent !== 'granted' || typeof window.gtag !== 'function') return false;
    if (callback) {
      window.gtag('event', name, params || {}, {
        event_callback: callback,
        event_timeout: 600,
      });
    } else {
      window.gtag('event', name, params || {});
    }
    return true;
  }

  function normalizedPrice(minorUnits, currency) {
    const raw = Number(minorUnits);
    const code = String(currency || '').toUpperCase();
    if (!Number.isFinite(raw) || raw < 0) return null;
    if (code === 'IRT') return { price: raw / 10, currency: 'IRR' };
    return { price: raw / 100, currency: code };
  }

  function readItem(element) {
    const normalized = normalizedPrice(element.dataset.priceMinor, element.dataset.currency);
    const item = {
      item_id: element.dataset.itemId || '',
      item_name: element.dataset.itemName || '',
      item_category: element.dataset.itemCategory || '',
    };
    if (normalized) item.price = normalized.price;
    return item;
  }

  function sendPendingAuthEvent() {
    const eventName = body.dataset.ga4PendingEvent;
    if (eventName === 'login' || eventName === 'sign_up') {
      track(eventName, { method: 'email' });
      delete body.dataset.ga4PendingEvent;
    }
  }

  function sendPageContextEvents() {
    const products = Array.from(document.querySelectorAll('[data-ga4-view-item]'));
    if (products.length) {
      const items = products.map(readItem);
      const currencies = products.map(
        (product) => normalizedPrice(product.dataset.priceMinor, product.dataset.currency)?.currency
      );
      const distinctCurrencies = [...new Set(currencies.filter(Boolean))];
      const params = { items };
      if (distinctCurrencies.length === 1) {
        params.currency = distinctCurrencies[0];
        if (products.length === 1) {
          const price = normalizedPrice(products[0].dataset.priceMinor, products[0].dataset.currency);
          if (price) params.value = price.price;
        }
      }
      if (distinctCurrencies.length > 1) items.forEach((item) => delete item.price);
      track(products.length > 1 ? 'view_item_list' : 'view_item', params);
    }

    const cart = document.querySelector('[data-ga4-view-cart]');
    if (cart) {
      const rows = Array.from(cart.querySelectorAll('[data-ga4-cart-item]'));
      const items = rows.map(readItem);
      const currencies = rows.map(
        (row) => normalizedPrice(row.dataset.priceMinor, row.dataset.currency)?.currency
      );
      const distinctCurrencies = [...new Set(currencies.filter(Boolean))];
      const params = { items };
      if (distinctCurrencies.length === 1) {
        params.currency = distinctCurrencies[0];
        params.value = rows.reduce((sum, row) => {
          const price = normalizedPrice(row.dataset.priceMinor, row.dataset.currency);
          return sum + (price?.price || 0);
        }, 0);
      }
      if (distinctCurrencies.length > 1) items.forEach((item) => delete item.price);
      track('view_cart', params);
    }
  }

  function sendPurchaseEvent() {
    const payloadElement = document.getElementById('ga4-purchase-data');
    if (!payloadElement) return;

    let payload;
    try {
      payload = JSON.parse(payloadElement.textContent || '{}');
    } catch {
      return;
    }
    if (!payload.transaction_id || !Array.isArray(payload.items)) return;

    const key = 'nv_ga4_purchase_' + payload.transaction_id;
    window.__nvGa4PurchaseSent = window.__nvGa4PurchaseSent || {};
    if (window.__nvGa4PurchaseSent[payload.transaction_id]) return;
    try {
      if (window.localStorage.getItem(key)) return;
    } catch {
      // Local storage can be disabled by browser privacy settings.
    }

    if (track('purchase', payload)) {
      window.__nvGa4PurchaseSent[payload.transaction_id] = true;
      try {
        window.localStorage.setItem(key, '1');
      } catch {
        // Local storage can be disabled by browser privacy settings.
      }
    }
  }

  function submitAfterTracking(form, eventName, params) {
    let submitted = false;
    const submit = () => {
      if (submitted) return;
      submitted = true;
      HTMLFormElement.prototype.submit.call(form);
    };

    if (!track(eventName, params, submit)) {
      submit();
      return;
    }
    window.setTimeout(submit, 700);
  }

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;

    if (form.hasAttribute('data-ga4-add-to-cart')) {
      event.preventDefault();
      const item = readItem(form);
      const normalized = normalizedPrice(form.dataset.priceMinor, form.dataset.currency);
      submitAfterTracking(form, 'add_to_cart', {
        currency: normalized?.currency,
        value: normalized?.price,
        items: [item],
      });
      return;
    }

    if (form.hasAttribute('data-ga4-begin-checkout')) {
      event.preventDefault();
      const itemRows = Array.from(document.querySelectorAll('[data-ga4-cart-item]'));
      const items = itemRows.length ? itemRows.map(readItem) : [];
      const currency = form.dataset.currency || '';
      const normalized = normalizedPrice(form.dataset.priceMinor, currency);
      submitAfterTracking(form, 'begin_checkout', {
        currency: normalized?.currency,
        value: normalized?.price,
        items,
      });
    }
  });

  function showConsentBanner() {
    if (consentBanner) consentBanner.hidden = false;
  }

  function hideConsentBanner() {
    if (consentBanner) consentBanner.hidden = true;
  }

  function withdrawConsent() {
    const wasGranted = window.__nvGa4Consent === 'granted';
    saveConsent('denied');
    window.__nvGa4Consent = 'denied';
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', deniedConsent);
    }
    document.cookie.split(';').forEach((cookie) => {
      const name = cookie.split('=')[0].trim();
      if (name.startsWith('_ga')) {
        document.cookie = name + '=; Max-Age=0; Path=/; SameSite=Lax';
      }
    });
    hideConsentBanner();
    if (wasGranted) window.location.reload();
  }

  consentBanner?.querySelector('[data-ga4-accept]')?.addEventListener('click', () => {
    saveConsent('granted');
    hideConsentBanner();
    ensureGoogleTag();
  });
  consentBanner?.querySelector('[data-ga4-reject]')?.addEventListener('click', withdrawConsent);
  document.querySelectorAll('[data-ga4-open-settings]').forEach((button) => {
    button.addEventListener('click', showConsentBanner);
  });

  const currentConsent = readConsent();
  if (currentConsent === 'granted') {
    ensureGoogleTag();
  } else if (currentConsent === 'denied') {
    window.__nvGa4Consent = 'denied';
  } else {
    showConsentBanner();
  }
})();
