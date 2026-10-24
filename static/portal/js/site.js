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
});
