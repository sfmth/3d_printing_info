"""Build one crawlable, sourced comparison for every unordered catalog pair.

The HTML is a deployment artifact, not a second catalog. Shared assets and a
tracked hash manifest keep ~12,000 pages reproducible without checking them in.
"""
from hashlib import sha256
from html import escape
from itertools import combinations
import json
from pathlib import Path
import re
from urllib.parse import quote

REVISION = '2026-10-31'
KINDS = {'materials': ('filaments.html', 'filament', 'Filament'),
         'printers': ('comparison.html', 'printer', 'Printer')}


def e(value):
    return escape(str(value), quote=True)


def pair_path(kind, left, right):
    """IDs, not display names or source order, determine the permanent URL."""
    if kind not in KINDS:
        raise ValueError('Unknown comparison kind: '+kind)
    ids = sorted(item['id'] if isinstance(item, dict) else item for item in (left, right))
    if ids[0] == ids[1] or any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', key) for key in ids):
        raise ValueError('A comparison needs two distinct catalog IDs')
    return 'compare/'+kind+'/'+ids[0]+'-vs-'+ids[1]+'.html'


def short_name(cat, kind):
    return cat.get('sh', cat['n']) if kind == 'materials' else cat['n']


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def _shell(base, path, title, description, body, *, left=None, right=None):
    depth = '../' * path.count('/')
    # Directory URLs have a trailing slash and already encode their depth.
    url = base+path
    schema = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': title,
              'description': description, 'url': url,
              'isPartOf': {'@type': 'WebSite', 'name': '3D Printing Info', 'url': base}}
    if left and right:
        schema['about'] = [{'@type': 'Thing', 'name': cat['n']} for cat in (left, right)]
    head = '<!doctype html>\n<html lang="en" data-theme="auto"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    head += '<title>'+e(title)+' | 3D Printing Info</title><meta name="description" content="'+e(description)+'"><meta name="robots" content="index,follow"><link rel="canonical" href="'+e(url)+'">'
    for key, value in {'og:title': title, 'og:description': description, 'og:url': url,
                       'og:type': 'website', 'og:site_name': '3D Printing Info',
                       'og:image': base+'assets/og-card.png'}.items():
        head += '<meta property="'+key+'" content="'+e(value)+'">'
    head += '<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="'+e(title)+'"><meta name="twitter:description" content="'+e(description)+'"><meta name="twitter:image" content="'+base+'assets/og-card.png">'
    head += '<link rel="icon" href="'+depth+'assets/site-icon.svg"><link rel="stylesheet" href="'+depth+'assets/pair-comparisons.css"><script defer src="'+depth+'assets/pair-comparisons.js"></script>'
    head += '<link rel="stylesheet" href="'+depth+'assets/analytics-consent.css"><script defer src="'+depth+'assets/analytics-consent.js"></script><script type="application/ld+json">'+_json(schema)+'</script></head>'
    attributes = ' data-left="'+e(left['id'])+'" data-right="'+e(right['id'])+'"' if left and right else ''
    nav = '<a class="brand" href="'+depth+'"><img src="'+depth+'assets/site-icon.svg" width="28" height="28" alt="">3D Printing Info</a><nav class="pair-nav" aria-label="Primary"><a href="'+depth+'filaments.html">Filaments</a><a href="'+depth+'comparison.html">Printers</a><a href="'+depth+'compare/">Comparisons</a></nav>'
    footer = '<footer class="pair-footer"><p>Values retain their individual source dates; prices are dated snapshots. Comparison layout revision: '+REVISION+'.</p><a href="'+depth+'sitemap.xml">Sitemap</a><span class="privacy-links"><a href="'+depth+'privacy.html">Privacy</a><button type="button" data-analytics-settings hidden>Analytics settings</button></span></footer>'
    return head+'<body class="pair-page"'+attributes+'><div class="pair-wrap"><div class="pair-topbar">'+nav+'</div><main>'+body+'</main>'+footer+'</div></body></html>\n'


def _picker(kind, cats, left, right):
    def options(selected):
        return ''.join('<option value="'+e(cat['id'])+'"'+(' selected' if cat['id'] == selected else '')+'>'+e(cat['n'])+'</option>' for cat in cats)
    return '<div class="pair-controls"><form id="pair-picker" data-kind="'+kind+'" hidden><label>First '+KINDS[kind][1]+'<select name="first">'+options(left['id'])+'</select></label><label>Second '+KINDS[kind][1]+'<select name="second">'+options(right['id'])+'</select></label><button type="submit">Compare</button></form><button id="pair-differences" type="button" aria-pressed="false" hidden>Show differences only</button><p id="pair-status" role="status" aria-live="polite">2 selected · all documented properties</p><noscript><p>Use the “More comparisons” links below to choose another pair. The complete comparison and sources are available without JavaScript.</p></noscript></div>'


def _table(data, kind, left, right, note=''):
    seen = []
    def reference(sid):
        if sid not in seen:
            seen.append(sid)
        number = seen.index(sid)+1
        return '<a class="source-ref" href="#source-'+str(number)+'" aria-label="Source '+str(number)+'">['+str(number)+']</a>'
    def cell(cat, fid):
        entry = cat['sp'].get(fid)
        if entry is None:
            return '<td class="property-value missing"><span class="value">Not documented</span></td>'
        sources = entry.get('s', [])
        return '<td class="property-value" data-sources="'+e(' '.join(sources))+'"><span class="value">'+e(entry['v'])+'</span>'+''.join(reference(sid) for sid in sources)+'</td>'
    rows = []
    if kind == 'printers':
        rows.append('<tr class="pair-section"><th colspan="3" scope="colgroup"><span>Identity</span></th></tr>')
        for label, key in (('Brand', 'brand'), ('Class', 'f')):
            values = [cat.get(key, 'Not documented') for cat in (left, right)]
            rows.append('<tr data-different="'+str(values[0] != values[1]).lower()+'"><th scope="row" class="field-name">'+label+'</th>'+''.join('<td class="property-value"><span class="value">'+e(value)+'</span></td>' for value in values)+'</tr>')
    if kind == 'materials':
        rows.append('<tr class="pair-section"><th colspan="3" scope="colgroup"><span>Market snapshot</span></th></tr>')
        prices = []
        for cat in (left, right):
            px = cat.get('px')
            prices.append(('${:.2f}/kg median; ${:.2f}–${:.2f}/kg across {} dated product listings'.format(px['med'], px['min'], px['max'], px['n'])) if px else 'Not documented')
        rows.append('<tr data-different="'+str(prices[0] != prices[1]).lower()+'"><th scope="row" class="field-name">Listing price<small>USD/kg; dated snapshots</small></th>'+''.join('<td class="property-value"><span class="value">'+e(price)+'</span></td>' for price in prices)+'</tr>')
    for section, label in data['sections'].items():
        fields = [field for field in data['fields'] if field['sec'] == section and any(field['id'] in cat['sp'] for cat in (left, right))]
        if not fields:
            continue
        rows.append('<tr class="pair-section"><th colspan="3" scope="colgroup"><span>'+e(label)+'</span></th></tr>')
        for field in fields:
            fid = field['id']
            entries = [cat['sp'].get(fid) for cat in (left, right)]
            different = (entries[0] or {}).get('v') != (entries[1] or {}).get('v')
            label = e(field['name'])+('<small>'+e(field['unit'])+'</small>' if field.get('unit') else '')
            rows.append('<tr data-field="'+e(fid)+'" data-different="'+str(different).lower()+'"><th scope="row" class="field-name">'+label+'</th>'+cell(left, fid)+cell(right, fid)+'</tr>')
    heads = ''.join('<th scope="col"><a href="../../'+kind+'/'+e(cat['id'])+'.html">'+e(cat['n'])+'</a><small>'+e(cat['f'])+'</small></th>' for cat in (left, right))
    table = '<section class="pair-table-wrap" aria-label="Side-by-side comparison" tabindex="0"><table id="pair-table"><caption>'+e(short_name(left, kind)+' vs '+short_name(right, kind))+' — documented properties and sources</caption><thead><tr><th scope="col">Property</th>'+heads+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></section>'
    sources = []
    for number, sid in enumerate(seen, 1):
        source = data['src'][sid]
        title = e(source.get('t', sid))
        if source.get('u'):
            title = '<a href="'+e(source['u'])+'">'+title+'</a>'
        context = ' · '.join(str(source[key]) for key in ('p', 'd', 'k') if source.get(key))
        sources.append('<li id="source-'+str(number)+'" data-source-id="'+e(sid)+'">'+title+(' <span>'+e(context)+'</span>' if context else '')+'</li>')
    return table+note+'<section class="pair-sources" id="sources"><h2>Sources for this comparison</h2><ol>'+''.join(sources)+'</ol></section>'


def render_pair(base, kind, data, left, right):
    left, right = sorted((left, right), key=lambda cat: cat['id'])
    path = pair_path(kind, left, right)
    name = short_name(left, kind)+' vs '+short_name(right, kind)
    topic = 'printing settings, strength, heat resistance, dated prices and sources' if kind == 'materials' else 'hardware, build volume, printing specifications, dated prices and sources'
    description = name+': compare '+topic+' side by side. Every documented field from both catalog entries, with source notes.'
    title = name+' — '+KINDS[kind][1]+' comparison'
    guide_links = ''.join('<a href="../../'+kind+'/'+e(cat['id'])+'.html">'+e(cat['n'])+' guide</a>' for cat in (left, right))
    body = '<header class="pair-heading"><p class="pair-kicker">'+KINDS[kind][2]+' comparison</p><h1>'+e(name)+'</h1><p>'+e('Compare '+topic+'.')+'</p><div class="pair-selected">'+guide_links+'</div></header>'
    body += _picker(kind, sorted(data['cats'], key=lambda cat: cat['n'].casefold()), left, right)
    ids = quote(left['id']+','+right['id'], safe=',')
    body += '<div class="pair-actions"><a id="pair-interactive" href="../../'+KINDS[kind][0]+'?compare='+ids+'">Open these two in the interactive comparison</a><a href="./'+e(left['id'])+'/">More '+e(short_name(left, kind))+' comparisons</a><a href="./'+e(right['id'])+'/">More '+e(short_name(right, kind))+' comparisons</a></div>'
    note = ('Material entries describe families or representative grades, not an interchangeable specification for every spool. Test methods, orientations and conditions may differ.' if kind == 'materials' else 'Manufacturer claims, independent measurements, packages and test conditions retain their source wording. FDM linear speed and resin vertical speed use different units and are not directly comparable.')
    note = '<p class="pair-notes">'+e(note)+' Unknown values are marked “Not documented”. Prices and source dates remain historical snapshots; check the linked guide for product details. Differences highlight text, not a universal winner.</p>'
    body += _table(data, kind, left, right, note)
    return _shell(base, path, title, description, body, left=left, right=right)


def generate_comparisons(root, base, datasets):
    root = Path(root)
    paths, hashes = [], {}
    def write(path, html):
        target = root/(path+'index.html' if path.endswith('/') else path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = html.encode()
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
        if path in hashes:
            raise ValueError('Comparison URL collision: '+path)
        paths.append(path)
        hashes[path] = sha256(content).hexdigest()
    for kind, (catalog, singular, plural) in KINDS.items():
        data = datasets[catalog] if catalog in datasets else datasets[kind]
        cats = sorted(data['cats'], key=lambda cat: cat['id'])
        for left, right in combinations(cats, 2):
            write(pair_path(kind, left, right), render_pair(base, kind, data, left, right))
        for cat in cats:
            path = 'compare/'+kind+'/'+cat['id']+'/'
            body = '<header class="pair-heading"><p class="pair-kicker">'+plural+' comparisons</p><h1>Compare '+e(short_name(cat, kind))+'</h1><p>Choose another '+singular+' to open the complete side-by-side comparison.</p><a href="../../../'+kind+'/'+e(cat['id'])+'.html">Read the '+e(cat['n'])+' guide</a></header><ul class="pair-directory">'
            for other in cats:
                if other['id'] != cat['id']:
                    body += '<li><a href="../'+pair_path(kind, cat, other).rsplit('/', 1)[1]+'">'+e(short_name(cat, kind)+' vs '+short_name(other, kind))+'</a></li>'
            body += '</ul><p><a href="../">All '+singular+' comparisons</a></p>'
            title = short_name(cat, kind)+' comparisons'
            write(path, _shell(base, path, title, 'Compare '+cat['n']+' with every other '+singular+' in the sourced catalog.', body))
        path = 'compare/'+kind+'/'
        count = len(cats)*(len(cats)-1)//2
        body = '<header class="pair-heading"><p class="pair-kicker">Side by side</p><h1>'+plural+' comparisons</h1><p>'+format(count, ',')+' distinct pair comparisons. Pick a '+singular+' below, then its counterpart.</p></header><ul class="pair-directory">'
        body += ''.join('<li><a href="'+e(cat['id'])+'/">Compare '+e(cat['n'])+'</a></li>' for cat in sorted(cats, key=lambda cat: cat['n'].casefold()))+'</ul>'
        write(path, _shell(base, path, plural+' comparisons', 'Browse every '+singular+' matchup in the sourced comparison catalog.', body))
    path = 'compare/'
    body = '<header class="pair-heading"><p class="pair-kicker">Side by side</p><h1>Compare two filaments or printers</h1><p>Open a dedicated comparison with two items selected, every documented property and the original source notes.</p></header><ul class="pair-directory"><li><a href="materials/">Filament comparisons</a></li><li><a href="printers/">Printer comparisons</a></li></ul>'
    write(path, _shell(base, path, 'Filament and printer comparisons', 'Find a side-by-side comparison for every pair of filament materials or 3D printers in the catalog.', body))
    # Remove only obsolete HTML inside this generator's owned, ignored folder.
    expected = {(root/(path+'index.html' if path.endswith('/') else path)).resolve() for path in paths}
    for existing in (root/'compare').rglob('*.html'):
        if existing.resolve() not in expected:
            existing.unlink()
    (root/'data').mkdir(exist_ok=True)
    (root/'data/pair-comparison-manifest.json').write_text(json.dumps({'version': 1, 'pages': dict(sorted(hashes.items()))}, indent=2)+'\n')
    return paths
