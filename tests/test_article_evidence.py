"""Regression checks for provenance and comparison errors; fixtures stay in memory."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_articles import PRINTING_FIELDS, strict_load_json, validate_evidence
from material_articles import measure_value


def valid_documents():
    source = {
        'title': 'Maker PLA technical data sheet', 'publisher': 'Maker Polymers',
        'authors': ['Maker Polymers'], 'url': 'https://example.org/pla.pdf',
        'document_date': '2024-01-01', 'version': '1.1', 'accessed': '2026-10-18',
        'kind': 'manufacturer-test', 'scope': 'Printed coupons, not molded resin.',
    }
    series = {
        'source_id': 'maker-tds', 'grade': 'Maker PLA Regular', 'manufacturer': 'Maker Polymers',
        'material_id': 'pla', 'base_polymer': 'PLA', 'filler': None, 'process': 'FFF',
        'orientation': 'Horizontal XY; long axis X', 'specimen_geometry': None,
        'test_standard': 'ISO 527-1', 'test_rate': None, 'test_temperature': None,
        'conditioning': None, 'printer': None, 'post_processing': None,
        'sample_count': None, 'scatter_definition': None,
        'printing': dict.fromkeys(PRINTING_FIELDS), 'locator': 'PDF p. 3, printing note.',
    }
    modulus = {
        'series_id': 'pla-horizontal', 'property': 'tensile_modulus',
        'definition': 'Axial elastic modulus in the initial tensile region.',
        'unit': 'MPa', 'value': 2300, 'qualifier': '=', 'spread': 100,
        'locator': 'PDF p. 2, tensile modulus row, horizontal column.',
        'finding': 'The plus/minus term has unspecified statistical meaning.',
    }
    strength = {
        'series_id': 'pla-horizontal', 'property': 'tensile_yield_strength',
        'definition': 'Tensile yield stress, distinct from ultimate or rupture stress.',
        'unit': 'MPa', 'value': 51, 'qualifier': '=', 'spread': 3,
        'locator': 'PDF p. 2, yield row, horizontal column.',
        'finding': 'The plus/minus term has unspecified statistical meaning.',
    }
    evidence = {
        'schema_version': 1, 'sources': {'maker-tds': source},
        'series': {'pla-horizontal': series},
        'measurements': {'pla-modulus': modulus, 'pla-yield': strength},
        'claims': {'load-path': {'source_id': 'maker-tds', 'locator': 'PDF p. 4, design guidance.',
                                 'finding': 'Align the load with the documented coupon orientation.'}},
    }
    article = {
        'id': 'choosing-a-load-bearing-material', 'title': 'Choose a load-bearing material',
        'description': 'Connect a load case to grade-specific test evidence.', 'category': 'Mechanical performance',
        'author': {'@type': 'Organization', 'name': 'Maker Engineering'},
        'authorship_note': 'Prepared by Maker Engineering; supplier data retain their test context.',
        'published': '2026-10-01', 'modified': '2026-10-18', 'materials': {'pla': 'PLA'},
        'answer': {'heading': 'Start with the load', 'paragraphs': [
            {'text': 'Choose an orientation appropriate for the load path.', 'refs': ['load-path']}]},
        'sections': [
            {'id': 'measurements', 'title': 'Grade measurements', 'paragraphs': []},
            {'id': 'methods', 'title': 'Test conditions', 'paragraphs': []},
            {'id': 'verification', 'title': 'Verification', 'items': [
                {'text': 'Check the actual component under its service load.'}]},
        ],
        'table': {'caption': 'Printed coupons; compare the full test conditions.',
                  'rows': [{'modulus': 'pla-modulus', 'strength': 'pla-yield'}], 'notes': []},
        'measurements': ['pla-modulus', 'pla-yield'], 'claims': ['load-path'],
    }
    return evidence, {'articles': [article]}


class ArticleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.evidence, self.articles = valid_documents()
        self.article = self.articles['articles'][0]

    def validate(self):
        validate_evidence(self.evidence, self.articles, {'pla', 'petg', 'asa', 'pc'})

    def test_valid_documents_and_explicit_unknowns_are_unchanged(self):
        before = deepcopy((self.evidence, self.articles))
        self.validate()
        self.assertEqual(before, (self.evidence, self.articles))
        self.assertIsNone(self.evidence['series']['pla-horizontal']['conditioning'])

    def test_multiple_articles_and_multiple_grades_are_supported(self):
        other_series = deepcopy(self.evidence['series']['pla-horizontal'])
        other_series.update(grade='Maker PETG Clear', material_id='petg', base_polymer='PETG')
        self.evidence['series']['petg-horizontal'] = other_series
        other = deepcopy(self.article)
        other.update(id='petg-load-guide', materials={'petg': 'PETG'}, measurements=['petg-modulus', 'petg-yield'])
        other['table']['rows'] = [{'modulus': 'petg-modulus', 'strength': 'petg-yield'}]
        for key in ('modulus', 'yield'):
            measurement = deepcopy(self.evidence['measurements'][f'pla-{key}'])
            measurement['series_id'] = 'petg-horizontal'
            self.evidence['measurements'][f'petg-{key}'] = measurement
        self.articles['articles'].append(other)
        self.validate()

    def test_modulus_units_must_match_the_table_heading(self):
        self.evidence['measurements']['pla-modulus']['unit'] = 'GPa'
        with self.assertRaisesRegex(ValueError, 'tensile_modulus in MPa'):
            self.validate()

    def test_ultimate_strength_cannot_enter_the_yield_column(self):
        self.evidence['measurements']['pla-yield']['property'] = 'ultimate_tensile_strength'
        with self.assertRaisesRegex(ValueError, 'tensile_yield_strength'):
            self.validate()

    def test_table_cannot_combine_orientations_even_for_the_same_grade(self):
        other = deepcopy(self.evidence['series']['pla-horizontal'])
        other['orientation'] = 'Upright; long axis Z'
        self.evidence['series']['pla-upright'] = other
        self.evidence['measurements']['pla-yield']['series_id'] = 'pla-upright'
        with self.assertRaisesRegex(ValueError, 'incompatible test series'):
            self.validate()

    def test_missing_condition_is_not_silently_assumed(self):
        del self.evidence['series']['pla-horizontal']['conditioning']
        with self.assertRaisesRegex(ValueError, 'missing fields: conditioning'):
            self.validate()

    def test_missing_printing_condition_is_not_silently_assumed(self):
        del self.evidence['series']['pla-horizontal']['printing']['chamber_temperature']
        with self.assertRaisesRegex(ValueError, 'missing fields: chamber_temperature'):
            self.validate()

    def test_invented_or_misspelled_printing_condition_is_rejected(self):
        self.evidence['series']['pla-horizontal']['printing']['test_speed'] = '200 mm/s'
        with self.assertRaisesRegex(ValueError, 'unknown fields: test_speed'):
            self.validate()

    def test_unknown_condition_requires_null(self):
        self.evidence['series']['pla-horizontal']['conditioning'] = 'not reported'
        with self.assertRaisesRegex(ValueError, 'unknown values must be null'):
            self.validate()

    def test_dangling_series_source_is_rejected(self):
        self.evidence['series']['pla-horizontal']['source_id'] = 'missing-source'
        with self.assertRaisesRegex(ValueError, 'unknown source_id'):
            self.validate()

    def test_measurement_cannot_override_its_series_source(self):
        self.evidence['measurements']['pla-modulus']['source_id'] = 'fabricated-source'
        with self.assertRaisesRegex(ValueError, 'unknown fields: source_id'):
            self.validate()

    def test_dangling_measurement_series_is_rejected(self):
        self.evidence['measurements']['pla-modulus']['series_id'] = 'missing-series'
        with self.assertRaisesRegex(ValueError, 'unknown series_id'):
            self.validate()

    def test_missing_evidence_record_is_rejected(self):
        self.article['claims'].append('fabricated-claim')
        with self.assertRaisesRegex(ValueError, 'declared evidence does not exist'):
            self.validate()

    def test_used_evidence_must_be_declared(self):
        self.article['claims'] = []
        with self.assertRaisesRegex(ValueError, 'not declared'):
            self.validate()

    def test_declared_evidence_must_be_used(self):
        self.article['answer']['paragraphs'][0]['refs'] = []
        with self.assertRaisesRegex(ValueError, 'unused declared evidence'):
            self.validate()

    def test_source_location_is_required_for_every_claim(self):
        del self.evidence['claims']['load-path']['locator']
        with self.assertRaisesRegex(ValueError, 'missing fields: locator'):
            self.validate()

    def test_source_location_is_required_for_every_measurement(self):
        self.evidence['measurements']['pla-modulus']['locator'] = ''
        with self.assertRaisesRegex(ValueError, 'locator'):
            self.validate()

    def test_modification_date_cannot_precede_publication(self):
        self.article['modified'] = '2026-09-01'
        with self.assertRaisesRegex(ValueError, 'modified date precedes'):
            self.validate()

    def test_nonfinite_and_boolean_measurements_are_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf'), True):
            with self.subTest(value=value):
                self.evidence['measurements']['pla-modulus']['value'] = value
                with self.assertRaisesRegex(ValueError, 'finite number'):
                    self.validate()

    def test_spread_must_be_finite_and_nonnegative(self):
        for spread in (-1, float('nan'), float('inf'), True):
            with self.subTest(spread=spread):
                self.evidence['measurements']['pla-modulus']['spread'] = spread
                with self.assertRaises(ValueError):
                    self.validate()

    def test_unspecified_plus_minus_does_not_become_standard_deviation(self):
        self.evidence['series']['pla-horizontal']['scatter_definition'] = 'Standard deviation'
        with self.assertRaisesRegex(ValueError, 'unspecified plus/minus'):
            self.validate()

    def test_lower_bound_is_preserved_through_validation_and_display(self):
        item = self.evidence['measurements']['pla-yield']
        item.update(value=16.5, qualifier='>', spread=None)
        self.validate()
        self.assertEqual(item['qualifier'], '>')
        self.assertEqual(measure_value(item), '>16.5')

    def test_bound_cannot_have_an_exact_value_spread(self):
        self.evidence['measurements']['pla-yield']['qualifier'] = '>'
        with self.assertRaisesRegex(ValueError, 'bound cannot carry'):
            self.validate()

    def test_https_and_source_metadata_are_required(self):
        self.evidence['sources']['maker-tds']['url'] = 'http://example.org/pla.pdf'
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            self.validate()

    def test_unknown_source_date_and_version_can_be_null(self):
        self.evidence['sources']['maker-tds'].update(document_date=None, version=None)
        self.validate()

    def test_required_and_unique_section_ids_are_enforced(self):
        self.article['sections'][1]['id'] = 'measurements'
        with self.assertRaisesRegex(ValueError, 'duplicate or reserved section ID'):
            self.validate()

    def test_unsafe_article_slug_is_rejected(self):
        self.article['id'] = '../outside'
        with self.assertRaisesRegex(ValueError, 'safe lowercase'):
            self.validate()

    def test_generic_byline_is_not_a_named_author(self):
        self.article['author']['name'] = 'Editorial team'
        with self.assertRaisesRegex(ValueError, 'named person or organization'):
            self.validate()

    def test_duplicate_json_ids_are_rejected_without_writing_files(self):
        with patch('check_articles.Path.read_text', return_value='{"claims": {"id": {}, "id": {}}}'):
            with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                strict_load_json('unused.json')

    def test_nonstandard_json_numbers_are_rejected_without_writing_files(self):
        with patch('check_articles.Path.read_text', return_value='{"value": NaN}'):
            with self.assertRaisesRegex(ValueError, 'nonfinite JSON number'):
                strict_load_json('unused.json')


if __name__ == '__main__':
    unittest.main()
