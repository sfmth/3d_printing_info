/* Progressive enhancement for complete, server-rendered comparison pages. */
(() => {
  'use strict';
  const form = document.getElementById('pair-picker');
  const table = document.getElementById('pair-table');
  const status = document.getElementById('pair-status');
  const differences = document.getElementById('pair-differences');

  function announce(message, error = false) {
    if (!status) return;
    status.textContent = message;
    status.dataset.state = error ? 'error' : 'ready';
  }

  if (form && ['materials', 'printers'].includes(form.dataset.kind)) {
    const first = form.querySelector('select[name="first"]');
    const second = form.querySelector('select[name="second"]');
    if (first && second) {
      const known = new Set([...first.options].map(option => option.value).filter(Boolean));
      const valid = value => known.has(value) && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
      function resetError() {
        first.removeAttribute('aria-invalid');
        second.removeAttribute('aria-invalid');
        announce('Select Compare to open the chosen pair.');
      }
      first.addEventListener('change', resetError);
      second.addEventListener('change', resetError);
      form.addEventListener('submit', event => {
        event.preventDefault();
        if (!valid(first.value) || !valid(second.value)) {
          const invalid = !valid(first.value) ? first : second;
          invalid.setAttribute('aria-invalid', 'true');
          announce('Choose two items from this catalog to compare.', true);
          invalid.focus();
          return;
        }
        if (first.value === second.value) {
          second.setAttribute('aria-invalid', 'true');
          announce('Choose two different items to compare.', true);
          second.focus();
          return;
        }
        const ids = [first.value, second.value].sort();
        const next = new URL(ids.join('-vs-') + '.html', new URL('.', location.href));
        if (next.pathname === location.pathname) {
          announce('This comparison is already open.');
          return;
        }
        location.assign(next.href);
      });
      form.hidden = false;
    }
  }

  if (!table || !differences) return;
  // Market snapshots also carry comparison state, without inventing catalog IDs.
  const rows = [...table.querySelectorAll('tbody tr[data-different]')];
  if (!rows.length) return;
  let differencesOnly = false;

  function renderDifferences() {
    let visible = 0;
    for (const row of rows) {
      row.hidden = differencesOnly && row.dataset.different !== 'true';
      if (!row.hidden) visible++;
    }
    for (const body of table.tBodies) {
      let heading = null;
      let hasVisibleFields = false;
      function finishSection() {
        if (heading) heading.hidden = differencesOnly && !hasVisibleFields;
      }
      for (const row of body.rows) {
        if (row.classList.contains('pair-section')) {
          finishSection();
          heading = row;
          hasVisibleFields = false;
        } else if (row.hasAttribute('data-different') && !row.hidden) {
          hasVisibleFields = true;
        }
      }
      finishSection();
    }
    differences.setAttribute('aria-pressed', String(differencesOnly));
    differences.textContent = differencesOnly ? 'Show all properties' : 'Show differences only';
    announce(differencesOnly
      ? (visible ? 'Showing ' + visible + ' of ' + rows.length + ' properties with different values.' : 'No property values differ. Select Show all properties to read the complete records.')
      : 'Showing all ' + rows.length + ' properties.');
  }

  differences.hidden = false;
  differences.setAttribute('aria-controls', table.id);
  differences.addEventListener('click', () => {
    differencesOnly = !differencesOnly;
    renderDifferences();
  });
  renderDifferences();
})();
