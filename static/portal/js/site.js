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
  // Scroll-aware section navigation. The first dashboard item is active on load;
  // the active item changes only when its section reaches the reading line.
  const railLinks = [...document.querySelectorAll(".nv-rail-link[href^='#']")];
  const railTargets = railLinks
    .map((link) => document.querySelector(link.getAttribute('href')))
    .filter(Boolean)
    .sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
  const homeLinks = [
    ...document.querySelectorAll(".desktop-nav a[href*='#'], .mobile-nav a[href*='#']"),
  ].filter((link) => {
    try {
      return (
        new URL(link.href, location.href).pathname === location.pathname &&
        Boolean(new URL(link.href, location.href).hash)
      );
    } catch {
      return false;
    }
  });
  const homeTargets = [
    ...new Set(
      homeLinks
        .map((link) => {
          try {
            return document.querySelector(
              decodeURIComponent(new URL(link.href, location.href).hash)
            );
          } catch {
            return null;
          }
        })
        .filter(Boolean)
    ),
  ].sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
  const syncScrollNavigation = () => {
    const header = document.querySelector('.site-header');
    // Match the active-section reading line to the actual sticky-header offset.
    const line = (header?.getBoundingClientRect().bottom || 0) + 28;
    const sync = (links, targets, fallbackId) => {
      if (!links.length || !targets.length) return;
      let current = targets[0];
      for (const target of targets) {
        if (target.getBoundingClientRect().top <= line) current = target;
      }
      if (window.scrollY < 8 && fallbackId)
        current = document.getElementById(fallbackId) || current;
      links.forEach((link) => {
        let hash = '';
        try {
          hash = new URL(link.href, location.href).hash;
        } catch {
          // Invalid link URLs are ignored for active-section highlighting.
        }
        const active = hash === '#' + current.id;
        link.classList.toggle('is-current', active);
        if (active) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    };
    sync(railLinks, railTargets, 'dashboard-overview');
    sync(homeLinks, homeTargets, 'home');
  };
  const getHashTarget = (hash) => {
    if (!hash) return null;
    try {
      return document.getElementById(decodeURIComponent(hash.replace(/^#/, '')));
    } catch {
      // Malformed percent-encoding in a URL fragment should not break page initialization.
      return null;
    }
  };
  const requestNavSync = (() => {
    let pending = false;
    return () => {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(() => {
        syncScrollNavigation();
        pending = false;
      });
    };
  })();
  const scrollToAnchor = (target, smooth = true) => {
    if (!target) return;
    const header = document.querySelector('.site-header');
    const offset = (header?.getBoundingClientRect().height || 0) + 12;
    const top = Math.max(0, window.scrollY + target.getBoundingClientRect().top - offset);
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top, behavior: smooth && !reduced ? 'smooth' : 'auto' });
    requestNavSync();
  };
  if (railTargets.length || homeTargets.length) {
    window.addEventListener('scroll', requestNavSync, { passive: true });
    window.addEventListener('resize', requestNavSync, { passive: true });
    window.addEventListener('hashchange', requestNavSync);
    window.addEventListener('popstate', () => {
      const target = getHashTarget(location.hash);
      if (target) scrollToAnchor(target);
      else requestNavSync();
    });
    document.querySelectorAll('a[href*="#"]').forEach((link) => {
      link.addEventListener('click', (event) => {
        let url;
        try {
          url = new URL(link.href, location.href);
        } catch {
          return;
        }
        if (url.pathname !== location.pathname || !url.hash) return;
        const target = getHashTarget(url.hash);
        if (!target) return;
        event.preventDefault();
        if (toggle && nav && link.closest('.mobile-nav')) {
          toggle.setAttribute('aria-expanded', 'false');
          nav.hidden = true;
        }
        const nextUrl = url.pathname + url.search + url.hash;
        if (location.pathname + location.search + location.hash !== nextUrl) {
          history.pushState(null, '', nextUrl);
        }
        scrollToAnchor(target);
      });
    });
    // Correct direct links such as /dashboard/#my-licenses after layout settles.
    if (location.hash) {
      window.setTimeout(() => {
        const target = getHashTarget(location.hash);
        if (target) scrollToAnchor(target, false);
        else requestNavSync();
      }, 100);
    } else {
      syncScrollNavigation();
    }
  }

  // Lightweight responsive starfield inspired by the desktop app: drifting,
  // softly twinkling particles with reduced-motion and background-tab support.
  const starCanvas = document.querySelector('.nv-starfield');
  const starContext = starCanvas?.getContext('2d', { alpha: true });
  if (starCanvas && starContext) {
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const stars = [];
    let width = 0,
      height = 0,
      dpr = 1,
      raf = 0,
      lastTime = 0;
    let pointerX = -10000,
      pointerY = -10000,
      pointerActive = false;
    let pointerTargetX = -10000,
      pointerTargetY = -10000;
    window.addEventListener(
      'pointermove',
      (event) => {
        if (event.pointerType === 'touch') return;
        pointerTargetX = event.clientX;
        pointerTargetY = event.clientY;
        pointerActive = true;
      },
      { passive: true }
    );
    window.addEventListener(
      'pointerleave',
      () => {
        pointerActive = false;
      },
      { passive: true }
    );
    const makeStar = () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: 0.35 + Math.random() * 1.15,
      alpha: 0.2 + Math.random() * 0.62,
      phase: Math.random() * Math.PI * 2,
      speed: 0.035 + Math.random() * 0.13,
      drift: 0.5 + Math.random() * 3.2,
    });
    const resizeStars = () => {
      const oldWidth = width || window.innerWidth,
        oldHeight = height || window.innerHeight;
      width = Math.max(1, window.innerWidth);
      height = Math.max(1, window.innerHeight);
      dpr = Math.min(window.devicePixelRatio || 1, 1.7);
      starCanvas.width = Math.round(width * dpr);
      starCanvas.height = Math.round(height * dpr);
      starCanvas.style.width = width + 'px';
      starCanvas.style.height = height + 'px';
      starContext.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(230, Math.max(65, Math.round((width * height) / 7200)));
      if (!stars.length) for (let i = 0; i < count; i++) stars.push(makeStar());
      else {
        stars.forEach((star) => {
          star.x = (star.x / oldWidth) * width;
          star.y = (star.y / oldHeight) * height;
        });
        while (stars.length < count) stars.push(makeStar());
        stars.length = count;
      }
      paintStars(0, false);
    };
    const paintStars = (time, animate) => {
      starContext.clearRect(0, 0, width, height);
      // Ease the pointer independently from raw input so nearby stars glide instead of snapping.
      if (pointerActive) {
        pointerX += (pointerTargetX - pointerX) * 0.075;
        pointerY += (pointerTargetY - pointerY) * 0.075;
      }
      for (const star of stars) {
        if (animate) {
          star.y -= (star.drift * Math.min(time, 32)) / 1000;
          star.x += Math.sin(time * 0.00012 + star.phase) * 0.08;
          if (star.y < -3) {
            star.y = height + 3;
            star.x = Math.random() * width;
          }
          if (star.x < -3) star.x = width + 3;
          if (star.x > width + 3) star.x = -3;
        }
        const shimmer =
          0.82 + 0.18 * Math.sin(window.performance.now() * 0.00045 * star.speed * 12 + star.phase);
        let drawX = star.x,
          drawY = star.y;
        if (pointerActive) {
          const dx = star.x - pointerX,
            dy = star.y - pointerY;
          const distance = Math.hypot(dx, dy);
          const radius = 205;
          if (distance > 0 && distance < radius) {
            const falloff = 1 - distance / radius;
            const influence = falloff * falloff * 5.5;
            drawX += (dx / distance) * influence;
            drawY += (dy / distance) * influence;
          }
        }
        starContext.beginPath();
        starContext.fillStyle = 'rgba(198, 215, 255, ' + star.alpha * (animate ? shimmer : 1) + ')';
        starContext.arc(drawX, drawY, star.radius, 0, Math.PI * 2);
        starContext.fill();
        if (star.radius > 1.15) {
          starContext.beginPath();
          starContext.fillStyle = 'rgba(116, 151, 255, ' + 0.06 * star.alpha + ')';
          starContext.arc(drawX, drawY, star.radius * 2.8, 0, Math.PI * 2);
          starContext.fill();
        }
      }
    };
    const stopStars = () => {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      lastTime = 0;
    };
    const animateStars = (now) => {
      raf = 0;
      if (document.hidden || motionPreference.matches) {
        paintStars(0, false);
        return;
      }
      const delta = lastTime ? Math.min(now - lastTime, 32) : 16;
      lastTime = now;
      paintStars(delta, true);
      raf = requestAnimationFrame(animateStars);
    };
    const startStars = () => {
      stopStars();
      if (!document.hidden && !motionPreference.matches) raf = requestAnimationFrame(animateStars);
      else paintStars(0, false);
    };
    resizeStars();
    startStars();
    window.addEventListener('resize', resizeStars, { passive: true });
    document.addEventListener('visibilitychange', startStars);
    motionPreference.addEventListener?.('change', startStars);
  }
  // Cursor-following nebula glow, matching the desktop app's soft pointer light.
  const ambientLayers = [...document.querySelectorAll('.ambient')];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia('(pointer: fine)').matches;
  if (ambientLayers.length && !reduceMotion && finePointer) {
    let framePending = false;
    let pointerX = 0;
    let pointerY = 0;
    window.addEventListener(
      'pointermove',
      (event) => {
        const x = Math.max(0, Math.min(window.innerWidth, event.clientX));
        const y = Math.max(0, Math.min(window.innerHeight, event.clientY));
        pointerX = (x / Math.max(window.innerWidth, 1) - 0.5) * 2;
        pointerY = (y / Math.max(window.innerHeight, 1) - 0.5) * 2;
        document.documentElement.style.setProperty('--nv-pointer-x', x + 'px');
        document.documentElement.style.setProperty('--nv-pointer-y', y + 'px');
        document.documentElement.style.setProperty('--nv-pointer-glow', '1');
        if (framePending) return;
        framePending = true;
        window.requestAnimationFrame(() => {
          ambientLayers.forEach((layer, index) => {
            const depth = index === 0 ? 14 : -10;
            layer.style.transform = `translate3d(${pointerX * depth}px, ${pointerY * depth}px, 0)`;
          });
          framePending = false;
        });
      },
      { passive: true }
    );
    window.addEventListener('pointerleave', () => {
      ambientLayers.forEach((layer) => {
        layer.style.transform = '';
      });
      document.documentElement.style.setProperty('--nv-pointer-glow', '0');
    });
  }
});
