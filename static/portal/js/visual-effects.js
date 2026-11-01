// Non-critical canvas and pointer effects, loaded after the initial page render.
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
