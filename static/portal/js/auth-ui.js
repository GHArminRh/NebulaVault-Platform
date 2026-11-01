// Page-only behavior for the two-sided sign-in / registration card.
// Accessible two-sided sign-in / registration card.
document.querySelectorAll('.nv-auth-shell').forEach((shell) => {
  const card = shell.querySelector('[data-auth-card]');
  if (!card) return;
  const setSide = (side) => {
    card.classList.toggle('is-register', side === 'register');
    shell.setAttribute('data-auth-side', side);
    shell.querySelectorAll('.nv-auth-face').forEach((face) => {
      const active = (side === 'register') === face.classList.contains('nv-auth-register');
      face.inert = !active;
      face.setAttribute('aria-hidden', String(!active));
    });
    if (typeof window.nvRenderAuthTurnstile === 'function') window.nvRenderAuthTurnstile();
  };
  shell.querySelectorAll('[data-auth-flip]').forEach((button) => {
    button.addEventListener('click', () => setSide(button.getAttribute('data-auth-flip')));
  });
  setSide(shell.getAttribute('data-auth-side') || 'login');
});
