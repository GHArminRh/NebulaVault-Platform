(() => {
  'use strict';

  document.querySelectorAll('.nv-copy-license[data-copy-target]').forEach((button) => {
    button.addEventListener('click', async () => {
      const target = document.getElementById(button.dataset.copyTarget);
      if (!(target instanceof HTMLInputElement)) return;

      const originalLabel = button.textContent || 'کپی کلید';
      let copied = false;

      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(target.value);
          copied = true;
        } catch {
          // Fall back to selection-based copying if clipboard access is denied.
        }
      }

      if (!copied) {
        target.focus();
        target.select();
        try {
          copied = document.execCommand('copy');
        } catch {
          copied = false;
        }

        try {
          target.setSelectionRange(0, 0);
        } catch {
          // Some input implementations do not support selection ranges.
        }
      }

      const feedback = copied ? 'کپی شد' : 'کپی نشد';
      button.textContent = feedback;
      button.setAttribute('aria-label', feedback);
      window.setTimeout(() => {
        button.textContent = originalLabel;
        button.setAttribute('aria-label', originalLabel);
      }, 1800);
    });
  });
})();
