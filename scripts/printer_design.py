"""Readable printer reference pages, derived from the unchanged catalog."""
from html import escape
import json
from pathlib import Path
import re
from printer_resources import load_resources, entries_for, chapter_context, review_notes

ROOT = Path(__file__).resolve().parents[1]
E = lambda value: escape(str(value), quote=True)

FAMILIES = {
    'BEDSLINGER': ('Bed-slinger', 'A moving bed and a gantry-mounted printhead.', 'bedslinger'),
    'COREXY': ('CoreXY', 'Belt-driven XY motion; the build platform or gantry moves in Z.', 'corexy'),
    'IDEX': ('Dual extrusion', 'Two extrusion paths. The head arrangement varies by model.', 'idex'),
    'TOOLCHANGER': ('Tool changing', 'Multiple tools or printheads; switching arrangements vary by model.', 'toolchanger'),
    'RESIN': ('Resin', 'Liquid photopolymer cured in successive layers.', 'resin'),
    'INDUSTRIAL': ('Industrial', 'Production-oriented equipment with model-specific process requirements.', 'industrial'),
}

SECTIONS = {
    'A': 'Model, variants & pricing', 'B': 'Size, frame & enclosure',
    'C': 'Motion system', 'D': 'Speed & acceleration',
    'E': 'Vibration compensation', 'F': 'Extrusion pressure control',
    'G': 'Extruder', 'H': 'Hotend & nozzle', 'I': 'Build plate & heating',
    'J': 'Leveling & Z-offset', 'K': 'Filament handling', 'L': 'Cooling & filtration',
    'M': 'Electronics & power', 'N': 'Firmware & openness',
    'O': 'Connectivity, display & camera', 'P': 'Calibration & everyday use',
    'Q': 'Interruption recovery', 'R': 'Supported materials',
    'S': 'Safety', 'T': 'Noise & power consumption', 'U': 'Support & ecosystem',
    'V': 'Independent measurements', 'W': 'Resin system',
}

CHAPTERS = (
    ('machine', 'Machine & motion', 'Dimensions, construction and the hardware that moves the print.', 'ABCD'),
    ('printing', 'Printing system', 'Extrusion, heating, leveling and material handling.', 'EFGHIJKLRW'),
    ('workflow', 'Software & workflow', 'Firmware, controls, connections and calibration.', 'MNOPQ'),
    ('ownership', 'Safety, support & testing', 'Published safeguards, support terms and independent evidence.', 'STUV'),
)


def images():
    path = ROOT / 'data/printer-images.json'
    return json.loads(path.read_text())['images'] if path.exists() else {}


def count_label(number, noun):
    return str(number) + ' ' + noun + ('' if number == 1 else 's')


def photo(c, entry):
    return ('<figure class="printer-visual has-product-image"><div class="printer-image-stage">'
            '<span class="printer-image-label">Model reference</span><img data-printer-image="' + E(c['id']) + '" src="../' + E(entry['image']) +
            '" alt="' + E(entry['alt']) + '" width="' + str(entry['width']) + '" height="' + str(entry['height']) +
            '" fetchpriority="high" decoding="async"></div><figcaption>' + E(entry['kind']) + ' · ' + E(entry['credit']) +
            ' · <a href="' + E(entry['source_url']) + '">Image source <span aria-hidden="true">↗</span></a></figcaption></figure>')


def diagram(c):
    label, description, filename = FAMILIES[c['f']]
    return ('<figure class="printer-visual is-diagram"><div class="printer-image-stage">'
            '<span class="printer-image-label">Architecture reference</span><img data-printer-diagram="' + filename +
            '" src="../assets/printers/' + filename + '.svg" alt="' + E(label) +
            ' architecture illustration; not an image of this model" width="720" height="560"></div>'
            '<figcaption>' + E(label) + ' · Generic illustration, not this model’s appearance or construction.</figcaption></figure>')


def source_disclosure(data, ids, refs, label='Sources & dates'):
    if not ids:
        return '<p class="printer-missing-source">No linked source in the catalog.</p>'
    return '<details class="printer-inline-sources"><summary>' + E(label) + '</summary>' + refs(data, ids) + '</details>'


def overview(data, c, refs):
    selected = [('B1', 'Build volume', 'Advertised dimensions; check usable space and variants.')]
    if c['f'] == 'RESIN':
        candidates = [('W1', 'Masking display', 'Published resin-display specification.'),
                      ('W4', 'Vertical speed', 'Manufacturer figure in mm/h; retain the layer and resin conditions.')]
    else:
        candidates = [('H2', 'Nozzle temperature', 'Published limits; hardware and firmware limits may differ.'),
                      ('B5', 'Enclosure', 'Published enclosure and chamber-heating notes.')]
    selected.extend(next(([entry] for entry in candidates if entry[0] in c['sp']), []))
    selected.append(('A4', 'Price snapshot', 'Dated listing, not a live offer. Read the configuration and region.'))
    body = '<section class="printer-section" id="overview" aria-labelledby="overview-heading"><div class="printer-section-heading"><div><span class="printer-eyebrow">Start here</span><h2 id="overview-heading">At a glance</h2></div><a class="printer-text-link" href="#specifications">Explore this printer <span aria-hidden="true">↓</span></a></div><div class="printer-overview-grid">'
    for index, (fid, label, note) in enumerate(selected, 1):
        entry = c['sp'].get(fid)
        body += '<article class="printer-overview-card"><span class="printer-card-index" aria-hidden="true">0' + str(index) + '</span><h3>' + E(label) + '</h3>'
        body += '<p class="printer-overview-value">' + E(entry['v'] if entry else 'Not recorded in this catalog.') + '</p><p class="printer-card-note">' + E(note) + '</p>'
        if entry:
            body += source_disclosure(data, entry.get('s', []), refs)
        body += '</article>'
    return body + '</div></section>'


def spec_group(data, c, sid, refs):
    fields = [f for f in data['fields'] if f['sec'] == sid and f['id'] in c['sp']]
    if not fields:
        return ''
    body = ('<details class="printer-spec-group" id="spec-' + sid.lower() + '"><summary><span class="printer-spec-title">' + E(SECTIONS[sid]) +
            '</span><span class="printer-spec-count">' + count_label(len(fields), 'field') + '</span></summary><div class="printer-spec-content">'
            '<div class="table-scroll"><table role="table"><caption>' + E(c['n'] + ' — ' + data['sections'][sid]) +
            '</caption><thead><tr role="row"><th scope="col" role="columnheader">Property and unit</th><th scope="col" role="columnheader">Published value and conditions</th><th scope="col" role="columnheader">Sources and dates</th></tr></thead><tbody>')
    for field in fields:
        entry = c['sp'][field['id']]
        body += '<tr role="row" data-field="' + E(field['id']) + '"><th scope="row" role="rowheader">' + E(field['name'])
        if field.get('unit'):
            body += ' <span class="printer-unit">(' + E(field['unit']) + ')</span>'
        body += '</th><td role="cell" class="printer-property-value">' + E(entry['v']) + '</td><td role="cell" class="printer-property-sources">'
        ids = entry.get('s', [])
        if ids:
            body += '<details class="printer-row-sources"><summary>' + count_label(len(dict.fromkeys(ids)), 'source') + '</summary>' + refs(data, ids) + '</details>'
        else:
            body += '<span class="printer-missing-source">—</span>'
        body += '</td></tr>'
    return body + '</tbody></table></div></div></details>'


def related(data, c):
    siblings = [x for x in data['cats'] if x.get('brand') == c.get('brand') and x['id'] != c['id']]
    if not siblings:
        return ''
    body = '<section class="printer-section printer-related" id="related"><div class="printer-section-heading"><div><span class="printer-eyebrow">Keep exploring</span><h2>More from ' + E(c['brand']) + '</h2></div><a class="printer-text-link" href="./">All printer guides <span aria-hidden="true">↗</span></a></div><ul class="printer-related-list">'
    for sibling in siblings:
        body += '<li><a href="' + E(sibling['id']) + '.html"><span>' + E(sibling['n']) + '</span><small>' + E(FAMILIES[sibling['f']][0]) + '</small><span aria-hidden="true">↗</span></a></li>'
    return body + '</ul></section>'


def detail_body(data, c, refs):
    used = list(dict.fromkeys(sid for entry in c['sp'].values() for sid in entry.get('s', [])))
    family = FAMILIES[c['f']]
    media = images().get(c['id'])
    ownership = load_resources().get(c['id'])
    body = ('<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../">Home</a><span aria-hidden="true">/</span><a href="./">Printer guides</a><span aria-hidden="true">/</span><span aria-current="page">' + E(c['n']) + '</span></nav>'
            '<header class="printer-hero"><div class="printer-hero-copy"><div class="printer-model-tags"><span class="printer-family-tag">' + E(family[0]) + '</span><span class="printer-eyebrow">' + E(c.get('brand', '')) + '</span></div><h1>' + E(c['n']) +
            '</h1><p class="printer-lede">' + E(c.get('sum', '')) + '</p><div class="printer-hero-actions"><a class="printer-primary-action" href="../comparison.html#' + E(c['id']) + '">Open in interactive comparison <span aria-hidden="true">↗</span></a><a class="printer-secondary-action" href="./">Browse printers</a></div>'
            '<p class="printer-record-meta">' + count_label(len(c['sp']), 'catalog field') + '<span aria-hidden="true">·</span>' + count_label(len(used), 'catalog source') + '</p></div>' + (photo(c, media) if media else diagram(c)) + '</header>'
            '<nav class="printer-jumps" aria-label="On this page"><a href="#overview">At a glance</a><a href="#specifications">Hardware & ownership</a><a href="#sources">Sources & notes</a>' + ('<a href="#related">Related printers</a>' if any(x.get('brand') == c.get('brand') and x['id'] != c['id'] for x in data['cats']) else '') + '</nav>')
    body += overview(data, c, refs)
    body += '<section class="printer-section" id="specifications" aria-labelledby="specifications-heading"><div class="printer-section-heading"><div><span class="printer-eyebrow">A closer look</span><h2 id="specifications-heading">Hardware, software & ownership</h2></div><span class="printer-quiet-label">Full specifications inside each chapter</span></div><p class="printer-section-intro">Understand the hardware, explore compatible changes and find a diagnostic starting point when something goes wrong. Expand the specification sections for every recorded value, condition and original reference.</p><div class="printer-spec-layout"><nav class="printer-chapter-nav" aria-label="Specification chapters">'
    active = [(slug, title, desc, sids) for slug, title, desc, sids in CHAPTERS if any(f['sec'] in sids and f['id'] in c['sp'] for f in data['fields']) or (ownership and entries_for(ownership, sids))]
    for slug, title, _, _ in active:
        body += '<a href="#' + slug + '">' + E(title) + '<span aria-hidden="true">↘</span></a>'
    body += '</nav><div class="printer-spec-chapters">'
    for slug, title, desc, sids in active:
        body += '<section class="printer-spec-chapter" id="' + slug + '"><div class="printer-chapter-heading"><h3>' + E(title) + '</h3><p>' + E(desc) + '</p></div>'
        for sid in sids:
            context = chapter_context(ownership, sid) if ownership else ''
            specifications = spec_group(data, c, sid, refs)
            if context or specifications:
                body += '<div class="printer-topic" data-printer-topic="' + sid + '">' + context + ('<div class="printer-spec-list">' + specifications + '</div>' if specifications else '') + '</div>'
        body += '</section>'
    body += '</div></div></section>'
    body += '<section class="printer-section printer-reading-notes" id="sources" aria-labelledby="sources-heading"><div class="printer-section-heading"><div><span class="printer-eyebrow">Read with context</span><h2 id="sources-heading">Sources & notes</h2></div></div><div class="printer-notes-grid"><div><h3>How to read this guide</h3><p>This guide presents the catalog’s sourced record for this exact model. Source dates belong to each reference; a page update does not mean every specification has been rechecked.</p><p>Prices are dated listing snapshots, with configuration, regional and sale conditions. They are not current offers. Unknown values remain unfilled.</p><p>Firmware, variants and available accessories can change. Read the original reference before making a purchase or planning a process.</p></div><details class="printer-source-library"><summary><span>Catalog references</span><span>' + count_label(len(used), 'source') + '</span></summary>' + refs(data, used) + '</details></div>'
    if ownership:
        body += review_notes(ownership)
    body += '</section>'
    return body + related(data, c)


def write_diagrams():
    """Original explanatory vectors; explicitly not model photographs or drawings."""
    folder = ROOT / 'assets/printers'
    folder.mkdir(exist_ok=True)
    frame = '<path d="M205 395V147l243-33 102 63v245M205 147l105 64 240-34M310 211v249M205 395l105 65 240-38M448 114v244"/>'
    bed = '<path class="panel" d="m233 353 199-26 83 52-199 26z"/><path d="M316 405v24m-83-76v18m282 8v18"/>'
    illustrations = {
        'bedslinger': ('Moving bed', '<path d="M209 397V165h278v232M231 397V188h232v209"/><path class="panel" d="m185 376 217-40 132 51-219 42z"/><path d="M231 252h232M231 269h232"/><rect class="orange-fill" x="337" y="232" width="49" height="57" rx="5"/><path class="orange" d="m361 290 0 21m-7-7 7 8 7-8M271 431l38 17m-4-9 6 11-13 0M401 339l-35-14m4 10-8-12 14-1"/><path d="M209 398h-27m305 0h27"/>'),
        'corexy': ('XY belt motion', frame + bed + '<path class="orange" d="m215 156 231-32 94 55-231 32zM215 156l325 23M309 211l137-87"/><path d="m251 224 232-31m-73-63v195"/><path class="orange-fill" d="m363 209 38-5 17 11v39l-36 5-19-12z"/><path class="orange" d="M389 261v37m-7-8 7 8 7-8"/>'),
        'idex': ('Two extrusion paths', frame + bed + '<path d="m228 230 286-40m-286 61 286-40"/><path class="orange-fill" d="m271 222 43-6 12 9v39l-43 6-12-9zm141-20 43-6 12 9v39l-43 6-12-9z"/><path class="orange" d="M297 273v27m142-47v27M298 196l28-4m-7-6 9 5-7 9M437 175l-28 4m9 5-12-5 8-8"/>'),
        'toolchanger': ('Tools at the ready', frame + bed + '<path d="m226 218 291-39"/><path class="panel" d="m244 157 204-28 48 30-204 28z"/><path class="orange-fill" d="m272 170 25-4v35l-25 4zm51-7 25-4v35l-25 4zm51-7 25-4v35l-25 4zm51-7 25-4v35l-25 4z"/><path class="orange" d="m367 247 32-4 14 9v32l-32 4-14-9zM391 289v33m-8-8 8 8 8-8"/>'),
        'resin': ('Layers cured in resin', '<path class="panel" d="m235 402 228-24 69 43-228 24z"/><path d="M235 402v43l69 43 228-24v-43M304 445v43"/><path class="orange-panel" d="M248 389V167l176-24 94 60v204l-213 25z"/><path d="m248 167 87 55 183-19M335 222v210M424 143v235"/><path d="M392 201v107M408 198v107"/><path class="panel" d="m330 323 98-13 45 28-98 13z"/><path class="orange" d="m357 367 88-11 35 22-88 11zM400 254v-31m-7 7 7-8 7 8"/>'),
        'industrial': ('Production equipment', '<path class="panel" d="M218 427V142l219-29 99 59v282l-219 30z"/><path d="m218 142 99 61 219-31M317 203v281"/><path class="window" d="m339 226 162-20v163l-162 20z"/><path d="m351 337 118-15 22 13-118 15zM374 244v78m92-89v89"/><path class="orange" d="m386 263 43-5v29l-43 5z"/><path d="m237 192 61 37v133l-61-36zM501 242v54m-164 121 167-21M339 443l165-20"/><path class="orange-fill" d="m343 405 48-6v13l-48 6z"/>'),
    }
    for filename, (title, drawing) in illustrations.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 560" width="720" height="560" role="img" aria-labelledby="title desc"><title id="title">' + title +
               '</title><desc id="desc">General explanatory illustration, not a drawing of an individual printer model. Arrangements vary by model.</desc><defs><pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#dbe2d9" stroke-width=".7"/></pattern></defs><rect width="720" height="560" fill="#eff2e9"/><rect x="40" y="52" width="640" height="460" rx="12" fill="url(#grid)"/><ellipse cx="367" cy="466" rx="207" ry="22" fill="#243b2b" opacity=".06"/><g fill="none" stroke="#344a3d" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">' +
               '<style>.panel{fill:#e2e8dc}.orange{stroke:#cc4b21}.orange-fill{fill:#dc673e;stroke:#a7411d}.orange-panel{fill:#dc673e;fill-opacity:.16;stroke:#ad4c2d}.window{fill:#d1ddce;fill-opacity:.6}</style>' + drawing +
               '</g><text x="62" y="88" fill="#52675a" font-family="system-ui,sans-serif" font-size="12" letter-spacing="2">' + title.upper() +
               '</text><text x="62" y="510" fill="#617365" font-family="system-ui,sans-serif" font-size="11" letter-spacing="1">CONCEPT ILLUSTRATION · NOT TO SCALE</text></svg>\n')
        (folder / (filename + '.svg')).write_text(svg)
