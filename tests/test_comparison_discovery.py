"""Curated discovery must reach canonical pairs without changing source evidence."""
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from comparison_discovery import (COMPARISONS, FEATURED, render_article_comparisons,
                                  render_guide_comparisons, render_home_comparisons,
                                  validate_discovery)
from material_articles import article_body, load_articles, load_evidence
from pair_comparisons import pair_path, short_name
from sync_site import ROOT, payload


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.hrefs = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(dict(attrs).get('href'))


class ComparisonDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datasets = {name: payload((ROOT / name).read_text())
                        for name in ('filaments.html', 'comparison.html')}
        cls.catalogs = {kind: cls.datasets[name] for kind, name in
                        (('materials', 'filaments.html'), ('printers', 'comparison.html'))}

    def test_thirteen_valid_canonical_pairs_and_eight_featured(self):
        resolved = validate_discovery(self.datasets)
        self.assertEqual(len(resolved), 13)
        self.assertEqual(len({item['path'] for item in resolved}), 13)
        self.assertEqual(len(FEATURED), 8)
        for item in resolved:
            self.assertEqual(item['path'], pair_path(item['kind'], item['right'], item['left']))
            cats = {cat['id']: cat for cat in self.catalogs[item['kind']]['cats']}
            self.assertEqual(item['title'], ' vs '.join(short_name(cats[key], item['kind'])
                             for key in sorted((item['left'], item['right']))))

    def test_every_featured_pair_is_reachable_from_home_and_both_guides(self):
        home = Links(render_home_comparisons(self.datasets)).hrefs
        self.assertEqual(home, [*FEATURED, 'compare/'])
        for item in validate_discovery(self.datasets):
            data = self.catalogs[item['kind']]
            cats = {cat['id']: cat for cat in data['cats']}
            for key in (item['left'], item['right']):
                html = render_guide_comparisons(item['kind'], cats[key], data)
                self.assertIn('../' + item['path'], Links(html).hrefs)
                self.assertIn('id="selected-comparisons"', html)

    def test_unselected_guide_gets_no_irrelevant_panel(self):
        data = self.catalogs['materials']
        cat = next(cat for cat in data['cats'] if cat['id'] == 'peba')
        self.assertEqual(render_guide_comparisons('materials', cat, data), '')

    def test_article_pairs_require_both_candidate_materials(self):
        data = self.catalogs['materials']
        article = {'materials': {'pla': 'PLA', 'petg': 'PETG'}}
        html = render_article_comparisons(article, data)
        self.assertEqual(Links(html).hrefs, ['../compare/materials/petg-vs-pla.html'])
        self.assertIn('grade-specific measurements and test conditions', html)
        self.assertEqual(render_article_comparisons({'materials': {'pla': 'PLA'}}, data), '')

    def test_article_integration_preserves_existing_evidence_and_legacy_callers(self):
        evidence = load_evidence()
        for article in load_articles()['articles']:
            before = article_body(article, evidence)
            added = render_article_comparisons(article, self.catalogs['materials'])
            after = article_body(article, evidence, catalog_data=self.catalogs['materials'])
            self.assertEqual(after.replace(added, '', 1) if added else after, before)
            if added:
                self.assertLess(after.index('id="related-materials"'), after.index('id="catalog-comparisons"'))
                self.assertLess(after.index('id="catalog-comparisons"'), after.index('id="sources"'))

    def test_reject_unknown_id_self_pair_unknown_kind_and_reversed_duplicate(self):
        original = copy.deepcopy(COMPARISONS[0])
        invalid = [dict(original, left='not-a-catalog-id'),
                   dict(original, right=original['left']), dict(original, kind='mixed')]
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                validate_discovery(self.datasets, [item])
        reversed_pair = dict(original, left=original['right'], right=original['left'])
        with self.assertRaisesRegex(ValueError, 'Duplicate unordered'):
            validate_discovery(self.datasets, [original, reversed_pair])

    def test_reject_duplicate_catalog_ids_and_missing_explanations(self):
        datasets = copy.deepcopy(self.datasets)
        datasets['filaments.html']['cats'].append(copy.deepcopy(datasets['filaments.html']['cats'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate catalog ID'):
            validate_discovery(datasets)
        with self.assertRaisesRegex(ValueError, 'explanation'):
            validate_discovery(self.datasets, [dict(COMPARISONS[0], description=' ')])

    def test_labels_are_escaped_and_resolved_from_the_catalog(self):
        datasets = copy.deepcopy(self.datasets)
        cat = next(cat for cat in datasets['filaments.html']['cats'] if cat['id'] == 'pla')
        cat['sh'] = 'PLA <special> & revised'
        html = render_home_comparisons(datasets)
        self.assertIn('PLA &lt;special&gt; &amp; revised', html)
        self.assertNotIn('<special>', html)
        self.assertIn('compare/materials/petg-vs-pla.html', Links(html).hrefs)


if __name__ == '__main__':
    unittest.main()
