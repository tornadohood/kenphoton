"""Unit tests for lib/math_utils."""

from __future__ import unicode_literals

import unittest

# Python 2/3 compatibility change, intentionally overwriting range
# pylint: disable=redefined-builtin
from builtins import range
from photon.lib import math_utils


class RMSETestCase(unittest.TestCase):
    """Unit tests for rmse."""

    def test_valid(self):
        """Valid contents to rmse."""
        result = math_utils.rmse(range(1, 10), range(2, 11))
        self.assertEqual(result, 1.0)

    def test_invalid(self):
        """Should raise a TypeError."""
        with self.assertRaises(TypeError):
            math_utils.rmse(['a'], [1])

    def test_single_value(self):
        """Should return no variance from the mean."""
        self.assertEqual(math_utils.rmse([1], [10]), 9.0)


class SafeDivideTestCase(unittest.TestCase):
    """Unit tests for safe_divide."""

    def test_with_zero(self):
        """safe_divide by zero."""
        result = math_utils.safe_divide(1, 0)
        self.assertEqual(result, 0, msg='Division n/0 failed.')
        result = math_utils.safe_divide(0, 1)
        self.assertEqual(result, 0, msg='Division 0/d failed.')

    def test_normal(self):
        """safe_divide by non-zero whole numbers."""
        result = math_utils.safe_divide(10, 2)
        self.assertEqual(result, 5., msg='Division 10/2 failed.')
        result = math_utils.safe_divide(-10, 7)
        self.assertEqual(result, -1.43, msg='Division -10/7 failed')
