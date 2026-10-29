document.addEventListener('DOMContentLoaded', () => {
  // Slim top-edge progress indicator for document loads, navigations and form submissions.
  const progress = document.querySelector('.nv-page-progress');
  if (progress) {
    let progressValue = 0;
    let progressTimer = null;
    const setProgress = (value, ceiling = 94) => {
      progressValue = Math.max(progressValue, Math.min(ceiling, value));
      progress.style.setProperty('--nv-progress', progressValue + '%');
      progress.setAttribute('aria-valuenow', String(Math.round(progressValue)));
    };
    const startProgress = () => {
      progress.classList.add('is-loading');
      progress.classList.remove('is-complete');
      progressValue = 0;
      setProgress(8);
      window.clearInterval(progressTimer);
      progressTimer = window.setInterval(
        () => setProgress(progressValue + Math.max(1, (88 - progressValue) * 0.075)),
        120
      );
    };
    const completeProgress = () => {
      window.clearInterval(progressTimer);
      setProgress(100, 100);
      progress.classList.add('is-complete');
      window.setTimeout(() => {
        progress.classList.remove('is-loading', 'is-complete');
        progress.style.setProperty('--nv-progress', '0%');
        progress.setAttribute('aria-valuenow', '0');
        progressValue = 0;
      }, 320);
    };
    if (document.readyState === 'complete') completeProgress();
    else {
      startProgress();
      window.addEventListener('load', completeProgress, { once: true });
    }
    document.addEventListener(
      'click',
      (event) => {
        const link = event.target.closest('a[href]');
        if (
          !link ||
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey ||
          link.target === '_blank' ||
          link.hasAttribute('download')
        )
          return;
        const destination = new URL(link.href, window.location.href);
        if (
          destination.origin !== window.location.origin ||
          (destination.pathname === location.pathname &&
            destination.search === location.search &&
            destination.hash)
        )
          return;
        startProgress();
      },
      true
    );
    document.addEventListener(
      'submit',
      (event) => {
        const form = event.target;
        if (form instanceof HTMLFormElement && form.method.toLowerCase() !== 'dialog')
          startProgress();
      },
      true
    );
    window.addEventListener('pageshow', completeProgress);
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
