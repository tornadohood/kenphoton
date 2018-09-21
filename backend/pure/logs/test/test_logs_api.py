"""Unit tests for the logs API."""

import os
import unittest

from photon.backend.pure.logs import logs_api
from photon.lib import array_utils
from photon.lib import custom_errors
from photon.lib import test_utils
from photon.lib import time_utils

PATH = os.path.dirname(__file__)
# Photon base directory:
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(PATH))))
IDENT = array_utils.ArrayIdent(fqdn='slc-coz.purestorage.com')
TIMEFRAME = time_utils.Timeframe('2017/12/11', '2017/12/12')
# pylint: disable=protected-access
# TODO: Unit tests for get_fuse_logs, get_live_logs, get_fields.


class GetSourceOrderTestCase(unittest.TestCase):
    """Unit tests for Logs.get_source_order."""
    # pylint: disable=no-member
    api = test_utils.mock_api(logs_api.Logs, ident=IDENT, timeframe=TIMEFRAME)
    # ident, timeframe

    def setUp(self):
        """Helper to reset the test environment."""
        self.api.log_files = set()
        self.api.log_files_dict = {}
        self.api.timeframe.granularity = time_utils.Timedelta('1h')

    def test_no_fields(self):
        """Test what happens when we request no fields."""
        with self.assertRaises(custom_errors.LogParserError):
            self.api.get_source_order(fields=[])

    def test_duplicate_fields(self):
        """Test what happens when we request duplicate fields."""
        self.api.log_files_dict = {'frequentdiagnostics.log': ['path/frequentdiagnostics.log-2017121100.gz'],
                                   'diagnostics.log': ['path/diagnostics.log-2017121100.gz'],
                                   'array_info.json': ['path/array_info.json.gz']}
        result = self.api.get_source_order(fields=['array_name', 'array_name'])
        expected = ['array_info.json', 'diagnostics.log', 'frequentdiagnostics.log']
        self.assertEqual(expected, result)

    def test_single_log_type(self):
        """Test what happens when a field only has one log type as a source."""
        self.api.log_files_dict = {'hardware.log': ['path/hardware.log-2017121100.gz']}
        result = self.api.get_source_order(fields=['sas_view'])
        expected = ['hardware.log']
        self.assertEqual(expected, result)

    def test_same_granularity(self):
        """Test what happens when two log types have the same granularity for a field."""
        # The tie breakers can be: complexity and number of fields.
        self.api.log_files_dict = {'diagnostics.log': ['path/diagnostics.log-2017121100.gz'],
                                   'array_info.json': ['path/array_info.json.gz']}
        result = self.api.get_source_order(fields=['array_name', 'domain_name'])
        expected = ['array_info.json', 'diagnostics.log']
        self.assertEqual(expected, result)

    def test_same_complexity(self):
        """Test what happens when two log types have the same complexity."""
        # The tie breakers can be: granularity and number of fields.
        self.api.log_files_dict = {'hardware.log': ['path/hardware.log-2017121100.gz'],
                                   'platform.log': ['path/platform.log-2017121100.gz']}
        result = self.api.get_source_order(fields=['purity_version', 'purity_uptime'])
        expected = ['platform.log', 'hardware.log']
        self.assertEqual(expected, result)

    def test_same_field_count(self):
        """Test what happens when two log types have the same field count for a field."""
        # The tie breakers can be: granularity and complexity.
        self.api.log_files_dict = {'hardware.log': ['path/hardware.log-2017121100.gz'],
                                   'platform.log': ['path/platform.log-2017121100.gz']}
        result = self.api.get_source_order(fields=['purity_version'])
        expected = ['platform.log', 'hardware.log']
        self.assertEqual(expected, result)

    def test_no_files(self):
        """Test what happens when we don't have any logs for any log types."""
        self.api. log_files_dict = {}
        # Because we have no log_files_dict, we will go generate one and fail because we are not in a valid path.
        result = self.api.get_source_order(fields=['purity_version'])
        expected = []
        self.assertEqual(expected, result)

    def test_daily_granularity(self):
        """Test what happens when we adjust the granularity to 1 day."""
        self.api.timeframe.granularity = time_utils.Timedelta('1d')
        self.api.log_files_dict = {'frequentdiagnostics.log': ['path/frequentdiagnostics.log-2017121100.gz'],
                                   'hardware.log': ['path/hardware.log-2017121100.gz'],
                                   'diagnostics.log': ['path/diagnostics.log-2017121100.gz']}
        result = self.api.get_source_order(fields=['purity_version'])
        # This results in a 3 way tie; so we would sort by name in reverse:
        expected = ['diagnostics.log', 'hardware.log', 'frequentdiagnostics.log']
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
