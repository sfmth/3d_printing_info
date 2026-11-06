"""Verify publication history, canonical discovery links and both feed formats."""
import copy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from updates_feed import ATOM, feed_head, generate_updates, load_updates, validate_updates

BASE = 'https://example.org/library/'
NS = {'a': ATOM}


def fixture():
    return {
        'version': 1, 'title': 'Updates & evidence', 'description': 'A <curated> record, not a build clock.',
        'entries': [
            {'id': 'older-release', 'title': 'Older comparison', 'published': '2026-10-18T22:23:25Z',
             'updated': '2026-10-18T22:23:25Z', 'summary': 'Sources keep their dates.',
             'links': [{'path': 'articles/', 'title': 'Selection articles'}], 'commit': 'a'*40},
            {'id': 'newer-release', 'title': 'ASA & PLA <comparison>', 'published': '2026-10-31T17:30:57Z',
             'updated': '2026-11-01T18:20:03Z', 'summary': 'Two <families> & dated sources; "unknown" stays unknown.',
             'links': [{'path': 'compare/materials/asa-vs-pla.html', 'title': 'ASA & PLA'},
                       {'path': 'compare/', 'title': 'All comparisons'}], 'commit': 'b'*40},
        ],
    }


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.ids = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('a', 'link'):
            self.links.append((tag, attrs))
        if attrs.get('id'):
            self.ids.append(attrs['id'])


class UpdatesFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'data').mkdir()
        self.data = fixture()

    def generate(self, data=None, base=BASE):
        (self.root/'data/site-updates.json').write_text(json.dumps(data or self.data), encoding='utf-8')
        return generate_updates(self.root, base)

    def xml(self, filename):
        return ET.parse(self.root/filename).getroot()

    def test_rss_and_atom_have_complete_dates_absolute_links_and_stable_ids(self):
        self.assertEqual(self.generate(), {'updates/': '2026-11-01'})
        rss = self.xml('feed.xml')
        self.assertEqual(rss.tag, 'rss')
        self.assertEqual(rss.attrib['version'], '2.0')
        channel = rss.find('channel')
        self.assertEqual(channel.findtext('title'), self.data['title'])
        self.assertEqual(channel.findtext('link'), BASE+'updates/')
        self.assertEqual(channel.find('a:link', NS).attrib,
                         {'href': BASE+'feed.xml', 'rel': 'self', 'type': 'application/rss+xml'})
        items = channel.findall('item')
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].findtext('guid'), BASE+'updates/#newer-release')
        self.assertEqual(items[0].find('guid').attrib, {'isPermaLink': 'true'})
        self.assertEqual(items[0].findtext('link'), BASE+'compare/materials/asa-vs-pla.html')
        self.assertEqual(items[0].findtext('title'), 'ASA & PLA <comparison>')
        self.assertEqual(parsedate_to_datetime(items[0].findtext('pubDate')),
                         datetime(2026, 10, 31, 17, 30, 57, tzinfo=timezone.utc))
        self.assertEqual(parsedate_to_datetime(channel.findtext('lastBuildDate')),
                         datetime(2026, 11, 1, 18, 20, 3, tzinfo=timezone.utc))
        atom = self.xml('atom.xml')
        self.assertEqual(atom.tag, '{'+ATOM+'}feed')
        self.assertEqual(atom.findtext('a:id', namespaces=NS), BASE+'updates/')
        self.assertEqual(atom.findtext('a:updated', namespaces=NS), '2026-11-01T18:20:03Z')
        self.assertEqual(atom.find('a:link[@rel="self"]', NS).attrib,
                         {'rel': 'self', 'href': BASE+'atom.xml', 'type': 'application/atom+xml'})
        entries = atom.findall('a:entry', NS)
        self.assertEqual([item.findtext('a:id', namespaces=NS) for item in entries],
                         [item.findtext('guid') for item in items])
        self.assertEqual(entries[0].findtext('a:published', namespaces=NS), '2026-10-31T17:30:57Z')
        self.assertEqual(entries[0].findtext('a:updated', namespaces=NS), '2026-11-01T18:20:03Z')
        self.assertEqual(entries[0].find('a:content', NS).attrib, {'type': 'html'})
        self.assertIn('https://github.com/sfmth/3d_printing_info/commit/'+'b'*40,
                      entries[0].findtext('a:content', namespaces=NS))

    def test_feed_and_html_text_are_escaped_without_losing_real_links(self):
        self.generate()
        rss_html = self.xml('feed.xml').findtext('channel/item/description')
        atom_html = self.xml('atom.xml').findtext('a:entry/a:content', namespaces=NS)
        self.assertEqual(rss_html, atom_html)
        for source in [rss_html, atom_html, (self.root/'updates/index.html').read_text()]:
            self.assertIn('Two &lt;families&gt; &amp; dated sources;', source)
            parsed = Links(source)
            hrefs = [attrs['href'] for _, attrs in parsed.links]
            self.assertIn(BASE+'compare/materials/asa-vs-pla.html', hrefs)
            self.assertIn(BASE+'compare/', hrefs)
            self.assertNotIn('<families>', source)
        archive = (self.root/'updates/index.html').read_text()
        self.assertIn('<time datetime="2026-10-31T17:30:57Z">October 31, 2026</time>', archive)
        self.assertIn('newer-release', Links(archive).ids)
        head_links = [attrs for tag, attrs in Links(archive).links if tag == 'link']
        self.assertEqual([attrs['href'] for attrs in head_links if attrs.get('rel') == 'canonical'], [BASE+'updates/'])
        self.assertEqual({attrs['type']: attrs['href'] for attrs in head_links if attrs.get('rel') == 'alternate'},
                         {'application/rss+xml': BASE+'feed.xml', 'application/atom+xml': BASE+'atom.xml'})
        self.assertIn('../assets/materials.css', archive)
        self.assertIn('../assets/analytics-consent.js', archive)
        self.assertIn('data-analytics-settings hidden', archive)
        self.assertIn('href="../privacy.html"', archive)

    def test_rebuild_is_deterministic_and_does_not_refresh_publication_dates(self):
        self.generate()
        paths = [self.root/path for path in ('feed.xml', 'atom.xml', 'updates/index.html')]
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
        self.generate()
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths})
        changed = copy.deepcopy(self.data)
        changed['entries'].reverse()
        self.generate(changed)
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths})
        changed['entries'][0]['title'] = 'A corrected title'
        self.generate(changed)
        ids = [entry.findtext('a:id', namespaces=NS) for entry in self.xml('atom.xml').findall('a:entry', NS)]
        self.assertEqual(ids, [BASE+'updates/#newer-release', BASE+'updates/#older-release'])
        self.assertEqual(self.xml('atom.xml').findtext('a:updated', namespaces=NS), '2026-11-01T18:20:03Z')

    def test_websub_is_only_advertised_when_explicitly_configured(self):
        self.generate()
        self.assertIsNone(self.xml('feed.xml').find('channel/a:link[@rel="hub"]', NS))
        self.assertIsNone(self.xml('atom.xml').find('a:link[@rel="hub"]', NS))
        configured = copy.deepcopy(self.data)
        configured['websub_hub'] = 'https://pubsubhubbub.appspot.com/'
        self.generate(configured)
        self.assertEqual(self.xml('feed.xml').find('channel/a:link[@rel="hub"]', NS).get('href'), configured['websub_hub'])
        self.assertEqual(self.xml('atom.xml').find('a:link[@rel="hub"]', NS).get('href'), configured['websub_hub'])

    def test_rejects_invalid_dates_duplicate_ids_and_untraceable_records(self):
        mutations = [
            lambda data: data.update(version=True),
            lambda data: data.update(entries=[]),
            lambda data: data['entries'][0].update(published='2026-10-18'),
            lambda data: data['entries'][0].update(published='2026-10-18T22:23:25'),
            lambda data: data['entries'][0].update(published='2026-02-31T22:23:25Z'),
            lambda data: data['entries'][0].update(updated='2026-10-17T22:23:25Z'),
            lambda data: data['entries'][0].update(commit='short-sha'),
            lambda data: data['entries'][0].update(id=data['entries'][1]['id']),
            lambda data: data['entries'][0].update(summary='bad\x00text'),
            lambda data: data['entries'][0].update(links=[]),
            lambda data: data['entries'][0].update(unrecognized='silent typo'),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.data)
                mutation(data)
                with self.assertRaises(ValueError):
                    self.generate(data)
                self.assertFalse((self.root/'feed.xml').exists(), 'Invalid records must fail before output')

    def test_rejects_offsite_or_noncanonical_update_links(self):
        for path in ['https://elsewhere.example/x.html', '//elsewhere.example/x.html', '../escape.html',
                     'articles/../escape.html', '/articles/', 'articles/?view=new', 'articles/#new',
                     'articles/%2e%2e/escape.html', 'articles\\escape.html', 'javascript:alert(1)',
                     'articles//', 'feed.xml']:
            with self.subTest(path=path):
                data = copy.deepcopy(self.data)
                data['entries'][0]['links'][0]['path'] = path
                with self.assertRaises(ValueError):
                    validate_updates(data)
        for hub in ['http://hub.example/', '//hub.example/', 'https://user:password@hub.example/',
                    'https://hub.example/#fragment']:
            data = copy.deepcopy(self.data)
            data['websub_hub'] = hub
            with self.assertRaises(ValueError):
                validate_updates(data)

    def test_discovery_links_use_the_supplied_base_at_any_depth(self):
        head = Links(feed_head(BASE))
        self.assertEqual({link['href'] for _, link in head.links}, {BASE+'feed.xml', BASE+'atom.xml'})
        for base in ['http://example.org/', 'https://example.org/library', 'https://example.org/?query=x',
                     'https://user:secret@example.org/', 'https://example.org/#anchor']:
            with self.subTest(base=base), self.assertRaises(ValueError):
                self.generate(base=base)

    def test_curated_repository_updates_have_unique_history_and_real_content_targets(self):
        root = Path(__file__).resolve().parents[1]
        data = load_updates(root)
        self.assertEqual(data['websub_hub'], 'https://pubsubhubbub.appspot.com/')
        self.assertGreaterEqual(len(data['entries']), 4)
        # Generated comparisons may be absent in a clean checkout; their tracked
        # manifest is the authoritative inventory, not a network request.
        manifest = json.loads((root/'data/pair-comparison-manifest.json').read_text())['pages']
        for entry in data['entries']:
            for link in entry['links']:
                path = link['path']
                target = root/(path+'index.html' if path.endswith('/') else path)
                self.assertTrue(target.exists() or path in manifest, path)


if __name__ == '__main__':
    unittest.main()
