(() => {
  'use strict';

  document.addEventListener('click', (event) => {
    const origin = event.target;
    if (!(origin instanceof Element)) return;

    const toggle = origin.closest('.nv-reply-toggle[data-reply-target]');
    if (!toggle) return;

    const replyForm = document.getElementById(toggle.dataset.replyTarget);
    if (!replyForm) return;

    replyForm.hidden = !replyForm.hidden;
    toggle.setAttribute('aria-expanded', String(!replyForm.hidden));
  });

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.confirm) return;

    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
})();
