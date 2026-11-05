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

  // Copy the active face's Turnstile token and registration consents to the
  // provider-start form. The server re-validates the token and terms checkbox.
  shell.querySelectorAll('form[data-social-start]').forEach((socialForm) => {
    socialForm.addEventListener('submit', () => {
      const flow = socialForm.dataset.socialFlow;
      const sourceSelector =
        flow === 'register' ? '.nv-auth-register .nv-auth-form' : '.nv-auth-login .nv-auth-form';
      const sourceForm = shell.querySelector(sourceSelector);
      if (!sourceForm) return;

      const token = sourceForm.querySelector('[name="cf-turnstile-response"]')?.value || '';
      const tokenField = socialForm.querySelector('[name="cf-turnstile-response"]');
      if (tokenField) tokenField.value = token;

      if (flow === 'register') {
        const terms = sourceForm.querySelector('[name="accept_terms"]');
        const newsletter = sourceForm.querySelector('[name="newsletter_opt_in"]');
        const termsField = socialForm.querySelector('[name="accept_terms"]');
        const newsletterField = socialForm.querySelector('[name="newsletter_opt_in"]');

        if (termsField) termsField.value = terms?.checked ? 'on' : '';
        if (newsletterField) {
          newsletterField.value = newsletter?.checked ? 'on' : '';
        }
      }

      const next = sourceForm.querySelector('[name="next"]')?.value || '';
      const nextField = socialForm.querySelector('[name="next"]');
      if (nextField) nextField.value = next;
    });
  });
});
