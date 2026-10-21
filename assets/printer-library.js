/* Every model is already in the document. Filtering is an optional enhancement. */
(() => {
  const library = document.querySelector('.printer-library');
  const panel = document.getElementById('printer-search-panel');
  const input = document.getElementById('printer-search');
  if (!library || !panel || !input) return;

  const groups = [...library.querySelectorAll('[data-printer-family]')];
  const cards = [...library.querySelectorAll('[data-printer-card]')];
  const buttons = [...library.querySelectorAll('[data-printer-filter]')];
  const status = document.getElementById('printer-results');
  const empty = document.getElementById('printer-no-results');
  const featured = document.getElementById('printer-starting-points');
  const normalize = value => value.toLowerCase().normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  const params = new URLSearchParams(location.search);
  const initialFamily = params.get('family');
  let family = groups.some(group => group.dataset.printerFamily === initialFamily) ? initialFamily : '';
  input.value = params.get('q') || '';
  const searchText = new Map(cards.map(card => [card, normalize(card.dataset.search)]));

  function render() {
    const words = normalize(input.value).split(' ').filter(Boolean);
    let count = 0;
    for (const group of groups) {
      let matches = 0;
      for (const card of group.querySelectorAll('[data-printer-card]')) {
        const visible = (!family || group.dataset.printerFamily === family)
          && words.every(word => searchText.get(card).includes(word));
        card.hidden = !visible;
        if (visible) matches++;
      }
      group.hidden = matches === 0;
      if (matches && (family || words.length)) group.open = true;
      group.querySelector('[data-family-count]').textContent = `${matches} ${matches === 1 ? 'guide' : 'guides'}`;
      count += matches;
    }
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.printerFilter === family)));
    const label = buttons.find(button => button.dataset.printerFilter === family)?.textContent;
    status.textContent = `${count} of ${cards.length} printers${family ? ` · ${label}` : ''}`;
    empty.hidden = count > 0;
    if (featured) featured.hidden = Boolean(family || words.length);
  }

  function clear() {
    input.value = '';
    family = '';
    groups.forEach(group => { group.open = true; });
    render();
    input.focus();
  }

  input.addEventListener('input', render);
  input.addEventListener('keydown', event => {
    if (event.key === 'Escape') clear();
  });
  buttons.forEach(button => button.addEventListener('click', () => {
    family = button.dataset.printerFilter;
    render();
  }));
  document.getElementById('clear-printer-search').addEventListener('click', clear);
  library.querySelectorAll('[data-clear-printer-search]').forEach(button => button.addEventListener('click', clear));
  render();
  panel.hidden = false;
})();
