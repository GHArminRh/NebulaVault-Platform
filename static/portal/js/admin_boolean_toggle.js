(() => {
  'use strict';
  const endpoint = '/admin/quick-toggle/';
  const protectedFields = new Set(['is_staff', 'is_superuser']);
  const actionCellClass = 'nv-record-actions';
  function csrfToken() {
    const cookie = document.cookie.split('; ').find((part) => part.startsWith('csrftoken='));
    const formToken = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return cookie
      ? decodeURIComponent(cookie.split('=').slice(1).join('='))
      : formToken
        ? formToken.value
        : '';
  }
  function objectIdForRow(row) {
    if (!row) return null;
    if (row.dataset.objectPk) return row.dataset.objectPk;
    const action = row.querySelector('input[name="_selected_action"]');
    if (action) return action.value;
    const link = row.querySelector('th a[href$="/change/"],td a[href$="/change/"]');
    const match = link && link.getAttribute('href').match(/\/([^/]+)\/change\/$/);
    return match ? decodeURIComponent(match[1]) : null;
  }
  function appAndModel() {
    const parts = window.location.pathname.split('/').filter(Boolean),
      i = parts.indexOf('admin');
    return i >= 0 && parts[i + 1] && parts[i + 2]
      ? { app_label: parts[i + 1], model_name: parts[i + 2] }
      : null;
  }
  function renderButton(cell, icon, context) {
    if (cell.querySelector('.nv-boolean-toggle')) return;
    const fieldClass = Array.from(cell.classList).find((n) => n.startsWith('field-'));
    if (!fieldClass || protectedFields.has(fieldClass.slice(6))) return;
    const fieldName = fieldClass.slice(6),
      initial = icon.alt === 'True',
      button = document.createElement('button');
    button.type = 'button';
    button.className = 'nv-boolean-toggle' + (initial ? ' is-on' : '');
    button.setAttribute('role', 'switch');
    button.setAttribute('aria-checked', String(initial));
    button.dataset.value = String(initial);
    const track = document.createElement('span');
    track.className = 'nv-switch-track';
    track.setAttribute('aria-hidden', 'true');
    const thumb = document.createElement('span');
    thumb.className = 'nv-switch-thumb';
    track.appendChild(thumb);
    button.appendChild(track);
    function paint(v) {
      button.dataset.value = String(v);
      button.classList.toggle('is-on', v);
      button.setAttribute('aria-checked', String(v));
      button.title = v ? 'Click to disable' : 'Click to enable';
    }
    let pending = false;
    button.addEventListener('click', async () => {
      if (pending) return;
      const previous = button.dataset.value === 'true',
        next = !previous,
        id = objectIdForRow(cell.closest('tr'));
      if (!id) {
        window.alert('Could not identify this record. Refresh the page and try again.');
        return;
      }
      pending = true;
      button.disabled = true;
      paint(next);
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: JSON.stringify({ ...context, object_id: id, field_name: fieldName, value: next }),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || 'Could not save this change.');
        paint(Boolean(data.value));
      } catch (e) {
        paint(previous);
        window.alert(e.message || 'Could not save this change.');
      } finally {
        pending = false;
        button.disabled = false;
      }
    });
    cell.replaceChildren(button);
  }
  function addRecordActions(row, context) {
    if (row.querySelector('.' + actionCellClass)) return;
    const id = objectIdForRow(row);
    if (!id) return;
    const cell = document.createElement('td');
    cell.className = actionCellClass;
    const link = document.createElement('a');
    link.href =
      '/admin/' +
      encodeURIComponent(context.app_label) +
      '/' +
      encodeURIComponent(context.model_name) +
      '/' +
      encodeURIComponent(id) +
      '/delete/';
    link.title = 'Delete this record';
    link.setAttribute('aria-label', 'Delete this record');
    const img = document.createElement('img');
    img.src = '/static/admin/img/icon-deletelink.svg';
    img.alt = '';
    img.className = 'nv-record-actions__delete-icon';
    link.appendChild(img);
    cell.appendChild(link);
    row.appendChild(cell);
  }
  function enhance() {
    const context = appAndModel();
    if (!context) return;
    const table = document.querySelector('#result_list'),
      header = table && table.querySelector('thead tr');
    if (header && !header.querySelector('.' + actionCellClass + '-header')) {
      const th = document.createElement('th');
      th.className = actionCellClass + '-header';
      th.scope = 'col';
      th.textContent = 'Tools';
      header.appendChild(th);
    }
    document.querySelectorAll('#result_list tbody tr').forEach((row) => {
      addRecordActions(row, context);
      row.querySelectorAll("td[class*='field-']").forEach((cell) => {
        const icon = cell.querySelector('img[alt="True"],img[alt="False"]');
        if (icon) renderButton(cell, icon, context);
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', enhance);
  else enhance();
})();
