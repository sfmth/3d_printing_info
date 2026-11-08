"""Static matchups must preserve catalog evidence and form a complete crawl graph."""
import copy
import hashlib
import json
import re
from itertools import combinations
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pair_comparisons import generate_comparisons, pair_path
from comparison_hub import render_hub
from check_site import Document, validate_pair_comparisons
from sync_site import PAGES, ROOT, payload

BASE = 'https://example.org/project/'


def sample_catalog():
    return {
        'sections': {'A': 'Identity', 'B': 'Properties', 'C': 'Unreported'},
        'fields': [
            {'id': 'A1', 'sec': 'A', 'name': 'Exact identity', 'unit': ''},
            {'id': 'B1', 'sec': 'B', 'name': 'Strength & conditions', 'unit': 'MPa'},
            {'id': 'B2', 'sec': 'B', 'name': 'Temperature', 'unit': '°C'},
            {'id': 'C1', 'sec': 'C', 'name': 'Never documented', 'unit': ''},
        ],
        'families': ['FDM'],
        'cats': [
            {'id': 'z', 'n': 'Zeta', 'sh': 'Zeta', 'f': 'FDM', 'sp': {'A1': {'v': 'Zeta'}}},
            {'id': 'b', 'n': 'Beta', 'sh': 'Beta', 'f': 'FDM', 'sp': {
                'A1': {'v': 'Beta'}, 'B1': {'v': '>30 MPa; XY, dry', 'n': 30, 's': ['s1']},
            }},
            {'id': 'a', 'n': 'Alpha & <prototype>', 'sh': 'Alpha', 'f': 'FDM', 'sp': {
                'A1': {'v': 'Alpha & <prototype>'},
                'B1': {'v': '>30 MPa; XY, dry', 'n': 30, 's': ['s1']},
                'B2': {'v': '80–95 °C; <2 h', 's': ['s1', 's2']},
            }},
        ],
        'src': {
            's1': {'t': 'Test <conditions> & results', 'u': 'https://example.org/source?a=1&b=2', 'p': 'Test lab', 'd': '2026-09-01', 'k': 'experiment'},
            's2': {'t': 'Separate thermal source', 'u': 'https://example.org/thermal', 'p': 'Manufacturer', 'd': '2025-12', 'k': 'tds'},
        },
    }


class PairComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.datasets = {name: copy.deepcopy(sample_catalog()) for name in PAGES}
        # Only local existence is checked; fixture sources never contact a network.
        for name in ['index.html', 'privacy.html', 'sitemap.xml', 'feed.xml', 'atom.xml', *PAGES,
                     'assets/site-icon.svg', 'assets/pair-comparisons.css', 'assets/pair-comparisons.js',
                     'assets/comparison-hub.css', 'assets/comparison-hub.js',
                     'assets/analytics-consent.css', 'assets/analytics-consent.js']:
            target = self.root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('fixture')
        for kind in ['materials', 'printers']:
            for cat in sample_catalog()['cats']:
                target = self.root/kind/(cat['id']+'.html')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('fixture guide')
        self.paths = generate_comparisons(self.root, BASE, self.datasets)

    def validate(self):
        return validate_pair_comparisons(self.root, BASE, self.datasets)

    def rewrite_pair(self, transform, update_manifest=True):
        relative = pair_path('materials', 'a', 'b')
        target = self.root/relative
        old = target.read_text()
        new = transform(old)
        self.assertNotEqual(new, old, 'Mutation must change the fixture')
        target.write_text(new)
        if update_manifest:
            manifest_path = self.root/'data/pair-comparison-manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['pages'][relative] = hashlib.sha256(target.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))

    def test_one_url_for_each_unordered_pair_and_complete_directories(self):
        pairs, directories, _ = self.validate()
        self.assertEqual(len(pairs), 6)
        self.assertEqual(len(directories), 9)
        self.assertEqual(len(self.paths), len(set(self.paths)))
        for a, b in combinations(['z', 'a', 'b'], 2):
            self.assertEqual(pair_path('materials', a, b), pair_path('materials', b, a))
        self.assertEqual(pair_path('materials', 'z', 'a'), 'compare/materials/a-vs-z.html')

    def test_hub_accepts_catalog_aliases_and_escapes_names_with_featured_pairs(self):
        catalogs = {
            'materials': {'cats': [{'id': 'pla', 'n': 'PLA & <prototype>'}, {'id': 'petg', 'n': 'PETG'}]},
            'printers': {'cats': [{'id': 'bambu-a1', 'n': 'A1'}, {'id': 'bambu-p1s', 'n': 'P1S'}]},
        }
        html = render_hub(catalogs)
        self.assertEqual(html, render_hub({'filaments.html': catalogs['materials'], 'comparison.html': catalogs['printers']}))
        self.assertIn('PLA &amp; &lt;prototype&gt;', html)
        doc = Document(html).root
        links = {node.attrs['href'] for node in doc.find('a')}
        self.assertTrue({'materials/petg-vs-pla.html', 'printers/bambu-a1-vs-bambu-p1s.html'} <= links)
        self.assertEqual(len(list(doc.find('select'))), 4)

    def test_bare_two_link_hub_is_rejected_even_with_a_matching_manifest(self):
        path = self.root/'compare/index.html'
        html = re.sub(r'<main>.*?</main>', '<main><a href="materials/">Filaments</a><a href="printers/">Printers</a></main>', path.read_text(), flags=re.S)
        path.write_text(html)
        manifest_path = self.root/'data/pair-comparison-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['pages']['compare/'] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(AssertionError, 'Missing comparison browse cards'):
            self.validate()

    def test_union_preserves_values_qualifiers_conditions_and_exact_sources(self):
        self.validate()
        document = Document((self.root/pair_path('materials', 'a', 'b')).read_text()).root
        rows = {row.attrs['data-field']: row for row in document.find('tr') if 'data-field' in row.attrs}
        self.assertEqual(set(rows), {'A1', 'B1', 'B2'})
        self.assertEqual(rows['B1'].attrs['data-different'], 'false')
        self.assertEqual([node.text for node in rows['B1'].find(cls='value')], ['>30 MPa; XY, dry']*2)
        self.assertEqual([node.text for node in rows['B2'].find(cls='value')], ['80–95 °C; <2 h', 'Not documented'])
        missing = list(rows['B2'].find('td'))[1]
        self.assertNotIn('data-sources', missing.attrs)
        self.assertIn('missing', missing.attrs['class'])
        sources = [node for node in document.find('li') if 'data-source-id' in node.attrs]
        self.assertEqual([node.attrs['data-source-id'] for node in sources], ['s1', 's2'])
        self.assertEqual(list(sources[0].find('a'))[0].attrs['href'], sample_catalog()['src']['s1']['u'])
        self.assertIn('Test <conditions> & results', sources[0].text)
        self.assertEqual(len(list(document.find('script'))), 3, 'Catalog text cannot inject script markup')

    def test_checker_rejects_loss_of_a_qualifier_even_with_updated_hash(self):
        self.rewrite_pair(lambda html: html.replace('&gt;30 MPa; XY, dry', '30 MPa; XY, dry', 1))
        with self.assertRaisesRegex(AssertionError, 'Published value changed'):
            self.validate()

    def test_checker_rejects_transferred_field_sources(self):
        self.rewrite_pair(lambda html: html.replace('data-sources="s1 s2"', 'data-sources="s2"', 1))
        with self.assertRaisesRegex(AssertionError, 'Field source mismatch'):
            self.validate()

    def test_checker_rejects_a_changed_field_unit(self):
        self.rewrite_pair(lambda html: html.replace('<small>MPa</small>', '<small>kPa</small>', 1))
        with self.assertRaisesRegex(AssertionError, 'Field unit changed'):
            self.validate()

    def test_checker_rejects_a_dropped_documented_field(self):
        self.rewrite_pair(lambda html: re.sub(r'<tr data-field="B2".*?</tr>', '', html, count=1))
        with self.assertRaisesRegex(AssertionError, 'Lost or extra documented field'):
            self.validate()

    def test_checker_rejects_broken_local_targets(self):
        self.rewrite_pair(lambda html: html.replace('href="./a/"', 'href="./missing-item/"', 1))
        with self.assertRaisesRegex(AssertionError, 'Missing local target'):
            self.validate()

    def test_pair_metadata_cannot_become_a_second_dataset(self):
        self.rewrite_pair(lambda html: html.replace('</head>', '<script type="application/ld+json">{"@type":"Dataset"}</script></head>', 1))
        with self.assertRaisesRegex(AssertionError, 'Unsupported comparison metadata'):
            self.validate()

    def test_checker_rejects_manifest_drift(self):
        self.rewrite_pair(lambda html: html.replace('>Not documented<', '>Unknown<', 1), update_manifest=False)
        with self.assertRaisesRegex(AssertionError, 'Stale pair manifest'):
            self.validate()

    def test_self_pairs_and_unsafe_ids_are_rejected(self):
        for kind, a, b in [('materials', 'a', 'a'), ('printers', '../a', 'b'), ('materials', 'A', 'b'), ('unknown', 'a', 'b')]:
            with self.subTest(kind=kind, a=a, b=b), self.assertRaises(ValueError):
                pair_path(kind, a, b)

    def test_ambiguous_pair_names_raise_a_collision(self):
        data = sample_catalog()
        data['cats'] = [dict(data['cats'][0], id=key, n=key, sh=key) for key in ['a', 'a-vs-b', 'b-vs-c', 'c']]
        with self.assertRaisesRegex(ValueError, 'collision'):
            generate_comparisons(self.root, BASE, {name: copy.deepcopy(data) for name in PAGES})

    def test_generation_is_idempotent_and_removes_only_owned_obsolete_html(self):
        files = list((self.root/'compare').rglob('*.html'))
        before = {path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in files}
        manifest = (self.root/'data/pair-comparison-manifest.json').read_bytes()
        stale = self.root/'compare/materials/obsolete.html'
        stale.write_text('obsolete')
        unrelated = self.root/'materials/unrelated.html'
        unrelated.write_text('preserve')
        self.assertEqual(generate_comparisons(self.root, BASE, self.datasets), self.paths)
        self.assertFalse(stale.exists())
        self.assertEqual(unrelated.read_text(), 'preserve')
        self.assertEqual((self.root/'data/pair-comparison-manifest.json').read_bytes(), manifest)
        self.assertEqual({path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in files}, before)

    def test_real_catalog_ids_have_no_pair_path_collisions(self):
        for kind, catalog in [('materials', 'filaments.html'), ('printers', 'comparison.html')]:
            ids = [cat['id'] for cat in payload((ROOT/catalog).read_text())['cats']]
            paths = [pair_path(kind, a, b) for a, b in combinations(ids, 2)]
            self.assertEqual(len(paths), len(set(paths)))
            self.assertEqual(len(paths), len(ids)*(len(ids)-1)//2)


if __name__ == '__main__':
    unittest.main()
