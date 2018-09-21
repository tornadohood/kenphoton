"""Unit tests for the Photon API."""

import os
import unittest

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Tuple
except ImportError:
    pass

from photon import api
from photon.lib.time_utils import Timestamp
from photon.lib import test_utils


# pylint: disable=line-too-long
class FlashArrayTestCase(unittest.TestCase):
    """Unit tests for FlashArray."""

    def test_init_bad_fqdn(self):  # type: (...) -> None
        """Test instantiating with an invalid FQDN."""
        # This will use the current directory.
        with self.assertRaises(ValueError):
            api.FlashArray(fqdn='bad_fqdn')

    @unittest.skip('OSError: [Errno 2] No such file or directory: \'/logs/purestorage.com/slc-coz-ct0\'')
    def test_init_no_timeframe(self):  # type: (...) -> None
        """Test instantiating without a time frame."""
        array = api.FlashArray(fqdn='slc-coz.purestorage.com')  # type: api.FlashArray
        # Ensure that a start and end were dynamically generated based upon the current time.
        self.assertTrue(array.timeframe.start)
        self.assertTrue(array.timeframe.end)

    @unittest.skip('OSError: [Errno 2] No such file or directory: \'/logs/domain.com/array-ct0\'')
    def test_valid_fuse_path(self):  # type: (...) -> None
        """Test instantiating with a valid FUSE path."""
        valid_log_paths = (
            '/logs/domain.com/array-ct0',
            '/logs/domain.com/array-ct1/2018_11_27'
        )  # type: Tuple
        for valid_path in valid_log_paths:
            self.assertTrue(api.FlashArray(log_path=valid_path))

    def test_init_no_input(self):  # type: (...) -> None
        """Test instantiating without any input."""
        array = api.FlashArray()  # type: api.FlashArray
        # This will instantiate without an identity and just use files in the current directory.
        self.assertTrue(array.ident.log_path == os.getcwd())

    @unittest.skip("KeyError: 'raw_lines' -> form_lines = self.form_lines['raw_lines']")
    def test_get_fields(self):  # type: (...) -> None
        """Basic tests for getting fields from logs."""
        test_logs = [test_utils.get_files_of_type('Uncategorized/diagnostics.log-2017121100')[0]]  # type: List[str]
        array = api.FlashArray(start='2017_12_10', end='2017_12_12', files=test_logs)
        expected = {'controller': ['CT0'], 'array_name': ['DR-Pure3'],
                    'Timestamp': [Timestamp('2018-12-11 00:17:14')]}
        results = array.get_fields(['array_name']).to_dict('list')  # type: Dict[str, Any]
        # This 'source' filename will vary based upon the path where the tests were run/stored.
        # For the context of this test, we don't really care about that path, just the result of the fields.
        del results['source']
        self.assertEqual(expected, results)

    def test_get_data_sources(self):  # type: (...) -> None
        """Test getting applicable data_sources."""
        # TODO: PT-1623 - Add real world tests for dynamic data sources once we have multiple.
        fields = ['array_name']  # type: List[str]
        test_logs = [test_utils.get_files_of_type('Uncategorized/diagnostics.log-2017121100')[0]]  # type: List[str]
        flasharray = api.FlashArray(files=test_logs)  # type: api.FlashArray
        result = flasharray.get_data_sources(fields)  # type: Dict[str, Any]
        expected = ['logs']  # type: List[str]
        self.assertEqual(expected, result)

    def test_get_latest_values(self):  # type: (...) -> None
        """Test getting the most recent values of test fields."""
        # This file ranges from 'Dec 10 17 23:18:232' -> 'Dec 11 17 00:17:21':
        expected = {'array_id': ['782859-14778676-1975978063281993217']}
        type_str = 'Uncategorized/frequentdiagnostics.log-2017121100'
        test_logs = [test_utils.get_files_of_type(type_str)[0]]  # type: List[str]
        array = api.FlashArray(files=test_logs)  # type: api.FlashArray
        result = array.get_latest_values(['array_id']).to_dict('list')  # type: Dict[str, Any]
        self.assertEqual(result, expected)

    def test_get_latest_values_both_controllers(self):  # type: (...) -> None
        """Test getting the most recent values of test fields from both controllers."""
        # This file ranges from 'Dec 10 17 23:18:232' -> 'Dec 11 17 00:17:21':
        expected = {'controller': ['CT0', 'CT1'],
                    'array_id': ['782859-14778676-1975978063281993217', None]}
        type_str = 'Uncategorized/frequentdiagnostics.log-2017121100'
        test_logs = [test_utils.get_files_of_type(type_str)[0]]  # type: List[str]
        array = api.FlashArray(files=test_logs)  # type: api.FlashArray
        result = array.get_latest_values(['array_id'], both_controllers=True).to_dict('list')  # type: Dict[str, Any]
        self.assertEqual(result, expected)

    def test_get_latest_value(self):  # type () -> None
        """Test getting the latest value for a field."""
        expected = '782859-14778676-1975978063281993217'
        test_logs = [test_utils.get_files_of_type('Uncategorized/frequentdiagnostics.log-2017121100')[0]]
        array = api.FlashArray(start='2017_12_11', end='2017_12_12', files=test_logs)  # type: api.FlashArray
        result = array.get_latest_value('array_id')
        self.assertEqual(result, expected)

    def test_get_latest_value_both_controllers(self):  # type () -> None
        """Test getting the latest value for a field from both controllers."""
        expected = {'CT0': '782859-14778676-1975978063281993217', 'CT1': None}
        test_logs = [test_utils.get_files_of_type('Uncategorized/frequentdiagnostics.log-2017121100')[0]]
        array = api.FlashArray(start='2017_12_11', end='2017_12_12', files=test_logs)  # type: api.FlashArray
        result = array.get_latest_value('array_id', both_controllers=True)
        self.assertEqual(result, expected)


@unittest.skip('Skipping the "full" test as it takes forever.')
class TestLogs(unittest.TestCase):
    """Test log source pulls and parsers for general use."""

    def test_array_info_json_pull(self):  # type: (...) -> None
        """Pull something from array_info_json logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['array_id']))

    # Skip until we have bcon stuff.
    @unittest.skip('No bcon fields to try and parse yet.')
    def test_bcon_pull(self):  # type: (...) -> None
        """Pull something from bcon logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    # Skip until we have cache stuff.
    @unittest.skip('No cache fields to try and parse yet.')
    def test_cache_pull(self):  # type: (...) -> None
        """Pull something from cache logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    def test_core_pull(self):  # type: (...) -> None
        """Pull something from core logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['postman_tcp_info_rcv_space_probe']))

    def test_diagnostics_pull(self):  # type: (...) -> None
        """Pull something from diagnostics logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['controller_mode']))

    def test_frequentdiagnostics_pull(self):  # type: (...) -> None
        """Pull something from frequentdiagnostics logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['num_shelves']))

    # Skip until we have kern stuff.
    @unittest.skip('No kern fields to try and parse yet.')
    def test_kern_pull(self):  # type: (...) -> None
        """Pull something from kern logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    # Skip until we have middleware stuff.
    @unittest.skip('No middleware fields to try and parse yet.')
    def test_middleware_pull(self):  # type: (...) -> None
        """Pull something from middleware logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    def test_hardware_pull(self):  # type: (...) -> None
        """Pull something from hardware logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['bmc_info']))

    # Skip until we have monitor stuff.
    @unittest.skip('No monitor fields to try and parse yet.')
    def test_monitor_pull(self):  # type: (...) -> None
        """Pull something from monitor logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    def test_platform_pull(self):  # type: (...) -> None
        """Pull something from platform logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    # Skip until we have remote stuff.
    @unittest.skip('No remote fields to try and parse yet.')
    def test_remote_kern_pull(self):  # type: (...) -> None
        """Pull something from remote logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    # Skip until we have rdmaoopsd stuff.
    @unittest.skip('No rdmaoopsd fields to try and parse yet.')
    def test_rdmaoopsd_pull(self):  # type: (...) -> None
        """Pull something from rdmaoopsd logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    # Skip until we have stats stuff.
    @unittest.skip('No stats fields to try and parse yet.')
    def test_stats_pull(self):  # type: (...) -> None
        """Pull something from stats logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['dev_info']))

    def test_syslog_pull(self):  # type: (...) -> None
        """Pull something from syslog logs to make sure it doesn't bork."""
        flasharray = api.FlashArray(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_10',
                                    start='Jan 10 00:00:00', end='Jan 10 23:23:23')  # type: api.FlashArray
        self.assertTrue(flasharray.get_fields(['abort_cmd_found']))


if __name__ == '__main__':
    unittest.main()
