(() => {
  "use strict";

  const form = document.querySelector("[data-resend-form]");
  if (!form) return;

  const button = form.querySelector("[data-resend-button]");
  const label = form.querySelector("[data-countdown]");
  if (!button || !label) return;

  const purpose = form.dataset.purpose || "";
  const email = (form.dataset.email || "").trim().toLowerCase();
  const storageKey = "nv-" + purpose + "-resend:" + email;
  const cooldownMs = 30_000;
  let until = 0;
  let timerId = 0;

  try {
    until = Number(window.sessionStorage.getItem(storageKey)) || 0;
  } catch (error) {
    // Storage is optional; the in-memory cooldown still protects this page view.
    until = 0;
  }

  if (until <= Date.now()) {
    until = Date.now() + cooldownMs;
    try {
      window.sessionStorage.setItem(storageKey, String(until));
    } catch (error) {
      // Continue with the in-memory cooldown when browser storage is unavailable.
    }
  }

  function renderCountdown() {
    window.clearTimeout(timerId);
    const remainingSeconds = Math.max(0, Math.ceil((until - Date.now()) / 1000));
    button.disabled = remainingSeconds > 0;
    label.textContent = remainingSeconds > 0 ? "(" + remainingSeconds + " ثانیه)" : "";

    if (remainingSeconds > 0) {
      timerId = window.setTimeout(renderCountdown, 250);
    }
  }

  form.addEventListener("submit", () => {
    until = Date.now() + cooldownMs;

    try {
      window.sessionStorage.setItem(storageKey, String(until));
    } catch (error) {
      // The timer still updates for this page view if storage is unavailable.
    }

    renderCountdown();
  });

  renderCountdown();
})();
