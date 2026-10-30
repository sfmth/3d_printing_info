#!/usr/bin/env python3
"""Validate complete catalogs, preservation, crawlability and generated output."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
from collections import Counter
from urllib.parse import urlsplit, unquote, quote
import hashlib
import json
import re
import subprocess
import statistics
import tempfile
import xml.etree.ElementTree as ET
from sync_site import ROOT, BASE, PAGES, PAYLOAD, LD, CATALOG_DATE, PRINTER_DATE, payload, counts
from material_design import EXAMPLES, APPLICATIONS
from printer_resources import load_resources, section_for, source_urls, CATEGORIES
from printer_design import CHAPTERS
from material_articles import load_articles, load_evidence, measure_value, context_label, DETAIL_CONTEXT_FIELDS
from check_articles import validate_evidence


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def schema_nodes(value):
    """Include nested entities and @graph/array entries when auditing JSON-LD."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from schema_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from schema_nodes(child)


def schema_type(value):
    return value.rstrip('/').rsplit('/', 1)[-1].rsplit(':', 1)[-1]


def snapshot(data):
    return {'cats': {c['id']: {
        'record': digest(c),
        'core': digest({k: v for k, v in c.items() if k not in ('pr', 'px')}),
        'products': [digest(p) for p in c.get('pr', [])],
        'px': c.get('px')
    } for c in data['cats']}, 'src': {k: digest(s) for k, s in data['src'].items()}}


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []; self.ids = []; self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs); self.tags.append((tag, a))
        if 'id' in a: self.ids.append(a['id'])

    def attrs(self, tag):
        return [a for t, a in self.tags if t == tag]


class Element:
    """Keep field values and citations attached to their actual rendered row."""
    def __init__(self, tag='', attrs=None, parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs or []), parent
        self.children = []

    @property
    def text(self):
        return ''.join(child.text if isinstance(child, Element) else child for child in self.children)

    def find(self, tag=None, cls=None, **attrs):
        for child in self.children:
            if not isinstance(child, Element):
                continue
            if ((tag is None or child.tag == tag)
                    and (cls is None or cls in child.attrs.get('class', '').split())
                    and all(child.attrs.get(key) == value for key, value in attrs.items())):
                yield child
            yield from child.find(tag, cls, **attrs)


class Document(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Element()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Element(tag, attrs, self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node.parent is not None:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


def webp_dimensions(data):
    """Read the image's own dimensions without adding a Pillow dependency to CI."""
    assert data[:4] == b'RIFF' and data[8:12] == b'WEBP', 'Printer photo is not WebP'
    offset = 12
    while offset + 8 <= len(data):
        kind, size = data[offset:offset+4], int.from_bytes(data[offset+4:offset+8], 'little')
        content = data[offset+8:offset+8+size]
        if kind == b'VP8X' and len(content) >= 10:
            return (1+int.from_bytes(content[4:7], 'little'), 1+int.from_bytes(content[7:10], 'little'))
        if kind == b'VP8 ' and len(content) >= 10 and content[3:6] == b'\x9d\x01\x2a':
            return (int.from_bytes(content[6:8], 'little') & 0x3fff,
                    int.from_bytes(content[8:10], 'little') & 0x3fff)
        if kind == b'VP8L' and len(content) >= 5 and content[0] == 0x2f:
            bits = int.from_bytes(content[1:5], 'little')
            return (1+(bits & 0x3fff), 1+((bits >> 14) & 0x3fff))
        offset += 8 + size + (size % 2)
    raise AssertionError('Printer photo has no decodable WebP dimensions')


def printer_images(catalog):
    from image_rights import validate_reuse, decisions
    manifest = json.loads((ROOT/'data/printer-images.json').read_text())
    assert set(manifest) == {'version', 'images'} and type(manifest['version']) is int and manifest['version'] == 2, 'Invalid printer image manifest'
    images = manifest['images']
    assert images and set(images) <= {c['id'] for c in catalog['cats']}, 'Printer photos must identify exact catalog models'
    records = decisions()
    assert set(records) == {c['id'] for c in catalog['cats']}, 'Every printer needs its recorded image disposition'
    assert {p.relative_to(ROOT).as_posix() for p in (ROOT/'assets/printers').glob('*.webp')} == {i['image'] for i in images.values()}, 'Unreferenced product photographs remain publicly served'
    fields = {'image', 'alt', 'width', 'height', 'source_url', 'image_url', 'credit', 'kind', 'checked', 'sha256', 'reuse'}
    for printer_id, image in images.items():
        assert set(image) == fields, (printer_id, 'Incomplete printer image provenance')
        validate_reuse(image)
        assert records[printer_id]['decision'] in {'retained-publisher-grant', 'retained-no-explicit-restriction-found', 'replaced-with-licensed-photo'}, (printer_id, 'Photo conflicts with recorded rights decision')
        path = Path(image['image'])
        assert path.parent.as_posix() == 'assets/printers' and path.suffix == '.webp', (printer_id, 'Photo must be a local printer WebP')
        assert all(isinstance(image[key], str) and image[key].strip() for key in ('alt', 'credit', 'kind')), printer_id
        assert all(image[key].startswith('https://') for key in ('source_url', 'image_url')), printer_id
        assert all(type(image[key]) is int and image[key] > 0 for key in ('width', 'height')), printer_id
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', image['checked']), printer_id
        assert re.fullmatch(r'[0-9a-f]{64}', image['sha256']), printer_id
        content = (ROOT/path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == image['sha256'], (printer_id, 'Photo integrity mismatch')
        assert webp_dimensions(content) == (image['width'], image['height']), (printer_id, 'Photo dimensions mismatch')
    assert len({image['image'] for image in images.values()}) == len(images), 'A printer photo must not be assigned to a sibling model'
    return images


def check_printer_record(html, catalog, printer, images, resources):
    document = Document(html).root
    printer_id = printer['id']
    body = next(document.find('body'))
    assert {'printer-page', 'printer-detail'} <= set(body.attrs.get('class', '').split()), printer_id
    groups = list(document.find('details', 'printer-spec-group'))
    expected_groups = {section for section in catalog['sections']
                       if any(field['sec'] == section and field['id'] in printer['sp'] for field in catalog['fields'])}
    assert {group.attrs.get('id') for group in groups} == {'spec-'+section.lower() for section in expected_groups}, (printer_id, 'Missing specification disclosure')
    assert all('open' not in group.attrs for group in groups), (printer_id, 'Technical specifications must start collapsed')
    rows = [row for row in document.find('tr') if 'data-field' in row.attrs]
    assert Counter(row.attrs['data-field'] for row in rows) == Counter(printer['sp'].keys()), (printer_id, 'Published fields must appear once in the specification tables')
    fields = {field['id']: field for field in catalog['fields']}
    for row in rows:
        field_id = row.attrs['data-field']; field = fields[field_id]; value = printer['sp'][field_id]
        group = row.parent
        while group is not None and 'printer-spec-group' not in group.attrs.get('class', '').split():
            group = group.parent
        assert group is not None and group.attrs.get('id') == 'spec-'+field['sec'].lower(), (printer_id, field_id, 'Field outside its native disclosure')
        label = next(row.find('th')).text
        assert field['name'] in label and (not field.get('unit') or field['unit'] in label), (printer_id, field_id, 'Field label or unit lost')
        cells = list(row.find('td', 'printer-property-value'))
        assert len(cells) == 1 and cells[0].text.strip() == value['v'].strip(), (printer_id, field_id, 'Published value changed or truncated')
        source_links = {link.attrs.get('href') for link in row.find('a')}
        for source_id in value.get('s', []):
            source = catalog['src'][source_id]
            assert list(row.find('details', 'printer-row-sources')), (printer_id, field_id, 'Missing native source disclosure')
            if source.get('u'):
                assert source['u'] in source_links, (printer_id, field_id, source_id, 'Source URL separated from field')
            for key in ('t', 'd', 'k'):
                if source.get(key):
                    assert source[key] in row.text, (printer_id, field_id, source_id, 'Source context lost', key)
    sources = list(document.find(id='sources'))
    assert len(sources) == 1, (printer_id, 'Missing consolidated catalog sources')
    source_ids = {sid for value in printer['sp'].values() for sid in value.get('s', [])}
    library = next(sources[0].find('details', 'printer-source-library'))
    assert len(list(library.find('li'))) == len(source_ids), (printer_id, 'Consolidated catalog sources must be deduplicated')
    for source_id in source_ids:
        source = catalog['src'][source_id]
        assert source.get('t', source_id) in sources[0].text, (printer_id, source_id, 'Source omitted from consolidated references')
    record = resources[printer_id]
    notes = list(document.find('article', 'printer-context-note'))
    expected = [(category, entry) for category in CATEGORIES for entry in record[category]]
    assert len(notes) == len(expected), (printer_id, 'Ownership evidence dropped or duplicated')
    for category, entry in expected:
        matches = [note for note in notes if note.attrs.get('data-resource-kind') == category and next(note.find('h4')).text == entry['title']]
        assert len(matches) == 1, (printer_id, entry['title'], 'Resource identity mismatch')
        note = matches[0]
        section = section_for(category, entry)
        assert note.attrs.get('data-resource-section') == section, (printer_id, 'Resource context changed')
        topic = note.parent
        while topic is not None and 'data-printer-topic' not in topic.attrs:
            topic = topic.parent
        assert topic is not None and topic.attrs['data-printer-topic'] == section, (printer_id, 'Resource separated from its technical topic')
        chapter = topic.parent
        assert chapter.attrs.get('id') == next(slug for slug, _, _, letters in CHAPTERS if section in letters), (printer_id, 'Resource outside its technical chapter')
        assert entry['summary'] in note.text and entry['compatibility'] in note.text and entry['evidence'].capitalize() in note.text, (printer_id, 'Resource limits or provenance lost')
        evidence = next(note.find('details', 'printer-resource-evidence'))
        for source in entry['sources']:
            assert source['url'] in {link.attrs.get('href') for link in evidence.find('a')}, (printer_id, 'Resource source lost')
            assert source['title'] in evidence.text and source['checked'] in evidence.text, (printer_id, 'Resource source date lost')
    review = list(sources[0].find('details', 'printer-resource-review'))
    assert len(review) == 1 and 'open' not in review[0].attrs, (printer_id, 'Research coverage must be discoverable within sources')
    for source in record['reviewed_sources']:
        assert source['url'] in {link.attrs.get('href') for link in review[0].find('a')}, (printer_id, 'Review scope source lost')
    visual = list(document.find('figure', 'printer-visual'))
    assert len(visual) == 1, (printer_id, 'Missing printer visual')
    photos = [image for image in visual[0].find('img') if 'data-printer-image' in image.attrs]
    if printer_id in images:
        image = images[printer_id]
        assert len(photos) == 1 and photos[0].attrs.get('data-printer-image') == printer_id and photos[0].attrs.get('src') == '../'+image['image'], (printer_id, 'Wrong model photograph')
        assert photos[0].attrs.get('alt') == image['alt'], printer_id
        assert (photos[0].attrs.get('width'), photos[0].attrs.get('height')) == (str(image['width']), str(image['height'])), printer_id
        assert image['source_url'] in {link.attrs.get('href') for link in visual[0].find('a')}, (printer_id, 'Missing photo credit link')
        assert image['credit'] in visual[0].text, (printer_id, 'Missing photo credit')
        if image['reuse'].get('license_url'):
            assert image['reuse']['license_url'] in {link.attrs.get('href') for link in visual[0].find('a')}, (printer_id, 'Missing image licence link')
            assert image['reuse']['changes'] in visual[0].text, (printer_id, 'Missing image modification disclosure')
    else:
        assert not photos, (printer_id, 'Unverified model must not borrow a product photograph')
        diagrams = list(visual[0].find('img', **{'data-printer-diagram': printer['f'].lower()}))
        assert len(diagrams) == 1 and 'generic' in visual[0].text.lower(), (printer_id, 'Fallback must be a clearly labeled generic architecture diagram')
        from image_rights import decisions
        assert decisions()[printer_id]['original_source_url'] in {link.attrs.get('href') for link in visual[0].find('a')}, (printer_id, 'Fallback lacks product-photo source link')


def check_printer_directory(catalog, images):
    document = Document((ROOT/'printers/index.html').read_text()).root
    cards = list(document.find('article', 'pl-printer-card'))
    assert Counter(card.attrs.get('data-printer-id') for card in cards) == Counter(c['id'] for c in catalog['cats']), 'Printer directory dropped or duplicated a model'
    lookup = {printer['id']: printer for printer in catalog['cats']}
    families = list(document.find('details', 'pl-family'))
    assert {family.attrs.get('data-printer-family') for family in families} == set(catalog['families']), 'Printer directory family groups differ from catalog'
    assert all('open' in family.attrs for family in families), 'Printer families must be browsable without JavaScript'
    assert 'hidden' in next(document.find(id='printer-search-panel')).attrs, 'Hide inactive printer search without JavaScript'
    features = list(document.find('article', 'pl-feature-card'))
    featured_ids = [card.attrs.get('data-featured-printer') for card in features]
    assert len(features) == len(set(featured_ids)) == 6 and set(featured_ids) <= lookup.keys(), 'Featured printer cards must identify six distinct models'
    for card in cards:
        printer_id = card.attrs['data-printer-id']; printer = lookup[printer_id]
        assert 'data-printer-card' in card.attrs, printer_id
        group = card.parent
        while group is not None and 'pl-family' not in group.attrs.get('class', '').split():
            group = group.parent
        assert group is not None and group.attrs.get('data-printer-family') == printer['f'], (printer_id, 'Model in wrong directory family')
        guide_links = list(card.find('a', 'pl-card-link'))
        assert len(guide_links) == 1 and guide_links[0].attrs.get('href') == printer_id+'.html', (printer_id, 'Wrong guide URL')
        assert printer['n'] in guide_links[0].text, (printer_id, 'Model name missing from guide link')
        comparisons = list(card.find('a', 'pl-card-compare'))
        assert len(comparisons) == 1 and comparisons[0].attrs.get('href') == '../comparison.html#'+printer_id, (printer_id, 'Comparison does not select the exact model')
    for card in [*cards, *features]:
        printer_id = card.attrs.get('data-printer-id') or card.attrs['data-featured-printer']
        photos = [image for image in card.find('img') if 'data-printer-photo' in image.attrs]
        if printer_id in images:
            image = images[printer_id]
            assert len(photos) == 1 and photos[0].attrs.get('data-printer-photo') == printer_id, (printer_id, 'Directory photo model mismatch')
            assert photos[0].attrs.get('src') == '../'+image['image'] and photos[0].attrs.get('alt') == image['alt'], printer_id
            assert (photos[0].attrs.get('width'), photos[0].attrs.get('height')) == (str(image['width']), str(image['height'])), printer_id
            assert image['source_url'] in {link.attrs.get('href') for link in card.find('a')}, (printer_id, 'Directory photo lacks source credit')
            if image['reuse'].get('license_url'):
                assert image['reuse']['license_url'] in {link.attrs.get('href') for link in card.find('a')}, (printer_id, 'Directory photo lacks licence link')
        else:
            assert not photos, (printer_id, 'Directory borrowed a sibling photograph')


def run():
    baseline = json.loads((ROOT/'data/baseline-integrity.json').read_text())
    checkpoint = json.loads((ROOT/'data/catalog-checkpoint.json').read_text())
    datasets = {}
    for name in PAGES:
        text = (ROOT/name).read_text(); d = payload(text); datasets[name] = d
        assert len(PAYLOAD.findall(text)) == 1, name
        cats = {c['id']:c for c in d['cats']}
        assert len(cats)==len(d['cats']), ('Duplicate category ID',name)
        fields={f['id']:f for f in d['fields']}
        assert len(fields)==len(d['fields']), ('Duplicate field ID',name)
        saved = checkpoint['catalogs'][name]
        # Appending products may change only the product list and its derived price summary.
        # Preserve every old product object, including repeated records, and all category specs.
        for key, expected in saved['cats'].items():
            assert key in cats, ('Catalog record dropped', name, key)
            c = cats[key]
            assert digest({k:v for k,v in c.items() if k not in ('pr','px')}) == expected['core'], ('Catalog specifications changed', name, key)
            assert not Counter(expected['products']) - Counter(digest(p) for p in c.get('pr', [])), ('Existing product changed/dropped', name, key)
            if digest(c) != expected['record']:
                assert name == 'filaments.html', ('Printer changed', key)
                prices = [p['k'] for p in c.get('pr', []) if p.get('k') is not None]
                derived = {'min':min(prices),'max':max(prices),'med':round(statistics.median(prices),2),'n':len(prices)} if prices else None
                assert c.get('px') == derived, ('Stale product price summary', key)
        for key,expected in saved['src'].items():
            assert key in d['src'] and digest(d['src'][key])==expected, ('Original source changed/dropped',name,key)
        # The newer checkpoint must retain every record/source protected by the rollback manifest.
        for key,expected in baseline['catalogs'][name]['cats'].items():
            assert saved['cats'][key]['record'] == expected, ('Rollback checkpoint mismatch', name, key)
        for key,expected in baseline['catalogs'][name]['src'].items():
            assert saved['src'][key] == expected, ('Rollback source checkpoint mismatch', name, key)
        raw_checkpoint = subprocess.run(['git','show',checkpoint['commit']+':'+name],cwd=ROOT,capture_output=True,text=True)
        if raw_checkpoint.returncode == 0:
            assert snapshot(payload(raw_checkpoint.stdout)) == saved, ('Checkpoint differs from Git object', name)
        # Check the recorded baseline against real Git objects whenever history is available.
        raw=subprocess.run(['git','show',baseline['baseline']+':'+name],cwd=ROOT,capture_output=True,text=True)
        if raw.returncode==0:
            old=payload(raw.stdout)
            assert {c['id']:digest(c) for c in old['cats']}==baseline['catalogs'][name]['cats'], name
            assert {k:digest(s) for k,s in old['src'].items()}==baseline['catalogs'][name]['src'], name
        def spec(values):
            assert set(values)<=fields.keys(), (name,'unknown field',set(values)-fields.keys())
            for k,e in values.items():
                assert isinstance(e.get('v'),str), (name,k,e)
                assert set(e.get('s',[]))<=d['src'].keys(), (name,k,'unknown source')
                if 'n' in e: assert isinstance(e['n'],(int,float)), (name,k,'invalid numeric value')
        for c in d['cats']:
            assert re.fullmatch('[a-z0-9-]+',c['id']), c['id']
            assert c['f'] in d['families'], c['id']
            spec(c['sp'])
            for p in c.get('pr',[]):
                spec(p.get('sp',{}))
                assert set(p.get('s',[]))<=d['src'].keys(),p
                assert set(p.get('tds') or [])<=d['src'].keys(),p
                if p.get('retail'):
                    r=p['retail']
                    assert r['store'] and r['location'] and r['status']
                    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',r['checked'])
                    assert set(r['s']) <= set(p['s']) and r['s'],p
                    assert all(d['src'][sid]['d']==r['checked'] and d['src'][sid]['p']==r['store'] for sid in r['s'])
                    assert r['mass_kg'] > 0
                    assert p['k'] == (round(r['listed_usd']/r['mass_kg'],2) if r['listed_usd'] is not None else None),p
                    assert r['reference_usd'] is None or r['reference_usd'] >= r['listed_usd'],p
                    # Linear print-speed claims must never populate volumetric flow.
                    if 'B7' in p['sp']: assert 'mm³/s' in p['sp']['B7']['v'] or 'mm3/s' in p['sp']['B7']['v'],p
        cs=counts(d)
        structured=[json.loads(m) for m in LD.findall(text)]
        webpage=next(x for x in structured if x['@type']=='WebPage')
        assert webpage['url']==BASE+name,name
        if name=='comparison.html': assert 'filament' not in webpage['description'].lower(),name
        items=next(x for x in structured if x['@type']=='ItemList')
        assert items['numberOfItems']==len(items['itemListElement'])==cs['items'],name
        assert [x['name'] for x in items['itemListElement']]==[c['n'] for c in d['cats']],name
        ds=next(x for x in structured if x['@type']=='Dataset')
        assert ds['url']==BASE+name and {x['name']:x['value'] for x in ds['additionalProperty']}==cs,name
        assert len(ds['variableMeasured'])==len(fields),name
        assert ds.get('creator') == {'@type':'Organization','name':'3D Printing Info','url':BASE}, (name,'Dataset creator is missing or inconsistent')
        assert ds.get('license') == 'https://www.gnu.org/licenses/gpl-3.0.html', (name,'Dataset must retain the repository GPL v3.0 license')
        attribution=list(Document(text).root.find(id='dataset-attribution'))
        assert len(attribution)==1 and ds['creator']['name'] in attribution[0].text, (name,'Dataset attribution must be visible')
        license_links=[link for link in attribution[0].find('a') if link.attrs.get('rel')=='license']
        assert len(license_links)==1 and license_links[0].attrs.get('href')==ds['license'], (name,'Visible and structured licenses must agree')
        assert 'Individual source documents and images retain their respective rights and terms.' in attribution[0].text, name
        static=re.search(r'<noscript>(.*?)</noscript>',text,re.S)[1]
        expected=cs['items']+(cs['products'] if name=='filaments.html' else 0)
        assert static.count('<th scope="row">')==expected,(name,'fallback rows')
        for c in d['cats']: assert c['n'].replace('&','&amp;') in static or c['n'] in static,(name,c['id'])
        print(f'{name}: {cs}; all original records and sources preserved')
    filaments=datasets['filaments.html']; printers=datasets['comparison.html']
    printer_photos = printer_images(printers)
    printer_resources = load_resources(expected_ids={c['id'] for c in printers['cats']})
    assert set(APPLICATIONS)=={c['id'] for c in filaments['cats']},'Every material must have an Applications section'
    for c in filaments['cats']:
        entry=APPLICATIONS[c['id']]
        assert 1<=len(entry['paragraphs'])<=4,(c['id'],'applications prose')
        assert all(isinstance(p,str) and p.strip() for p in entry['paragraphs']),(c['id'],'empty applications prose')
        assert 2<=len(entry['fields'])<=6 and len(set(entry['fields']))==len(entry['fields']),(c['id'],'application evidence fields')
        assert set(entry['fields'])<=set(c['sp']),(c['id'],'unknown application evidence field')
        assert any(c['sp'][fid].get('s') for fid in entry['fields']) or entry.get('sources'),(c['id'],'applications have no source')
        for source in entry.get('sources',[]):
            assert source['title'] and source['url'].startswith('https://'),(c['id'],'invalid application source')
        for case in entry.get('examples',[]):
            assert all(isinstance(case.get(k),str) and case[k].strip() for k in ('title','text','process','scope','url','source_title')),(c['id'],'incomplete industrial example')
            assert case['url'].startswith('https://') and case['evidence'] in ('case-study','manufacturer-application'),(c['id'],'unlabeled example evidence')
    retail=[p for c in filaments['cats'] for p in c['pr'] if p.get('retail')]
    assert {'Inland','Cookiecad','Insignia'} <= {p['b'] for p in retail}
    retail_page=(ROOT/'filaments.html').read_text()
    for brand in {p['b'] for p in retail}:
        assert 'filaments.html?brand='+quote(brand,safe='') in retail_page,brand
    for c in filaments['cats']:
        for p in c['pr']:
            if not p.get('retail'):continue
            guide=(ROOT/'materials'/(c['id']+'.html')).read_text()
            for value in [p['p'],p['pn'],p['nt'],p['u']]:assert escape(value) in guide,(c['id'],'missing product detail',p['p'])
    hardness=next(f for f in filaments['fields'] if f['id']=='E10')
    assert hardness['type']=='text' and hardness['mixed'] and not hardness['dir']
    peba=next(c for c in filaments['cats'] if c['id']=='peba')
    assert peba['sp']['B7']['n']==9 and 'mm³/s' in peba['sp']['B7']['v']
    assert 'n' not in peba['sp']['E10']
    assert 'n' not in peba['sp']['E1'] and '>' in peba['sp']['E1']['v']
    assert 'peba' in (ROOT/'materials/peba.html').read_text().lower()
    index=(ROOT/'index.html').read_text()
    summary={'printers':len(printers['cats']),'printer-fields':len(printers['fields']),'materials':len(filaments['cats']),'products':counts(filaments)['products']}
    for key,n in summary.items():
        found=re.findall('data-summary="'+key+r'">(\d+)',index)
        assert found and all(int(x)==n for x in found),(key,found,n)
    paths=[ROOT/'index.html',ROOT/'privacy.html',*(ROOT/x for x in PAGES),*(ROOT/'materials').glob('*.html'),*(ROOT/'printers').glob('*.html'),*(ROOT/'articles').glob('*.html')]
    assert len(list((ROOT/'materials').glob('*.html')))==len(filaments['cats'])+1
    assert len(list((ROOT/'printers').glob('*.html')))==len(printers['cats'])+1
    article_data, evidence = load_articles(), load_evidence()
    validate_evidence(evidence, article_data, {c['id'] for c in filaments['cats']})
    expected_articles={a['id']+'.html' for a in article_data['articles']}|{'index.html'}
    assert {p.name for p in (ROOT/'articles').glob('*.html')}==expected_articles,'Unexpected article pages'
    article_index=(ROOT/'articles/index.html').read_text()
    index_schema=next(json.loads(s) for s in LD.findall(article_index))
    assert index_schema['@type']=='CollectionPage' and index_schema['mainEntity']['numberOfItems']==len(article_data['articles'])
    assert [item['url'] for item in index_schema['mainEntity']['itemListElement']]==[BASE+'articles/'+a['id']+'.html' for a in article_data['articles']]
    for article in article_data['articles']:
        path=ROOT/'articles'/(article['id']+'.html'); html=path.read_text(); parsed=Page(html)
        schema=next(json.loads(s) for s in LD.findall(html)); entity=schema['mainEntity']
        assert schema['@type']=='WebPage' and entity['@type']=='TechArticle'
        assert entity['author']==article['author'] and entity['datePublished']==article['published'] and entity['dateModified']==article['modified']
        assert 'Article revision: '+article['modified'] in html and 'Catalog values retain' not in html
        assert article['id']+'.html' in article_index
        tables=article.get('tables',[article.get('table')])
        assert len([attrs for attrs in parsed.attrs('tr') if 'data-measurement' in attrs or 'data-observation' in attrs])==sum(len(table['rows']) for table in tables)
        if 'tables' in article:
            for table in tables:
                assert 'table-'+table['id'] in parsed.ids
                if table.get('kind') == 'observations':
                    for row in table['rows']:
                        assert 'data-observation="'+row['id']+'"' in html
                        for value in [row['grade'],row['process'],row['orientation'],row['conditioning'],row['observation'],*row['exposure'].values()]:
                            assert escape('Not reported' if value is None else value) in html
                    continue
                for row in table['rows']:
                    series=evidence['series'][row['series_id']]
                    assert 'data-test-series="'+row['series_id']+'"' in html
                    for key,value in series.get('context',{}).items():
                        label=context_label(key);shown='Not reported' if value is None else str(value)
                        assert '<dt>'+escape(label)+'</dt><dd>'+escape(shown)+'</dd>' in html,(article['id'],'missing full test context',key)
                        if key not in DETAIL_CONTEXT_FIELDS:
                            assert escape(label+': '+shown) in html,(article['id'],'missing adjacent test context',key)
        source_ids=set()
        for ref in [*article['measurements'],*article['claims']]:
            item=evidence['claims'].get(ref) or evidence['measurements'].get(ref)
            sid=item.get('source_id') or evidence['series'][item['series_id']]['source_id']; source_ids.add(sid)
            assert 'evidence-'+ref in parsed.ids and escape(item['locator']) in html,(article['id'],'missing evidence record',ref)
            if 'value' in item:assert escape(measure_value(item)) in html
        assert set(entity['citation'])=={evidence['sources'][sid]['url'] for sid in source_ids}
        for cid in article['materials']:
            assert '../materials/'+cid+'.html' in html
            assert '../articles/'+article['id']+'.html' in (ROOT/'materials'/(cid+'.html')).read_text()
        for attrs in parsed.attrs('a'):
            href=attrs.get('href','')
            if href.startswith('#'):assert unquote(href[1:]) in parsed.ids,(article['id'],'missing article anchor',href)
        for sid in source_ids:assert evidence['sources'][sid]['url'].replace('&','&amp;') in html
    for entry in ('index.html','filaments.html','materials/index.html'):
        assert 'articles/' in (ROOT/entry).read_text(),('Missing article discovery route',entry)
    canonicals=set()
    for path in paths:
        text=path.read_text();name=str(path.relative_to(ROOT)); parsed=Page(text)
        # Product nodes trigger rich-result validation even inside TechArticle.about.
        # This reference catalog has no supported offer/review/rating markup.
        for document in map(json.loads, LD.findall(text)):
            for node in schema_nodes(document):
                types=node.get('@type',[])
                if isinstance(types,str):types=[types]
                assert not any(schema_type(t)=='Product' for t in types),(name,'Unsupported Product rich-result markup')
        for tag,attrs in parsed.tags:
            for key in ('itemtype','typeof'):
                assert not any(schema_type(t)=='Product' for t in attrs.get(key,'').split()),(name,'Unsupported Product microdata/RDFa')
        assert 'bytes omitted' not in text and '[... omitted' not in text, name
        depth='../' if '/' in name else ''
        scripts=parsed.attrs('script')
        assert len([script for script in scripts if script.get('src')==depth+'assets/analytics-consent.js' and 'defer' in script])==1,(name,'Missing local analytics consent gate')
        assert not any(urlsplit(script.get('src','')).netloc for script in scripts),(name,'Remote scripts must not load before analytics consent')
        assert not re.search(r'\bgtag\s*\(',text),(name,'Unconditional analytics configuration in page HTML')
        assert len([link for link in parsed.attrs('link') if link.get('href')==depth+'assets/analytics-consent.css' and link.get('rel')=='stylesheet'])==1,name
        footer=Document(text).root
        footers=list(footer.find('footer'))
        assert len(footers)==1,(name,'Missing unique privacy footer')
        assert len([link for link in footers[0].find('a') if link.attrs.get('href')==depth+'privacy.html'])==1,(name,'Missing footer privacy link')
        settings=[button for button in footers[0].find('button') if 'data-analytics-settings' in button.attrs]
        assert len(settings)==1 and 'hidden' in settings[0].attrs,(name,'Settings must be available through the local gate, hidden without JavaScript')
        assert len(re.findall('<title>.*?</title>',text))==1,name
        canonical=[a['href'] for a in parsed.attrs('link') if a.get('rel')=='canonical']
        url=BASE+('' if name=='index.html' else name[:-10] if name.endswith('/index.html') else name)
        assert canonical==[url],(name,canonical)
        assert url not in canonicals,('Duplicate canonical',url)
        canonicals.add(url)
        assert any(a.get('name')=='robots' and a.get('content')=='index,follow' for a in parsed.attrs('meta')),name
        assert any(a.get('name')=='description' and a.get('content') for a in parsed.attrs('meta')),name
        assert any(a.get('aria-label')=='Primary' for a in parsed.attrs('nav')),name
        assert len(parsed.ids)==len(set(parsed.ids)),(name,'duplicate HTML IDs')
        for tag,a in parsed.tags:
            for key in ('href','src'):
                href=a.get(key)
                if not href or '${' in href: continue
                u=urlsplit(href)
                if u.scheme and not href.startswith(BASE): continue
                if u.netloc and not href.startswith(BASE): continue
                if href.startswith(BASE): local=ROOT/unquote(u.path[len('/3d_printing_info/'):])
                elif href.startswith('/'): raise AssertionError((name,'root-relative link breaks project Pages',href))
                else: local=path.parent/unquote(u.path)
                if local.is_dir():local=local/'index.html'
                assert local.exists(),(name,href,'missing target')
        for attrs,script in re.findall(r'<script([^>]*)>(.*?)</script>',text,re.S):
            if 'application/json' in attrs or 'ld+json' in attrs: json.loads(script)
            elif script.strip():
                with tempfile.NamedTemporaryFile(mode='w',suffix='.js') as tmp:
                    tmp.write(script);tmp.flush()
                    checked=subprocess.run(['node','--check',tmp.name],capture_output=True,text=True)
                    assert checked.returncode==0,(name,checked.stderr)
    for directory,data,comparison in [('materials',filaments,'filaments.html'),('printers',printers,'comparison.html')]:
        listing=(ROOT/comparison).read_text()
        itemlist=next(json.loads(x) for x in LD.findall(listing) if json.loads(x).get('@type')=='ItemList')
        assert [x['url'] for x in itemlist['itemListElement']]==[BASE+directory+'/'+c['id']+'.html' for c in data['cats']]
        for c in data['cats']:
            html=(ROOT/directory/(c['id']+'.html')).read_text()
            schema=json.loads(LD.findall(html)[0])
            assert schema['@type']=='WebPage' and schema['url']==BASE+directory+'/'+c['id']+'.html',(directory,c['id'],'guide metadata')
            article=schema['mainEntity']
            assert article['@type']=='TechArticle' and article['url']==schema['url'],(directory,c['id'],'technical article metadata')
            if directory=='printers':
                subject=article['about']
                assert subject['@type']=='Thing' and subject['name']==c['n'],(c['id'],'printer reference subject')
                check_printer_record(html, printers, c, printer_photos, printer_resources)
                assert set(source_urls(printer_resources[c['id']])) <= set(article['citation']), (c['id'], 'Ownership sources missing from article metadata')
            assert escape(c['n']) in html,c['id']
            assert 'Published value and conditions' in html and 'Sources and dates' in html,c['id']
            assert directory+'/'+c['id']+'.html' in listing,c['id']
            # Every published value and every attached source must survive static rendering.
            for e in c['sp'].values():
                assert escape(e['v']) in html,(directory,c['id'],'missing published value')
                for sid in e.get('s',[]):
                    source=data['src'][sid]
                    if source.get('u'):assert escape(source['u']) in html,(directory,c['id'],sid)
            if directory=='materials':
                parsed=Page(html)
                assert 'applications' in parsed.ids,(c['id'],'missing Applications section')
                assert 'data-application-example' not in html and 'application-card' not in html,(c['id'],'numbered application cards remain')
                entry=APPLICATIONS[c['id']]
                for paragraph in entry['paragraphs']:assert escape(paragraph) in html,(c['id'],'missing applications prose')
                for source in entry.get('sources',[]):assert escape(source['url']) in html,(c['id'],'missing engineering source')
                for case in entry.get('examples',[]):
                    for key in ('title','text','process','scope','url'):assert escape(case[key]) in html,(c['id'],'missing industrial application',key)
                assert not any(a.get('src','').startswith('../assets/materials/') for a in parsed.attrs('img')),c['id']
                assert ('prints' in parsed.ids)==bool(EXAMPLES.get(c['id'])),(c['id'],'printed examples only when documented')
                for host in ('www.printables.com/search/models?q=','makerworld.com/en/search/models?keyword=','www.thingiverse.com/search?q='):
                    assert any(a.get('href','').startswith('https://'+host) for a in parsed.attrs('a')),(c['id'],'missing model discovery link')
                if c['id'] in EXAMPLES:
                    for e in EXAMPLES[c['id']]:
                        if e.get('image'):
                            assert any(a.get('src')=='../'+e['image'] and a.get('alt')==e['alt'] for a in parsed.attrs('img')),c['id']
                        for key in ('url','license_url','creator','evidence','note','checked'): assert escape(e[key]) in html,(c['id'],'missing example provenance',key)

                # Disclosure changes visibility, never the complete record or its source links.
                for p in c.get('pr',[]):
                    for key in ('p','pn','nt'): assert escape(p.get(key,'')) in html,(c['id'],'missing product text',key)
                    for e in p.get('sp',{}).values():
                        assert escape(e['v']) in html,(c['id'],'missing product value')
                        for sid in e.get('s',[]):assert escape(data['src'][sid]['u']) in html,(c['id'],'missing product source')
                for a in parsed.attrs('a'):
                    if a.get('href','').startswith('#'):assert a['href'][1:] in parsed.ids,(c['id'],'broken guide anchor',a['href'])
    library=(ROOT/'materials/index.html').read_text()
    check_printer_directory(printers, printer_photos)
    assert len(re.findall(r'data-material="[^"]+"',library))==len(filaments['cats'])
    assert set(EXAMPLES)<=set(c['id'] for c in filaments['cats'])
    assert not (ROOT/'assets/materials').exists() or not list((ROOT/'assets/materials').glob('*.svg'))
    for key,entries in EXAMPLES.items():
        assert entries,(key,'empty example list')
        for e in entries:
            assert e['creator'] and e['evidence'] and e['note'] and e['material']
            assert e['url'].startswith('https://www.printables.com/model/')
            assert e['license'] and e['license_url'].startswith('https://')
            if e.get('image'):
                assert e['image'].startswith('assets/prints/') and '..' not in e['image']
                photo=ROOT/e['image']
                assert hashlib.sha256(photo.read_bytes()).hexdigest()==e['sha256'],(key,'photo bytes changed')
                assert e['width']>0 and e['height']>0 and e['alt']
                assert e['image_url'].startswith('https://media.printables.com/media/prints/')
                assert e['license_url'].startswith('https://creativecommons.org/')
            else:
                assert not {'image_url','sha256','width','height','alt'} & e.keys(),(key,'partial photo metadata')
            assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',e['checked'])
            assert escape(e['url']) in (ROOT/'materials'/(key+'.html')).read_text()
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls=[x.text for x in ET.parse(ROOT/'sitemap.xml').findall('s:url/s:loc',ns)]
    assert len(urls)==len(set(urls)) and set(urls)==canonicals,('sitemap/canonical mismatch',set(urls)^canonicals)
    revisions={url.find('s:loc',ns).text:url.find('s:lastmod',ns).text for url in ET.parse(ROOT/'sitemap.xml').findall('s:url',ns)}
    for name in PAGES:assert revisions[BASE+name]==CATALOG_DATE
    for article in article_data['articles']:assert revisions[BASE+'articles/'+article['id']+'.html']==article['modified']
    for printer in printers['cats']:assert revisions[BASE+'printers/'+printer['id']+'.html']==PRINTER_DATE
    assert revisions[BASE+'printers/']==PRINTER_DATE
    robots=(ROOT/'robots.txt').read_text()
    assert 'Disallow:' not in robots and BASE+'sitemap.xml' in robots
    # Staleness test: sync must be idempotent across all generated pages/metadata.
    files=[*paths,ROOT/'sitemap.xml',ROOT/'assets/materials.css',
           *(ROOT/'assets/printers'/(family.lower()+'.svg') for family in printers['families'])]
    before={p:p.read_bytes() for p in files}
    subprocess.run(['python3',str(ROOT/'scripts/sync_site.py')],check=True,capture_output=True)
    assert all(p.read_bytes()==content for p,content in before.items()),'Generated files out of date: run python scripts/sync_site.py'
    print(f'{len(paths)} pages validated: metadata, links, scripts, GA, sitemap, fallbacks and generated content agree.')

if __name__=='__main__':run()
