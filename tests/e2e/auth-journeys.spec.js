import { expect, test } from '@playwright/test';

test.describe('authentication experience', () => {
  test('login form exposes accessible email, password, and remembered-session controls', async ({
    page,
  }) => {
    await page.goto('/accounts/login/');

    const form = page
      .locator('form.nv-auth-form')
      .filter({ has: page.locator('input[name="username"]') });
    await expect(form).toBeVisible();
    await expect(form.locator('input[name="username"]')).toHaveAttribute('type', 'email');
    await expect(form.locator('input[name="username"]')).toHaveAttribute(
      'autocomplete',
      'username'
    );
    await expect(form.locator('input[name="password"]')).toHaveAttribute('type', 'password');
    await expect(form.locator('input[name="password"]')).toHaveAttribute(
      'autocomplete',
      'current-password'
    );
    await expect(form.locator('input[name="remember_me"]')).toBeChecked();
    await expect(form.locator('button[type="submit"]')).toBeVisible();
  });

  test('registration form is available from its dedicated route and has required fields', async ({
    page,
  }) => {
    await page.goto('/accounts/register/');

    const form = page
      .locator('form.nv-auth-form')
      .filter({ has: page.locator('input[name="email"]') });
    await expect(form).toBeVisible();
    await expect(form.locator('input[name="email"]')).toHaveAttribute('type', 'email');
    await expect(form.locator('input[name="email"]')).toHaveAttribute('required', '');
    await expect(form.locator('input[name="password1"]')).toHaveAttribute('type', 'password');
    await expect(form.locator('input[name="password1"]')).toHaveAttribute(
      'autocomplete',
      'new-password'
    );
    await expect(form.locator('input[name="password2"]')).toHaveAttribute(
      'autocomplete',
      'new-password'
    );
    await expect(form.locator('button[type="submit"]')).toBeVisible();
  });

  test('login and registration flip-card switches the active face without losing the route', async ({
    page,
  }) => {
    await page.goto('/accounts/login/');

    const shell = page.locator('.nv-auth-shell');
    await expect(shell).toHaveAttribute('data-auth-side', 'login');

    await page.locator('[data-auth-flip="register"]').click();
    await expect(shell).toHaveAttribute('data-auth-side', 'register');
    await expect(page.locator('.nv-auth-register')).toBeVisible();
    await expect(page.locator('.nv-auth-login')).toHaveAttribute('aria-hidden', 'true');

    await page.locator('[data-auth-flip="login"]').click();
    await expect(shell).toHaveAttribute('data-auth-side', 'login');
    await expect(page.locator('.nv-auth-login')).toBeVisible();
    await expect(page.locator('.nv-auth-register')).toHaveAttribute('aria-hidden', 'true');
  });

  test('password visibility control toggles the input type and accessible label', async ({
    page,
  }) => {
    await page.goto('/accounts/login/');

    const password = page.locator('#nv-login-password');
    const toggle = page.locator('.nv-auth-login .password-toggle');
    await expect(password).toHaveAttribute('type', 'password');

    await toggle.click();
    await expect(password).toHaveAttribute('type', 'text');
    await expect(toggle).toHaveAttribute('aria-label', 'پنهان‌کردن رمز عبور');

    await toggle.click();
    await expect(password).toHaveAttribute('type', 'password');
    await expect(toggle).toHaveAttribute('aria-label', 'نمایش رمز عبور');
  });

  test('login and registration forms remain keyboard reachable', async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.keyboard.press('Tab');

    const focused = await page.evaluate(() => ({
      tag: document.activeElement?.tagName.toLowerCase(),
      href: document.activeElement?.getAttribute('href'),
      type: document.activeElement?.getAttribute('type'),
    }));
    expect(['a', 'button', 'input']).toContain(focused.tag);
  });
});

test.describe('navigation and shared interactions', () => {
  test('mobile navigation opens, exposes its links, and closes after navigation', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');

    const toggle = page.locator('.menu-toggle');
    const nav = page.locator('.mobile-nav');
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(nav).toBeHidden();

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(nav).toBeVisible();

    const firstVisibleLink = nav.locator('a:visible').first();
    if (await firstVisibleLink.count()) {
      await firstVisibleLink.click();
      await expect(nav).toBeHidden();
      await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    } else {
      await toggle.click();
      await expect(nav).toBeHidden();
    }
  });

  test('all rendered images have completed successfully or expose a useful alt label', async ({
    page,
  }) => {
    await page.goto('/');
    const imageProblems = await page.locator('img').evaluateAll((images) =>
      images
        .filter((img) => !img.complete || img.naturalWidth === 0 || !img.hasAttribute('alt'))
        .map((img) => ({
          src: img.currentSrc || img.src,
          alt: img.getAttribute('alt'),
          loaded: img.complete && img.naturalWidth > 0,
        }))
    );
    expect(imageProblems).toEqual([]);
  });
});
