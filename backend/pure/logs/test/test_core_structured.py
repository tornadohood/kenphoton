"""Unit tests for core_structured."""

import gzip
import os
import unittest

import ujson

from six import itervalues

from photon.backend.pure.logs import core_structured

PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/core-structured-test.gz')
with gzip.open(os.path.join(PATH, 'test_files/core_structured.json.gz')) as j_file:
    EXPECTED_RESULTS = ujson.load(j_file)
# pylint: disable=line-too-long


class CoreStructuredParserTestCase(unittest.TestCase):
    """Unit tests for CoreStructuredParser."""
    parser = core_structured.CoreStructuredParser(LOG_FILE)

    def test_forms(self):
        """Ensure that forms include the needed information."""
        forms = self.parser.forms
        self.assertTrue(hasattr(forms, 'per_bdev_stats'))

    def test_fields(self):
        """Ensure that fields is well formed."""
        # If we add any other forms besides diagnostics then this needs to be updated.
        for log_data in itervalues(self.parser.fields):
            # Assert that each fields has one or more valid forms.
            forms = log_data.forms.keys()
            for form in forms:
                self.assertTrue(hasattr(self.parser.forms, form))

    def test_fields_tests(self):
        """Ensure that each item in fields has a unit test."""
        for datum in self.parser.fields:
            msg = 'Field "{}" does not have a unit test.  Please write one.'.format(datum)
            self.assertTrue('test_get_{}'.format(datum) in dir(CoreStructuredParserTestCase), msg=msg)

    def test_get_per_bdev_stats(self):
        """Test per_bdev_stats."""
        expected = EXPECTED_RESULTS['per_bdev_stats']
        result = ujson.dumps(sorted(self.parser.get_per_bdev_stats())[0])
        self.assertEqual(ujson.loads(result), sorted(expected)[0])

    def test_get_per_bdev_read_latency(self):
        """Test per_bdev_read_latency."""
        expected = EXPECTED_RESULTS['per_bdev_read_latency']
        result = ujson.dumps(sorted(self.parser.get_per_bdev_read_latency())[0])
        self.assertEqual(ujson.loads(result), sorted(expected)[0])

    def test_get_per_bdev_read_bytes(self):
        """Test per_bdev_read_bytes."""
        expected = EXPECTED_RESULTS['per_bdev_read_bytes']
        result = ujson.dumps(sorted(self.parser.get_per_bdev_read_bytes())[0])
        self.assertEqual(ujson.loads(result), sorted(expected)[0])

    def test_get_per_bdev_read_iops(self):
        """Test per_bdev_read_iops."""
        expected = EXPECTED_RESULTS['per_bdev_read_iops']
        result = ujson.dumps(sorted(self.parser.get_per_bdev_read_iops())[0])
        self.assertEqual(ujson.loads(result), sorted(expected)[0])

    def test_get_per_bdev_write_latency(self):
        """Test per_bdev_write_latency."""
        expected = EXPECTED_RESULTS['per_bdev_write_latency']
        result = ujson.dumps(sorted(self.parser.get_per_bdev_write_latency())[0])
        self.assertEqual(ujson.loads(result), sorted(expected)[0])

    def test_get_per_bdev_write_bytes(self):
        """Test per_bdev_write_bytes."""
        expected = EXPECTED_RESULTS['per_bdev_write_bytes']
        result = ujson.dumps(sorted(self.parser.get_per_bdev_write_bytes())[0])
        self.assertEqual(ujson.loads(result), sorted(expected)[0])

    def test_get_per_bdev_write_iops(self):
        """Test per_bdev_write_iops."""
        expected = EXPECTED_RESULTS['per_bdev_write_iops']
        result = ujson.dumps(sorted(self.parser.get_per_bdev_write_iops())[0])
        self.assertEqual(ujson.loads(result), sorted(expected)[0])
