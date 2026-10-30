"""A source credit alone must never silently become a reuse licence."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from image_rights import validate_reuse, license_credit


class ImageRightsTests(unittest.TestCase):
    def entry(self, status='no-explicit-restriction-found'):
        return {'reuse': {'status': status, 'checked': '2026-10-29', 'basis_url': 'https://example.org/photo', 'note': 'Owner decision; permission unverified.', 'changes': 'Resized proportionally.'}}

    def test_absent_terms_are_not_an_open_licence(self):
        image = self.entry()
        validate_reuse(image)
        self.assertEqual(license_credit(image), '')
        image['reuse']['license'] = 'Public domain'
        with self.assertRaises(AssertionError):
            validate_reuse(image)

    def test_explicit_grant_needs_license_and_source(self):
        image = self.entry('licensed')
        with self.assertRaises(AssertionError):
            validate_reuse(image)
        image['reuse'].update(license='CC BY-SA 4.0', license_url='https://creativecommons.org/licenses/by-sa/4.0/')
        validate_reuse(image)
        self.assertIn('CC BY-SA 4.0', license_credit(image))
        self.assertIn('Resized proportionally.', license_credit(image))

    def test_unsupported_or_undecided_basis_is_rejected(self):
        image = self.entry('restricted')
        with self.assertRaises(AssertionError):
            validate_reuse(image)


if __name__ == '__main__':
    unittest.main()
