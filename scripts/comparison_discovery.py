"""Curated, static entry points into the complete catalog pair library.

Selections are editorial and use catalog IDs. Search Console state is deliberately
not an input: the same catalogs always produce the same ordinary HTML links.
"""
from html import escape

from pair_comparisons import KINDS, pair_path, short_name


COMPARISONS = (
    {'kind': 'materials', 'left': 'pla', 'right': 'petg', 'featured': True,
     'description': 'Check printing setup, stiffness, toughness and heat limits for everyday functional prints.'},
    {'kind': 'materials', 'left': 'abs', 'right': 'asa', 'featured': True,
     'description': 'Compare enclosure needs, weather exposure notes and finish requirements.'},
    {'kind': 'materials', 'left': 'asa', 'right': 'petg', 'featured': True,
     'description': 'Compare printing demands, outdoor exposure notes and moisture considerations.'},
    {'kind': 'materials', 'left': 'pc', 'right': 'petg', 'featured': False,
     'description': 'Inspect temperature, drying and printer setup constraints before choosing a grade.'},
    {'kind': 'materials', 'left': 'pa6', 'right': 'pa12', 'featured': False,
     'description': 'Compare moisture-conditioning notes, drying and mechanical property context.'},
    {'kind': 'materials', 'left': 'pa6-cf', 'right': 'pc-cf', 'featured': False,
     'description': 'Compare matrix chemistry, drying, thermal properties and the reported mechanical test conditions.'},
    {'kind': 'materials', 'left': 'pa6-cf', 'right': 'pa12-cf', 'featured': False,
     'description': 'Inspect moisture, processing and composite-property conditions before choosing a reinforced nylon.'},
    {'kind': 'materials', 'left': 'asa', 'right': 'pla', 'featured': True,
     'description': 'Compare exposure and heat considerations alongside print-setup requirements.'},
    {'kind': 'printers', 'left': 'bambu-a1', 'right': 'bambu-p1s', 'featured': True,
     'description': 'Compare open-frame and enclosed printer specifications, materials and ownership routes.'},
    {'kind': 'printers', 'left': 'bambu-a1', 'right': 'bambu-a1-mini', 'featured': True,
     'description': 'Check build volume, hardware, material constraints and dated configurations.'},
    {'kind': 'printers', 'left': 'bambu-p1s', 'right': 'creality-k1c', 'featured': True,
     'description': 'Compare enclosed CoreXY hardware, material support and model-specific maintenance routes.'},
    {'kind': 'printers', 'left': 'bambu-a1-mini', 'right': 'creality-ender-3-v3-se', 'featured': False,
     'description': 'Compare motion hardware, build volume, calibration and firmware records.'},
    {'kind': 'printers', 'left': 'bambu-p1s', 'right': 'bambu-x1c', 'featured': True,
     'description': 'Inspect sensing, electronics, material limits and dated configuration differences.'},
)

FEATURED = tuple(pair_path(item['kind'], item['left'], item['right'])
                 for item in COMPARISONS if item['featured'])


def _catalog(data):
    result = {}
    for cat in data['cats']:
        if cat['id'] in result:
            raise ValueError('Duplicate catalog ID: ' + cat['id'])
        if not isinstance(cat.get('n'), str) or not cat['n'].strip():
            raise ValueError('A comparison label needs a catalog name: ' + cat['id'])
        result[cat['id']] = cat
    return result


def _resolve(comparisons, catalogs):
    result, paths = [], set()
    for item in comparisons:
        kind = item['kind']
        path = pair_path(kind, item['left'], item['right'])
        if path in paths:
            raise ValueError('Duplicate unordered discovery pair: ' + path)
        paths.add(path)
        if not isinstance(item.get('description'), str) or not item['description'].strip():
            raise ValueError('A discovery pair needs an explanation: ' + path)
        if not isinstance(item.get('featured'), bool):
            raise ValueError('A discovery pair needs an explicit featured flag: ' + path)
        cats = catalogs[kind]
        missing = [key for key in (item['left'], item['right']) if key not in cats]
        if missing:
            raise ValueError('Unknown ' + kind + ' discovery ID: ' + ', '.join(missing))
        title = ' vs '.join(short_name(cats[key], kind) for key in sorted((item['left'], item['right'])))
        result.append({**item, 'path': path, 'title': title})
    return tuple(result)


def validate_discovery(datasets, comparisons=COMPARISONS):
    """Validate against complete catalogs and return records with path/title.

    ``datasets`` uses the existing ``filaments.html``/``comparison.html`` keys.
    A reversed duplicate, self-pair or unknown category/ID fails generation.
    """
    catalogs = {kind: _catalog(datasets[details[0]]) for kind, details in KINDS.items()}
    return _resolve(comparisons, catalogs)


def _section(items, *, section_id, title, description, depth, level=2):
    if not items:
        return ''
    e = lambda value: escape(str(value), quote=True)
    body = ('<section class="discovery-section" id="' + section_id + '" aria-labelledby="'
            + section_id + '-heading"><div class="discovery-heading"><h' + str(level)
            + ' id="' + section_id + '-heading">' + e(title) + '</h' + str(level)
            + '><p class="discovery-description">' + e(description) + '</p></div><div class="discovery-grid">')
    for item in items:
        kind = item['kind']
        body += ('<a class="discovery-card" data-discovery-pair="' + e(item['path']) + '" href="'
                 + depth + e(item['path']) + '"><span class="discovery-kicker">'
                 + ('Filament' if kind == 'materials' else 'Printer') + ' comparison</span><h'
                 + str(level + 1) + '>' + e(item['title']) + '</h' + str(level + 1)
                 + '><p>' + e(item['description'])
                 + '</p><span class="discovery-action">View side by side <span aria-hidden="true">→</span></span></a>')
    return body + '</div></section>'


def render_home_comparisons(datasets):
    items = [item for item in validate_discovery(datasets) if item['featured']]
    return _section(items, section_id='featured-comparisons', title='Start with a comparison',
                    description='Compare documented properties and follow their original sources. Material values summarize catalog families; check exact-grade evidence for engineering decisions.',
                    depth='').replace('</section>', '<p class="discovery-browse"><a href="compare/">Browse every filament and printer comparison →</a></p></section>')


def render_guide_comparisons(kind, cat, data):
    if kind not in KINDS:
        raise ValueError('Unknown comparison kind: ' + kind)
    selected = [item for item in COMPARISONS if item['kind'] == kind and cat['id'] in (item['left'], item['right'])]
    if not selected:
        return ''
    catalogs = {kind: _catalog(data)}
    if cat['id'] not in catalogs[kind]:
        raise ValueError('Unknown guide catalog ID: ' + cat['id'])
    items = _resolve(selected, catalogs)
    description = ('These compare material family catalog summaries. Values retain their original grades, methods and dates; they do not rank every spool or establish service limits.'
                   if kind == 'materials' else
                   'Compare the sourced records for these exact models, including configuration qualifiers, unknowns and dated prices.')
    return _section(items, section_id='selected-comparisons',
                    title='Compare ' + short_name(catalogs[kind][cat['id']], kind),
                    description=description, depth='../')


def render_article_comparisons(article, data):
    candidates = set(article['materials'])
    selected = [item for item in COMPARISONS if item['kind'] == 'materials'
                and {item['left'], item['right']} <= candidates]
    items = _resolve(selected, {'materials': _catalog(data)})
    return _section(items, section_id='catalog-comparisons', title='Compare the catalog summaries',
                    description='These material family comparisons provide printing settings and catalog properties. The article’s grade-specific measurements and test conditions above remain the basis for its engineering guidance.',
                    depth='../', level=3)
