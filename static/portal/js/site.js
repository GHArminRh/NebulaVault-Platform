document.addEventListener('DOMContentLoaded', () => {
  // Give every POST form an immediate, accessible loading state. The browser
  // continues the native submission; only the initiating submit control is locked.
  document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (form.dataset.submitting === 'true') {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = 'true';
      form.setAttribute('aria-busy', 'true');
      const submitter =
        event.submitter || form.querySelector('button[type="submit"], input[type="submit"]');
      if (!submitter) return;
      // Preserve the clicked submit button's name/value before disabling it.
      if (submitter.name && submitter.value) {
        const submittedValue = document.createElement('input');
        submittedValue.type = 'hidden';
        submittedValue.name = submitter.name;
        submittedValue.value = submitter.value;
        form.append(submittedValue);
      }
      submitter.classList.add('is-loading');
      submitter.setAttribute('aria-disabled', 'true');
      submitter.disabled = true;
      if (submitter.tagName === 'BUTTON') {
        const spinner = document.createElement('span');
        spinner.className = 'nv-button-spinner';
        spinner.setAttribute('aria-hidden', 'true');
        submitter.append(spinner);
      } else {
        submitter.dataset.originalValue = submitter.value;
        submitter.value = 'Processing…';
        const spinner = document.createElement('span');
        spinner.className = 'nv-button-spinner';
        spinner.setAttribute('aria-hidden', 'true');
        submitter.insertAdjacentElement('afterend', spinner);
      }
      form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach((control) => {
        if (control !== submitter) control.disabled = true;
      });
    });
  });

  // Reveal only the field belonging to the selected second-factor method.
  document.querySelectorAll('form').forEach((form) => {
    const selector = form.querySelector('[name="two_factor_method"]');
    const panels = form.querySelectorAll('[data-factor]');
    if (!selector || !panels.length) return;
    const updateFactorPanel = () => {
      const selected = selector.value;
      panels.forEach((panel) => {
        const active = panel.dataset.factor === selected;
        panel.hidden = !active;
        panel.querySelectorAll('input').forEach((input) => {
          input.disabled = !active;
          input.required = active && input.name !== 'email_otp_token';
        });
      });
    };
    selector.addEventListener('change', updateFactorPanel);
    updateFactorPanel();
  });

  // Page-load progress: animate with requestAnimationFrame and stop cleanly at 91%
  // until the browser confirms the load event. Keep the tip synchronized with the track.
  const progress = document.querySelector('.nv-page-progress');
  if (progress) {
    const targetProgress = 91;
    const referenceFrameMs = 1000 / 60;
    let progressValue = 0;
    let progressFrame = 0;
    let lastProgressFrameTime = 0;
    let finishTimer = 0;
    let resetTimer = 0;
    let isRunning = false;
    let isFinished = false;

    const setProgress = (value) => {
      progressValue = Math.max(progressValue, Math.min(100, value));
      progress.style.setProperty('--nv-progress', progressValue + '%');
      progress.style.setProperty('--nv-progress-ratio', String(progressValue / 100));
      progress.setAttribute('aria-valuenow', String(Math.round(progressValue)));
    };

    const advanceProgress = (timestamp) => {
      if (!isRunning || isFinished) {
        progressFrame = 0;
        return;
      }

      // Time-based easing is stable across 60 Hz, 120 Hz and throttled frames.
      const elapsed = lastProgressFrameTime
        ? Math.min(timestamp - lastProgressFrameTime, 100)
        : referenceFrameMs;
      lastProgressFrameTime = timestamp;

      const remaining = targetProgress - progressValue;
      if (remaining <= 0.05) {
        setProgress(targetProgress);
        progressFrame = 0;
        return;
      }

      const frameRatio = 1 - Math.pow(1 - 0.012, elapsed / referenceFrameMs);
      setProgress(Math.min(targetProgress, progressValue + remaining * frameRatio));
      progressFrame =
        progressValue < targetProgress ? window.requestAnimationFrame(advanceProgress) : 0;
    };

    const startProgress = () => {
      window.clearTimeout(finishTimer);
      window.clearTimeout(resetTimer);
      if (progressFrame) {
        window.cancelAnimationFrame(progressFrame);
        progressFrame = 0;
      }

      lastProgressFrameTime = 0;
      progressValue = 0;
      isRunning = true;
      isFinished = false;
      progress.classList.remove('is-complete');
      progress.classList.add('is-loading');
      setProgress(4);
      progressFrame = window.requestAnimationFrame(advanceProgress);
    };

    const completeProgress = () => {
      if (isFinished) return;

      isRunning = false;
      isFinished = true;
      if (progressFrame) {
        window.cancelAnimationFrame(progressFrame);
        progressFrame = 0;
      }
      lastProgressFrameTime = 0;
      setProgress(100);
      progress.classList.add('is-complete');

      // Keep the completed state briefly, then fade and reset for a possible restore.
      finishTimer = window.setTimeout(() => {
        progress.classList.remove('is-loading');
        resetTimer = window.setTimeout(() => {
          progress.classList.remove('is-complete');
          progress.style.setProperty('--nv-progress', '0%');
          progress.style.setProperty('--nv-progress-ratio', '0');
          progress.setAttribute('aria-valuenow', '0');
          progressValue = 0;
          lastProgressFrameTime = 0;
          isFinished = false;
        }, 420);
      }, 420);
    };

    if (document.readyState !== 'complete') {
      startProgress();
      window.addEventListener('load', completeProgress, { once: true });
    }

    window.addEventListener('pageshow', (event) => {
      if (event.persisted) completeProgress();
    });
  }

  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.mobile-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      nav.hidden = open;
    });
    nav.querySelectorAll('a[href*="#"]').forEach((link) =>
      link.addEventListener('click', () => {
        toggle.setAttribute('aria-expanded', 'false');
        nav.hidden = true;
      })
    );
  }
  document.querySelectorAll('.password-toggle').forEach((button) =>
    button.addEventListener('click', () => {
      const input = button.parentElement.querySelector('input');
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.textContent = show ? 'پنهان' : 'نمایش';
      button.setAttribute('aria-label', show ? 'پنهان‌کردن رمز عبور' : 'نمایش رمز عبور');
    })
  );
  document
    .querySelectorAll('.message-close')
    .forEach((button) =>
      button.addEventListener('click', () => button.closest('.message')?.remove())
    );
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        }),
      { threshold: 0.08 }
    );
    document
      .querySelectorAll('.product-card,.pricing-card,.feature-row,.panel,.stat-card')
      .forEach((el) => {
        el.classList.add('reveal');
        observer.observe(el);
      });
  }
  // Load page-specific enhancements separately so they do not inflate the shared entry point.
  if (document.querySelector('.nv-auth-shell')) {
    void import('./auth-ui.js');
  }

  const hasSectionNavigation =
    document.querySelector('.nv-rail-link[href^="#"]') ||
    [...document.querySelectorAll('.desktop-nav a[href*="#"], .mobile-nav a[href*="#"]')].some(
      (link) => {
        try {
          const url = new URL(link.href, location.href);
          return url.pathname === location.pathname && Boolean(url.hash);
        } catch {
          return false;
        }
      }
    );
  if (hasSectionNavigation) {
    void import('./section-navigation.js');
  }

  // The canvas/ambient effects are intentionally non-critical: fetch their chunk after first paint.
  if (document.querySelector('.nv-starfield, .ambient')) {
    const loadVisualEffects = () => void import('./visual-effects.js');
    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(loadVisualEffects, { timeout: 1200 });
    } else {
      window.setTimeout(loadVisualEffects, 250);
    }
  }
});
