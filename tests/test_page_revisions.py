"""Navigation release dates must not imply fresh research or catalog prices."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from comparison_discovery import COMPARISONS
from material_articles import article_body, generate_articles, load_articles, load_evidence
from page_revisions import (COMPARISON_NAVIGATION_PATHS, COMPARISON_NAVIGATION_RELEASE,
                            page_revision)
from sync_site import BASE, ROOT, guide_page


class PageRevisionTests(unittest.TestCase):
    def test_release_inventory_covers_exactly_the_published_panels(self):
        guide_paths = {item['kind'] + '/' + item[key] + '.html'
                       for item in COMPARISONS for key in ('left', 'right')}
        article_paths = {'articles/' + article['id'] + '.html'
                         for article in load_articles()['articles']
                         if any(item['kind'] == 'materials' and
                                {item['left'], item['right']} <= set(article['materials'])
                                for item in COMPARISONS)}
        self.assertEqual(COMPARISON_NAVIGATION_PATHS, guide_paths | article_paths)
        self.assertEqual(len(COMPARISON_NAVIGATION_PATHS), 23)
        self.assertEqual(sum(p.startswith('materials/') for p in COMPARISON_NAVIGATION_PATHS), 10)
        self.assertEqual(sum(p.startswith('printers/') for p in COMPARISON_NAVIGATION_PATHS), 6)
        self.assertEqual(sum(p.startswith('articles/') for p in COMPARISON_NAVIGATION_PATHS), 7)

    def test_affected_revision_wins_without_backdating_later_content(self):
        for path in COMPARISON_NAVIGATION_PATHS:
            with self.subTest(path=path):
                self.assertEqual(page_revision(path, '2026-10-18'), COMPARISON_NAVIGATION_RELEASE)
                self.assertEqual(page_revision(path, '2026-12-01'), '2026-12-01')

    def test_unrelated_pages_and_pair_inventory_keep_existing_dates(self):
        paths = ('materials/peba.html', 'printers/neptune4pro.html',
                 'articles/not-yet-published.html', 'articles/', 'materials/',
                 'printers/', 'materials/index.html', 'printers/index.html',
                 'articles/index.html', 'compare/materials/asa-vs-pla.html',
                 'comparison.html', 'filaments.html', 'privacy.html', '')
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(page_revision(path, '2026-10-29'), '2026-10-29')

    def test_invalid_base_date_is_not_silently_replaced(self):
        with self.assertRaises(ValueError):
            page_revision('materials/pla.html', 'not a date')

    def render_guide(self, path, schema=None):
        schema = schema or {'@context': 'https://schema.org', '@type': 'WebPage',
                            'mainEntity': {'@type': 'TechArticle', 'headline': 'A guide'}}
        html = guide_page('A guide', 'Description', path, '<h1>A guide</h1>', '', '', schema)
        metadata = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html)[1])
        return html, metadata

    def test_affected_guide_footer_and_both_metadata_levels_agree(self):
        schema = {'@type': 'WebPage', 'mainEntity': {'@type': 'TechArticle',
                  'datePublished': '2026-10-01'}}
        before = deepcopy(schema)
        for path in ('materials/pla.html', 'printers/bambu-p1s.html'):
            html, metadata = self.render_guide(path, schema)
            self.assertIn('Page revision: 2026-11-05.', html)
            self.assertIn('Catalog values retain their original source dates.', html)
            self.assertEqual(metadata['dateModified'], '2026-11-05')
            self.assertEqual(metadata['mainEntity']['dateModified'], '2026-11-05')
            self.assertEqual(metadata['mainEntity']['datePublished'], '2026-10-01')
        self.assertEqual(schema, before, 'rendering must not mutate caller metadata')

    def test_unaffected_guides_keep_footers_and_do_not_gain_dates(self):
        for path in ('materials/peba.html', 'printers/neptune4pro.html'):
            html, metadata = self.render_guide(path)
            self.assertIn('Page revision: 2026-10-29.', html)
            self.assertNotIn('dateModified', metadata)
            self.assertNotIn('dateModified', metadata['mainEntity'])

    def test_unaffected_existing_metadata_is_retained(self):
        schema = {'@type': 'WebPage', 'dateModified': '2026-10-15',
                  'mainEntity': {'@type': 'TechArticle', 'dateModified': '2026-10-14'}}
        _, metadata = self.render_guide('materials/peba.html', schema)
        self.assertEqual(metadata['dateModified'], '2026-10-15')
        self.assertEqual(metadata['mainEntity']['dateModified'], '2026-10-14')

    def test_article_body_distinguishes_navigation_and_evidence_revision(self):
        article = load_articles()['articles'][0]
        evidence = load_evidence()
        before = deepcopy((article, evidence))
        html = article_body(article, evidence)
        self.assertIn('Article revised <time datetime="2026-10-18">2026-10-18</time>', html)
        self.assertIn('Page navigation revised <time datetime="2026-11-05">2026-11-05</time>', html)
        self.assertEqual((article, evidence), before)

    def test_rendered_article_dates_preserve_evidence_and_index_revisions(self):
        data, evidence = load_articles(), load_evidence()
        before = deepcopy((data, evidence))
        source_bytes = {name: (ROOT / 'data' / name).read_bytes()
                        for name in ('material-articles.json', 'article-evidence.json')}
        with TemporaryDirectory() as directory, patch('material_articles.ROOT', Path(directory)), \
                patch('material_articles.load_articles', return_value=data), \
                patch('material_articles.load_evidence', return_value=evidence):
            material_ids = {key for article in data['articles'] for key in article['materials']}
            generate_articles(BASE, '', guide_page, material_ids)
            for article in data['articles']:
                path = 'articles/' + article['id'] + '.html'
                html = (Path(directory) / path).read_text()
                metadata = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html)[1])
                self.assertEqual(metadata['dateModified'], '2026-11-05')
                self.assertEqual(metadata['mainEntity']['dateModified'], '2026-11-05')
                self.assertEqual(metadata['mainEntity']['datePublished'], article['published'])
                self.assertIn('Page revision: 2026-11-05. Article revision: 2026-10-18.', html)
                self.assertIn('Measurements retain their source dates.', html)
            index = (Path(directory) / 'articles/index.html').read_text()
            self.assertIn('Article library revision: 2026-10-18.', index)
            self.assertNotIn('2026-11-05', index)
        self.assertEqual((data, evidence), before)
        for name, content in source_bytes.items():
            self.assertEqual((ROOT / 'data' / name).read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
