"""Validate article evidence before it reaches the HTML renderer.

This checks provenance and compatibility, not whether a source's experiment is
correct. Unknown test conditions must be explicit JSON nulls, not assumptions.
"""
from datetime import date
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit


SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
PROPERTY = re.compile(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z')
UNKNOWN = {'unknown', 'unspecified', 'not reported', 'n/a', 'na', 'none', '-'}
SERIES_FIELDS = {
    'source_id', 'grade', 'manufacturer', 'material_id', 'base_polymer', 'filler',
    'process', 'orientation', 'specimen_geometry', 'test_standard', 'test_rate',
    'test_temperature', 'conditioning', 'printer', 'printing', 'post_processing',
    'sample_count', 'scatter_definition', 'locator',
}
PRINTING_FIELDS = {
    'layer_height', 'infill', 'perimeters', 'nozzle_temperature',
    'bed_temperature', 'chamber_temperature', 'slicer', 'infill_print_speed',
    'top_bottom_solid_layers', 'specimen_cooling', 'extrusion_multiplier',
}
PROCESSES = {
    'FFF', 'FDM', 'MEX', 'SLS', 'SLA', 'DLP', 'MJF', 'material extrusion',
    'injection molding', 'compression molding', 'extrusion', 'casting',
}
QUALIFIERS = {'=', '>', '>=', '<', '<=', '≥', '≤', '≈', '~'}


def _fail(where, message):
    raise ValueError(f'{where}: {message}')


def _object(value, where):
    if not isinstance(value, dict):
        _fail(where, 'expected an object')
    return value


def _required(value, keys, where, *, exact=False):
    _object(value, where)
    missing = set(keys) - value.keys()
    if missing:
        _fail(where, 'missing fields: ' + ', '.join(sorted(missing)))
    if exact and (extra := value.keys() - set(keys)):
        _fail(where, 'unknown fields: ' + ', '.join(sorted(extra)))


def _text(value, where, *, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        _fail(where, 'expected nonempty text' + (' or null' if nullable else ''))
    if value.strip().lower() in UNKNOWN:
        _fail(where, 'unknown values must be null')


def _slug(value, where):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        _fail(where, 'expected a safe lowercase hyphenated ID')


def _date(value, where, *, nullable=False):
    if nullable and value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        _fail(where, 'expected an ISO YYYY-MM-DD date')
    if parsed.isoformat() != value:
        _fail(where, 'expected an ISO YYYY-MM-DD date')
    return parsed


def _https(value, where):
    _text(value, where)
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname and
                 not parsed.username and not parsed.password and not any(c.isspace() for c in value))
    except ValueError:
        valid = False
    if not valid:
        _fail(where, 'expected a public HTTPS URL without credentials')


def _number(value, where, *, minimum=None):
    try:
        finite = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        _fail(where, 'expected a finite number')
    if minimum is not None and value < minimum:
        _fail(where, f'must be at least {minimum}')


def _ids(value, where):
    if not isinstance(value, list):
        _fail(where, 'expected an ID list')
    for item in value:
        _slug(item, where)
    if len(set(value)) != len(value):
        _fail(where, 'duplicate reference')
    return set(value)


def strict_load_json(path):
    """Reject duplicate JSON keys and nonstandard NaN/Infinity literals."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail(str(path), f'duplicate JSON key {key!r}')
            result[key] = value
        return result

    def constant(value):
        _fail(str(path), f'nonfinite JSON number {value}')

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)


def validate_evidence(evidence, articles, material_ids):
    """Raise ValueError for incomplete provenance or incompatible article data.

    Accept the material-articles document or its articles list. The function is
    read-only; it never fills missing conditions or rewrites bound qualifiers.
    """
    _required(evidence, {'schema_version', 'sources', 'series', 'measurements', 'claims'}, 'evidence')
    if evidence['schema_version'] != 1 or isinstance(evidence['schema_version'], bool):
        _fail('evidence', 'unsupported schema_version')
    sources, series, measurements, claims = (
        _object(evidence[key], key) for key in ('sources', 'series', 'measurements', 'claims'))
    known_materials = set(material_ids)
    for group, records in (('sources', sources), ('series', series), ('measurements', measurements), ('claims', claims)):
        for rid in records:
            _slug(rid, group)
    if measurements.keys() & claims.keys():
        _fail('evidence', 'measurement and claim IDs must be distinct')

    for sid, source in sources.items():
        where = f'source {sid}'
        _required(source, {'title', 'publisher', 'authors', 'url', 'document_date', 'version', 'accessed', 'kind', 'scope'}, where)
        for key in ('title', 'publisher', 'kind', 'scope'):
            _text(source[key], f'{where}.{key}')
        _https(source['url'], f'{where}.url')
        published = _date(source['document_date'], f'{where}.document_date', nullable=True)
        accessed = _date(source['accessed'], f'{where}.accessed')
        if published and published > accessed:
            _fail(where, 'document date is later than access date')
        _text(source['version'], f'{where}.version', nullable=True)
        if not isinstance(source['authors'], list):
            _fail(where, 'authors must be a list')
        for author in source['authors']:
            _text(author, f'{where}.authors')

    for sid, item in series.items():
        where = f'series {sid}'
        _required(item, SERIES_FIELDS, where, exact=True)
        for key in ('source_id', 'grade', 'manufacturer', 'material_id', 'base_polymer', 'process', 'orientation', 'test_standard', 'locator'):
            _text(item[key], f'{where}.{key}')
        if item['source_id'] not in sources:
            _fail(where, 'unknown source_id')
        if item['material_id'] not in known_materials:
            _fail(where, 'unknown material_id')
        if item['grade'].strip().lower() == item['base_polymer'].strip().lower():
            _fail(where, 'grade must identify the actual commercial/test material')
        if item['process'] not in PROCESSES:
            _fail(where, 'process must identify a known fabrication process')
        for key in ('filler', 'specimen_geometry', 'test_rate', 'test_temperature', 'conditioning', 'printer', 'post_processing', 'scatter_definition'):
            _text(item[key], f'{where}.{key}', nullable=True)
        if item['sample_count'] is not None:
            if type(item['sample_count']) is not int or item['sample_count'] < 1:
                _fail(where, 'sample_count must be a positive integer or null')
        _required(item['printing'], PRINTING_FIELDS, f'{where}.printing', exact=True)
        for key, value in item['printing'].items():
            field = f'{where}.printing.{key}'
            if value is None:
                continue
            if isinstance(value, str):
                _text(value, field)
            else:
                _number(value, field, minimum=0)

    for mid, item in measurements.items():
        where = f'measurement {mid}'
        _required(item, {'series_id', 'property', 'definition', 'unit', 'value', 'qualifier', 'spread', 'locator', 'finding'}, where, exact=True)
        _text(item['series_id'], f'{where}.series_id')
        if item['series_id'] not in series:
            _fail(where, 'unknown series_id')
        for key in ('definition', 'unit', 'locator', 'finding'):
            _text(item[key], f'{where}.{key}')
        if not isinstance(item['property'], str) or not PROPERTY.fullmatch(item['property']):
            _fail(where, 'property must be a defined property ID')
        _number(item['value'], f'{where}.value')
        if not isinstance(item['qualifier'], str) or item['qualifier'] not in QUALIFIERS:
            _fail(where, 'unknown or missing bound qualifier')
        if item['spread'] is not None:
            _number(item['spread'], f'{where}.spread', minimum=0)
            if item['qualifier'] not in {'=', '≈', '~'}:
                _fail(where, 'a bound cannot carry an exact-value spread')
        test_series = series[item['series_id']]
        scope = sources[test_series['source_id']]['scope']
        if (test_series['scatter_definition'] is not None and
                re.search(r'(?:statistical meaning[^.]*unspecified|unspecified[^.]*statistical|no[^.]*definition[^.]*plus/minus)', scope + ' ' + item['finding'], re.I)):
            _fail(where, 'unspecified plus/minus cannot be assigned a statistical definition')

    for cid, item in claims.items():
        where = f'claim {cid}'
        _required(item, {'source_id', 'locator', 'finding'}, where, exact=True)
        _text(item['source_id'], f'{where}.source_id')
        if item['source_id'] not in sources:
            _fail(where, 'unknown source_id')
        _text(item['locator'], f'{where}.locator')
        _text(item['finding'], f'{where}.finding')

    if isinstance(articles, dict):
        _required(articles, {'articles'}, 'articles')
        articles = articles['articles']
    if not isinstance(articles, list) or not articles:
        _fail('articles', 'expected a nonempty article list')
    article_ids = set()
    for article in articles:
        _required(article, {'id', 'title', 'description', 'category', 'author', 'authorship_note',
                            'published', 'modified', 'materials', 'answer', 'sections', 'table',
                            'measurements', 'claims'}, 'article')
        aid = article['id']
        _slug(aid, 'article.id')
        where = f'article {aid}'
        if aid in article_ids:
            _fail(where, 'duplicate article ID')
        article_ids.add(aid)
        for key in ('title', 'description', 'category', 'authorship_note'):
            _text(article[key], f'{where}.{key}')
        published = _date(article['published'], f'{where}.published')
        modified = _date(article['modified'], f'{where}.modified')
        if modified < published:
            _fail(where, 'modified date precedes published date')
        author = article['author']
        _required(author, {'@type', 'name'}, f'{where}.author')
        if not isinstance(author['@type'], str) or author['@type'] not in {'Person', 'Organization'}:
            _fail(where, 'author must be a Person or Organization')
        _text(author['name'], f'{where}.author.name')
        if author['name'].strip().lower() in {'author', 'editorial team', 'staff', 'tbd', 'placeholder'}:
            _fail(where, 'author must identify a named person or organization')
        materials = _object(article['materials'], f'{where}.materials')
        if not materials or not materials.keys() <= known_materials:
            _fail(where, 'unknown or missing article material')
        for label in materials.values():
            _text(label, f'{where}.materials')
        declared_measurements = _ids(article['measurements'], f'{where}.measurements')
        declared_claims = _ids(article['claims'], f'{where}.claims')
        if not declared_measurements <= measurements.keys() or not declared_claims <= claims.keys():
            _fail(where, 'declared evidence does not exist')
        declared = declared_measurements | declared_claims
        used = set()

        def blocks(value, context):
            if not isinstance(value, list):
                _fail(context, 'expected a paragraph/item list')
            for block in value:
                _required(block, {'text'}, context)
                _text(block['text'], f'{context}.text')
                refs = _ids(block.get('refs', []), f'{context}.refs')
                if not refs <= declared:
                    _fail(context, 'used evidence is not declared by article')
                used.update(refs)

        _required(article['answer'], {'heading', 'paragraphs'}, f'{where}.answer')
        _text(article['answer']['heading'], f'{where}.answer.heading')
        blocks(article['answer']['paragraphs'], f'{where}.answer')
        if not isinstance(article['sections'], list):
            _fail(where, 'sections must be a list')
        section_ids = {'quick-answer', 'sources', 'related-materials'}
        actual_sections = set()
        for section in article['sections']:
            _required(section, {'id', 'title'}, f'{where}.section')
            _slug(section['id'], f'{where}.section.id')
            if section['id'] in section_ids:
                _fail(where, 'duplicate or reserved section ID')
            section_ids.add(section['id'])
            actual_sections.add(section['id'])
            _text(section['title'], f'{where}.section.title')
            blocks(section.get('paragraphs', []), f'{where}.{section["id"]}')
            blocks(section.get('items', []), f'{where}.{section["id"]}.items')
        if not {'methods', 'measurements', 'verification'} <= actual_sections:
            _fail(where, 'required methods, measurements and verification sections missing')
        table = article['table']
        _required(table, {'caption', 'rows', 'notes'}, f'{where}.table')
        _text(table['caption'], f'{where}.table.caption')
        blocks(table['notes'], f'{where}.table.notes')
        if not isinstance(table['rows'], list) or not table['rows']:
            _fail(where, 'measurement table needs rows')
        pairs = set()
        for row in table['rows']:
            _required(row, {'modulus', 'strength'}, f'{where}.table.row', exact=True)
            pair = (row['modulus'], row['strength'])
            for key, expected in (('modulus', 'tensile_modulus'), ('strength', 'tensile_yield_strength')):
                ref = row[key]
                if not isinstance(ref, str) or ref not in declared_measurements:
                    _fail(where, 'table measurement is missing or undeclared')
                measurement = measurements[ref]
                if measurement['property'] != expected or measurement['unit'] != 'MPa':
                    _fail(where, f'table {key} requires {expected} in MPa')
                used.add(ref)
            if pair in pairs:
                _fail(where, 'duplicate table row')
            pairs.add(pair)
            modulus, strength = (measurements[ref] for ref in pair)
            if modulus['series_id'] != strength['series_id']:
                _fail(where, 'table row combines incompatible test series')
            test_series = series[modulus['series_id']]
            if test_series['material_id'] not in materials:
                _fail(where, 'table material is outside article scope')
            if test_series['process'] not in {'FFF', 'FDM', 'MEX', 'material extrusion'}:
                _fail(where, 'FDM comparison table requires material-extrusion specimens')
        if used != declared:
            _fail(where, 'unused declared evidence: ' + ', '.join(sorted(declared - used)))
