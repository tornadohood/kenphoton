"""Unit tests for pandas_utils."""

import unittest

from pandas import DataFrame
from photon.lib import pandas_utils
from photon.lib import time_utils


class GetLatestValuesTestCase(unittest.TestCase):
    """Unit tests for get_latest_values."""

    def test_empty_frame(self):
        """Test what happens with an empty DataFrame."""
        frame = DataFrame({})
        result = pandas_utils.get_latest_values(frame, ['a'])
        assert result.empty

    def test_field_not_in_frame(self):
        """Test what happens when a requested field is not in the DataFrame."""
        frame = DataFrame({'a': [1, 2, 3]})
        result = pandas_utils.get_latest_values(frame, ['b'])
        assert result['b'][0] is None

    def test_partial(self):
        """Test what happens when some of the fields are not in the DataFrame."""
        expected = {'a': [3], 'b': [4], 'c': [None]}
        frame = DataFrame({'a': [1, 2, 3], 'b': [2, 3, 4]})
        result = pandas_utils.get_latest_values(frame, ['a', 'b', 'c'])
        assert result.to_dict('list') == expected

    def test_normal(self):
        """Test with all fields in the DataFrame."""
        frame = DataFrame({'a': [1, 2, 3], 'b': [2, 3, 4], 'c': [0, 0, 1]})
        expected = {'a': [3], 'b': [4], 'c': [1]}
        result = pandas_utils.get_latest_values(frame, ['a', 'b', 'c']).to_dict('list')
        self.assertEqual(result, expected)


class GetLatestValueTestCase(unittest.TestCase):
    """Unit tests for get_latest_value."""

    def test_empty_frame(self):
        """Test what happens with an empty DataFrame."""
        frame = DataFrame({})
        result = pandas_utils.get_latest_value(frame, 'a')
        assert result is None

    def test_field_not_in_frame(self):
        """Test what happens when a requested field is not in the DataFrame."""
        frame = DataFrame({'a': [1, 2, 3]})
        result = pandas_utils.get_latest_value(frame, 'b')
        assert result is None

    def test_normal(self):
        """Test with all fields in the DataFrame."""
        frame = DataFrame({'a': [1, 2, 3], 'b': [2, 3, 4], 'c': [0, 0, 1]})
        expected = 3
        result = pandas_utils.get_latest_value(frame, 'a')
        self.assertEqual(result, expected)


class SortByIndexAndColumnsTestCase(unittest.TestCase):
    """Unit tests for sort_by_index_and_columns."""

    def test_empty_frame(self):
        """Test what happens with an empty DataFrame."""
        frame = DataFrame({})
        result = pandas_utils.sort_by_index_and_columns(frame, ['a']).to_dict('list')
        expected = {}
        self.assertEqual(result, expected)

    def test_field_not_in_frame(self):
        """Test what happens when a requested field is not in the DataFrame."""
        frame = DataFrame({'a': [1, 2, 3]})
        with self.assertRaises(KeyError):
            pandas_utils.sort_by_index_and_columns(frame, ['b'])

    def test_normal(self):
        """Test with all fields in the DataFrame."""
        frame = DataFrame({'a': [1, 2, 3], 'b': [2, 3, 4], 'c': [0, 0, 1]})
        expected = {'a': {0: 1, 1: 2, 2: 3}, 'b': {0: 2, 1: 3, 2: 4}, 'c': {0: 0, 1: 0, 2: 1}}
        result = pandas_utils.sort_by_index_and_columns(frame, ['a']).to_dict()
        self.assertEqual(result, expected)

    def test_sort_by_multiple(self):
        """Test sorting by multiple fields."""
        frame = DataFrame({'a': [1, 0, 1], 'b': [2, 5, 4], 'c': [1, 0, 1]})
        expected = {'a': {0: 0, 1: 1, 2: 1}, 'b': {0: 5, 1: 2, 2: 4}, 'c': {0: 0, 1: 1, 2: 1}}
        result = pandas_utils.sort_by_index_and_columns(frame, ['a', 'b']).to_dict()
        self.assertEqual(result, expected)

    def test_with_timestamp(self):
        """Test sorting with a timestamped column."""
        frame = DataFrame({'a': [1, 2, 3], 'b': [2, 3, 4], 'c': [0, 0, 1],
                           'Timestamp': [time_utils.Timestamp('2018-05-16 10:30:37'),
                                         time_utils.Timestamp('2018-05-16 10:30:36'),
                                         time_utils.Timestamp('2018-05-16 10:30:38')]})
        expected = {'a': {0: 2, 1: 1, 2: 3},
                    'Timestamp': {0: time_utils.Timestamp('2018-05-16 10:30:36'),
                                  1: time_utils.Timestamp('2018-05-16 10:30:37'),
                                  2: time_utils.Timestamp('2018-05-16 10:30:38')},
                    'b': {0: 3, 1: 2, 2: 4},
                    'c': {0: 0, 1: 0, 2: 1}}
        result = pandas_utils.sort_by_index_and_columns(frame, ['Timestamp']).to_dict()
        self.assertEqual(result, expected)
