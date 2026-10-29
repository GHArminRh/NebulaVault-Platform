import js from '@eslint/js';

const browserAndWorkerGlobals = [
  'window',
  'document',
  'navigator',
  'location',
  'history',
  'Node',
  'Element',
  'HTMLElement',
  'HTMLInputElement',
  'HTMLFormElement',
  'MutationObserver',
  'IntersectionObserver',
  'ResizeObserver',
  'URL',
  'URLSearchParams',
  'Image',
  'requestAnimationFrame',
  'cancelAnimationFrame',
  'confirm',
  'alert',
  'fetch',
  'Response',
  'Request',
  'Headers',
  'caches',
  'self',
  'clients',
  'console',
  'matchMedia',
  'getComputedStyle',
  'localStorage',
  'sessionStorage',
  'setInterval',
  'clearInterval',
  'performance',
].reduce((globals, name) => {
  globals[name] = 'readonly';
  return globals;
}, {});

export default [
  {
    ignores: ['node_modules/**', 'playwright-report/**', 'test-results/**'],
  },
  {
    files: [
      'static/portal/js/**/*.js',
      'static/portal/service-worker.js',
      'accounts/static/**/*.js',
    ],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'script',
      globals: browserAndWorkerGlobals,
    },
    rules: {
      ...js.configs.recommended.rules,
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
];
