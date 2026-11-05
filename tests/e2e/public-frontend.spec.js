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

test('public pages load their stylesheets without failed CSS responses', async ({ page }) => {
  const failedStylesheets = [];
  page.on('response', (response) => {
    if (response.request().resourceType() === 'stylesheet' && response.status() >= 400) {
      failedStylesheets.push(`${response.status()} ${response.url()}`);
    }
  });

  const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
  expect(response).not.toBeNull();
  expect(response.status()).toBeLessThan(400);
  await expect(page.locator('link[rel="stylesheet"]')).not.toHaveCount(0);
  expect(failedStylesheets).toEqual([]);
});

test('shared foundation bundle preserves global design tokens', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  const foundation = page.locator('link[rel="stylesheet"][href*="portal/css/public-foundation"]');
  await expect(foundation).toHaveCount(1);

  const tokens = await page.locator('html').evaluate((element) => {
    const styles = getComputedStyle(element);
    return {
      background: styles.getPropertyValue('--bg').trim(),
      contentWidth: styles.getPropertyValue('--nv-content-width').trim(),
      glass: styles.getPropertyValue('--nv-glass').trim(),
    };
  });

  expect(tokens).toEqual({
    background: '#050a18',
    contentWidth: '1160px',
    glass: 'rgba(17, 25, 46, 0.72)',
  });
});

test('blog styles are loaded only on pages that render blog components', async ({ page }) => {
  for (const route of ['/', '/blog/']) {
    await page.goto(route, { waitUntil: 'domcontentloaded' });
    await expect(
      page.locator('link[rel="stylesheet"][href*="portal/css/blog"]'),
      `${route} should load the blog stylesheet`
    ).toHaveCount(1);
  }

  for (const route of ['/products/', '/pricing/', '/accounts/login/']) {
    await page.goto(route, { waitUntil: 'domcontentloaded' });
    await expect(
      page.locator('link[rel="stylesheet"][href*="portal/css/blog"]'),
      `${route} should not load the blog stylesheet`
    ).toHaveCount(0);
  }
});

test('homepage declares Persian RTL document metadata', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.locator('html')).toHaveAttribute('lang', 'fa');
});

test('deferred feature modules use Django static asset URLs', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const moduleUrls = await page.locator('body').evaluate((body) => ({
    auth: body.dataset.authUiSrc,
    sections: body.dataset.sectionNavigationSrc,
    effects: body.dataset.visualEffectsSrc,
  }));

  expect(moduleUrls.auth).toMatch(/\/static\/portal\/js\/auth-ui(?:\.[a-f0-9]{12})?\.js$/);
  expect(moduleUrls.sections).toMatch(
    /\/static\/portal\/js\/section-navigation(?:\.[a-f0-9]{12})?\.js$/
  );
  expect(moduleUrls.effects).toMatch(
    /\/static\/portal\/js\/visual-effects(?:\.[a-f0-9]{12})?\.js$/
  );
});

test('catalog and pricing pages expose a semantic section heading', async ({ page }) => {
  for (const [route, expectedHeading] of [
    ['/products/', 'فهرست محصولات'],
    ['/pricing/', 'طرح‌های اشتراک'],
  ]) {
    await page.goto(route, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('h2.nv-visually-hidden')).toHaveText(expectedHeading);
  }
});

test('registration form is visible and usable on narrow mobile screens', async ({ page }) => {
  for (const width of [320, 375, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/accounts/register/', { waitUntil: 'domcontentloaded' });

    const registerFace = page.locator('.nv-auth-register');
    await expect(registerFace).toBeVisible();
    await expect(registerFace.locator('input[name="email"]')).toBeVisible();
    await expect(registerFace.locator('input[name="password1"]')).toBeVisible();
    await expect(registerFace.locator('input[name="password2"]')).toBeVisible();
    await expect(registerFace.locator('button[type="submit"]')).toBeVisible();

    const layout = await registerFace.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      const faceStyle = getComputedStyle(element);
      const cardStyle = getComputedStyle(element.closest('.nv-auth-flip-card'));
      return {
        width: rect.width,
        height: rect.height,
        right: rect.right,
        viewport: window.innerWidth,
        position: faceStyle.position,
        transform: faceStyle.transform,
        backfaceVisibility: faceStyle.backfaceVisibility,
        cardTransform: cardStyle.transform,
      };
    });
    expect(layout.width).toBeGreaterThan(0);
    expect(layout.height).toBeGreaterThan(0);
    expect(layout.right).toBeLessThanOrEqual(layout.viewport + 1);
    expect(layout.position).toBe('relative');
    expect(layout.transform).toBe('none');
    expect(layout.backfaceVisibility).toBe('visible');
    expect(layout.cardTransform).toBe('none');
  }
});

test('mobile navigation opens, closes with Escape, and restores keyboard focus', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 844 });
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  const toggle = page.locator('.menu-toggle');
  const nav = page.locator('.mobile-nav');

  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(nav).toBeHidden();
  await toggle.click();
  await expect(nav).toBeVisible();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(toggle).toHaveAttribute('aria-label', 'بستن منو');

  const menuStyle = await nav.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      position: style.position,
      display: style.display,
      overflowY: style.overflowY,
    };
  });

  expect(menuStyle).toEqual({
    position: 'fixed',
    display: 'grid',
    overflowY: 'auto',
  });

  await page.keyboard.press('Escape');
  await expect(nav).toBeHidden();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(toggle).toHaveAttribute('aria-label', 'بازکردن منو');
  await expect(toggle).toBeFocused();
});

test.describe('public frontend smoke checks', () => {
  for (const route of PUBLIC_ROUTES) {
    test(`${route.name} route renders without a server error`, async ({ page }, testInfo) => {
      const pageErrors = [];
      const failedLocalAssets = [];
      const expectedOrigin = new URL(
        route.path,
        testInfo.project.use.baseURL || 'http://127.0.0.1:8000'
      ).origin;

      page.on('pageerror', (error) => pageErrors.push(error.message));
      page.on('response', (response) => {
        const url = new URL(response.url());
        if (
          url.origin === expectedOrigin &&
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
        await page.evaluate(async () => {
          await document.fonts.ready;
          await new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          );
        });
        await expect(page.locator('body.nv-portal')).toHaveCSS('overflow-x', 'clip');
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
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
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

test('admin image form keeps its normal submit flow when no replacement file is selected', async ({
  page,
}) => {
  await page.setContent(`
    <form id="image-form" method="post">
      <div data-nv-image-uploader data-max-bytes="12582912">
        <div data-dropzone>
          <input type="file" data-nv-image-input>
        </div>
        <div data-selection hidden>
          <img data-preview-image alt="Selected image preview">
          <span data-file-name></span>
          <span data-file-size></span>
        </div>
        <p data-uploader-message role="status"></p>
      </div>
      <button type="submit">Save</button>
    </form>
  `);

  await page.addScriptTag({ path: 'static/portal/js/nebula-image-uploader.js' });
  await page.evaluate(() => {
    const form = document.querySelector('#image-form');
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      form.dataset.normalSubmitReached = 'true';
    });
    form.requestSubmit();
  });

  await expect(page.locator('#image-form')).toHaveAttribute('data-normal-submit-reached', 'true');
  await expect(page.locator('#image-form')).not.toHaveAttribute('aria-busy');
});

test('direct image links become thumbnails and open in an in-page preview', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    const link = document.createElement('a');
    link.href = '/static/portal/img/pwa-icon-192.svg';
    link.textContent = 'Open image';
    link.id = 'image-preview-fixture';
    document.querySelector('main').prepend(link);
  });

  const link = page.locator('#image-preview-fixture');
  const thumbnail = link.locator('img.nv-image-preview-thumb');
  await expect(thumbnail).toBeVisible();
  await expect(thumbnail).toHaveAttribute('alt', 'Open image');
  await expect(link).not.toHaveAttribute('target', '_blank');

  await link.click();
  const dialog = page.locator('dialog.nv-image-preview-dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.locator('img.nv-image-preview-full')).toHaveAttribute(
    'src',
    /pwa-icon-192\.svg$/
  );

  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(link).toBeFocused();
});
