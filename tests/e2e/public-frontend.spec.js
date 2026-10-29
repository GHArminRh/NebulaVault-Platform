import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const MAIN_DOMAIN = 'https://mydigigi.ir';
const PUBLIC_ROUTES = [
  { name: 'home', path: '/' },
  { name: 'products', path: '/products/' },
  { name: 'pricing', path: '/pricing/' },
  { name: 'login', path: '/accounts/login/' },
  { name: 'registration', path: '/accounts/register/' },
  { name: 'blog', path: '/blog/' },
  { name: 'cart', path: '/cart/' },
  { name: 'dashboard entry', path: '/dashboard/' },
  { name: 'orders entry', path: '/orders/' },
  { name: 'subscriptions entry', path: '/subscriptions/' },
];
const ACCESSIBILITY_ROUTES = new Set([
  '/',
  '/products/',
  '/pricing/',
  '/accounts/login/',
  '/accounts/register/',
  '/blog/',
]);
const VIEWPORT_WIDTHS = [320, 375, 768, 1280];
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'https://nebula-vault-oesn.onrender.com';

async function settleLayout(page) {
  await page.evaluate(
    () =>
      new Promise((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(resolve));
      })
  );
}

async function assertNoHorizontalOverflow(page, route, width) {
  await page.setViewportSize({ width, height: 900 });
  await settleLayout(page);
  const dimensions = await page.evaluate(() => {
    const viewport = window.innerWidth;
    const overflowingElements = Array.from(document.querySelectorAll('*'))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          id: element.id,
          className: typeof element.className === 'string' ? element.className : '',
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
          position: getComputedStyle(element).position,
        };
      })
      .filter((element) => element.left < -1 || element.right > viewport + 1)
      .slice(0, 12);
    return {
      viewport,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
      overflowingElements,
    };
  });

  expect(
    Math.max(dimensions.document, dimensions.body),
    `${route} overflows horizontally at ${width}px: ${JSON.stringify(dimensions)}`
  ).toBeLessThanOrEqual(dimensions.viewport + 1);
}

function attachBrowserDiagnostics(page, routePath) {
  const pageErrors = [];
  const failedLocalAssets = [];
  const baseOrigin = new URL(BASE_URL).origin;
  page.on('pageerror', (error) => {
    // Render's test hostname is not registered as a production Turnstile domain.
    // Ignore only this exact provider hostname error on the two auth routes;
    // any other uncaught browser error remains a failure.
    const isExpectedTurnstileHostnameError =
      /^\[Cloudflare Turnstile\] Error: 110200\.?$/.test(error.message) &&
      ['/accounts/login/', '/accounts/register/'].includes(routePath) &&
      baseOrigin.includes('.onrender.com');
    if (!isExpectedTurnstileHostnameError) pageErrors.push(error.message);
  });
  page.on('response', (response) => {
    const url = new URL(response.url());
    if (
      url.origin === baseOrigin &&
      response.status() >= 400 &&
      /\.(css|js)(?:$|\?)/i.test(url.pathname + url.search)
    ) {
      failedLocalAssets.push(`${response.status()} ${url.pathname}`);
    }
  });
  return { pageErrors, failedLocalAssets };
}

test('deployed CSS contains the viewport overflow fix', async ({ page }) => {
  await expect
    .poll(
      async () => {
        try {
          const response = await page.goto(BASE_URL, {
            waitUntil: 'domcontentloaded',
            timeout: 15_000,
          });
          if (!response || response.status() >= 400) return 'unavailable';
          return await page.evaluate(() => {
            const leftGlow = document.querySelector('.ambient-one');
            const rightGlow = document.querySelector('.ambient-two');
            if (!leftGlow || !rightGlow) return 'missing';
            return `${getComputedStyle(leftGlow).left};${getComputedStyle(rightGlow).right}`;
          });
        } catch {
          return 'unavailable';
        }
      },
      {
        timeout: 240_000,
        intervals: [5_000, 10_000, 15_000],
        message: 'Wait for Render to publish the bounded ambient decorations',
      }
    )
    .toBe('0px;0px');
}, 250_000);

test.describe('public frontend smoke, responsive, and accessibility checks', () => {
  for (const route of PUBLIC_ROUTES) {
    test(`${route.name} renders, reflows, and uses valid markup`, async ({ page }) => {
      const diagnostics = attachBrowserDiagnostics(page, route.path);
      const response = await page.goto(route.path, { waitUntil: 'domcontentloaded' });
      expect(response, 'The browser should receive an HTTP response').not.toBeNull();
      expect(
        response.status(),
        `${route.path} returned HTTP ${response.status()}`
      ).toBeLessThan(400);
      await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
      await expect(page.locator('html')).toHaveAttribute('lang', 'fa');

      for (const width of VIEWPORT_WIDTHS) {
        await assertNoHorizontalOverflow(page, route.path, width);
      }

      if (ACCESSIBILITY_ROUTES.has(route.path)) {
        await page.setViewportSize({ width: 1280, height: 900 });
        await settleLayout(page);
        const results = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze();
        const blocking = results.violations.filter((violation) =>
          ['critical', 'serious'].includes(violation.impact || '')
        );
        expect(
          blocking.map((violation) => ({
            id: violation.id,
            impact: violation.impact,
            description: violation.description,
            nodes: violation.nodes.map((node) => ({
              target: node.target,
              summary: node.failureSummary,
            })),
          })),
          'Resolve serious and critical accessibility violations'
        ).toEqual([]);
      }

      expect(diagnostics.pageErrors, 'Uncaught browser JavaScript errors').toEqual([]);
      expect(diagnostics.failedLocalAssets, 'Same-origin CSS/JS resources must load').toEqual([]);
    });
  }
});

test('custom-domain homepage loads current styling without horizontal overflow', async ({
  page,
}) => {
  const response = await page.goto(MAIN_DOMAIN, { waitUntil: 'domcontentloaded' });
  expect(response, 'The custom domain should return an HTTP response').not.toBeNull();
  expect(response.status()).toBeLessThan(400);
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.locator('html')).toHaveAttribute('lang', 'fa');

  // This single custom-domain visit verifies the production hostname without
  // sending a burst of repeated requests through Cloudflare's bot challenge.
  for (const width of [320, 1280]) {
    await assertNoHorizontalOverflow(page, '/', width);
  }
});
