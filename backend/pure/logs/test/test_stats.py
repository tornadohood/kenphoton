"""Unit tests for stats."""

from __future__ import unicode_literals

import os
import unittest

from six import iteritems

from photon.lib import parser_utils
from photon.backend.pure.logs import stats
from photon.lib import test_utils
from photon.lib.time_utils import Timestamp

PATH = os.path.dirname(__file__)


class StatsFormDataTestCase(unittest.TestCase):
    """Unit tests for StatsFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        data = stats.StatsFormData()
        self.assertIsInstance(data.all_data, parser_utils.IntervalForm)
        # Not much else to test here afaik.


class StatsLogDataTestCase(unittest.TestCase):
    """Unit tests for StatsLogData."""

    def test_build(self):
        """Ensure that this builds with the right forms and text to match."""
        log = stats.StatsLogData(['all_data'])
        expected_text_to_match = None
        self.assertEqual(log.forms['all_data'].text_to_match, expected_text_to_match)
        # Not much else to test here afaik.


class StatsParserTestCase(unittest.TestCase):
    """Unit tests for StatsParser."""
    log_file = os.path.join(PATH, 'test_files/host_stats.log-test.gz')
    parser = stats.StatsParser(log_file)

    def test_forms(self):
        """Ensure that forms include the needed information."""
        forms = self.parser.forms
        # Currently only requires 'all_data'.
        self.assertTrue(hasattr(forms, 'all_data'))

    def test_fields(self):
        """Ensure that Fields are well formed."""
        # If we add any other forms besides 'all_data' then this needs to be updated.
        for field, log_data in iteritems(self.parser.fields):
            # Assert that each field has raw data
            msg = 'Field "{}" has no raw data.'.format(field)
            self.assertIn('all_data', log_data.forms, msg)
            # Assert that each field has a parser
            msg = 'Form "{}" has no parser.'.format(field)
            self.assertTrue(hasattr(self.parser, 'get_{}'.format(field)), msg=msg)

    def test_parsers(self):
        """Ensure that each public facing parser is defined in fields."""
        skip = ['get_form_lines', 'get_field', 'get_fields']
        getters = [atr for atr in dir(self.parser) if atr.startswith('get_') and atr not in skip]
        for getter in getters:
            # Assert that each getter has an entry in fields
            msg = 'Getter "{}" is not defined in Fields.'.format(getter)
            self.assertIn(getter.split('_', 1)[1], self.parser.fields, msg=msg)


class AllPerfDataTestCase(unittest.TestCase):
    """Unit tests for all_perf_data."""
    form = 'all_data'
    parser = test_utils.mock_parser(stats.StatsParser)

    def setUp(self):
        """Reset testing parameters."""
        self.parser._form_data = {}
        self.parser._all_perf_data = None

    def test_no_san(self):
        """Test when we have no SAN latency columns."""
        lines = [
            # pylint: disable=line-too-long
            'Name         Time                     B/s (read)  B/s (write)  op/s (read)  op/s (write)  us/op (read)  us/op (write)',
            'dr-toolshed  2018-06-12 23:18:29 EDT  0.00        0.00         0.00         0.00          0             0',
            'WDCPatching  2018-06-12 23:18:29 EDT  0.00        0.00         0.00         0.00          0             0',
            'Lillian      2018-06-12 23:18:29 EDT  0.00        0.00         0.00         0.00          0             0',
            'LillianVCAS  2018-06-12 23:18:29 EDT  0.00        19.96K       0.00         4.00          0             449',
            'WDCFiles     2018-06-12 23:18:29 EDT  0.00        0.00         0.00         0.00          0             0',
            '(total)      2018-06-12 23:18:29 EDT  0.00        19.96K       0.00         4.00          0             449'
        ]
        self.parser._form_data['all_data'] = [lines]
        # Old Pylint is confused about object inheritance
        # pylint: disable=no-member
        result = self.parser.get_perf_stats()
        expected = [(Timestamp('2018-06-12 23:18:29'), {'read_ms': 0.0, 'write_san_ms': None, 'read_bw': 0.0,
                                                        'read_san_ms': None, 'read_iops': 0.0, 'write_bw': 20439.04,
                                                        'write_ms': 0.45, 'write_iops': 4.0})]
        self.assertEqual(result, expected)

    def test_with_san(self):
        """Test when we have SAN latency columns."""
        lines = [
            # pylint: disable=line-too-long
            'Name      Time                     B/s (read)  B/s (write)  op/s (read)  op/s (write)  us/op (read)  SAN us/op (read)  us/op (write)  SAN us/op (write)',
            'pure_01   2018-06-13 23:17:22 EDT  1.78M       4.61M        43.00        179.00        352           88                218            555',
            'DS_FIN01  2018-06-13 23:17:22 EDT  0.00        0.00         0.00         0.00          0             0                 0              0',
            '(total)   2018-06-13 23:17:22 EDT  1.78M       4.61M        43.00        179.00        352           88                218            555'','
        ]
        self.parser._form_data['all_data'] = [lines]
        # Old Pylint is confused about object inheritance
        # pylint: disable=no-member
        result = self.parser.get_perf_stats()
        expected = [(Timestamp('2018-06-13 23:17:22'), {'read_ms': 0.35, 'write_san_ms': 0.56, 'read_bw': 1866465.28,
                                                        'read_san_ms': 0.09, 'read_iops': 43.0, 'write_bw': 4833935.36,
                                                        'write_ms': 0.22, 'write_iops': 179.0})]
        self.assertEqual(result, expected)

    def test_empty_total(self):
        """Test behavior when the total line is empty, but others are not."""
        lines = [
            # pylint: disable=line-too-long
            'Name      Time                     B/s (read)  B/s (write)  op/s (read)  op/s (write)  us/op (read)  SAN us/op (read)  us/op (write)  SAN us/op (write)',
            'pure_01   2018-06-13 23:17:22 EDT  1.78M       4.61M        43.00        179.00        352           88                218            555',
            'DS_FIN01  2018-06-13 23:17:22 EDT  0.00        0.00         0.00         0.00          0             0                 0              0',
            '(total)   2018-06-13 23:17:22 EDT  0.00        0.00         0.00         0.00          0             0                 0              0'','
        ]
        self.parser._form_data['all_data'] = [lines]
        # Old Pylint is confused about object inheritance
        # pylint: disable=no-member
        result = self.parser.get_perf_stats()
        expected = [(Timestamp('2018-06-13 23:17:22'), {'read_ms': 0.35, 'write_san_ms': 0.56, 'read_bw': 1866465.28,
                                                        'read_san_ms': 0.09, 'read_iops': 43.0, 'write_bw': 4833935.36,
                                                        'write_ms': 0.22, 'write_iops': 179.0})]
        self.assertEqual(result, expected)

    def test_bad_header(self):
        """Test behavior when we have a header that is the wrong order and missing columns."""
        lines = [
            # pylint: disable=line-too-long
            'Name      Timestamp                B/s (write)  B/s (read)  op/s (read)  op/s (write)  us/op (read)  SAN us/op (read)  us/op (write)  SAN us/op (write)',
            'pure_01   2018-06-13 23:17:22 EDT  1.78M       4.61M        43.00        179.00        352           88                218            555',
            'DS_FIN01  2018-06-13 23:17:22 EDT  0.00        0.00         0.00         0.00          0             0                 0              0',
            '(total)   2018-06-13 23:17:22 EDT  0.00        0.00         0.00         0.00          0             0                 0              0'','
        ]
        self.parser._form_data['all_data'] = [lines]
        with self.assertRaises(ValueError):
            # Old Pylint is confused about object inheritance
            # pylint: disable=no-member
            self.parser.get_perf_stats()


@unittest.skip('Not implemented.')
class KnownDataTestCases(unittest.TestCase):
    """Unit tests for all Fields in the StatsParser."""
    log_file = os.path.join(PATH, 'test_files/stats.log-test.gz')
    parser = stats.StatsParser(log_file)

    def test_results(self):
        pass


# TODO: Individual unit tests for each parser: PT-1171
