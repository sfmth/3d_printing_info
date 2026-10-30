"""Research articles use their own evidence, never catalog family scores."""
from html import escape
from pathlib import Path
import re
from check_articles import strict_load_json, validate_evidence

ROOT = Path(__file__).resolve().parents[1]
E = lambda value: escape(str(value), quote=True)
DETAIL_CONTEXT_FIELDS = {'recommended_filament_drying', 'recommended_chamber', 'orientation_support',
                         'specimen_settings_scope', 'dry_status_definition', 'annealing', 'thermal_state',
                         'filler_status', 'annealing_temperature_c', 'annealing_duration_h',
                         'uptake_condition_is_separate', 'strength_endpoint'}


def load_articles():
    return strict_load_json(ROOT / 'data/material-articles.json')


def load_evidence():
    return strict_load_json(ROOT / 'data/article-evidence.json')


def article_links(material_id):
    articles = [a for a in load_articles()['articles'] if material_id in a['materials']]
    if not articles:
        return ''
    return ('<section class="guide-section" id="selection-articles"><div class="section-heading">'
            '<h2>Material selection articles</h2></div><p class="section-description">'
            'Compare specific grades and connect test results to part design.</p><ul>'
            + ''.join('<li><a href="../articles/' + E(a['id']) + '.html">' + E(a['title']) + '</a></li>' for a in articles)
            + '</ul></section>')


def citation(evidence, ref):
    """Keep the primary source adjacent; link the full evidence record separately."""
    item = evidence['claims'].get(ref) or evidence['measurements'].get(ref)
    source_id = item.get('source_id') or evidence['series'][item['series_id']]['source_id']
    source = evidence['sources'][source_id]
    locator = item['locator']
    return ('<span class="citation"><a class="claim-citation" href="' + E(source['url']) + '" title="'
            + E(locator) + '">' + E(source['publisher']) + '</a> '
            '<a class="evidence-link" href="#evidence-' + E(ref) + '" aria-label="Evidence record: '
            + E(ref) + '">[details]</a></span>')


def paragraph(block, evidence):
    refs = block.get('refs', [])
    label = '<strong>Engineering interpretation.</strong> ' if block.get('kind') == 'interpretation' else ''
    return ('<p' + (' data-evidence-refs="' + E(' '.join(refs)) + '"' if refs else '') + '>'
            + label + E(block['text']) + (' <span class="citations">' + ' · '.join(citation(evidence, ref) for ref in refs) + '</span>' if refs else '') + '</p>')


def display(value):
    return 'Not reported' if value is None else str(value)


def source_kind(source):
    return source['kind'].replace('-', ' ').capitalize()


def measure_value(item):
    result = ('' if item['qualifier'] == '=' else item['qualifier']) + f"{item['value']:g}"
    if item['spread'] is not None:
        result += f" ± {item['spread']:g}"
    return result


def table_body(article, evidence):
    if 'tables' in article:
        return ''.join(comparison_table(table, evidence) for table in article['tables'])
    body = '<div class="table-scroll" role="region" aria-label="Grade measurements" tabindex="0"><table class="evidence-table"><caption>' + E(article['table']['caption']) + '</caption><thead><tr><th scope="col">Exact filament grade</th><th scope="col">Source orientation</th><th scope="col">Tensile modulus<br>MPa</th><th scope="col">Tensile yield strength<br>MPa</th><th scope="col">Test context</th></tr></thead><tbody>'
    for row in article['table']['rows']:
        modulus, strength = (evidence['measurements'][row[key]] for key in ('modulus', 'strength'))
        series = evidence['series'][modulus['series_id']]
        body += ('<tr data-measurement="' + E(row['modulus'] + ' ' + row['strength']) + '"><th scope="row">'
                 + E(series['grade']) + '</th><td>' + E(display(series['orientation'])) + '</td><td>'
                 + E(measure_value(modulus)) + '<br>' + citation(evidence, row['modulus']) + '</td><td>'
                 + E(measure_value(strength)) + '<br>' + citation(evidence, row['strength']) + '</td><td>'
                 + E(series['test_standard']) + '<br>' + E(display(series['test_temperature']))
                 + '<br><a href="#series-' + E(modulus['series_id']) + '">Printing &amp; test conditions</a></td></tr>')
    return body + '</tbody></table></div>'


def context_label(key):
    for suffix, unit in (('_percent', '%'), ('_temperature_c', '°C'), ('_duration_h', 'h')):
        if key.endswith(suffix):
            return key[:-len(suffix)].replace('_', ' ').capitalize() + (' temperature' if suffix == '_temperature_c' else ' duration' if suffix == '_duration_h' else '') + ' (' + unit + ')'
    return key.replace('_', ' ').capitalize()


def comparison_table(table, evidence):
    if table.get('kind') == 'observations':
        return observation_table(table, evidence)
    body = '<div class="comparison-group" id="table-' + E(table['id']) + '"><h3>' + E(table['title']) + '</h3>'
    caption_id = 'table-' + table['id'] + '-caption'
    body += '<p class="comparison-caption" id="' + E(caption_id) + '">' + E(table['caption']) + '</p>'
    body += '<div class="table-scroll" role="region" aria-label="' + E(table['title']) + '" tabindex="0"><table class="evidence-table" aria-label="' + E(table['title']) + '" aria-describedby="' + E(caption_id) + '" data-evidence-table="' + E(table['id']) + '"><thead><tr><th scope="col">Exact grade &amp; process</th><th scope="col">Orientation &amp; specimen state</th>'
    body += ''.join('<th scope="col">' + E(column['label']) + '<br>' + E(column['unit']) + '</th>' for column in table['columns'])
    body += '<th scope="col">Test conditions &amp; source</th></tr></thead><tbody>'
    for row in table['rows']:
        sid = row['series_id']; series = evidence['series'][sid]
        source = evidence['sources'][series['source_id']]
        refs = [ref for ref in row['values'].values() if ref is not None]
        body += '<tr data-measurement="' + E(' '.join(refs)) + '" data-test-series="' + E(sid) + '"><th scope="row">' + E(series['grade']) + '<span class="result-context">' + E(series['process'] + ' · ' + source_kind(source)) + '</span></th><td>'
        body += E(display(series['orientation'])) + '<span class="result-context">Conditioning: ' + E(display(series['conditioning'])) + '</span><span class="result-context">Post-processing: ' + E(display(series['post_processing'])) + '</span></td>'
        for column in table['columns']:
            ref = row['values'][column['key']]
            if ref is None:
                body += '<td class="evidence-gap">Not reported</td>'
            else:
                item = evidence['measurements'][ref]
                body += '<td data-result="' + E(ref) + '">' + E(measure_value(item)) + '<br>' + citation(evidence, ref) + '</td>'
        body += '<td><strong>' + E(series['test_standard']) + '</strong><span class="result-context">Test temperature: ' + E(display(series['test_temperature'])) + '</span>'
        for key, value in series.get('context', {}).items():
            if key in DETAIL_CONTEXT_FIELDS:
                continue
            body += '<span class="result-context">' + E(context_label(key) + ': ' + display(value)) + '</span>'
        body += '<a href="#series-' + E(sid) + '">Specimen &amp; processing details</a></td></tr>'
    body += '</tbody></table></div>'
    body += ''.join(paragraph(block, evidence) for block in table['notes'])
    return body + '</div>'


def observation_table(table, evidence):
    """Retain categorical source findings without converting them to scores."""
    tid = table['id']; caption_id = 'table-' + tid + '-caption'
    body = '<div class="comparison-group" id="table-' + E(tid) + '"><h3>' + E(table['title']) + '</h3>'
    body += '<p class="comparison-caption" id="' + E(caption_id) + '">' + E(table['caption']) + '</p>'
    body += '<div class="table-scroll" role="region" aria-label="' + E(table['title']) + '" tabindex="0"><table class="evidence-table observation-table" aria-label="' + E(table['title']) + '" aria-describedby="' + E(caption_id) + '" data-evidence-table="' + E(tid) + '"><thead><tr><th scope="col">Grade, process &amp; evidence</th><th scope="col">Exposure conditions</th><th scope="col">Reported observation &amp; boundary</th></tr></thead><tbody>'
    for row in table['rows']:
        source = evidence['sources'][evidence['claims'][row['refs'][0]]['source_id']]
        body += '<tr data-observation="' + E(row['id']) + '"><th scope="row">' + E(row['grade'])
        for label, value in (('Process', row['process']), ('Orientation', row['orientation']), ('Conditioning', row['conditioning'])):
            body += '<span class="result-context">' + E(label + ': ' + display(value)) + '</span>'
        body += '<span class="result-context">' + E(source_kind(source)) + '</span></th><td>'
        for key, value in row['exposure'].items():
            body += '<span class="result-context">' + E(context_label(key) + ': ' + display(value)) + '</span>'
        body += '</td><td>' + E(row['observation']) + '<br>' + ' · '.join(citation(evidence, ref) for ref in row['refs']) + '</td></tr>'
    body += '</tbody></table></div>' + ''.join(paragraph(block, evidence) for block in table['notes'])
    return body + '</div>'


def method_records(article, evidence):
    used = {evidence['measurements'][ref]['series_id'] for ref in article['measurements']}
    body = '<div class="method-records">'
    labels = {'process': 'Process', 'orientation': 'Source orientation', 'specimen_geometry': 'Specimen geometry',
              'test_standard': 'Test method', 'test_rate': 'Test rate', 'test_temperature': 'Test temperature',
              'conditioning': 'Specimen conditioning', 'printer': 'Printer', 'post_processing': 'Post-processing',
              'sample_count': 'Sample count', 'scatter_definition': 'Meaning of ±', 'locator': 'Source locator'}
    for sid, series in evidence['series'].items():
        if sid not in used:
            continue
        body += '<details data-series="' + E(sid) + '"><summary>' + E(series['grade'] + ' · ' + display(series['orientation'])) + '</summary><div id="series-' + E(sid) + '"><dl class="method-fields">'
        body += '<div><dt>Material identity</dt><dd>' + E(series['manufacturer'] + ' · ' + series['base_polymer'] + ' · filler: ' + display(series['filler'])) + '</dd></div>'
        for key, label in labels.items():
            body += '<div><dt>' + E(label) + '</dt><dd>' + E(display(series[key])) + '</dd></div>'
        for key, value in series['printing'].items():
            body += '<div><dt>' + E(key.replace('_', ' ').capitalize()) + '</dt><dd>' + E(display(value)) + '</dd></div>'
        for key, value in series.get('context', {}).items():
            body += '<div><dt>' + E(context_label(key)) + '</dt><dd>' + E(display(value)) + '</dd></div>'
        body += '</dl></div></details>'
    return body + '</div>'


def source_records(article, evidence):
    refs = [*article['measurements'], *article['claims']]
    source_ids = set()
    body = '<section id="sources"><h2>Sources and evidence records</h2><p>These records distinguish supplier tests, independent experiments and engineering interpretation. “Not reported” identifies a source gap; it is not an assumed test condition.</p><ol class="article-sources">'
    for ref in refs:
        item = evidence['claims'].get(ref) or evidence['measurements'].get(ref)
        source_ids.add(item.get('source_id') or evidence['series'][item['series_id']]['source_id'])
    for sid, source in evidence['sources'].items():
        if sid not in source_ids:
            continue
        body += '<li data-source="' + E(sid) + '" id="source-' + E(sid) + '"><a href="' + E(source['url']) + '">' + E(source['title']) + '</a><p>'
        body += E(source['publisher'] + ' · ' + source_kind(source) + ' · document date: ' + display(source['document_date']) + ' · version: ' + display(source['version']) + ' · accessed ' + source['accessed'])
        if source['authors']:
            body += '<br>' + E(', '.join(source['authors']))
        body += '</p><p>' + E(source['scope']) + '</p></li>'
    body += '</ol><details class="evidence-register"><summary>Read individual measurement and claim records</summary><dl>'
    for ref in refs:
        item = evidence['claims'].get(ref) or evidence['measurements'].get(ref)
        body += '<div id="evidence-' + E(ref) + '"><dt>' + E(ref.replace('-', ' ')) + '</dt><dd>'
        if 'series_id' in item:
            body += E(item['definition'] + ': ' + measure_value(item) + ' ' + item['unit']) + '. '
        body += E(item['finding']) + '<br><span class="source-note">' + E(item['locator']) + '</span> ' + citation(evidence, ref) + '</dd></div>'
    return body + '</dl></details></section>'


def article_body(article, evidence):
    body = '<div class="breadcrumbs"><a href="../">Home</a><span>/</span><a href="./">Selection articles</a><span>/</span><span>' + E(article['category']) + '</span></div><article><header class="article-header"><span class="kicker">Material selection · ' + E(article['category']) + '</span><h1>' + E(article['title']) + '</h1><p class="article-deck">' + E(article['description']) + '</p><p class="article-byline">'
    body += E(article['author']['name']) + ' · Published <time datetime="' + E(article['published']) + '">' + E(article['published']) + '</time> · Revised <time datetime="' + E(article['modified']) + '">' + E(article['modified']) + '</time></p><p class="authorship-note">' + E(article['authorship_note']) + '</p></header>'
    body += '<nav class="article-contents" aria-label="On this page"><a href="#quick-answer">The selection decision</a><a href="#measurements">Grade measurements</a><a href="#methods">Test conditions</a><a href="#verification">Before releasing a part</a><a href="#sources">Sources</a></nav>'
    body += '<section class="quick-answer" id="quick-answer"><h2>' + E(article['answer']['heading']) + '</h2>' + ''.join(paragraph(b, evidence) for b in article['answer']['paragraphs']) + '</section>'
    for section in article['sections']:
        body += '<section id="' + E(section['id']) + '"><h2>' + E(section['title']) + '</h2>'
        body += ''.join(paragraph(b, evidence) for b in section.get('paragraphs', []))
        if section['id'] == 'measurements':
            body += table_body(article, evidence)
            if 'table' in article:
                body += ''.join(paragraph(b, evidence) for b in article['table']['notes'])
        if section['id'] == 'methods':
            body += method_records(article, evidence)
        if section.get('items'):
            body += '<ol class="verification-list">' + ''.join('<li>' + paragraph(b, evidence) + '</li>' for b in section['items']) + '</ol>'
        body += '</section>'
    body += '<section id="related-materials"><h2>Explore the candidate grades</h2><p>Use the reference guides to find settings and individual product sources, then check the exact grade against the evidence above.</p><ul class="article-material-links">'
    body += ''.join('<li><a href="../materials/' + E(cid) + '.html">' + E(label) + ' material guide</a></li>' for cid, label in article['materials'].items())
    body += '</ul><a href="../filaments.html">Open the interactive filament comparison</a></section>'
    return body + source_records(article, evidence) + '</article>'


def index_body(data):
    body = '<header class="article-header"><span class="kicker">Engineering decisions</span><h1>Material selection articles</h1><p class="article-deck">Connect a part’s load and service conditions to specific filament grades, test evidence and the next verification step.</p></header>'
    groups = dict.fromkeys(article['category'] for article in data['articles'])
    for category in groups:
        section_id = re.sub(r'[^a-z0-9]+', '-', category.lower()).strip('-')
        body += '<section id="' + E(section_id) + '"><h2>' + E(category) + '</h2><div class="article-index">'
        for article in data['articles']:
            if article['category'] != category:
                continue
            body += '<a class="article-index-card" data-article-card href="' + E(article['id']) + '.html"><span class="kicker">' + E(article['category']) + '</span><h3>' + E(article['title']) + '</h3><p>' + E(article['description']) + '</p><span>Read the article ↗</span></a>'
        body += '</div></section>'
    if data.get('backlog'):
        body += '<section id="research-backlog"><h2>Further comparisons</h2><p>Research continues on ' + E('; '.join(data['backlog'])) + '. New articles follow review of their grade-specific evidence.</p></section>'
    body += '<section><h2>Use the reference library</h2><p><a href="../materials/">Browse all material guides</a> for sourced properties and product records, or <a href="../filaments.html">open the filament comparison</a> to inspect the existing catalog.</p></section>'
    return body


def generate_articles(base, index, guide_page, material_ids):
    data, evidence = load_articles(), load_evidence()
    validate_evidence(evidence, data, material_ids)
    analytics = ''  # guide_page supplies the local consent gate.
    folder = ROOT / 'articles'
    folder.mkdir(exist_ok=True)
    paths = []
    for article in data['articles']:
        path = 'articles/' + article['id'] + '.html'
        refs = [*article['measurements'], *article['claims']]
        source_ids = {(evidence['claims'].get(ref) or evidence['series'][evidence['measurements'][ref]['series_id']])['source_id'] for ref in refs}
        schema = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': article['title'], 'url': base + path,
                  'description': article['description'], 'mainEntity': {'@type': 'TechArticle', 'headline': article['title'],
                  'url': base + path, 'description': article['description'], 'author': article['author'],
                  'datePublished': article['published'], 'dateModified': article['modified'],
                  'about': list(article['materials'].values()), 'citation': [s['url'] for sid, s in evidence['sources'].items() if sid in source_ids]}}
        html = guide_page(article['title'], article['description'], path, article_body(article, evidence), analytics, '', schema)
        html = re.sub(r'Catalog values retain their original source dates\. Page revision: [\d-]+\.',
                      'Article revision: ' + article['modified'] + '. Measurements retain their source dates.', html)
        (ROOT / path).write_text(html)
        paths.append(path)
    path = 'articles/index.html'
    schema = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': 'Material selection articles', 'url': base + 'articles/',
              'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(paths), 'itemListElement': [
                  {'@type': 'ListItem', 'position': i, 'name': a['title'], 'url': base + 'articles/' + a['id'] + '.html'}
                  for i, a in enumerate(data['articles'], 1)]}}
    html = guide_page('Material selection articles', 'Evidence-led FDM material comparisons for mechanical performance and service environments.', path, index_body(data), analytics, '', schema)
    latest = max(a['modified'] for a in data['articles'])
    html = re.sub(r'Catalog values retain their original source dates\. Page revision: [\d-]+\.', 'Article library revision: ' + latest + '.', html)
    (ROOT / path).write_text(html)
    expected = {Path(p).name for p in paths} | {'index.html'}
    for existing in folder.glob('*.html'):
        if existing.name not in expected:
            raise ValueError('Unexpected article page: ' + str(existing))
    return ['articles/', *paths]
