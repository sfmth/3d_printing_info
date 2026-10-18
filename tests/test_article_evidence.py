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


def generic_documents():
    evidence, articles = valid_documents()
    article = articles['articles'][0]
    del article['table']
    article['tables'] = [{
        'id': 'tensile-results', 'title': 'Printed tensile coupons',
        'caption': 'Grade-specific values with their source test conditions.',
        'columns': [
            {'key': 'modulus', 'label': 'Tensile modulus', 'property': 'tensile_modulus', 'unit': 'MPa'},
            {'key': 'strength', 'label': 'Tensile yield strength', 'property': 'tensile_yield_strength', 'unit': 'MPa'},
        ],
        'rows': [{'series_id': 'pla-horizontal', 'values': {'modulus': 'pla-modulus', 'strength': 'pla-yield'}}],
        'notes': [],
    }]
    return evidence, articles


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


class GenericArticleTableTests(unittest.TestCase):
    def setUp(self):
        self.evidence, self.articles = generic_documents()
        self.article = self.articles['articles'][0]
        self.table = self.article['tables'][0]
        self.series = self.evidence['series']['pla-horizontal']

    def validate(self):
        validate_evidence(self.evidence, self.articles, {'pla', 'petg', 'asa', 'pc'})

    def use_hdt_table(self):
        self.article['category'] = 'Service environment'
        self.series.update(test_standard='ISO 75-2', context={
            'stress': '1.8 MPa', 'duration': None, 'humidity': None,
            'annealing': 'No annealing reported by the source.', 'heating_rate': None,
        })
        hdt = deepcopy(self.evidence['measurements']['pla-modulus'])
        hdt.update(property='heat_deflection_temperature', definition='Temperature at the specified deflection under load.',
                   unit='°C', value=62, spread=None, locator='PDF p. 3, HDT at 1.8 MPa.',
                   finding='Supplier HDT at the stated test stress; not a continuous service temperature.')
        self.evidence['measurements']['pla-hdt'] = hdt
        self.article['measurements'] = ['pla-hdt']
        self.table['columns'] = [{'key': 'hdt', 'label': 'HDT at 1.8 MPa', 'property': 'heat_deflection_temperature', 'unit': '°C'}]
        self.table['rows'][0]['values'] = {'hdt': 'pla-hdt'}

    def test_generic_tables_and_optional_context_are_unchanged(self):
        self.series['context'] = {'stress': None, 'humidity': '50% RH', 'duration': 24, 'annealing': None}
        before = deepcopy((self.evidence, self.articles))
        self.validate()
        self.assertEqual(before, (self.evidence, self.articles))

    def test_unreported_orientation_can_be_null_but_cannot_be_omitted(self):
        self.series['orientation'] = None
        self.validate()
        self.assertIsNone(self.series['orientation'])
        del self.series['orientation']
        with self.assertRaisesRegex(ValueError, 'missing fields: orientation'):
            self.validate()

    def test_generic_tables_can_preserve_labeled_molding_specimens(self):
        self.series['process'] = 'injection molding'
        self.validate()
        self.assertEqual(self.series['process'], 'injection molding')

    def test_legacy_pilot_table_still_requires_material_extrusion(self):
        evidence, articles = valid_documents()
        evidence['series']['pla-horizontal']['process'] = 'injection molding'
        with self.assertRaisesRegex(ValueError, 'material-extrusion specimens'):
            validate_evidence(evidence, articles, {'pla'})

    def test_unknown_table_cells_remain_explicit_nulls(self):
        self.table['columns'].append({'key': 'impact', 'label': 'Notched impact strength',
                                      'property': 'notched_impact_strength', 'unit': 'kJ/m²'})
        self.table['rows'][0]['values']['impact'] = None
        self.validate()
        self.assertIsNone(self.table['rows'][0]['values']['impact'])
        self.assertIsNone(self.series['filler'])

    def test_empty_rows_cannot_be_published_as_measurements(self):
        self.table['rows'][0]['values'] = {'modulus': None, 'strength': None}
        with self.assertRaisesRegex(ValueError, 'at least one measurement'):
            self.validate()

    def test_generic_columns_enforce_property_and_units(self):
        for column, field, invalid in ((0, 'unit', 'GPa'), (1, 'property', 'ultimate_tensile_strength')):
            with self.subTest(field=field):
                original = self.table['columns'][column][field]
                self.table['columns'][column][field] = invalid
                with self.assertRaisesRegex(ValueError, 'requires'):
                    self.validate()
                self.table['columns'][column][field] = original

    def test_cells_cannot_mix_notch_or_conditioning_series(self):
        other = deepcopy(self.series)
        other.update(conditioning='Equilibrated at 50% RH', context={'notch': 'Unnotched'})
        self.evidence['series']['pla-conditioned'] = other
        self.evidence['measurements']['pla-yield']['series_id'] = 'pla-conditioned'
        self.series['context'] = {'notch': 'Type A notch'}
        with self.assertRaisesRegex(ValueError, 'incompatible test series'):
            self.validate()

    def test_cell_must_match_the_explicit_row_series(self):
        self.evidence['series']['pla-other'] = deepcopy(self.series)
        self.table['rows'][0]['series_id'] = 'pla-other'
        with self.assertRaisesRegex(ValueError, 'incompatible test series'):
            self.validate()

    def test_cell_references_must_exist_and_be_declared_measurements(self):
        for ref in ('missing-measurement', 'load-path', 23, False):
            with self.subTest(ref=ref):
                self.table['rows'][0]['values']['modulus'] = ref
                with self.assertRaisesRegex(ValueError, 'missing or undeclared'):
                    self.validate()

    def test_rows_require_exact_column_keys(self):
        del self.table['rows'][0]['values']['modulus']
        with self.assertRaisesRegex(ValueError, 'missing fields: modulus'):
            self.validate()
        self.table['rows'][0]['values']['modulus'] = 'pla-modulus'
        self.table['rows'][0]['values']['unexpected'] = None
        with self.assertRaisesRegex(ValueError, 'unknown fields: unexpected'):
            self.validate()

    def test_table_requires_existing_row_series(self):
        self.table['rows'][0]['series_id'] = 'missing-series'
        with self.assertRaisesRegex(ValueError, 'unknown series_id'):
            self.validate()

    def test_duplicate_rows_and_column_keys_are_rejected(self):
        self.table['rows'].append(deepcopy(self.table['rows'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate table row'):
            self.validate()
        self.table['rows'].pop()
        self.table['columns'].append(deepcopy(self.table['columns'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate column key'):
            self.validate()

    def test_table_ids_are_unique_and_cannot_shadow_sections(self):
        self.article['tables'].append(deepcopy(self.table))
        with self.assertRaisesRegex(ValueError, 'duplicate table ID'):
            self.validate()
        self.article['tables'].pop()
        self.article['sections'].append({'id': 'table-tensile-results', 'title': 'Conflicting section'})
        with self.assertRaisesRegex(ValueError, 'collides with a section anchor'):
            self.validate()

    def test_missing_or_ambiguous_table_forms_are_rejected(self):
        self.article['table'] = valid_documents()[1]['articles'][0]['table']
        with self.assertRaisesRegex(ValueError, 'exactly one of table or tables'):
            self.validate()
        del self.article['tables']
        del self.article['table']
        with self.assertRaisesRegex(ValueError, 'exactly one of table or tables'):
            self.validate()

    def test_generic_tables_and_columns_cannot_be_empty(self):
        self.article['tables'] = []
        with self.assertRaisesRegex(ValueError, 'nonempty list'):
            self.validate()
        self.article['tables'] = [self.table]
        self.table['columns'] = []
        with self.assertRaisesRegex(ValueError, 'needs measurement columns'):
            self.validate()

    def test_table_notes_cannot_cite_undeclared_evidence(self):
        self.table['notes'] = [{'text': 'The source did not report conditioning.', 'refs': ['missing-claim']}]
        with self.assertRaisesRegex(ValueError, 'not declared'):
            self.validate()

    def test_generic_tables_do_not_hide_unused_declared_measurements(self):
        self.table['rows'][0]['values']['strength'] = None
        with self.assertRaisesRegex(ValueError, 'unused declared evidence: pla-yield'):
            self.validate()

    def test_hdt_requires_stress_with_units_and_celsius(self):
        self.use_hdt_table()
        self.validate()
        for stress in (None, 1.8, '1.8', '23 °C', 'Unspecified stress'):
            with self.subTest(stress=stress):
                self.series['context']['stress'] = stress
                with self.assertRaisesRegex(ValueError, 'context.stress with stress units'):
                    self.validate()
        self.series['context']['stress'] = '1.8 MPa'
        self.evidence['measurements']['pla-hdt']['unit'] = 'K'
        with self.assertRaisesRegex(ValueError, 'heat_deflection_temperature requires °C'):
            self.validate()

    def test_hdt_cannot_omit_stress_or_context(self):
        self.use_hdt_table()
        del self.series['context']['stress']
        with self.assertRaisesRegex(ValueError, 'context.stress'):
            self.validate()
        del self.series['context']
        with self.assertRaisesRegex(ValueError, 'context.stress'):
            self.validate()

    def test_hdt_can_preserve_different_stated_stress_units(self):
        self.use_hdt_table()
        for stress in ('0.45 MPa', '264 psi', '1.8 N/mm²'):
            with self.subTest(stress=stress):
                self.series['context']['stress'] = stress
                self.validate()
                self.assertEqual(self.series['context']['stress'], stress)

    def test_context_requires_safe_keys_and_finite_plain_values(self):
        for context in ({'test stress': '1.8 MPa'}, {'<script>': 'invalid'}, {'humidity': True},
                        {'duration': float('nan')}, {'annealing': {'temperature': 100}}, {'stress': []}):
            with self.subTest(context=context):
                self.series['context'] = context
                with self.assertRaises(ValueError):
                    self.validate()

    def test_unknown_context_values_must_be_null(self):
        self.series['context'] = {'humidity': 'not reported'}
        with self.assertRaisesRegex(ValueError, 'unknown values must be null'):
            self.validate()

    def test_optional_context_does_not_enable_other_series_fields(self):
        self.series['context'] = {'humidity': None}
        self.series['invented_test_context'] = 'not a supported field'
        with self.assertRaisesRegex(ValueError, 'unknown fields: invented_test_context'):
            self.validate()

    def test_article_categories_are_explicit(self):
        self.article['category'] = 'Unclassified marketing'
        with self.assertRaisesRegex(ValueError, 'unknown article category'):
            self.validate()


class ServiceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.evidence, self.articles = generic_documents()
        self.article = self.articles['articles'][0]
        self.series = self.evidence['series']['pla-horizontal']

    def validate(self):
        validate_evidence(self.evidence, self.articles, {'pla'})

    def observation(self):
        self.article['measurements'] = []
        self.article['tables'] = [{
            'id': 'immersion', 'kind': 'observations', 'title': 'Immersion observations',
            'caption': 'Categorical findings are not numerical design values.', 'notes': [],
            'rows': [{'id': 'pla-water', 'grade': 'Maker PLA Regular', 'material_id': 'pla',
                      'process': 'FFF', 'orientation': None, 'conditioning': None,
                      'exposure': {'method': 'Liquid immersion', 'chemical': 'Water',
                                   'concentration': None, 'duration': '7 days',
                                   'temperature': '23 °C', 'applied_stress': None},
                      'observation': 'No visible change reported; detection limits absent.',
                      'refs': ['load-path']}],
        }]
        return self.article['tables'][0]['rows'][0]

    def test_categorical_observation_retains_unknowns_without_fake_measurements(self):
        self.observation()
        before = deepcopy((self.evidence, self.articles))
        self.validate()
        self.assertEqual(before, (self.evidence, self.articles))

    def test_observation_requires_explicit_exposure_stress(self):
        row = self.observation()
        del row['exposure']['applied_stress']
        with self.assertRaisesRegex(ValueError, 'missing fields: applied_stress'):
            self.validate()

    def test_observation_cannot_replace_unknown_with_zero(self):
        row = self.observation()
        row['exposure']['concentration'] = 0
        with self.assertRaisesRegex(ValueError, 'expected nonempty text or null'):
            self.validate()

    def test_observation_cannot_relabel_a_numeric_measurement_as_a_claim(self):
        row = self.observation()
        row['refs'] = ['pla-modulus']
        with self.assertRaisesRegex(ValueError, 'observation needs declared claim'):
            self.validate()

    def test_observation_cannot_combine_source_evidence_types(self):
        row = self.observation()
        self.evidence['sources']['independent-study'] = deepcopy(self.evidence['sources']['maker-tds'])
        self.evidence['sources']['independent-study']['kind'] = 'independent-experiment'
        self.evidence['claims']['other-finding'] = dict(source_id='independent-study', locator='Table 1', finding='A different experiment.')
        self.article['claims'].append('other-finding')
        row['refs'].append('other-finding')
        with self.assertRaisesRegex(ValueError, 'single source and evidence type'):
            self.validate()

    def time_dependent(self, property='flexural_creep_modulus'):
        self.evidence['measurements']['pla-modulus']['property'] = property
        self.article['tables'][0]['columns'][0]['property'] = property
        self.series['context'] = dict(control_mode='constant load', load='10 N', stress=None,
                                      duration='170 h', humidity=None, strain=None)

    def test_creep_requires_actual_control_and_applied_load(self):
        self.time_dependent()
        self.series['context']['load'] = None
        with self.assertRaisesRegex(ValueError, 'reported load or stress'):
            self.validate()

    def test_unknown_humidity_is_explicit_not_omitted(self):
        self.time_dependent()
        del self.series['context']['humidity']
        with self.assertRaisesRegex(ValueError, 'missing fields: humidity'):
            self.validate()

    def test_relaxation_requires_fixed_imposed_strain(self):
        self.time_dependent('relaxation_residual_stress')
        with self.assertRaisesRegex(ValueError, 'constant strain and reported imposed strain'):
            self.validate()
        self.series['context'].update(control_mode='constant strain', strain='2%')
        self.validate()

    def test_exposure_measurement_requires_duration_stress_and_humidity_fields(self):
        self.series['context'] = {'exposure_method': 'QUV weathering'}
        with self.assertRaisesRegex(ValueError, 'missing fields: applied_stress, duration, humidity'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
