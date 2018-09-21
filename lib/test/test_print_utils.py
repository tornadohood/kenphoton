"""Unit tests for print_utils."""

from __future__ import unicode_literals

import unittest

from photon.lib import print_utils


class StatusUpdateTestCase(unittest.TestCase):
    """Unit tests for status_update."""

    def test_valid_str(self):
        """Ensure that we have no crashes/bad behavior when feeding it a valid string."""
        self.assertIsNone(print_utils.status_update('This is a test.'))

    def test_not_a_str(self):
        """Ensure that this raises a TypeError."""
        with self.assertRaises(TypeError):
            print_utils.status_update(12345)

    def test_bad_pipe(self):
        """Ensure that this raises a TypeError."""
        with self.assertRaises(TypeError):
            print_utils.status_update('a valid string', 'fake_pipe')
