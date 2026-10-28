document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".mobile-nav");
  if (toggle && nav) toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!open));
    nav.hidden = open;
  });
  document.querySelectorAll(".password-toggle").forEach(button => button.addEventListener("click", () => {
    const input = button.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "پنهان" : "نمایش";
    button.setAttribute("aria-label", show ? "پنهان‌کردن رمز عبور" : "نمایش رمز عبور");
  }));
  document.querySelectorAll(".message-close").forEach(button => button.addEventListener("click", () => button.closest(".message")?.remove()));
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); }
    }), {threshold: .08});
    document.querySelectorAll(".product-card,.pricing-card,.feature-row,.panel,.stat-card").forEach(el => {el.classList.add("reveal");observer.observe(el);});
  }
  // Accessible two-sided sign-in / registration card.
  document.querySelectorAll(".nv-auth-shell").forEach(shell => {
    const card = shell.querySelector("[data-auth-card]");
    if (!card) return;
    const setSide = side => {
      card.classList.toggle("is-register", side === "register");
      shell.setAttribute("data-auth-side", side);
      shell.querySelectorAll(".nv-auth-face").forEach(face => {
        const active = (side === "register") === face.classList.contains("nv-auth-register");
        face.inert = !active;
        face.setAttribute("aria-hidden", String(!active));
      });
    };
    shell.querySelectorAll("[data-auth-flip]").forEach(button => {
      button.addEventListener("click", () => setSide(button.getAttribute("data-auth-flip")));
    });
    setSide(shell.getAttribute("data-auth-side") || "login");
  });
  // Keep dashboard rail's active state in sync with the visible section.
  const railLinks = [...document.querySelectorAll(".nv-rail-link[href^='#']")];
  const railTargets = railLinks.map(link => document.querySelector(link.getAttribute("href"))).filter(Boolean);
  if ("IntersectionObserver" in window && railTargets.length) {
    const railObserver = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) railLinks.forEach(link => link.classList.toggle("is-current", link.getAttribute("href") === "#" + entry.target.id));
    }), {rootMargin: "-20% 0px -65% 0px", threshold: 0});
    railTargets.forEach(target => railObserver.observe(target));
  }
  // Subtle mouse-reactive ambient lighting for pointer devices only.
  const ambientLayers = [...document.querySelectorAll(".ambient")];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(pointer: fine)").matches;
  if (ambientLayers.length && !reduceMotion && finePointer) {
    let framePending = false;
    let pointerX = 0;
    let pointerY = 0;
    window.addEventListener("pointermove", event => {
      pointerX = (event.clientX / Math.max(window.innerWidth, 1) - 0.5) * 2;
      pointerY = (event.clientY / Math.max(window.innerHeight, 1) - 0.5) * 2;
      if (framePending) return;
      framePending = true;
      window.requestAnimationFrame(() => {
        ambientLayers.forEach((layer, index) => {
          const depth = index === 0 ? 14 : -10;
          layer.style.transform = `translate3d(${pointerX * depth}px, ${pointerY * depth}px, 0)`;
        });
        framePending = false;
      });
    }, { passive: true });
    window.addEventListener("pointerleave", () => {
      ambientLayers.forEach(layer => { layer.style.transform = ""; });
    });
  }
});