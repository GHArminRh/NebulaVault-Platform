(() => {
  const IMAGE_EXTENSION = /\.(?:avif|bmp|gif|jpe?g|png|svg|webp)(?:$|[?#])/i;
  const LINK_SELECTOR = 'a[href]:not([data-nv-image-preview])';
  let dialog;
  let dialogImage;
  let closeButton;
  let lastFocusedElement;

  function isDirectImageUrl(value) {
    if (!value || value.startsWith('javascript:')) return false;
    try {
      const url = new URL(value, window.location.href);
      return (
        ['http:', 'https:', 'blob:'].includes(url.protocol) && IMAGE_EXTENSION.test(url.pathname)
      );
    } catch {
      return false;
    }
  }

  function createDialog() {
    if (dialog) return;

    dialog = document.createElement('dialog');
    dialog.className = 'nv-image-preview-dialog';
    dialog.setAttribute('aria-label', 'پیش‌نمایش تصویر');

    const frame = document.createElement('div');
    frame.className = 'nv-image-preview-frame';

    closeButton = document.createElement('button');
    closeButton.className = 'nv-image-preview-close';
    closeButton.type = 'button';
    closeButton.setAttribute('aria-label', 'بستن پیش‌نمایش تصویر');
    closeButton.textContent = '×';

    dialogImage = document.createElement('img');
    dialogImage.className = 'nv-image-preview-full';
    dialogImage.alt = '';
    dialogImage.draggable = false;

    frame.append(closeButton, dialogImage);
    dialog.append(frame);
    document.body.append(dialog);

    closeButton.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener('close', () => {
      dialogImage.removeAttribute('src');
      document.body.classList.remove('nv-image-preview-open');
      if (lastFocusedElement?.isConnected) lastFocusedElement.focus();
    });
  }

  function openPreview(url, alt, trigger) {
    createDialog();
    lastFocusedElement = trigger;
    dialogImage.alt = alt || 'پیش‌نمایش تصویر';
    dialogImage.src = url;
    document.body.classList.add('nv-image-preview-open');
    if (!dialog.open) dialog.showModal();
    closeButton.focus();
  }

  function enhanceLink(link) {
    if (link.dataset.nvImagePreview === 'true') return;

    const href = link.getAttribute('href');
    if (!isDirectImageUrl(href)) return;

    link.dataset.nvImagePreview = 'true';
    link.classList.add('nv-image-preview-link');

    const fileName = (() => {
      try {
        return decodeURIComponent(new URL(href, window.location.href).pathname.split('/').pop());
      } catch {
        return 'تصویر';
      }
    })();
    const alt =
      link.getAttribute('aria-label') ||
      link.getAttribute('title') ||
      link.textContent.trim() ||
      fileName;

    const thumbnail = document.createElement('img');
    thumbnail.className = 'nv-image-preview-thumb';
    thumbnail.src = href;
    thumbnail.alt = alt;
    thumbnail.loading = 'lazy';
    thumbnail.decoding = 'async';

    thumbnail.addEventListener(
      'error',
      () => {
        thumbnail.classList.add('is-unavailable');
        thumbnail.alt = 'تصویر در دسترس نیست';
      },
      { once: true }
    );

    link.replaceChildren(thumbnail);
    link.setAttribute('aria-label', 'نمایش تصویر: ' + alt);
    link.removeAttribute('target');
    link.removeAttribute('download');
    link.addEventListener('click', (event) => {
      event.preventDefault();
      openPreview(href, alt, link);
    });
  }

  function scan(root = document) {
    if (root instanceof Element && root.matches(LINK_SELECTOR)) enhanceLink(root);
    root.querySelectorAll?.(LINK_SELECTOR).forEach(enhanceLink);
  }

  function initialize() {
    scan();
    const observer = new MutationObserver((records) => {
      records.forEach((record) => {
        record.addedNodes.forEach((node) => {
          if (node instanceof Element) scan(node);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})();
