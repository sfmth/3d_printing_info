"""Ownership-resource provenance, compatibility and contextual-rendering regressions."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import printer_resources as resources
import printer_design


def catalog():
    match = re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>',
                      (ROOT / 'comparison.html').read_text(), re.S)
    return json.loads(match.group(1))


def source():
    return {'title': 'Creator installation and model limits',
            'url': 'https://example.org/install?variant=original&rev=2',
            'checked': '2026-10-20'}


def entry(section='H'):
    return {'title': 'Replaceable nozzle assembly',
            'summary': 'The kit changes nozzle access; install the matching heater and thermistor together.',
            'compatibility': 'Original model with board revision 1; not its Plus variant.',
            'evidence': 'manufacturer documentation', 'section': section,
            'sources': [source()]}


def record():
    return {'firmware': [], 'printed_mods': [], 'hardware_mods': [entry()],
            'issues': [], 'reviewed_sources': [source()]}


def document():
    return {'version': 1, 'checked': '2026-10-20', 'models': {'test-printer': record()}}


class ContextParser(HTMLParser):
    """Track resource article ancestry, rather than relying on prose substrings."""
    def __init__(self):
        super().__init__()
        self.stack = []
        self.notes = []
        self.tags = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == 'a':
            self.links.append(attrs.get('href'))
        if tag == 'article' and 'data-resource-kind' in attrs:
            chapters = [a.get('id') for t, a in self.stack
                        if t == 'section' and 'printer-spec-chapter' in a.get('class', '').split()]
            self.notes.append((attrs['data-resource-kind'], attrs.get('data-resource-section'),
                               chapters[-1] if chapters else None))
        if tag not in {'img', 'input', 'br', 'hr', 'meta', 'link', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track'}:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


class PrinterResourceSchemaTests(unittest.TestCase):
    def setUp(self):
        self.models = {'test-printer': record()}

    def assert_invalid(self):
        with self.assertRaises(ValueError):
            resources.validate_resources(self.models, {'test-printer'})

    def test_valid_minimal_record_and_honest_empty_categories(self):
        resources.validate_resources(self.models, {'test-printer'})
        self.models['test-printer'] = {**dict.fromkeys(resources.CATEGORIES, []),
                                      'reviewed_sources': [source()]}
        resources.validate_resources(self.models, {'test-printer'})

    def test_catalog_coverage_cannot_silently_omit_or_add_a_model(self):
        for ids in [set(), {'test-printer', 'extra-model'}]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                resources.validate_resources(self.models, ids)

    def test_all_four_categories_are_required_and_extra_categories_rejected(self):
        for category in resources.CATEGORIES:
            altered = deepcopy(self.models)
            del altered['test-printer'][category]
            with self.subTest(category=category), self.assertRaises(ValueError):
                resources.validate_resources(altered)
        self.models['test-printer']['miscellaneous'] = []
        self.assert_invalid()

    def test_missing_review_provenance_is_rejected(self):
        self.models['test-printer']['reviewed_sources'] = []
        self.assert_invalid()

    def test_malformed_container_types_raise_value_error(self):
        for key in [*resources.CATEGORIES, 'reviewed_sources']:
            for bad in [None, {}, 'not a list']:
                altered = deepcopy(self.models)
                altered['test-printer'][key] = bad
                with self.subTest(key=key, value=bad), self.assertRaises(ValueError):
                    resources.validate_resources(altered)
        for bad in [None, [], 'not a mapping']:
            with self.subTest(record=bad), self.assertRaises(ValueError):
                resources.validate_resources({'test-printer': bad})

    def test_required_entry_fields_and_unknown_fields(self):
        for key in ['title', 'summary', 'compatibility', 'evidence', 'sources']:
            altered = deepcopy(self.models)
            del altered['test-printer']['hardware_mods'][0][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                resources.validate_resources(altered)
        self.models['test-printer']['hardware_mods'][0]['unverified'] = True
        self.assert_invalid()

    def test_required_context_cannot_be_blank_or_nontext(self):
        for key in ['title', 'summary', 'compatibility']:
            for bad in ['', '  ', None, 1]:
                altered = deepcopy(self.models)
                altered['test-printer']['hardware_mods'][0][key] = bad
                with self.subTest(key=key, value=bad), self.assertRaises(ValueError):
                    resources.validate_resources(altered)

    def test_summary_word_limit_is_enforced(self):
        self.models['test-printer']['hardware_mods'][0]['summary'] = 'word ' * 71
        self.assert_invalid()

    def test_evidence_must_use_the_declared_provenance_types(self):
        for bad in ['verified', 'official', None]:
            altered = deepcopy(self.models)
            altered['test-printer']['hardware_mods'][0]['evidence'] = bad
            with self.subTest(evidence=bad), self.assertRaises(ValueError):
                resources.validate_resources(altered)

    def test_section_is_one_known_catalog_letter(self):
        for bad in ['AB', 'HI', '', 'X', 'h', None, 3]:
            altered = deepcopy(self.models)
            altered['test-printer']['hardware_mods'][0]['section'] = bad
            with self.subTest(section=bad), self.assertRaises(ValueError):
                resources.validate_resources(altered)
        # Omitting this optional field still uses the documented category default.
        del self.models['test-printer']['hardware_mods'][0]['section']
        resources.validate_resources(self.models)

    def test_source_requires_title_url_and_date(self):
        for key in ['title', 'url', 'checked']:
            altered = deepcopy(self.models)
            del altered['test-printer']['reviewed_sources'][0][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                resources.validate_resources(altered)
        self.models['test-printer']['hardware_mods'][0]['sources'] = []
        self.assert_invalid()

    def test_sources_require_lists_and_source_mappings(self):
        for bad in [None, {}, 'https://example.org']:
            altered = deepcopy(self.models)
            altered['test-printer']['hardware_mods'][0]['sources'] = bad
            with self.subTest(value=bad), self.assertRaises(ValueError):
                resources.validate_resources(altered)
        for bad in [None, 'source', 5]:
            altered = deepcopy(self.models)
            altered['test-printer']['hardware_mods'][0]['sources'] = [bad]
            with self.subTest(source=bad), self.assertRaises(ValueError):
                resources.validate_resources(altered)

    def test_source_url_requires_https_and_no_embedded_credentials(self):
        for bad in ['http://example.org', 'javascript:alert(1)', '/relative',
                    'https:///missing-host', 'https://user:secret@example.org']:
            altered = deepcopy(self.models)
            altered['test-printer']['reviewed_sources'][0]['url'] = bad
            with self.subTest(url=bad), self.assertRaises(ValueError):
                resources.validate_resources(altered)

    def test_source_review_date_is_a_real_iso_calendar_date(self):
        for bad in ['2026-2-03', '2026-02-30', '2026-13-01', '', None]:
            altered = deepcopy(self.models)
            altered['test-printer']['reviewed_sources'][0]['checked'] = bad
            with self.subTest(checked=bad), self.assertRaises(ValueError):
                resources.validate_resources(altered)

    def test_source_provenance_cannot_silently_accept_extra_keys(self):
        self.models['test-printer']['reviewed_sources'][0]['model_guess'] = 'Plus'
        self.assert_invalid()

    def test_identifier_must_be_a_safe_catalog_slug(self):
        for bad in ['../model', 'Printer', 'with space', '', None]:
            with self.subTest(identifier=bad), self.assertRaises(ValueError):
                resources.validate_resources({bad: record()})

    def load_temporary(self, texts):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for number, text in enumerate(texts):
                (folder / f'printer-resources-{number}.json').write_text(text)
            return resources.load_resources(folder)

    def test_loader_checks_document_schema_and_review_date(self):
        for key, bad in [('version', 2), ('version', True), ('checked', '2026-02-30'),
                         ('checked', None), ('models', []), ('models', None)]:
            altered = document()
            altered[key] = bad
            with self.subTest(key=key, value=bad), self.assertRaises(ValueError):
                self.load_temporary([json.dumps(altered)])
        altered = document()
        altered['extra'] = True
        with self.assertRaises(ValueError):
            self.load_temporary([json.dumps(altered)])

    def test_loader_rejects_a_source_review_after_the_document_review(self):
        altered = document()
        altered['checked'] = '2026-10-19'
        with self.assertRaises(ValueError):
            self.load_temporary([json.dumps(altered)])

    def test_loader_rejects_duplicates_across_files(self):
        with self.assertRaises(ValueError):
            self.load_temporary([json.dumps(document()), json.dumps(document())])

    def test_loader_rejects_duplicate_json_keys_within_a_file(self):
        text = json.dumps(document())
        duplicate_model = text.replace('"models": {', '"models": {"test-printer": {}, ', 1)
        duplicate_entry = text.replace('"title": "Replaceable nozzle assembly"',
                                      '"title": "discarded title", "title": "Replaceable nozzle assembly"', 1)
        for bad in [duplicate_model, duplicate_entry]:
            with self.subTest(text=bad), self.assertRaises(ValueError):
                self.load_temporary([bad])


class PrinterResourceRenderingTests(unittest.TestCase):
    def test_explicit_section_overrides_conservative_category_defaults(self):
        for category, default in [('firmware', 'N'), ('printed_mods', 'B'),
                                  ('hardware_mods', 'B'), ('issues', 'U')]:
            with self.subTest(category=category):
                self.assertEqual(resources.section_for(category, {}), default)
                self.assertEqual(resources.section_for(category, {'section': 'K'}), 'K')

    def test_context_only_contains_matching_sections_and_issues_precede_mods(self):
        value = record()
        value['firmware'] = [entry('N')]
        value['printed_mods'] = [entry('K')]
        value['issues'] = [entry('H')]
        self.assertEqual([category for category, _ in resources.entries_for(value, 'H')],
                         ['issues', 'hardware_mods'])
        self.assertEqual(resources.chapter_context(value, 'T'), '')
        html = resources.chapter_context(value, 'H')
        self.assertIn('data-resource-section="H"', html)
        self.assertNotIn('data-resource-section="N"', html)
        self.assertNotIn('data-resource-section="K"', html)
        self.assertLess(html.index('data-resource-kind="issues"'),
                        html.index('data-resource-kind="hardware_mods"'))

    def test_html_escapes_all_text_and_link_attributes(self):
        value = record()
        note = value['hardware_mods'][0]
        note['title'] = '<script>alert("title")</script>'
        note['summary'] = '<img src=x onerror="alert(1)"> & owner text'
        note['compatibility'] = 'Model "Original" < Plus'
        note['sources'][0]['title'] = '<b>Creator & maintainer</b>'
        note['sources'][0]['url'] = 'https://example.org/?x=" onmouseover="bad&y=1'
        value['reviewed_sources'] = deepcopy(note['sources'])
        html = resources.chapter_context(value, 'H') + resources.review_notes(value)
        parser = ContextParser()
        parser.feed(html)
        self.assertNotIn('script', parser.tags)
        self.assertNotIn('img', parser.tags)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img src=x onerror=&quot;', html)
        self.assertIn('Model &quot;Original&quot; &lt; Plus', html)
        self.assertIn('&lt;b&gt;Creator &amp; maintainer&lt;/b&gt;', html)
        self.assertTrue(all(url == note['sources'][0]['url'] for url in parser.links))
        self.assertIn('Checked 2026-10-20', html)

    def test_detail_places_every_resource_once_in_its_technical_chapter(self):
        data = catalog()
        printer = deepcopy(data['cats'][0])
        printer['id'] = 'test-printer'
        value = record()
        value['printed_mods'] = [entry('B'), entry('K')]
        value['firmware'] = [entry('N')]
        value['issues'] = [entry('U')]
        with patch.object(printer_design, 'load_resources', return_value={'test-printer': value}), \
             patch.object(printer_design, 'images', return_value={}):
            html = printer_design.detail_body(data, printer, lambda *args: '')
        parser = ContextParser()
        parser.feed(html)
        self.assertCountEqual(parser.notes, [
            ('printed_mods', 'B', 'machine'), ('printed_mods', 'K', 'printing'),
            ('hardware_mods', 'H', 'printing'), ('firmware', 'N', 'workflow'),
            ('issues', 'U', 'ownership')])
        self.assertNotIn('id="ownership-resources"', html)


class PublishedPrinterResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalog()
        cls.models = resources.load_resources()
        cls.consumer = json.loads((ROOT / 'data/printer-resources-consumer.json').read_text())['models']

    def test_full_catalog_coverage_with_no_untracked_records(self):
        resources.validate_resources(self.models, {m['id'] for m in self.data['cats']})

    def test_consumer_assignment_matches_catalog_brands_exactly(self):
        brands = {'Anycubic', 'Creality', 'ELEGOO', 'Elegoo', 'Sovol', 'AnkerMake'}
        expected = {m['id'] for m in self.data['cats'] if m['brand'] in brands}
        self.assertEqual(set(self.consumer), expected)

    def test_every_published_entry_has_a_concrete_section_and_reviewed_sources(self):
        for printer_id, value in self.models.items():
            with self.subTest(printer=printer_id):
                self.assertTrue(value['reviewed_sources'])
                for category in resources.CATEGORIES:
                    for note in value[category]:
                        self.assertRegex(note['section'], r'^[A-W]$')
                        self.assertLessEqual(len(note['summary'].split()), 70)
                        self.assertTrue(note['sources'])

    def test_kobra_2_pro_rinkhals_board_limit_is_preserved(self):
        notes = self.consumer['anycubic-kobra-2-pro']['firmware']
        rinkhals = next(note for note in notes if 'Rinkhals' in note['title'])
        self.assertIn('Trigorilla Spe B v1.0.x', rinkhals['compatibility'])
        for model in ['anycubic-kobra-2', 'anycubic-kobra-2-neo',
                      'anycubic-kobra-2-plus', 'anycubic-kobra-2-max']:
            self.assertFalse(any('Rinkhals' in note['title'] for note in self.consumer[model]['firmware']))

    def test_kobra_x_warning_cannot_be_misrepresented_as_a_rinkhals_release(self):
        note = next(note for note in self.consumer['anycubic-kobra-x']['firmware']
                    if 'Rinkhals' in note['title'])
        self.assertIn('excludes Kobra X', note['summary'])
        self.assertIn('not a replacement firmware', note['compatibility'])

    def test_cc1_cosmos_is_not_transferred_to_other_centauri_variants(self):
        self.assertTrue(any('COSMOS' in note['title']
                            for note in self.consumer['elegoo-centauri-carbon']['firmware']))
        for model in ['elegoo-centauri-2', 'elegoo-centauri-2-combo',
                      'elegoo-centauri-carbon-2-combo', 'cc2']:
            self.assertFalse(any('COSMOS' in note['title'] for note in self.consumer[model]['firmware']))

    def test_thermistor_and_probe_geometry_kit_boundaries_are_explicit(self):
        for model in ['elegoo-centauri-carbon', 'elegoo-centauri-carbon-2-combo', 'cc2',
                      'creality-k2', 'creality-k2-pro', 'creality-k2-plus']:
            note = next(note for note in self.consumer[model]['hardware_mods']
                        if 'FlowTech' in note['title'])
            self.assertIn('thermistor', note['summary'])
        se = next(note for note in self.consumer['creality-ender-3-v3-se']['hardware_mods']
                  if 'FlowTech' in note['title'])
        self.assertIn('CR Touch spacer', se['summary'])
        self.assertIn('duct', se['summary'])

    def test_nebula_camera_mount_does_not_leak_from_v3_to_plus(self):
        v3 = next(note for note in self.consumer['creality-ender-3-v3']['printed_mods']
                  if note['title'] == 'Z-axis Nebula camera bracket')
        self.assertIn('excludes V3 Plus', v3['compatibility'])
        self.assertFalse(any(note['title'] == v3['title']
                             for note in self.consumer['creality-ender-3-v3-plus']['printed_mods']))


if __name__ == '__main__':
    unittest.main()
