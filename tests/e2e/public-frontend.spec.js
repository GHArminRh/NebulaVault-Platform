import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

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

test('deployed frontend styles are updated before regression checks', async ({ page }) => {
  await expect
    .poll(
      async () => {
        try {
          const response = await page.goto('/', {
            waitUntil: 'domcontentloaded',
            timeout: 15_000,
          });
          if (!response || response.status() >= 500) return 'unavailable';
          return await page.evaluate(() => getComputedStyle(document.documentElement).overflowX);
        } catch {
          return 'unavailable';
        }
      },
      {
        timeout: 240_000,
        intervals: [5_000, 10_000, 15_000],
        message: 'Wait for Render to publish the new frontend CSS',
      }
    )
    .toBe('clip');
}, 250_000);

test.describe('public frontend smoke checks', () => {
  for (const route of PUBLIC_ROUTES) {
    test(`${route.name} route renders without a server error`, async ({ page }) => {
      const pageErrors = [];
      const failedLocalAssets = [];
      const baseURL = new URL(process.env.PLAYWRIGHT_BASE_URL || 'https://mydigigi.ir');

      page.on('pageerror', (error) => pageErrors.push(error.message));
      page.on('response', (response) => {
        const url = new URL(response.url());
        if (
          url.origin === baseURL.origin &&
          response.status() >= 400 &&
          /\.(css|js)(?:$|\?)/i.test(url.pathname + url.search)
        ) {
          failedLocalAssets.push(`${response.status()} ${url.pathname}`);
        }
      });

      const response = await page.goto(route.path, { waitUntil: 'domcontentloaded' });
      expect(response, 'The browser should receive an HTTP response').not.toBeNull();
      expect(response.status(), `${route.path} returned HTTP ${response.status()}`).toBeLessThan(
        400
      );
      await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
      await expect(page.locator('html')).toHaveAttribute('lang', 'fa');

      expect(pageErrors, 'Uncaught browser JavaScript errors').toEqual([]);
      expect(failedLocalAssets, 'Same-origin CSS/JS resources must load').toEqual([]);
    });
  }
});

test.describe('responsive layout', () => {
  const responsiveRoutes = [
    '/',
    '/products/',
    '/pricing/',
    '/accounts/login/',
    '/accounts/register/',
    '/blog/',
    '/cart/',
  ];

  for (const width of [320, 375, 768, 1280]) {
    test(`public pages have no horizontal overflow at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });

      for (const route of responsiveRoutes) {
        await page.goto(route, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
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
            .slice(0, 20);
          return {
            viewport,
            document: document.documentElement.scrollWidth,
            body: document.body.scrollWidth,
            overflowingElements,
          };
        });

        expect(
          Math.max(dimensions.document, dimensions.body),
          `${route} overflows horizontally: ${JSON.stringify(dimensions)}`
        ).toBeLessThanOrEqual(dimensions.viewport + 1);
      }
    });
  }
});

test.describe('accessibility', () => {
  for (const route of [
    { name: 'home', path: '/' },
    { name: 'products', path: '/products/' },
    { name: 'pricing', path: '/pricing/' },
    { name: 'login', path: '/accounts/login/' },
    { name: 'registration', path: '/accounts/register/' },
    { name: 'blog', path: '/blog/' },
  ]) {
    test(`${route.name} has no serious or critical axe violations`, async ({ page }) => {
      await page.goto(route.path, { waitUntil: 'domcontentloaded' });

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
    });
  }
});
