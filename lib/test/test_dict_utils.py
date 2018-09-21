""" Unit tests for dict_utils. """
from __future__ import unicode_literals

import unittest

from photon.lib.dict_utils import ValueOrderDict


class TestValueOrderDict(unittest.TestCase):
    """ Test the ValueOrderDict for normal functionality. """
    test = ValueOrderDict()
    test.append_value_to_key('test2', 'hi')
    test.append_value_to_key('test', 'there')
    test.append_value_to_key('test', 'buddy')
    test.append_value_to_key('test2', 'hi')

    def test_index(self):
        """ Test that index increments. """
        test_dict = ValueOrderDict()
        self.assertEqual(test_dict.index_total, 0)
        test_dict.append_value_to_key('value', 'key')
        self.assertEqual(test_dict.index_total, 1)

    def test_tuples(self):
        """ Test that the dict contains all the expected tuples. """
        expected = [('hi', 0, 'test2'),
                    ('hi', 3, 'test2'),
                    ('there', 1, 'test'),
                    ('buddy', 2, 'test')]
        for tup in self.test.tuples:
            self.assertTrue(tup in expected)

    def test_ordered_tuples(self):
        """ Test that the tuples are ordered correctly. """
        expected = [('buddy', 2, 'test'),
                    ('hi', 0, 'test2'),
                    ('hi', 3, 'test2'),
                    ('there', 1, 'test')]
        self.assertEqual(expected, self.test.ordered_tuples)

    def test_ordered_values(self):
        """ Test that ordered values is in order. """
        expected = ['buddy', 'hi', 'hi', 'there']
        self.assertEqual(expected, self.test.ordered_values)

    def test_indexed_order_values(self):
        """ Test against values in order they were indexed. """
        expected = ['hi', 'there', 'buddy', 'hi']
        self.assertEqual(expected, self.test.indexed_order_values)

    def test_getitem(self):
        """ Test __getitem__ implementation to make sure it works. """
        expected = ['there', 'buddy']
        self.assertEqual(expected, self.test['test'])
