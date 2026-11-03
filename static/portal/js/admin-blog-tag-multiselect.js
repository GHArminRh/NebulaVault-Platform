(function () {
  'use strict';

  function initTagMultiSelect(root) {
    if (root.dataset.nvEnhanced === 'true') return;

    var select = root.querySelector('select[multiple]');
    if (!select) return;

    root.dataset.nvEnhanced = 'true';

    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'nv-blog-tag-select__trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');

    var triggerText = document.createElement('span');
    triggerText.className = 'nv-blog-tag-select__trigger-text';

    var chevron = document.createElement('span');
    chevron.className = 'nv-blog-tag-select__chevron';
    chevron.setAttribute('aria-hidden', 'true');
    trigger.append(triggerText, chevron);

    var panel = document.createElement('div');
    panel.className = 'nv-blog-tag-select__panel';
    panel.hidden = true;

    var searchWrap = document.createElement('div');
    searchWrap.className = 'nv-blog-tag-select__search-wrap';

    var search = document.createElement('input');
    search.type = 'search';
    search.className = 'nv-blog-tag-select__search';
    search.placeholder = 'Search tags…';
    search.setAttribute('aria-label', 'Search tags');
    search.autocomplete = 'off';
    searchWrap.append(search);

    var list = document.createElement('div');
    list.className = 'nv-blog-tag-select__options';
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-multiselectable', 'true');

    var empty = document.createElement('p');
    empty.className = 'nv-blog-tag-select__empty';
    empty.textContent = 'No tags found';
    empty.hidden = true;

    var footer = document.createElement('div');
    footer.className = 'nv-blog-tag-select__footer';

    var reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'nv-blog-tag-select__footer-action';
    reset.textContent = 'Reset';

    var selectAll = document.createElement('button');
    selectAll.type = 'button';
    selectAll.className =
      'nv-blog-tag-select__footer-action nv-blog-tag-select__footer-action--primary';
    selectAll.textContent = 'Select all';

    footer.append(reset, selectAll);
    panel.append(searchWrap, list, empty, footer);
    root.append(trigger, panel);
    root.classList.add('is-enhanced');

    var rows = [];

    Array.prototype.forEach.call(select.options, function (option, index) {
      var row = document.createElement('div');
      row.className = 'nv-blog-tag-select__option';
      row.dataset.searchText = option.textContent.trim().toLocaleLowerCase();

      var checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'nv-blog-tag-select__checkbox';
      checkbox.checked = option.selected;
      checkbox.disabled = option.disabled;
      checkbox.value = option.value;
      checkbox.tabIndex = -1;
      checkbox.setAttribute('aria-hidden', 'true');

      var checkmark = document.createElement('span');
      checkmark.className = 'nv-blog-tag-select__checkmark';
      checkmark.setAttribute('aria-hidden', 'true');

      var label = document.createElement('span');
      label.className = 'nv-blog-tag-select__option-label';
      label.textContent = option.textContent.trim();

      row.append(checkbox, checkmark, label);
      row.setAttribute('role', 'option');
      row.tabIndex = 0;
      row.setAttribute('aria-selected', option.selected ? 'true' : 'false');
      row.dataset.optionIndex = String(index);
      list.append(row);
      rows.push({ row: row, checkbox: checkbox, option: option });
    });

    function selectedCount() {
      return rows.reduce(function (count, item) {
        return count + (item.option.selected ? 1 : 0);
      }, 0);
    }

    function refresh() {
      var count = selectedCount();
      triggerText.textContent = count
        ? count + (count === 1 ? ' tag selected' : ' tags selected')
        : 'Select tags';

      rows.forEach(function (item) {
        item.checkbox.checked = item.option.selected;
        item.row.setAttribute('aria-selected', item.option.selected ? 'true' : 'false');
        item.row.setAttribute('aria-checked', item.option.selected ? 'true' : 'false');
      });

      reset.disabled = count === 0;
      selectAll.disabled = rows.length === 0 || count === rows.length;
      trigger.setAttribute(
        'aria-label',
        count ? count + (count === 1 ? ' tag selected' : ' tags selected') : 'Select blog tags'
      );
    }

    function filterOptions() {
      var query = search.value.trim().toLocaleLowerCase();
      var visible = 0;

      rows.forEach(function (item) {
        var matches = !query || item.row.dataset.searchText.indexOf(query) !== -1;
        item.row.hidden = !matches;
        if (matches) visible += 1;
      });

      empty.hidden = visible !== 0;
    }

    function setOpen(open) {
      panel.hidden = !open;
      trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
      root.classList.toggle('is-open', open);
      if (open) {
        search.focus();
        filterOptions();
      } else {
        search.value = '';
        filterOptions();
      }
    }

    function notifyChange() {
      select.dispatchEvent(new window.Event('change', { bubbles: true }));
      refresh();
    }

    rows.forEach(function (item) {
      item.checkbox.addEventListener('change', function () {
        item.option.selected = item.checkbox.checked;
        notifyChange();
      });

      item.row.addEventListener('click', function (event) {
        if (event.target === item.checkbox || item.option.disabled) return;
        item.checkbox.checked = !item.checkbox.checked;
        item.option.selected = item.checkbox.checked;
        notifyChange();
      });

      item.row.addEventListener('keydown', function (event) {
        if (event.key !== ' ' && event.key !== 'Enter') return;
        event.preventDefault();
        if (item.option.disabled) return;
        item.checkbox.checked = !item.checkbox.checked;
        item.option.selected = item.checkbox.checked;
        notifyChange();
      });
    });

    trigger.addEventListener('click', function () {
      setOpen(panel.hidden);
    });

    search.addEventListener('input', filterOptions);

    reset.addEventListener('click', function () {
      rows.forEach(function (item) {
        if (!item.option.disabled) item.option.selected = false;
      });
      notifyChange();
    });

    selectAll.addEventListener('click', function () {
      rows.forEach(function (item) {
        if (!item.option.disabled) item.option.selected = true;
      });
      notifyChange();
    });

    document.addEventListener('click', function (event) {
      if (!root.contains(event.target)) setOpen(false);
    });

    panel.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        setOpen(false);
        trigger.focus();
      }
    });

    select.addEventListener('change', refresh);
    var form = select.closest('form');
    if (form) {
      form.addEventListener('reset', function () {
        window.setTimeout(refresh, 0);
      });
    }

    refresh();
  }

  function initAll() {
    document.querySelectorAll('[data-nv-blog-tag-select]').forEach(initTagMultiSelect);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
