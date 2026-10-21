"""A crawlable printer library, enhanced by optional client-side filters.

The complete comparison payload remains the source of printer specifications.
Images are selected by exact catalog ID from the separately audited manifest.
"""
from html import escape
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
E = lambda value: escape(str(value), quote=True)
FAMILIES = {
    'COREXY': ('CoreXY', 'Explore the catalog’s CoreXY group, from compact frames to enclosed machines.', 'XY'),
    'BEDSLINGER': ('Bedslingers', 'Moving-bed printers, from compact desktop models to larger build areas.', 'i3'),
    'IDEX': ('Dual extrusion', 'The catalog’s IDEX group includes different dual-head arrangements. Check the exact model.', '2×'),
    'TOOLCHANGER': ('Toolchangers', 'Printers grouped around interchangeable tools and multi-head configurations.', 'T+'),
    'RESIN': ('Resin', 'Explore resin systems, their build areas, light engines and handling features.', 'UV'),
    'INDUSTRIAL': ('Industrial & professional', 'Specialized systems for production workflows, composites and higher temperatures.', 'PRO'),
}
FEATURE_PREFERENCES = {
    'COREXY': ('bambu-x1c', 'bambu-p1s', 'prusa-core-one', 'voron-24'),
    'BEDSLINGER': ('prusa-mk4s', 'bambu-a1', 'bambu-a1-mini'),
    'IDEX': ('snapmaker-j1s', 'flashforge-creator-4', 'raise3d-pro3'),
    'TOOLCHANGER': ('prusa-xl-5t', 'prusa-xl-2t', 'snapmaker-u1'),
    'RESIN': ('formlabs-form-4', 'anycubic-photon-p1-max', 'elegoo-mars-5-ultra'),
    'INDUSTRIAL': ('markforged-x7', 'stratasys-f370', 'ultimaker-factor-4'),
}
SUMMARIES = {
    'snapmaker-artisan': 'A large 3-in-1 system for dual-extrusion printing, laser cutting and CNC work.',
}


def compact(value, limit=144):
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'


def image_manifest():
    path = ROOT / 'data/printer-images.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text())['images']


def family_info(family):
    return FAMILIES.get(family, (family, 'Explore the complete sourced model records.', family))


def photograph(model, images, *, eager=False):
    entry = images.get(model['id'])
    if not entry:
        return ''
    return ('<img class="pl-product-photo" data-printer-photo="' + E(model['id'])
            + '" src="../' + E(entry['image']) + '" alt="' + E(entry['alt'])
            + '" width="' + E(entry['width']) + '" height="' + E(entry['height'])
            + '" loading="' + ('eager' if eager else 'lazy') + '" decoding="async"'
            + (' fetchpriority="high"' if eager else '') + '>')


def image_credit(model, images):
    entry = images.get(model['id'])
    if not entry:
        return ''
    return ('<span class="pl-image-credit">Image: <a href="' + E(entry['source_url'])
            + '">' + E(entry['credit']) + '</a></span>')


def visual(model, images):
    photo = photograph(model, images)
    if photo:
        return '<div class="pl-card-visual">' + photo + '</div>'
    label, _, mark = family_info(model['f'])
    return ('<div class="pl-card-visual pl-type-visual" aria-hidden="true"><span>'
            + E(mark) + '</span><small>' + E(label) + ' / hardware guide</small></div>')


def card(model, images, *, featured=False):
    cid = model['id']
    family = family_info(model['f'])[0]
    summary = SUMMARIES.get(cid) or model.get('sum') or 'Explore the hardware, firmware and complete sourced specifications for this model.'
    volume = model.get('sp', {}).get('B1', {}).get('v')
    attrs = (' data-featured-printer="' + E(cid) + '"' if featured else
             ' data-printer-card data-printer-id="' + E(cid) + '" data-search="'
             + E(' '.join(str(model.get(key) or '') for key in ('n', 'brand', 'aka', 'sh')))
             + '"')
    body = ('<article class="' + ('pl-feature-card' if featured else 'pl-printer-card')
            + (' pl-has-photo' if cid in images else ' pl-no-photo') + '"' + attrs + '>')
    body += '<a class="pl-card-link" href="' + E(cid) + '.html">' + visual(model, images)
    body += ('<div class="pl-card-copy"><span class="pl-card-kicker">'
             + E(model.get('brand') or 'Brand not reported') + '<span aria-hidden="true"> / </span>'
             + E(family) + '</span><h3>' + E(model['n']) + '</h3><p class="pl-card-description">'
             + E(compact(summary, 152 if featured else 128)) + '</p>')
    body += ('<div class="pl-build-volume"><span>Build volume</span><p>'
             + E(compact(volume, 126) if volume else 'Not reported') + '</p></div>')
    body += '<span class="pl-read-guide">Read guide <span aria-hidden="true">↗</span></span></div></a>'
    if featured:
        if cid in images:
            body += '<div class="pl-card-footer">' + image_credit(model, images) + '</div>'
    else:
        body += ('<div class="pl-card-footer"><a class="pl-card-compare" href="../comparison.html#'
                 + E(cid) + '" aria-label="Open ' + E(model['n'])
                 + ' in interactive comparison">Compare specifications <span aria-hidden="true">↗</span></a>'
                 + image_credit(model, images) + '</div>')
    return body + '</article>'


def featured_models(cats, images):
    selected = []
    by_id = {model['id']: model for model in cats}
    for family in FAMILIES:
        members = [model for model in cats if model['f'] == family]
        if not members:
            continue
        preferred = [by_id[cid] for cid in FEATURE_PREFERENCES[family]
                     if cid in by_id and by_id[cid]['f'] == family]
        photographed = [model for model in preferred + members if model['id'] in images]
        selected.append((photographed or preferred or members)[0])
    return selected


def directory_body(data):
    cats = data['cats']
    images = image_manifest()
    featured = featured_models(cats, images)
    families = [family for family in FAMILIES if any(model['f'] == family for model in cats)]
    families += [family for family in data.get('families', [])
                 if family not in families and any(model['f'] == family for model in cats)]
    brands = {model['brand'] for model in cats if model.get('brand')}
    hero_model = next((model for model in featured if model['id'] in images), None)

    body = '<div class="printer-library"><div class="pl-breadcrumbs"><a href="../">Home</a><span aria-hidden="true">/</span><span>Printer guides</span></div>'
    body += '<header class="pl-hero"><div class="pl-hero-copy"><span class="pl-eyebrow">The hardware library</span><h1>Printer guides</h1>'
    body += '<p class="pl-lede">Find your next machine.<br>Understand the one you have.</p><p class="pl-intro">Explore desktop, resin and production printers. Start with a model, then look closer at its hardware, software and sourced specifications.</p>'
    body += '<div class="pl-hero-actions"><a class="pl-comparison-link" href="../comparison.html">Compare printers <span aria-hidden="true">↗</span></a><a class="pl-browse-link" href="#browse-printers">Browse the library <span aria-hidden="true">↓</span></a></div>'
    body += ('<dl class="pl-stats"><div><dt>Model guides</dt><dd>' + str(len(cats))
             + '</dd></div><div><dt>Brands</dt><dd>' + str(len(brands))
             + '</dd></div><div><dt>Printer groups</dt><dd>' + str(len(families)) + '</dd></div></dl></div>')
    if hero_model:
        body += '<figure class="pl-hero-visual"><div class="pl-hero-image">' + photograph(hero_model, images, eager=True) + '</div><figcaption><span><span class="pl-eyebrow">In the library</span><a href="' + E(hero_model['id']) + '.html">' + E(hero_model['n']) + ' <span aria-hidden="true">↗</span></a></span>' + image_credit(hero_model, images) + '</figcaption></figure>'
    else:
        body += '<div class="pl-hero-visual pl-hero-type" aria-hidden="true"><span class="pl-eyebrow">From first layer to full workflow</span><span class="pl-display-type">Build.<br>Compare.<br><em>Understand.</em></span><span class="pl-type-caption">FDM / resin / production</span></div>'
    body += '</header>'

    body += '<section class="pl-browse" id="browse-printers" aria-labelledby="printer-library-heading"><div class="pl-section-heading"><div><span class="pl-eyebrow">The complete collection</span><h2 id="printer-library-heading">Find a printer.</h2></div><span class="pl-total">' + str(len(cats)) + ' model guides</span></div>'
    body += '<div class="pl-search-panel" id="printer-search-panel" hidden><label for="printer-search">Search by brand or model</label><div class="pl-search-row"><span class="pl-search-icon" aria-hidden="true">⌕</span><input id="printer-search" type="search" placeholder="Try Prusa, X1 or Saturn…" autocomplete="off" spellcheck="false" aria-controls="printer-groups"><button id="clear-printer-search" type="button">Clear filters</button></div><div class="pl-filters" role="group" aria-label="Printer group"><button type="button" data-printer-filter="" aria-pressed="true">All printers</button>'
    body += ''.join('<button type="button" data-printer-filter="' + E(family) + '" aria-pressed="false">' + E(family_info(family)[0]) + '</button>' for family in families)
    body += '</div><p id="printer-results" role="status" aria-live="polite" aria-atomic="true">' + str(len(cats)) + ' of ' + str(len(cats)) + ' printers</p></div>'
    body += '<section class="pl-featured" id="printer-starting-points" aria-labelledby="featured-printers"><div class="pl-section-heading"><div><span class="pl-eyebrow">A few starting points</span><h2 id="featured-printers">Different ways to print.</h2></div><p>One guide from each group.<br>A starting point for exploring the library.</p></div><div class="pl-feature-grid">' + ''.join(card(model, images, featured=True) for model in featured) + '</div></section>'
    body += '<div id="printer-groups">'
    for index, family in enumerate(families, 1):
        members = [model for model in cats if model['f'] == family]
        label, description, mark = family_info(family)
        body += ('<details class="pl-family" data-printer-family="' + E(family) + '" open><summary><span class="pl-family-index" aria-hidden="true">'
                 + f'{index:02}' + '</span><span class="pl-family-title"><span>' + E(label)
                 + '</span><small>' + E(description) + '</small></span><span class="pl-family-count" data-family-count>'
                 + str(len(members)) + ' guides</span><span class="pl-family-toggle" aria-hidden="true"></span></summary>')
        body += '<div class="pl-printer-grid">' + ''.join(card(model, images) for model in members) + '</div></details>'
    body += '</div><div id="printer-no-results" class="pl-no-results" hidden><span class="pl-eyebrow">No matches</span><h3>Try a different starting point.</h3><p>Check the model name, try its brand, or clear the filters to see the full library.</p><button type="button" data-clear-printer-search>Show all printers</button></div>'
    body += '<p class="pl-library-note">Specifications and prices retain their individual source dates. Build-volume text preserves catalog qualifiers; open a guide for the complete record and source links.</p></section>'
    body += '<aside class="pl-comparison-note"><div><span class="pl-eyebrow">Ready to look closer?</span><h2>Put the details side by side.</h2><p>Choose models, inspect the fields and compare the specifications that matter to your work.</p></div><a class="pl-comparison-link" href="../comparison.html">Open printer comparison <span aria-hidden="true">↗</span></a></aside></div>'
    return body
