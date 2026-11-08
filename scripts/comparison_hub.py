"""A usable, static entry point into the complete unordered-pair library."""
from html import escape


HUB_REVISION = '2026-11-08'
KINDS = (
    ('materials', 'filaments.html', 'filament', 'Filament', 'material families', ('pla', 'petg')),
    ('printers', 'comparison.html', 'printer', 'Printer', 'printer models', ('bambu-a1', 'bambu-p1s')),
)


def _e(value):
    return escape(str(value), quote=True)


def _catalogs(datasets):
    return {kind: datasets[catalog] if catalog in datasets else datasets[kind]
            for kind, catalog, *_ in KINDS}


def _picker(kind, singular, title, cats, defaults):
    selected = [key for key in defaults if any(cat['id'] == key for cat in cats)]
    selected += [cat['id'] for cat in cats if cat['id'] not in selected]
    if len(selected) < 2:
        return ''
    body = ('<form class="hub-selector" data-hub-picker data-kind="' + kind
            + '" data-pair-base="' + kind + '/" hidden><h3>' + title + ' comparison</h3>'
            + '<p>Choose two ' + ('material families' if kind == 'materials' else 'printer models')
            + ' to open their complete sourced comparison.</p>')
    for index, name in enumerate(('first', 'second')):
        field_id = 'hub-' + kind + '-' + name
        body += ('<div class="hub-field"><label for="' + field_id + '">'
                 + ('First ' if index == 0 else 'Second ') + singular
                 + '</label><select id="' + field_id + '" name="' + name + '" required>')
        body += ''.join('<option value="' + _e(cat['id']) + '"'
                        + (' selected' if cat['id'] == selected[index] else '')
                        + '>' + _e(cat['n']) + '</option>' for cat in cats)
        body += '</select></div>'
    return (body + '<button class="hub-submit" type="submit">Compare ' + singular + 's</button>'
            + '<p class="hub-status hub-selector-status" id="hub-' + kind
            + '-status" role="status" aria-live="polite">Choose Compare to open this pair.</p></form>')


def _featured(datasets, catalogs):
    # Local imports avoid the discovery module's dependency on pair_path creating
    # an import cycle. Tiny test catalogs show only applicable editorial pairs.
    from comparison_discovery import COMPARISONS, validate_discovery
    available = {kind: {cat['id'] for cat in data['cats']} for kind, data in catalogs.items()}
    selection = tuple(item for item in COMPARISONS if item['featured']
                      and {item['left'], item['right']} <= available[item['kind']])
    if not selection:
        return ''
    body = ('<section class="hub-featured" aria-labelledby="hub-featured-heading">'
            + '<h2 id="hub-featured-heading">Start with a comparison</h2>'
            + '<p>Selected starting points from the catalog. These are editorial choices, '
            + 'not measured popularity rankings.</p><div class="hub-featured-grid">')
    normalized = {catalog: catalogs[kind] for kind, catalog, *_ in KINDS}
    for item in validate_discovery(normalized, selection):
        body += ('<a class="hub-featured-card" data-hub-featured-pair="' + _e(item['path'])
                 + '" href="' + _e(item['path'].removeprefix('compare/')) + '">'
                 + '<span class="hub-card-kicker">'
                 + ('Filament' if item['kind'] == 'materials' else 'Printer') + ' comparison</span>'
                 + '<h3>' + _e(item['title']) + '</h3><p>' + _e(item['description'])
                 + '</p><span class="hub-card-action">View side by side →</span></a>')
    return body + '</div></section>'


def render_hub(datasets):
    """Render ordinary browse/featured links and optional independent pickers."""
    catalogs = _catalogs(datasets)
    body = ('<div class="comparison-hub"><header class="pair-heading hub-intro">'
            + '<p class="pair-kicker">Side by side</p><h1>Compare two filaments or printers</h1>'
            + '<p>Choose any two materials or printer models, open a selected matchup, '
            + 'or browse the complete comparison library. Every pair includes its documented '
            + 'properties and original source notes.</p></header><div class="hub-category-grid">')
    for kind, _, singular, title, noun, _ in KINDS:
        count = len(catalogs[kind]['cats'])
        pairs = count * (count - 1) // 2
        body += ('<a class="hub-category-card" data-hub-category="' + kind + '" href="' + kind
                 + '/"><span class="hub-card-kicker">Browse the library</span><h2>' + title
                 + ' comparisons</h2><p class="hub-count">' + format(count, ',') + ' ' + noun
                 + '</p><p class="hub-card-description">' + format(pairs, ',')
                 + ' dedicated pair comparisons. Pick one ' + singular + ', then its counterpart.</p>'
                 + '<span class="hub-card-action">Browse all ' + singular + ' comparisons →</span></a>')
    body += ('</div><section class="hub-selectors" aria-labelledby="hub-selectors-heading">'
             + '<h2 id="hub-selectors-heading">Choose your own pair</h2>'
             + '<p>Open the exact comparison you need. Unknown values stay labeled; '
             + 'source dates and test conditions remain beside the data.</p><div class="hub-selector-grid">')
    for kind, _, singular, title, _, defaults in KINDS:
        cats = sorted(catalogs[kind]['cats'], key=lambda cat: (cat['n'].casefold(), cat['id']))
        body += _picker(kind, singular, title, cats, defaults)
    body += ('</div><noscript><p>To choose a pair without JavaScript, browse '
             + '<a href="materials/">filament comparisons</a> or <a href="printers/">printer comparisons</a>, '
             + 'then choose the two items. The selected comparisons below open directly.</p></noscript></section>')
    return body + _featured(datasets, catalogs) + '</div>'
