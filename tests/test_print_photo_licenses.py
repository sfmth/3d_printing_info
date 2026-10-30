"""Attribution roles, individual terms and complete licensed image display."""
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import material_design as design


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.images = []
        self.links = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))
        elif tag == 'a':
            self.links.append(dict(attrs))

    def handle_data(self, data):
        self.text.append(data)


def example(license='CC BY-NC-ND 4.0'):
    return {
        'title': 'A flexible stand', 'material': 'TPU 85A',
        'creator': 'Listing uploader', 'creator_role': 'listing uploader',
        'platform': 'Printables', 'url': 'https://www.printables.com/model/123-stand',
        'image': 'assets/prints/stand.jpg',
        'image_url': 'https://media.printables.com/media/prints/123/stand.jpg',
        'alt': 'Stand shown in the uploader’s listing', 'width': 800, 'height': 600,
        'license': license, 'license_url': 'https://creativecommons.org/licenses/by-nc-nd/4.0/',
        'checked': '2026-10-17', 'photo_author': None,
        'evidence': 'Printed in TPU 85A.', 'note': 'A stand reported in flexible TPU.',
    }


def category(cid='sample'):
    return {'id': cid, 'n': 'Sample material', 'f': 'FLEX', 'sp': {}, 'pr': [], 'sum': 'Flexible parts.'}


class PrintPhotoLicenseTests(unittest.TestCase):
    def assert_credit(self, html, e):
        parsed = Markup(html)
        text = ' '.join(parsed.text)
        self.assertIn('listing uploaded by '+e['creator'], text)
        self.assertIn('Image bytes unchanged; displayed in full.', text)
        self.assertNotIn('Photo & model by', text)
        self.assertNotIn('Photo and model:', text)
        self.assertIn(e['license'], text)
        self.assertTrue(any(a.get('href') == e['license_url'] and a.get('rel') == 'license'
                            for a in parsed.links))
        self.assertTrue(any(a.get('href') == e['image_url'] for a in parsed.links))
        return parsed

    def test_hero_retains_source_and_terms_without_inventing_authorship(self):
        e = example()
        parsed = self.assert_credit(design.photograph(e), e)
        self.assertIn('photo-no-derivatives', parsed.images[0]['class'].split())
        self.assertNotIn('Image author:', ' '.join(parsed.text))

    def test_directory_and_related_cards_keep_terms_outside_the_guide_link(self):
        e = example()
        with patch.dict(design.EXAMPLES, {'sample': [e]}):
            for featured in [False, True]:
                with self.subTest(featured=featured):
                    parsed = self.assert_credit(design.card(category(), featured), e)
                    self.assertEqual(parsed.images[0]['src'], '../'+e['image'])
                    self.assertIn('photo-no-derivatives', parsed.images[0]['class'].split())
                    self.assertTrue(any(a.get('href') == e['url'] for a in parsed.links))

    def test_secondary_photo_and_model_only_story_keep_distinct_provenance(self):
        primary = example('CC BY 4.0')
        secondary = example()
        secondary['title'] = 'Secondary stand'
        linked = {k: v for k, v in example().items()
                  if k not in {'image', 'image_url', 'width', 'height', 'alt', 'photo_author'}}
        linked['image_omission_reason'] = 'Linked only; underlying design rights are unverified.'
        with patch.dict(design.EXAMPLES, {'sample': [primary, secondary, linked]}):
            parsed = self.assert_credit(design.print_section({}, category(), lambda *a: ''), secondary)
        self.assertEqual(len(parsed.images), 1)
        self.assertIn('photo-no-derivatives', parsed.images[0]['class'].split())
        self.assertIn(linked['image_omission_reason'], ' '.join(parsed.text))

    def test_noncommercial_sharealike_and_nd_conditions_remain_individual(self):
        for licence, expected in [
            ('CC BY 4.0', []),
            ('CC BY-NC 4.0', ['Noncommercial reuse only.']),
            ('CC BY-SA 4.0', ['ShareAlike applies to adaptations.']),
            ('CC BY-NC-SA 4.0', ['Noncommercial reuse only.', 'ShareAlike applies to adaptations.']),
            ('CC BY-NC-ND 4.0', ['Noncommercial reuse only.', 'No derivatives may be shared.']),
        ]:
            with self.subTest(licence=licence):
                rendered = ' '.join(Markup(design.photo_terms(example(licence))).text)
                for condition in expected:
                    self.assertIn(condition, rendered)
                self.assertEqual('Noncommercial reuse only.' in rendered, '-NC' in licence)
                self.assertEqual('ShareAlike applies to adaptations.' in rendered, '-SA ' in licence)
                self.assertEqual('No derivatives may be shared.' in rendered, '-ND ' in licence)

    def test_known_credits_and_notices_survive_and_are_escaped(self):
        e = example()
        e['creator'] = 'Uploader <script>'
        e['photo_author'] = 'Photographer & Co'
        e['credit_notices'] = ['Copyright © Original Photographer; no warranty.']
        e['model_credits'] = [{'name': 'Original <Designer>', 'role': 'Original model',
                               'source_url': 'https://example.org/credit?x="&y=2'}]
        html = design.photograph(e)
        parsed = self.assert_credit(html, e)
        self.assertNotIn('<script>', html)
        self.assertIn('Image author: Photographer & Co', ' '.join(parsed.text))
        self.assertIn('Original model: Original <Designer>', ' '.join(parsed.text))
        self.assertIn(e['credit_notices'][0], ' '.join(parsed.text))
        self.assertTrue(any(a.get('href') == e['model_credits'][0]['source_url'] for a in parsed.links))

    def test_retained_photo_files_are_unchanged_and_have_no_orphaned_assets(self):
        entries = [e for es in design.EXAMPLES.values() for e in es if e.get('image')]
        paths = {e['image'] for e in entries}
        actual = {p.relative_to(ROOT).as_posix() for p in (ROOT/'assets/prints').iterdir()
                  if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}}
        self.assertEqual(actual, paths)
        for e in entries:
            with self.subTest(image=e['image']):
                self.assertEqual(sha256((ROOT/e['image']).read_bytes()).hexdigest(), e['sha256'])
                self.assertEqual(e['creator_role'], 'listing uploader')
                self.assertIn('photo_author', e)
                self.assertTrue(e['photo_author'] is None or isinstance(e['photo_author'], str))
                self.assertIn('print-source-photo', Markup(design.photograph(e)).images[0]['class'].split())

    def test_franchise_example_is_link_only_and_original_mouse_credit_is_retained(self):
        fish = design.EXAMPLES['pla-matte'][0]
        self.assertIn('440466', fish['url'])
        self.assertFalse({'image', 'image_url', 'sha256', 'width', 'height', 'alt'} & fish.keys())
        self.assertIn('underlying Octonauts franchise design', fish['image_omission_reason'])
        self.assertFalse((ROOT/'assets/prints/pla-matte.jpg').exists())
        mouse = design.EXAMPLES['pla-hs'][0]
        self.assertTrue(any(c['name'] == 'Whitney Richmond' for c in mouse['model_credits']))
        self.assertIn('Whitney Richmond', ' '.join(Markup(design.photograph(mouse)).text))

    def test_final_styles_protect_full_image_display_after_mobile_rules(self):
        css = (ROOT/'assets/material-guides.css').read_text()
        for selector in ['.material-page img.print-source-photo', '.material-page img.photo-no-derivatives']:
            rule = re.search(re.escape(selector)+r'\{([^}]+)\}', css)
            self.assertIsNotNone(rule)
            self.assertIn('object-fit:contain', rule.group(1))
            self.assertGreater(rule.start(), css.rfind('@media'))


if __name__ == '__main__':
    unittest.main()
