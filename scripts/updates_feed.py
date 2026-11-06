"""Generate a curated updates archive and deterministic RSS/Atom feeds.

Dates and stable entry IDs come from data/site-updates.json, never the build
clock. Generating the feeds makes no network requests and sends no WebSub
notifications. A hub is advertised only when an owner configures one explicitly.
"""
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ATOM = 'http://www.w3.org/2005/Atom'
ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sfmth.github.io/3d_printing_info/'
PACIFIC = ZoneInfo('America/Los_Angeles')
FEED_ROUTES = ('feed.xml', 'atom.xml')


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(label+' must be nonempty trimmed text')
    if any((ord(char) < 32 and char not in '\n\t') or 0xd800 <= ord(char) <= 0xdfff
           or ord(char) in (0xfffe, 0xffff) for char in value):
        raise ValueError(label+' contains a character forbidden in XML')
    return value


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise ValueError('Update dates must be complete UTC timestamps ending in Z')
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def _https_url(value, label):
    _text(value, label)
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise ValueError(label+' must be an absolute HTTPS URL without credentials or a fragment')
    return value


def _path(value):
    _text(value, 'Update link path')
    # Allow only canonical local content routes, never a query, fragment, encoded
    # traversal, host-relative URL or backslash interpreted differently by readers.
    if (not re.fullmatch(r'[a-zA-Z0-9_-][a-zA-Z0-9_.-]*(?:/[a-zA-Z0-9_-][a-zA-Z0-9_.-]*)*/?', value)
            or any(part in ('.', '..') for part in value.split('/'))
            or not (value.endswith('/') or value.endswith('.html'))):
        raise ValueError('Update links must be canonical relative HTML paths or directories')
    return value


def validate_updates(data):
    """Validate editorial records before any generated output is written."""
    if not isinstance(data, dict) or set(data)-{'version', 'title', 'description', 'entries', 'websub_hub'}:
        raise ValueError('Unknown updates metadata fields')
    if type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Unsupported updates schema version')
    _text(data.get('title'), 'Feed title')
    _text(data.get('description'), 'Feed description')
    if 'websub_hub' in data:
        _https_url(data['websub_hub'], 'WebSub hub')
    if not isinstance(data.get('entries'), list) or not data['entries']:
        raise ValueError('The feed needs at least one factual update')
    ids = set()
    for entry in data['entries']:
        if not isinstance(entry, dict) or set(entry) != {'id', 'title', 'published', 'updated', 'summary', 'links', 'commit'}:
            raise ValueError('Invalid update fields')
        key = entry['id']
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', key) or key in ids:
            raise ValueError('Update IDs must be unique permanent lowercase slugs')
        ids.add(key)
        _text(entry['title'], 'Update title')
        _text(entry['summary'], 'Update summary')
        if _date(entry['updated']) < _date(entry['published']):
            raise ValueError('An update cannot precede its publication')
        if not isinstance(entry['commit'], str) or not re.fullmatch(r'[0-9a-f]{40}', entry['commit']):
            raise ValueError('Each update needs its full release commit hash')
        if not isinstance(entry['links'], list) or not entry['links']:
            raise ValueError('Each update needs at least one content link')
        paths = set()
        for link in entry['links']:
            if not isinstance(link, dict) or set(link) != {'path', 'title'}:
                raise ValueError('Invalid update content link')
            path = _path(link['path'])
            if path in paths:
                raise ValueError('Duplicate content link within an update')
            paths.add(path)
            _text(link['title'], 'Update link title')
    return data


def load_updates(root=ROOT):
    return validate_updates(json.loads((Path(root)/'data/site-updates.json').read_text(encoding='utf-8')))


def _base_url(base):
    _https_url(base, 'Site base URL')
    if not base.endswith('/') or urlsplit(base).query:
        raise ValueError('The site base must end in / and have no query string')
    return base


def feed_discovery(base):
    """Absolute auto-discovery links suitable for a page at any nesting depth."""
    base = _base_url(base)
    return ('<link rel="alternate" type="application/rss+xml" title="3D Printing Info updates (RSS)" href="'
            +escape(base+'feed.xml', quote=True)+'">'
            +'<link rel="alternate" type="application/atom+xml" title="3D Printing Info updates (Atom)" href="'
            +escape(base+'atom.xml', quote=True)+'">')


# Shared templates can import this short name without depending on feed output.
feed_head = feed_discovery


def _ordered(data):
    return sorted(data['entries'], key=lambda entry: (entry['published'], entry['id']), reverse=True)


def _latest(data):
    return max(entry['updated'] for entry in data['entries'])


def _commit_url(entry):
    return 'https://github.com/sfmth/3d_printing_info/commit/'+entry['commit']


def _entry_html(entry, base):
    body = '<p>'+escape(entry['summary'])+'</p><ul>'
    body += ''.join('<li><a href="'+escape(base+link['path'], quote=True)+'">'
                    +escape(link['title'])+'</a></li>' for link in entry['links'])
    return body+'</ul><p><a href="'+_commit_url(entry)+'">Release details</a></p>'


def _xml(document):
    ET.indent(document, space='  ')
    return ET.tostring(document, encoding='utf-8', xml_declaration=True)+b'\n'


def render_rss(data, base):
    document = ET.Element('rss', {'version': '2.0', 'xmlns:atom': ATOM})
    channel = ET.SubElement(document, 'channel')
    for name, value in [('title', data['title']), ('link', base+'updates/'),
                        ('description', data['description']), ('language', 'en'),
                        ('lastBuildDate', format_datetime(_date(_latest(data)), usegmt=True))]:
        ET.SubElement(channel, name).text = value
    ET.SubElement(channel, 'atom:link', {'href': base+'feed.xml', 'rel': 'self', 'type': 'application/rss+xml'})
    if data.get('websub_hub'):
        ET.SubElement(channel, 'atom:link', {'href': data['websub_hub'], 'rel': 'hub'})
    for entry in _ordered(data):
        item = ET.SubElement(channel, 'item')
        for name, value in [('title', entry['title']), ('link', base+entry['links'][0]['path']),
                            ('pubDate', format_datetime(_date(entry['published']), usegmt=True)),
                            ('description', _entry_html(entry, base))]:
            ET.SubElement(item, name).text = value
        ET.SubElement(item, 'guid', {'isPermaLink': 'true'}).text = base+'updates/#'+entry['id']
    return _xml(document)


def render_atom(data, base):
    document = ET.Element('feed', {'xmlns': ATOM, '{http://www.w3.org/XML/1998/namespace}lang': 'en'})
    for name, value in [('id', base+'updates/'), ('title', data['title']),
                        ('subtitle', data['description']), ('updated', _latest(data))]:
        ET.SubElement(document, name).text = value
    ET.SubElement(document, 'link', {'rel': 'self', 'href': base+'atom.xml', 'type': 'application/atom+xml'})
    ET.SubElement(document, 'link', {'rel': 'alternate', 'href': base+'updates/', 'type': 'text/html'})
    if data.get('websub_hub'):
        ET.SubElement(document, 'link', {'rel': 'hub', 'href': data['websub_hub']})
    author = ET.SubElement(document, 'author')
    ET.SubElement(author, 'name').text = '3D Printing Info'
    ET.SubElement(author, 'uri').text = base
    for entry in _ordered(data):
        item = ET.SubElement(document, 'entry')
        for name, value in [('id', base+'updates/#'+entry['id']), ('title', entry['title']),
                            ('published', entry['published']), ('updated', entry['updated']),
                            ('summary', entry['summary'])]:
            ET.SubElement(item, name).text = value
        ET.SubElement(item, 'link', {'rel': 'alternate', 'href': base+entry['links'][0]['path'], 'type': 'text/html'})
        ET.SubElement(item, 'content', {'type': 'html'}).text = _entry_html(entry, base)
    return _xml(document)


def render_archive(data, base):
    title = escape(data['title'])
    description = escape(data['description'], quote=True)
    canonical = escape(base+'updates/', quote=True)
    head = '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    head += '<title>'+title+' | 3D Printing Info</title><meta name="description" content="'+description+'"><meta name="robots" content="index,follow"><link rel="canonical" href="'+canonical+'">'
    head += '<meta property="og:title" content="'+title+'"><meta property="og:description" content="'+description+'"><meta property="og:url" content="'+canonical+'"><meta property="og:type" content="website"><meta property="og:site_name" content="3D Printing Info"><meta property="og:image" content="'+escape(base+'assets/og-card.png', quote=True)+'">'
    head += '<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="'+title+'"><meta name="twitter:description" content="'+description+'"><meta name="twitter:image" content="'+escape(base+'assets/og-card.png', quote=True)+'">'
    schema = {'@context': 'https://schema.org', '@type': 'CollectionPage',
              'name': data['title'], 'description': data['description'], 'url': base+'updates/',
              'dateModified': _latest(data),
              'isPartOf': {'@type': 'WebSite', 'name': '3D Printing Info', 'url': base},
              'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(data['entries']),
                             'itemListElement': [{'@type': 'ListItem', 'position': number,
                                                  'name': entry['title'], 'url': base+'updates/#'+entry['id']}
                                                 for number, entry in enumerate(_ordered(data), 1)]}}
    head += feed_discovery(base)+'<link rel="icon" href="../assets/site-icon.svg"><link rel="stylesheet" href="../assets/materials.css"><link rel="stylesheet" href="../assets/updates.css"><link rel="stylesheet" href="../assets/analytics-consent.css"><script defer src="../assets/analytics-consent.js"></script>'
    head += '<script type="application/ld+json">'+json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')+'</script></head>'
    body = '<body><div class="updates-wrap"><header class="updates-topbar"><a class="brand" href="../"><img src="../assets/site-icon.svg" width="28" height="28" alt="">3D Printing Info</a><nav aria-label="Primary"><a href="../">Home</a><a href="../compare/">Comparisons</a><a href="../articles/">Selection articles</a></nav></header><main><header class="updates-heading"><p class="eyebrow">From the reference library</p><h1>'+title+'</h1><p>'+escape(data['description'])+'</p><div class="subscribe-links"><a href="../feed.xml" type="application/rss+xml">Subscribe with RSS</a><a href="../atom.xml" type="application/atom+xml">Subscribe with Atom</a></div></header><div class="updates-list">'
    for entry in _ordered(data):
        published = _date(entry['published']).astimezone(PACIFIC)
        date_label = published.strftime('%B ')+str(published.day)+published.strftime(', %Y')
        body += '<article id="'+entry['id']+'"><time datetime="'+entry['published']+'">'+date_label+'</time><h2><a href="#'+entry['id']+'">'+escape(entry['title'])+'</a></h2>'
        if entry['updated'] != entry['published']:
            updated = _date(entry['updated']).astimezone(PACIFIC)
            body += '<p class="updated">Updated <time datetime="'+entry['updated']+'">'+updated.strftime('%B ')+str(updated.day)+updated.strftime(', %Y')+'</time></p>'
        body += _entry_html(entry, base)+'</article>'
    body += '</div></main><footer><p>Dates follow the linked repository releases and are displayed in Pacific time. Source and price dates remain with each guide.</p><a href="../sitemap.xml">Sitemap</a><span class="privacy-links"><a href="../privacy.html">Privacy</a><button type="button" data-analytics-settings hidden>Analytics settings</button></span></footer></div></body></html>\n'
    return head+body


def generate_updates(root=ROOT, base=BASE):
    """Write the archive and feeds; return canonical HTML path/lastmod metadata.

    Only the HTML archive belongs in the sitemap. RSS and Atom are discovered
    through alternate links and their visible subscription links instead.
    """
    root = Path(root)
    base = _base_url(base)
    data = load_updates(root)
    content = {'feed.xml': render_rss(data, base), 'atom.xml': render_atom(data, base),
               'updates/index.html': render_archive(data, base).encode('utf-8')}
    for relative, value in content.items():
        path = root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != value:
            path.write_bytes(value)
    return {'updates/': _latest(data)[:10]}


if __name__ == '__main__':
    print(json.dumps(generate_updates(), sort_keys=True))
