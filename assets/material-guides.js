/* Progressive enhancement: every material link is already present in the HTML. */
(() => {
  const input = document.getElementById('material-search');
  if (!input) return;
  const panel = document.querySelector('.material-search');
  const groups = [...document.querySelectorAll('[data-family-group]')];
  const cards = [...document.querySelectorAll('[data-material]')];
  const buttons = [...document.querySelectorAll('[data-family]')];
  const status = document.getElementById('material-results');
  const normalize = value => value.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, ' ').trim();
  const initial = new URLSearchParams(location.search).get('family');
  let family = groups.some(g => g.dataset.familyGroup === initial) ? initial : '';
  panel.hidden = false;
  function render() {
    const words = normalize(input.value).split(' ').filter(Boolean);
    let count = 0;
    for (const group of groups) {
      let matches = 0;
      for (const card of group.querySelectorAll('[data-material]')) {
        const text = normalize(card.dataset.search);
        const visible = (!family || group.dataset.familyGroup === family) && words.every(w => text.includes(w));
        card.hidden = !visible;
        if (visible) matches++;
      }
      group.hidden = !matches;
      group.open = Boolean(matches && (family || words.length));
      count += matches;
    }
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.family === family)));
    status.textContent = `${count} of ${cards.length} materials${family ? ` · ${family}` : ''}`;
    document.getElementById('material-no-results').hidden = count > 0;
  }
  input.addEventListener('input', render);
  buttons.forEach(button => button.addEventListener('click', () => { family = button.dataset.family; render(); }));
  document.getElementById('clear-material-search').addEventListener('click', () => { input.value = ''; family = ''; render(); input.focus(); });
  input.addEventListener('keydown', event => { if (event.key === 'Escape') { input.value = ''; family = ''; render(); } });
  render();
})();
