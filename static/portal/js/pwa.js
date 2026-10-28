(() => {
  "use strict";
  let installPrompt = null;
  const button = document.getElementById("nv-install-app");
  if (!button) return;

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    button.hidden = false;
    button.dataset.installAvailable = "true";
    button.setAttribute("aria-label", "نصب اپلیکیشن نبیولا والت");
  });

  window.addEventListener("appinstalled", () => {
    installPrompt = null;
    button.hidden = true;
  });

  button.addEventListener("click", async () => {
    if (installPrompt) {
      installPrompt.prompt();
      await installPrompt.userChoice;
      installPrompt = null;
      return;
    }
    const ua = navigator.userAgent || "";
    const isAppleMobile = /iPhone|iPad|iPod/i.test(ua) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const message = isAppleMobile
      ? "برای نصب در آیفون یا آیپد، سایت را در Safari باز کنید، دکمهٔ Share را بزنید و گزینهٔ Add to Home Screen (افزودن به صفحهٔ اصلی) را انتخاب کنید."
      : "اگر گزینهٔ نصب نمایش داده نمی‌شود، سایت را با آخرین نسخهٔ Chrome یا Edge باز کنید و از منوی مرورگر گزینهٔ Install app یا نصب برنامه را انتخاب کنید. در موبایل نیز می‌توانید از منوی مرورگر گزینهٔ Add to Home screen را بزنید.";
    window.alert(message);
  });

  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(() => {});
    }, { once: true });
  }
})();
