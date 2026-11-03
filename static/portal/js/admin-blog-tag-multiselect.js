(function () {
  'use strict';

  function initAdminMultiSelect(root) {
    if (root.dataset.nvEnhanced === 'true') return;

    var select = root.querySelector('select[multiple]');
    if (!select) return;

    root.dataset.nvEnhanced = 'true';

    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'nv-admin-multiselect__trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');

    var triggerText = document.createElement('span');
    triggerText.className = 'nv-admin-multiselect__trigger-text';

    var chevron = document.createElement('span');
    chevron.className = 'nv-admin-multiselect__chevron';
    chevron.setAttribute('aria-hidden', 'true');
    trigger.append(triggerText, chevron);

    var panel = document.createElement('div');
    panel.className = 'nv-admin-multiselect__panel';
    panel.hidden = true;

    var searchWrap = document.createElement('div');
    searchWrap.className = 'nv-admin-multiselect__search-wrap';

    var search = document.createElement('input');
    search.type = 'search';
    search.className = 'nv-admin-multiselect__search';
    search.placeholder = 'Search options…';
    search.setAttribute('aria-label', 'Search options');
    search.autocomplete = 'off';
    searchWrap.append(search);

    var list = document.createElement('div');
    list.className = 'nv-admin-multiselect__options';
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-multiselectable', 'true');

    var empty = document.createElement('p');
    empty.className = 'nv-admin-multiselect__empty';
    empty.textContent = 'No options found';
    empty.hidden = true;

    var footer = document.createElement('div');
    footer.className = 'nv-admin-multiselect__footer';

    var reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'nv-admin-multiselect__footer-action';
    reset.textContent = 'Reset';

    var selectAll = document.createElement('button');
    selectAll.type = 'button';
    selectAll.className =
      'nv-admin-multiselect__footer-action nv-admin-multiselect__footer-action--primary';
    selectAll.textContent = 'Select all';

    footer.append(reset, selectAll);
    panel.append(searchWrap, list, empty, footer);
    root.append(trigger, panel);
    root.classList.add('is-enhanced');

    var rows = [];

    function getOptionLabel(option) {
      var group = option.parentElement;
      var groupLabel = group && group.tagName === 'OPTGROUP' ? group.label.trim() : '';
      var label = option.textContent.trim();
      return groupLabel ? groupLabel + ' — ' + label : label;
    }

    function selectedCount() {
      return rows.reduce(function (count, item) {
        return count + (item.option.selected ? 1 : 0);
      }, 0);
    }

    function refresh() {
      var count = selectedCount();
      triggerText.textContent = count
        ? count + (count === 1 ? ' option selected' : ' options selected')
        : 'Select options';

      rows.forEach(function (item) {
        item.checkbox.checked = item.option.selected;
        item.row.setAttribute('aria-selected', item.option.selected ? 'true' : 'false');
        item.row.setAttribute('aria-checked', item.option.selected ? 'true' : 'false');
      });

      reset.disabled = count === 0;
      selectAll.disabled = rows.length === 0 || count === rows.length;
      trigger.setAttribute(
        'aria-label',
        count ? count + (count === 1 ? ' option selected' : ' options selected') : 'Select options'
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

    function addOptionRow(option, index) {
      var row = document.createElement('div');
      row.className = 'nv-admin-multiselect__option';
      row.dataset.searchText = getOptionLabel(option).toLocaleLowerCase();

      var checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'nv-admin-multiselect__checkbox';
      checkbox.checked = option.selected;
      checkbox.disabled = option.disabled;
      checkbox.value = option.value;
      checkbox.tabIndex = -1;
      checkbox.setAttribute('aria-hidden', 'true');

      var checkmark = document.createElement('span');
      checkmark.className = 'nv-admin-multiselect__checkmark';
      checkmark.setAttribute('aria-hidden', 'true');

      var label = document.createElement('span');
      label.className = 'nv-admin-multiselect__option-label';
      label.textContent = getOptionLabel(option);

      row.append(checkbox, checkmark, label);
      row.setAttribute('role', 'option');
      row.tabIndex = 0;
      row.setAttribute('aria-selected', option.selected ? 'true' : 'false');
      row.dataset.optionIndex = String(index);
      list.append(row);

      var item = { row: row, checkbox: checkbox, option: option };
      rows.push(item);

      checkbox.addEventListener('change', function () {
        option.selected = checkbox.checked;
        notifyChange();
      });

      row.addEventListener('click', function (event) {
        if (event.target === checkbox || option.disabled) return;
        checkbox.checked = !checkbox.checked;
        option.selected = checkbox.checked;
        notifyChange();
      });

      row.addEventListener('keydown', function (event) {
        if (event.key !== ' ' && event.key !== 'Enter') return;
        event.preventDefault();
        if (option.disabled) return;
        checkbox.checked = !checkbox.checked;
        option.selected = checkbox.checked;
        notifyChange();
      });
    }

    function syncOptions() {
      var options = Array.prototype.slice.call(select.options);

      rows = rows.filter(function (item) {
        if (options.indexOf(item.option) !== -1) return true;
        item.row.remove();
        return false;
      });

      options.forEach(function (option, index) {
        var existing = rows.find(function (item) {
          return item.option === option;
        });
        if (!existing) {
          addOptionRow(option, index);
        } else {
          existing.row.dataset.optionIndex = String(index);
          existing.row.dataset.searchText = getOptionLabel(option).toLocaleLowerCase();
          existing.row.querySelector('.nv-admin-multiselect__option-label').textContent =
            getOptionLabel(option);
          existing.checkbox.disabled = option.disabled;
          list.append(existing.row);
        }
      });

      refresh();
      filterOptions();
    }

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

    select.addEventListener('change', function () {
      syncOptions();
    });

    var form = select.closest('form');
    if (form) {
      form.addEventListener('reset', function () {
        window.setTimeout(refresh, 0);
      });
    }

    // Django's related-object popup inserts a new <option> into
    // the native select. Watch that source of truth so the custom menu stays
    // in sync without requiring a page reload.
    if (window.MutationObserver) {
      var optionsObserver = new MutationObserver(function () {
        syncOptions();
      });
      optionsObserver.observe(select, { childList: true, subtree: true });
    }

    syncOptions();
  }

  function initAll() {
    document.querySelectorAll('[data-nv-admin-multiselect]').forEach(initAdminMultiSelect);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
