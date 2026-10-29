(() => {
  "use strict";

  const shell = document.querySelector(".nv-auth-shell");
  if (!shell) return;

  function renderActiveTurnstile() {
    if (!window.turnstile) return;

    const side = shell.getAttribute("data-auth-side") || "login";
    const face = shell.querySelector(side === "register" ? ".nv-auth-register" : ".nv-auth-login");
    if (!face) return;

    face.querySelectorAll('.nv-turnstile-widget:not([data-rendered="true"])').forEach((widget) => {
      const siteKey = widget.getAttribute("data-sitekey");
      if (!siteKey) return;

      try {
        window.turnstile.render(widget, {
          sitekey: siteKey,
          theme: "dark",
          language: "fa",
          size: "normal",
          appearance: "always",
        });
        widget.setAttribute("data-rendered", "true");

        const box = widget.closest(".turnstile-shell");
        const loading = box && box.querySelector(".turnstile-loading");
        if (!loading) return;

        const hideLoaderWhenReady = () => {
          if (!widget.querySelector("iframe")) return false;
          loading.style.display = "none";
          return true;
        };

        if (!hideLoaderWhenReady()) {
          const observer = new MutationObserver(() => {
            if (hideLoaderWhenReady()) observer.disconnect();
          });
          observer.observe(widget, { childList: true, subtree: true });
        }
      } catch (error) {
        // Preserve the loading/error surface if the provider is unavailable.
      }
    });
  }

  window.nvRenderAuthTurnstile = renderActiveTurnstile;
  window.nvTurnstileReady = () => {
    document.documentElement.classList.add("turnstile-script-loaded");
    renderActiveTurnstile();
  };
})();
