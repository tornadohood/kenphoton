"""Unit tests for the Pure1 API."""

import os
import unittest

from photon.lib import array_utils
from photon.lib import time_utils
from photon.backend.pure.pure1 import pure1_api

PATH = os.path.dirname(__file__)
# Photon base directory:
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(PATH))))
# Health status looks like this if it's good: b'["JVM-Thread-Deadlock: OK","Datastore-Query: OK"]'

PURE1_AVAIL = pure1_api.check_kairos()


class Pure1ConnectionTestCase(unittest.TestCase):
    """Test basic instantiation of Pure1Connection."""

    @unittest.skipIf(bool(not PURE1_AVAIL), "Pure1 is not in good health.")
    def test_is_available_180(self):
        """Test if the 180s granularity is available as expected."""
        expected_results = {
            '1ms': False,
            '1s': False,
            '30s': False,
            '3m': True,
            '1h': True,
            '1d': True,
        }
        start = '2018/04/24 00:00:00'
        end = '2018/04/25 10:00:00'
        fields = ['bm_cpu_job_1']
        ident = array_utils.ArrayIdent(fqdn='nycm70pure01.1199nbf.org')
        dummy_timeframe = time_utils.Timeframe(start, end, '45s')
        db_source = pure1_api.Pure1Connection(ident=ident, timeframe=dummy_timeframe)
        for granularity in expected_results:
            timeframe = time_utils.Timeframe(start, end, granularity)
            result = db_source.is_available(ident, fields, timeframe)
            expected = expected_results.get(granularity)
            self.assertEqual(expected, result)

    @unittest.skipIf(bool(not PURE1_AVAIL), "Pure1 is not in good health.")
    def test_is_available_30(self):
        """Test if the 30s granularity is available as expected."""
        expected_results = {
            '1ms': False,
            '1s': False,
            '30s': True,
            '3m': True,
            '1h': True,
            '1d': True,
        }
        start = '2018/04/24 00:00:00'
        end = '2018/04/25 10:00:00'
        fields = ['data_reduction']
        ident = array_utils.ArrayIdent(fqdn='nycm70pure01.1199nbf.org')
        dummy_timeframe = time_utils.Timeframe(start, end, '45s')
        db_source = pure1_api.Pure1Connection(ident=ident, timeframe=dummy_timeframe)
        for granularity in expected_results:
            timeframe = time_utils.Timeframe(start, end, granularity)
            result = db_source.is_available(ident, fields, timeframe)
            expected = expected_results.get(granularity)
            self.assertEqual(expected, result)


class TestGetFieldAvailability(unittest.TestCase):
    """Test get_field_availability."""
    def test_get_fields_avail_30(self):
        """Test that 30s granularity resolves properly."""
        granularity = time_utils.Timedelta('30s')
        result = pure1_api.get_fields_availability(['not_here'], granularity)
        expected = {'not_here': False}
        self.assertEqual(result, expected)

    def test_get_fields_avail_180(self):
        """Test that 180s granularity resolves properly."""
        granularity = time_utils.Timedelta('180s')
        result = pure1_api.get_fields_availability(['cpu_busyness'], granularity)
        expected = {'cpu_busyness': True}
        self.assertEqual(result, expected)

    def test_get_fields_avail_day(self):
        """Test that 86400s granularity resolves properly."""
        granularity = time_utils.Timedelta('86400s')
        result = pure1_api.get_fields_availability(['cpu_busyness'], granularity)
        expected = {'cpu_busyness': True}
        self.assertEqual(result, expected)


class TestGetMetricQueries(unittest.TestCase):
    """Test that we make the proper metric query strings."""
    def test_converted_to_bm(self):
        """Test a field name that would convert to bm_<field>."""
        fields = ['cpu_busyness']
        granularity = time_utils.Timedelta('1d')
        result = pure1_api.get_metric_queries(fields, granularity, '123')
        expected = {'cpu_busyness': {'cpu_busyness': 'orgid_123|type_array|rollup_PT3M|bm_cpu_busyness'}}
        self.assertEqual(result, expected)

    def test_bad_granularity(self):
        """Test a bad granularity."""
        fields = ['cpu_busyness']
        granularity = time_utils.Timedelta('1s')
        result = pure1_api.get_metric_queries(fields, granularity, '123')
        expected = {'cpu_busyness': {}}
        self.assertEqual(result, expected)

    def test_normal_field_name(self):
        """Test a normal field name."""
        fields = ['data_reduction']
        granularity = time_utils.Timedelta('30s')
        result = pure1_api.get_metric_queries(fields, granularity, '123')
        expected = {'data_reduction': {'data_reduction': 'orgid_123|type_array|rollup_PT30S|data_reduction'}}
        self.assertEqual(result, expected)
