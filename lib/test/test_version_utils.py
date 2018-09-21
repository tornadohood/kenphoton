"""Unit tests for version_utils."""

from __future__ import unicode_literals

import unittest

from photon.lib import version_utils


class CompareVersionsTestCase(unittest.TestCase):
    """Unit tests for compare_versions."""

    def test_equal_to(self):
        """Compare same versions."""
        self.assertTrue(version_utils.compare_versions('4.5.0', '4.5.0'))

    def test_same_major(self):
        """Compare versions of the same major branch."""
        self.assertTrue(version_utils.compare_versions('4.8.10', '4.8.9'))
        self.assertFalse(version_utils.compare_versions('4.8.1', '4.8.2'))

    def test_same_minor(self):
        """Compare versions of the same minor branch."""
        self.assertTrue(version_utils.compare_versions('4.8.10', '4.7.10'))
        self.assertFalse(version_utils.compare_versions('4.8.1', '4.9.1'))

    def test_different_family(self):
        """Compare versions of a different family branch."""
        self.assertTrue(version_utils.compare_versions('5.8.10', '4.7.10'))
        self.assertFalse(version_utils.compare_versions('4.8.1', '5.0.1'))

    def test_mixed_styles(self):
        """Compare versions with different naming styles."""
        # 4.9.5 comes after 4.9.bravo
        self.assertTrue(version_utils.compare_versions('4.9.5', '4.9.bravo'))
        # 4.5.14.post comes before 4.5.15
        self.assertFalse(version_utils.compare_versions('4.5.14.post', '4.5.15'))
        # 4.5.14.post should be after 4.5.14
        self.assertTrue(version_utils.compare_versions('4.5.14.post', '4.5.14'))
        # 4.8.1 comes before 4.8.echo
        self.assertTrue(version_utils.compare_versions('4.8.1', '4.8.echo'))

    def test_edge_cases(self):
        """Compare abnormally named releases."""
        cases = (
            # 4.1.0.pb1 < 4.1.1
            ('4.1.0.PlatinumBeta1', '4.1.1'),
            # 4.1.0.pb1 < 4.1.0.PlatinumBeta2
            ('4.1.0.PlatinumBeta1', '4.1.0.PlatinumBeta2'),
            # 4.0.14 < 4.0.14.post
            ('4.0.14', '4.0.14.post'),
        )
        for lesser, greater in cases:
            msg = '{} is supposed to be less than {}.'.format(lesser, greater)
            self.assertFalse(version_utils.compare_versions(lesser, greater), msg=msg)


class CompareMultipleVersionsTestCase(unittest.TestCase):
    """Unit tests for compare_multiple_versions."""

    def test_equal_to(self):
        """Compare same versions."""
        self.assertTrue(version_utils.compare_multiple_versions('4.5.0', ['4.5.0']))

    def test_same_minor(self):
        """Compare versions of the same minor branch."""
        self.assertTrue(version_utils.compare_multiple_versions('4.8.10', ['4.8.9', '4.9.5']))
        # We shouldn't compare against the 4.7 version ,because there is an explicit mention of our major.minor (4.8).
        self.assertFalse(version_utils.compare_multiple_versions('4.8.1', ['4.7.15', '4.8.2']))

    def test_same_rev(self):
        """Compare versions of the same revision."""
        self.assertTrue(version_utils.compare_multiple_versions('4.8.10', ['4.7.10']))
        self.assertFalse(version_utils.compare_multiple_versions('4.8.1', ['4.9.1']))

    def test_different_major(self):
        """Compare versions of a different family branch."""
        self.assertTrue(version_utils.compare_multiple_versions('5.8.10', ['4.7.10']))
        self.assertFalse(version_utils.compare_multiple_versions('4.8.1', ['5.0.1']))

    def test_mixed_styles(self):
        """Compare versions with different naming styles."""
        # 4.9.5 comes after 4.9.bravo
        self.assertTrue(version_utils.compare_multiple_versions('4.9.5', ['4.9.bravo']))
        # 4.5.14.post comes before 4.5.15
        self.assertFalse(version_utils.compare_multiple_versions('4.5.14.post', ['4.5.15']))
        # 4.5.14.post should be after 4.5.14
        self.assertTrue(version_utils.compare_multiple_versions('4.5.14.post', ['4.5.14']))
        # 4.8.1 comes before 4.8.echo
        self.assertTrue(version_utils.compare_multiple_versions('4.8.1', ['4.8.echo']))

    def test_edge_cases(self):
        """Compare abnormally named releases."""
        cases = (
            # 4.1.0.pb1 < 4.1.1
            ('4.1.0.PlatinumBeta1', ['4.1.1']),
            # 4.1.0.pb1 < 4.1.0.PlatinumBeta2
            ('4.1.0.PlatinumBeta1', ['4.1.0.PlatinumBeta2']),
            # 4.0.14 < 4.0.14.post
            ('4.0.14', ['4.0.14.post']),
            # 4.8.1 > 4.7.10, however 4.8.1 < 4.8.8
            ('4.8.1', ['4.7.10', '4.8.8', '4.9.0']),
            ('4.9.0', ['4.9.10', '4.10.bravo'])
        )
        for lesser, greater in cases:
            msg = '{} is supposed to be less than {}.'.format(lesser, greater)
            self.assertFalse(version_utils.compare_multiple_versions(lesser, greater), msg=msg)

    def test_string_fixed_in(self):
        """This should raise a TypeError."""
        with self.assertRaises(TypeError):
            version_utils.compare_multiple_versions('4.8.0', '4.7.5')


if __name__ == '__main__':
    unittest.main()
