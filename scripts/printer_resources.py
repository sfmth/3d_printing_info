"""Model-specific ownership evidence, woven into the printer's technical chapters."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
E = lambda value: escape(str(value), quote=True)
CATEGORIES = ('firmware', 'printed_mods', 'hardware_mods', 'issues')
LABELS = {'firmware': 'Firmware & software', 'printed_mods': 'Printable modification',
          'hardware_mods': 'Hardware & upgrades', 'issues': 'Problems & troubleshooting'}
EVIDENCE = {'maintainer documentation', 'manufacturer documentation', 'creator listing',
            'owner report', 'official troubleshooting'}


def review_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Missing source review date')
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError('Invalid review date: ' + value) from error


def validate_resources(models, expected_ids=None):
    if not isinstance(models, dict):
        raise ValueError('Printer resources must be an object')
    if expected_ids is not None and set(models) != set(expected_ids):
        raise ValueError('Printer resource coverage differs from catalog: ' + str(sorted(set(models) ^ set(expected_ids))))
    for printer_id, record in models.items():
        if not isinstance(printer_id, str) or not re.fullmatch(r'[a-z0-9-]+', printer_id):
            raise ValueError('Invalid printer resource ID: ' + str(printer_id))
        if not isinstance(record, dict) or set(record) != {*CATEGORIES, 'reviewed_sources'}:
            raise ValueError('Incomplete resource categories: ' + printer_id)
        if not isinstance(record['reviewed_sources'], list) or not record['reviewed_sources']:
            raise ValueError('Missing model review sources: ' + printer_id)
        for category in CATEGORIES:
            if not isinstance(record[category], list):
                raise ValueError('Resource category must be a list: ' + printer_id)
            for entry in record[category]:
                required = {'title', 'summary', 'compatibility', 'evidence', 'sources'}
                if not isinstance(entry, dict) or not required <= set(entry) or set(entry) - required - {'section'}:
                    raise ValueError('Incomplete resource entry: ' + printer_id)
                if any(not isinstance(entry[key], str) or not entry[key].strip() for key in ('title', 'summary', 'compatibility')):
                    raise ValueError('Missing resource context: ' + printer_id)
                if len(entry['summary'].split()) > 70:
                    raise ValueError('Resource summary exceeds 70 words: ' + printer_id)
                if not isinstance(entry['evidence'], str) or entry['evidence'] not in EVIDENCE or not isinstance(entry['sources'], list) or not entry['sources']:
                    raise ValueError('Missing resource evidence: ' + printer_id)
                if 'section' in entry and (not isinstance(entry['section'], str) or not re.fullmatch(r'[A-W]', entry['section'])):
                    raise ValueError('Unknown technical section: ' + printer_id)
        sources = [*record['reviewed_sources'], *(source for category in CATEGORIES for entry in record[category] for source in entry['sources'])]
        for source in sources:
            if not isinstance(source, dict) or set(source) != {'title', 'url', 'checked'} or not isinstance(source['title'], str) or not source['title'].strip():
                raise ValueError('Incomplete source provenance: ' + printer_id)
            if not isinstance(source['url'], str):
                raise ValueError('Invalid source URL: ' + printer_id)
            parsed = urlsplit(source['url'])
            if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or any(character.isspace() for character in source['url']):
                raise ValueError('Invalid source URL: ' + printer_id)
            review_date(source['checked'])


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate printer resource JSON key: ' + key)
        result[key] = value
    return result


def load_resources(folder=None, expected_ids=None):
    models = {}
    for path in sorted((folder or ROOT/'data').glob('printer-resources-*.json')):
        document = json.loads(path.read_text(), object_pairs_hook=unique_keys)
        if not isinstance(document, dict) or set(document) != {'version', 'checked', 'models'} or type(document['version']) is not int or document['version'] != 1:
            raise ValueError('Unknown printer resource schema: ' + str(path))
        review_date(document['checked'])
        if not isinstance(document['models'], dict):
            raise ValueError('Printer resources must be an object: ' + str(path))
        duplicates = models.keys() & document['models'].keys()
        if duplicates:
            raise ValueError('Duplicate printer resource records: ' + str(sorted(duplicates)))
        validate_resources(document['models'])
        for record in document['models'].values():
            sources = [*record['reviewed_sources'], *(source for category in CATEGORIES for entry in record[category] for source in entry['sources'])]
            if any(source['checked'] > document['checked'] for source in sources):
                raise ValueError('Source reviewed after resource document: ' + str(path))
        models.update(document['models'])
    validate_resources(models, expected_ids)
    return models


def section_for(category, entry):
    """Editorial section tags take precedence; conservative defaults avoid false links."""
    return entry.get('section') or {'firmware': 'N', 'printed_mods': 'B', 'hardware_mods': 'B', 'issues': 'U'}[category]


def entries_for(record, section_ids):
    # Problems appear before modifications: establish the symptom before an optional change.
    return [(category, entry) for category in ('issues', 'firmware', 'printed_mods', 'hardware_mods')
            for entry in record.get(category, []) if section_for(category, entry) in section_ids]


def chapter_context(record, section_ids):
    entries = entries_for(record, section_ids)
    if not entries:
        return ''
    body = '<div class="printer-chapter-context">'
    for category, entry in entries:
        body += '<article class="printer-context-note" data-resource-kind="' + category + '" data-resource-section="' + section_for(category, entry) + '">'
        body += '<span class="printer-context-label">' + LABELS[category] + '</span><h4>' + E(entry['title']) + '</h4><p>' + E(entry['summary']) + '</p>'
        body += '<p class="printer-resource-compatibility"><strong>Applies to:</strong> ' + E(entry['compatibility']) + '</p>'
        body += '<details class="printer-resource-evidence"><summary>' + E(entry['evidence'].capitalize()) + ' <span aria-hidden="true">·</span> Sources & dates</summary><ul>'
        for source in entry['sources']:
            body += '<li><a href="' + E(source['url']) + '">' + E(source['title']) + ' <span aria-hidden="true">↗</span></a> · Checked ' + E(source['checked']) + '</li>'
        body += '</ul></details></article>'
    return body + '</div>'


def review_notes(record):
    missing = [label for key, label in [('firmware', 'firmware customization or update guidance'), ('printed_mods', 'printable modifications'),
                                       ('hardware_mods', 'hardware upgrades'), ('issues', 'model-specific diagnostics or fault reports')]
               if not record[key]]
    body = '<details class="printer-resource-review"><summary>Ownership research & coverage</summary><p>Firmware, modifications and troubleshooting links are checked against the model and stated hardware or firmware revision. A creator’s compatibility claim is not a fit test by this site. Official troubleshooting describes a diagnostic route; individual reports do not establish a failure rate.</p>'
    if missing:
        body += '<p>This review did not verify ' + E(', '.join(missing)) + ' for this exact model. That is a research gap, not a claim that none exist.</p>'
    body += '<ul>'
    for source in record['reviewed_sources']:
        body += '<li><a href="' + E(source['url']) + '">' + E(source['title']) + '</a> · Checked ' + E(source['checked']) + '</li>'
    return body + '</ul></details>'


def source_urls(record):
    return list(dict.fromkeys(source['url'] for category in CATEGORIES for entry in record.get(category, []) for source in entry['sources']))
