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