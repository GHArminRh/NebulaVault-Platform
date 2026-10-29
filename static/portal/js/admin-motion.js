(() => {
  'use strict';
  const initialize = () => {
    if (document.body.classList.contains('login')) return;
    const progress = document.createElement('div');
    progress.className = 'nv-admin-page-progress';
    progress.setAttribute('role', 'progressbar');
    progress.setAttribute('aria-label', 'Page loading');
    progress.setAttribute('aria-valuemin', '0');
    progress.setAttribute('aria-valuemax', '100');
    progress.setAttribute('aria-valuenow', '0');
    const track = document.createElement('span');
    track.className = 'nv-admin-page-progress__track';
    const tip = document.createElement('span');
    tip.className = 'nv-admin-page-progress__tip';
    progress.append(track, tip);
    document.body.appendChild(progress);

    const target = 90;
    const frameMs = 1000 / 60;
    let value = 0, frame = 0, lastTime = 0, finishTimer = 0, resetTimer = 0;
    let running = false, finished = false;
    const setValue = next => {
      value = Math.max(value, Math.min(100, next));
      progress.style.setProperty('--nv-admin-progress', value + '%');
      progress.style.setProperty('--nv-admin-progress-ratio', String(value / 100));
      progress.setAttribute('aria-valuenow', String(Math.round(value)));
    };
    const stopFrame = () => {
      if (frame) window.cancelAnimationFrame(frame);
      frame = 0;
      lastTime = 0;
    };
    const advance = timestamp => {
      if (!running || finished) { frame = 0; return; }
      const elapsed = lastTime ? Math.min(timestamp - lastTime, 100) : frameMs;
      lastTime = timestamp;
      const remaining = target - value;
      if (remaining <= 0.05) { setValue(target); frame = 0; return; }
      const ratio = 1 - Math.pow(1 - 0.012, elapsed / frameMs);
      setValue(Math.min(target, value + remaining * ratio));
      frame = value < target ? window.requestAnimationFrame(advance) : 0;
    };
    const start = () => {
      window.clearTimeout(finishTimer);
      window.clearTimeout(resetTimer);
      stopFrame();
      value = 0; running = true; finished = false;
      progress.classList.remove('is-complete');
      progress.classList.add('is-loading');
      setValue(4);
      frame = window.requestAnimationFrame(advance);
    };
    const complete = () => {
      if (finished) return;
      running = false; finished = true; stopFrame(); setValue(100);
      progress.classList.add('is-complete');
      finishTimer = window.setTimeout(() => {
        progress.classList.remove('is-loading');
        resetTimer = window.setTimeout(() => {
          progress.classList.remove('is-complete');
          value = 0; setValue(0); finished = false;
        }, 260);
      }, 260);
    };
    if (document.readyState !== 'complete') {
      start();
      window.addEventListener('load', complete, { once: true });
    }
    document.addEventListener('click', event => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = event.target.closest('a[href]');
      if (!link || link.hasAttribute('download') || (link.target && link.target !== '_self') || link.dataset.noPageProgress !== undefined) return;
      let destination;
      try { destination = new URL(link.href, window.location.href); } catch { return; }
      if (destination.origin !== window.location.origin) return;
      if (destination.pathname === location.pathname && destination.search === location.search && destination.hash) return;
      start();
    }, true);
    document.addEventListener('submit', event => {
      if (event.defaultPrevented || !(event.target instanceof HTMLFormElement)) return;
      const form = event.target;
      if ((form.target && form.target !== '_self') || form.dataset.noPageProgress !== undefined) return;
      start();
    }, true);
    window.addEventListener('pageshow', event => {
      if (!event.persisted) return;
      window.clearTimeout(finishTimer); window.clearTimeout(resetTimer); stopFrame();
      running = false; finished = false; value = 0;
      progress.classList.remove('is-loading', 'is-complete'); setValue(0);
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
})();
