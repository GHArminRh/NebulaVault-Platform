// Scroll-aware section navigation for the home page and account dashboard.
const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.mobile-nav');
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
          return document.querySelector(decodeURIComponent(new URL(link.href, location.href).hash));
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
    if (window.scrollY < 8 && fallbackId) current = document.getElementById(fallbackId) || current;
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
