/* Enhance independent hub pickers; ordinary comparison links need no script. */
(() => {
  'use strict';
  for (const form of document.querySelectorAll('form[data-hub-picker]')) {
    const kind = form.dataset.kind;
    const first = form.querySelector('select[name="first"]');
    const second = form.querySelector('select[name="second"]');
    const status = form.querySelector('[role="status"]');
    if (!['materials', 'printers'].includes(kind) || !first || !second || !status
        || form.dataset.pairBase !== kind + '/') continue;
    const known = new Set([...first.options].map(option => option.value));
    const valid = value => known.has(value) && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
    const announce = (message, error = false) => {
      status.textContent = message;
      status.dataset.state = error ? 'error' : 'ready';
    };
    const reset = () => {
      first.removeAttribute('aria-invalid');
      second.removeAttribute('aria-invalid');
      announce('Choose Compare to open this pair.');
    };
    first.setAttribute('aria-describedby', status.id);
    second.setAttribute('aria-describedby', status.id);
    first.addEventListener('change', reset);
    second.addEventListener('change', reset);
    form.addEventListener('submit', event => {
      event.preventDefault();
      reset();
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
      const pair = [first.value, second.value].sort().join('-vs-') + '.html';
      const directory = new URL(form.dataset.pairBase, new URL('.', location.href));
      location.assign(new URL(pair, directory).href);
    });
    form.hidden = false;
  }
})();
