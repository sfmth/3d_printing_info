"""Research articles use their own evidence, never catalog family scores."""
from html import escape
from pathlib import Path
import re
from check_articles import strict_load_json, validate_evidence

ROOT = Path(__file__).resolve().parents[1]
E = lambda value: escape(str(value), quote=True)


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


def measure_value(item):
    result = ('' if item['qualifier'] == '=' else item['qualifier']) + f"{item['value']:g}"
    if item['spread'] is not None:
        result += f" ± {item['spread']:g}"
    return result


def table_body(article, evidence):
    body = '<div class="table-scroll" role="region" aria-label="Grade measurements" tabindex="0"><table class="evidence-table"><caption>' + E(article['table']['caption']) + '</caption><thead><tr><th scope="col">Exact filament grade</th><th scope="col">Source orientation</th><th scope="col">Tensile modulus<br>MPa</th><th scope="col">Tensile yield strength<br>MPa</th><th scope="col">Test context</th></tr></thead><tbody>'
    for row in article['table']['rows']:
        modulus, strength = (evidence['measurements'][row[key]] for key in ('modulus', 'strength'))
        series = evidence['series'][modulus['series_id']]
        body += ('<tr data-measurement="' + E(row['modulus'] + ' ' + row['strength']) + '"><th scope="row">'
                 + E(series['grade']) + '</th><td>' + E(series['orientation']) + '</td><td>'
                 + E(measure_value(modulus)) + '<br>' + citation(evidence, row['modulus']) + '</td><td>'
                 + E(measure_value(strength)) + '<br>' + citation(evidence, row['strength']) + '</td><td>'
                 + E(series['test_standard']) + '<br>' + E(display(series['test_temperature']))
                 + '<br><a href="#series-' + E(modulus['series_id']) + '">Printing &amp; test conditions</a></td></tr>')
    return body + '</tbody></table></div>'


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
        body += '<details data-series="' + E(sid) + '" id="series-' + E(sid) + '"><summary>' + E(series['grade'] + ' · ' + series['orientation']) + '</summary><dl class="method-fields">'
        body += '<div><dt>Material identity</dt><dd>' + E(series['manufacturer'] + ' · ' + series['base_polymer'] + ' · filler: ' + display(series['filler'])) + '</dd></div>'
        for key, label in labels.items():
            body += '<div><dt>' + E(label) + '</dt><dd>' + E(display(series[key])) + '</dd></div>'
        for key, value in series['printing'].items():
            body += '<div><dt>' + E(key.replace('_', ' ').capitalize()) + '</dt><dd>' + E(display(value)) + '</dd></div>'
        body += '</dl></details>'
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
        body += E(source['publisher'] + ' · ' + source['kind'] + ' · document date: ' + display(source['document_date']) + ' · version: ' + display(source['version']) + ' · accessed ' + source['accessed'])
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
    body = '<div class="breadcrumbs"><a href="../">Home</a><span>/</span><a href="./">Selection articles</a><span>/</span><span>Mechanical performance</span></div><article><header class="article-header"><span class="kicker">Material selection · Mechanical performance</span><h1>' + E(article['title']) + '</h1><p class="article-deck">' + E(article['description']) + '</p><p class="article-byline">'
    body += E(article['author']['name']) + ' · Published <time datetime="' + E(article['published']) + '">' + E(article['published']) + '</time> · Revised <time datetime="' + E(article['modified']) + '">' + E(article['modified']) + '</time></p><p class="authorship-note">' + E(article['authorship_note']) + '</p></header>'
    body += '<nav class="article-contents" aria-label="On this page"><a href="#quick-answer">The selection decision</a><a href="#measurements">Grade measurements</a><a href="#methods">Test conditions</a><a href="#verification">Before releasing a part</a><a href="#sources">Sources</a></nav>'
    body += '<section class="quick-answer" id="quick-answer"><h2>' + E(article['answer']['heading']) + '</h2>' + ''.join(paragraph(b, evidence) for b in article['answer']['paragraphs']) + '</section>'
    for section in article['sections']:
        body += '<section id="' + E(section['id']) + '"><h2>' + E(section['title']) + '</h2>'
        body += ''.join(paragraph(b, evidence) for b in section.get('paragraphs', []))
        if section['id'] == 'measurements':
            body += table_body(article, evidence)
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
    body = '<header class="article-header"><span class="kicker">Engineering decisions</span><h1>Material selection articles</h1><p class="article-deck">Connect a part’s load and service conditions to specific filament grades, test evidence and the next verification step.</p></header><section id="mechanical-performance"><h2>Mechanical performance</h2><div class="article-index">'
    for article in data['articles']:
        body += '<a class="article-index-card" data-article-card href="' + E(article['id']) + '.html"><span class="kicker">' + E(article['category']) + '</span><h3>' + E(article['title']) + '</h3><p>' + E(article['description']) + '</p><span>Read the article ↗</span></a>'
    body += '</div></section><section id="service-environment"><h2>Service environment and further comparisons</h2><p>The research backlog covers structural composites; heat under load; conditioned nylon; outdoor exposure; creep and stress relaxation; and chemical exposure. These topics will be added as their grade-specific evidence is reviewed.</p></section><section><h2>Use the reference library</h2><p><a href="../materials/">Browse all material guides</a> for sourced properties and product records, or <a href="../filaments.html">open the filament comparison</a> to inspect the existing catalog.</p></section>'
    return body


def generate_articles(base, index, guide_page, material_ids):
    data, evidence = load_articles(), load_evidence()
    validate_evidence(evidence, data, material_ids)
    analytics = re.search(r'<!-- Google tag.*?</script>\s*<script>.*?</script>', index, re.S)[0]
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
