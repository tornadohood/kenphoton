"""Unit tests for lib/time_utils."""

from __future__ import unicode_literals

import datetime
import unittest

import numpy
import pandas
import pytest
import pytz

from photon.lib import array_utils
from photon.lib import config_utils
from photon.lib import time_utils


START = pandas.Timestamp('2017-12-19 16:30:05.418725')
END = pandas.Timestamp('2017-12-21 16:31:05.418727')
FREQ = pandas.Timedelta('0 days 00:01:00')

GOOD_TS = ('2018 Jan 17 00:16:32',
           '2018_01_01',
           '2018_10_27-22',
           '10/27/2017 10:3722.123')
GOOD_TS_MANUAL = {'year': 2018, 'month': 1, 'day': 17, 'hour': 00, 'minute': 16, 'second': 32}
BAD_TS = 'Jan 17 00:16:32'
SETTINGS = config_utils.get_settings()

# We're testing the protected class methods on purpose, so disabling this.
# pylint: disable=protected-access, invalid-name
# TODO: PT-2212 - Convert to pytest completely.

LOGFILES = [
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010200.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010201.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010202.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010203.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010204.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010205.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010206.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010207.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010208.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010209.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010210.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010211.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010212.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010213.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010214.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010215.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010216.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010217.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010218.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010219.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010220.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010221.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010222.gz',
    '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010223.gz',
]


@pytest.fixture(autouse=True)
def os_listdir(monkeypatch):
    """Replace os.listdir with static results for testing purposes."""
    monkeypatch.setattr(time_utils.os, 'listdir',
                        lambda _: LOGFILES)


def test_good_ts():
    """Test valid pandas timestamp."""
    expected = pandas.Timestamp(**GOOD_TS_MANUAL)
    result = time_utils.Timestamp(GOOD_TS[0])
    assert expected == result


def test_bad_ts():
    """ Test invalid pandas timestamp."""
    expected = pandas.Timestamp(**GOOD_TS_MANUAL)
    result = time_utils.Timestamp(BAD_TS, year=2018)
    assert expected == result


def test_good_ts_manual():
    """ Test that manual input works equivalently. """
    expected = pandas.Timestamp(**GOOD_TS_MANUAL)
    result = time_utils.Timestamp(**GOOD_TS_MANUAL)
    assert expected == result


def test_bad_ts_manual_no_day():
    """ Make sure we raise errors when we should."""
    with pytest.raises(TypeError):
        time_utils.Timestamp(year=2018, month=1)


def test_bad_ts_manual_string_month():
    """ Make sure we can't take the wrong kind of input since we're subclassing."""
    with pytest.raises(TypeError):
        time_utils.Timestamp(year=2018, month='Jan', day=1)


def test_epoch_time_input():
    """Make sure that we can handle epoch time float/int as input."""
    # Test integer
    assert time_utils.Timestamp(1518481882)
    assert time_utils.Timestamp(1518481882.0000000001)


def test_invalid_ts():
    """Test that Epoch 0 evaluates between Timestamp objects."""
    # NOTE: For epoch 0, we had to default to using a pandas.Timestamp object
    # so that we could define that without needing to use a time_utils.Timestamp
    # object before it was defined, and with as little complication as possible.
    # This tests that assumptions based on that comparison will still be true,
    # like if a Timestamp() object at epoch zero is actually equivalent to the
    # INVALID_TIMESTAMP.
    assert pandas.Timestamp('Jan 1 1970 00:00:00') == time_utils.Timestamp('Jan 1 1970 00:00:00')


def test_ts_comparisons():
    """Testing comparisons for timestamps for various timedelta differences."""
    # First, ensure that our comparisons have a valid basis by equating
    # the invalidation criteria for an invalid timestamp comparison:
    # Deltas will be added and subtracted to the base timestamp and then the comparison will be made
    deltas = (
        time_utils.Timedelta('365 days'),
        time_utils.Timedelta('30 days'),
        time_utils.Timedelta('1 days'),
        time_utils.Timedelta('1h'),
        time_utils.Timedelta('1m'),
        time_utils.Timedelta('1s'),
        time_utils.Timedelta('1ms'),
        time_utils.Timedelta('1us'),
    )
    # To simplify the test itself, rather than writing all of these explicitely, we're going through each
    # a tuple that has the operator/symbol for message creation, and then two lambdas.
    # The first lambda:
    # is the action lambda - this will modify the timstamp in the way we want for the comparison - e.g. for
    # a comparison where we would expect one to be greater than the other, we will add the delta to one and
    # then check that it's greater than it was.  Likewise with less than operations.
    # The second lambda:
    # is the actual comparison lambda that compares the modified timestamp to the original timestamp in the way
    # that we expect to result in true for the comparison type and timedelta.
    operators = [
        # Keeping the whitespace bad makes this significantly easier to follow what the things are.
        # pylint: disable=bad-whitespace
        # operator, symbol, action lambda, comparison lambda
        ('>',  '+',  lambda base_ts, delta: base_ts + delta,   lambda mod_ts, base_ts: mod_ts > base_ts),
        ('<',  '-',  lambda base_ts, delta: base_ts - delta,   lambda mod_ts, base_ts: mod_ts < base_ts),
        ('==', '',   lambda base_ts, delta: base_ts,           lambda mod_ts, base_ts: mod_ts == base_ts),
        ('!=', '-',  lambda base_ts, delta: base_ts - delta,   lambda mod_ts, base_ts: mod_ts != base_ts),
        ('!=', '+',  lambda base_ts, delta: base_ts + delta,   lambda mod_ts, base_ts: mod_ts != base_ts),
        ('>=', '+',  lambda base_ts, delta: base_ts + delta,   lambda mod_ts, base_ts: mod_ts >= base_ts),
        ('<=', '-',  lambda base_ts, delta: base_ts - delta,   lambda mod_ts, base_ts: mod_ts <= base_ts),
    ]
    # base_ts is what we will modify and compare against.
    base_ts = time_utils.Timestamp('2018-08-08 14:48:32.731669')
    for operator, symbol, action, cmp in operators:
        for delta in deltas:
            # Run through the comparisons at each timedelta difference, creating a "modified" timestamp that we
            # will compare with the original.
            mod_ts = action(base_ts, delta)
            assert cmp(mod_ts, base_ts), 'Failed comparison {} {} {} ({}) {} {}'.format(base_ts, symbol, delta, mod_ts, operator, base_ts)
            # We also want to test these comparisons against the instance where it might be a string.


class TimeframeTestCase(unittest.TestCase):
    """Tests for the Timeframe object."""
    log_files = [
        # A log type with no timestamp in the file but it is in the path.
        '/logs/domain.com/array-ct0/2017_12_31/array_info.json.gz',
        '/logs/domain.com/array-ct0/2018_01_01/array_info.json.gz',
        '/logs/domain.com/array-ct0/2018_01_02/array_info.json.gz',
        '/logs/domain.com/array-ct0/2018_01_03/array_info.json.gz',
        'diagnostics.log-2017123122.gz',
        'diagnostics.log-2017123123.gz',
        'diagnostics.log-2018010100.gz',
        'diagnostics.log-2018010101.gz',
        'diagnostics.log-2018010102.gz',
        'diagnostics.log-2018010103.gz',
        'diagnostics.log-2018010104.gz',
        'diagnostics.log-2018010123.gz',
        'diagnostics.log-2018010200.gz',
        'diagnostics.log-2018010201.gz',
        'diagnostics.log-2018010202.gz',
        'diagnostics.log-2018010203.gz',
        'hardware.log-2017123100.gz',
        'hardware.log-2018010100.gz',
        'hardware.log-2018010200.gz',
        'hardware.log-2018010300.gz',
    ]

    def test_validate_input(self):
        """Test that invalid inputs are raised as errors."""
        # We should assert if start time is after end time
        with self.assertRaises(ValueError):
            time_utils.Timeframe(start=END, end=START)
        # We should assert if granularity is greater than end - start
        with self.assertRaises(ValueError):
            time_utils.Timeframe(start=START, end=END,
                                 granularity=pandas.Timedelta('4 days 00:00:00'))

    def test_filter_logs_by_time_1(self):
        """Test filtering log files by a same day one hour range."""
        time_frame = time_utils.Timeframe(start='2018_01_01-01', end='2018_01_01-02')
        result = time_frame.filter_logs_by_time(self.log_files)
        expected = [
            '/logs/domain.com/array-ct0/2018_01_01/array_info.json.gz',
            'diagnostics.log-2018010100.gz',
            'diagnostics.log-2018010101.gz',
            'diagnostics.log-2018010102.gz',
            'hardware.log-2018010100.gz',
        ]
        self.assertEqual(expected, result)

    def test_filter_logs_keep_daily(self):
        """Test filtering log files by a same day one hour range that would exclude daily if we don't filter properly."""
        time_frame = time_utils.Timeframe(start='2018_01_01-01 02:00:00', end='2018_01_01-01 03:00:00')
        result = time_frame.filter_logs_by_time(self.log_files)
        expected = [
            '/logs/domain.com/array-ct0/2018_01_01/array_info.json.gz',
            'diagnostics.log-2018010101.gz',
            'diagnostics.log-2018010102.gz',
            'diagnostics.log-2018010103.gz',
            'hardware.log-2018010100.gz',
        ]
        self.assertEqual(expected, result)

    def test_filter_logs_by_time_2(self):
        """Test filtering log files by a midnight one hour same day range."""
        time_frame = time_utils.Timeframe(start='2018_01_01-00', end='2018_01_01-01')
        result = time_frame.filter_logs_by_time(self.log_files)
        expected = [
            '/logs/domain.com/array-ct0/2018_01_01/array_info.json.gz',
            'diagnostics.log-2017123123.gz',
            'diagnostics.log-2018010100.gz',
            'diagnostics.log-2018010101.gz',
            'hardware.log-2018010100.gz',
        ]
        self.assertEqual(expected, result)

    def test_filter_logs_by_time_3(self):
        """Test filtering log files by time range spanning midnight."""
        time_frame = time_utils.Timeframe(start='2018_01_01-23', end='2018_01_02-01')
        result = time_frame.filter_logs_by_time(self.log_files)
        expected = [
            '/logs/domain.com/array-ct0/2018_01_01/array_info.json.gz',
            '/logs/domain.com/array-ct0/2018_01_02/array_info.json.gz',
            'diagnostics.log-2018010123.gz',
            'diagnostics.log-2018010200.gz',
            'diagnostics.log-2018010201.gz',
            'hardware.log-2018010100.gz',
            'hardware.log-2018010200.gz',
        ]
        self.assertEqual(expected, result)

    def test_filter_logs_by_time_4(self):
        """Test filtering log files by time range one hour before midnight to midnight."""
        time_frame = time_utils.Timeframe(start='2018_01_01-23', end='2018_01_02-00')
        result = time_frame.filter_logs_by_time(self.log_files)
        expected = [
            '/logs/domain.com/array-ct0/2018_01_01/array_info.json.gz',
            '/logs/domain.com/array-ct0/2018_01_02/array_info.json.gz',
            'diagnostics.log-2018010123.gz',
            'diagnostics.log-2018010200.gz',
            'hardware.log-2018010100.gz',
            'hardware.log-2018010200.gz',
        ]
        self.assertEqual(expected, result)

    def test_filter_logs_by_time_5(self):
        """Test filtering log files by a time range at the end of the day before 11pm"""
        time_frame = time_utils.Timeframe(start='2018_01_01-21', end='2018_01_01-23')
        result = time_frame.filter_logs_by_time(self.log_files)
        expected = [
            '/logs/domain.com/array-ct0/2018_01_01/array_info.json.gz',
            'diagnostics.log-2018010123.gz',
            'hardware.log-2018010100.gz',
        ]
        self.assertEqual(expected, result)

    def test_generate_interval_times(self):
        """Ensure that when we do from_start that we get the same times."""
        timeframe_from_start = time_utils.Timeframe(START, END, from_start=True, granularity='60s')
        timeframe_from_end = time_utils.Timeframe(START, END, from_start=False, granularity='60s')
        self.assertNotEqual(timeframe_from_start.times[0:5], timeframe_from_end.times[0:5])
        self.assertNotEqual(timeframe_from_start.times[-6:-1], timeframe_from_end.times[-6:-1])
        from_start = [time_utils.Timestamp('2017-12-19 16:30:05.418725'),
                      time_utils.Timestamp('2017-12-19 16:31:05.418725'),
                      time_utils.Timestamp('2017-12-19 16:32:05.418725'),
                      time_utils.Timestamp('2017-12-19 16:33:05.418725'),
                      time_utils.Timestamp('2017-12-19 16:34:05.418725')]
        from_end = [time_utils.Timestamp('2017-12-19 16:30:05.418725'),
                    time_utils.Timestamp('2017-12-19 16:30:05.418727'),
                    time_utils.Timestamp('2017-12-19 16:31:05.418727'),
                    time_utils.Timestamp('2017-12-19 16:32:05.418727'),
                    time_utils.Timestamp('2017-12-19 16:33:05.418727')]
        self.assertEqual(timeframe_from_start.times[0:5], from_start)
        self.assertEqual(timeframe_from_end.times[0:5], from_end)

    def test_generate_interval(self):
        """Test that we can generate an interval based on the same criteria as our timeframe."""
        timeframe = time_utils.Timeframe(start=START, end=END, granularity=FREQ)
        timeframe_interval = timeframe.generate_interval(granularity='10min')
        pd_interval = pandas.date_range(start=START, end=END, freq='10min')
        # Check that interval granularity is the same
        self.assertEqual(timeframe_interval[1] - timeframe_interval[0],
                         pandas.Timedelta(pd_interval.freq))
        # Check that we have the same value for our first entry
        self.assertEqual(timeframe_interval[3], pandas.Timestamp(pd_interval.to_series()[3]))

    def test_generate_filenames(self):
        """Tests that timeframe.generate_file_stamps is equivalent to the generate_file_stamps."""
        timeframe = time_utils.Timeframe(start=START, end=END, granularity=FREQ)
        timeframe_file_stamps = timeframe.generate_filenames('core.log')
        file_stamps = time_utils.generate_filenames_in_range('core.log', '.gz', START, END)
        self.assertEqual(timeframe_file_stamps, file_stamps)

    def test_times(self):
        """Test that start and end times are equivalent to their respective timestamps."""
        # Start and end timestamps should be equal.
        self.assertEqual(time_utils.Timeframe(START, END).times[0], START)
        self.assertEqual(time_utils.Timeframe(START, END).times[-1], END)
        # The times shouldn't be equivalent for the from_start True vs False
        self.assertNotEqual(time_utils.Timeframe(START, END, from_start=True).times[1],
                            time_utils.Timeframe(START, END, from_start=False).times[1])

    def test_dates(self):
        """Test that dates aren't modified incorrectly when instantiating."""
        timeframe = time_utils.Timeframe(START, END)
        dates = [time_utils.Timestamp(day.date()) for day in pandas.date_range(start=START, end=END)]
        # pylint: disable=no-member
        self.assertEqual(timeframe.start.date(), START.date())
        self.assertEqual(timeframe.end.date(), END.date())
        self.assertEqual(timeframe.dates, dates)

    def test_exportable(self):
        """Test that exportable dictionary is what we'd expect."""
        timeframe = time_utils.Timeframe(START, END, FREQ)
        expected_exportable_dict = {'start': START, 'end': END, 'granularity': FREQ}
        self.assertEqual(expected_exportable_dict, timeframe.exportable)

    def test_from_exportable(self):
        """Test that exported dictionary instantiated timeframe is equivalent to normal."""
        exportable_dict = {'start': START, 'end': END, 'granularity': FREQ}
        timeframe_from_exportable = time_utils.Timeframe.from_exportable(exportable_dict)
        timeframe = time_utils.Timeframe(start=START, end=END, granularity=FREQ)
        # These should be equivalent if we're exporting correctly.
        self.assertEqual(timeframe.times, timeframe_from_exportable.times)
        self.assertEqual(timeframe.start, timeframe_from_exportable.start)
        self.assertEqual(timeframe.end, timeframe_from_exportable.end)
        self.assertEqual(timeframe.granularity, timeframe_from_exportable.granularity)
        self.assertEqual(timeframe.dates, timeframe_from_exportable.dates)
        # We should assert if we get a dict that doesn't have the keys we need.
        with self.assertRaises(TypeError):
            time_utils.Timeframe.from_exportable({'bad': 1, 'dict': 2})

    def test_from_exact_time(self):
        """Test that when creating from exact time we create the same as we would manually."""
        timeframe = time_utils.Timeframe.from_exact_time(
            exact_time=START, buffer_time=pandas.Timedelta('0 days 00:10:00'),
            granularity=pandas.Timedelta('0 days 00:00:30'))
        upper_time = START + pandas.Timedelta('0 days 00:10:00')
        lower_time = START - pandas.Timedelta('0 days 00:10:00')
        # We should have the exact_time - buffer_time and + buffer time
        self.assertIn(upper_time, timeframe.times)
        self.assertIn(lower_time, timeframe.times)
        self.assertIn(START, timeframe.times)
        # A Timeframe built from the exact_time should have the same original exact time in it
        timeframe_from_exact_time_timeframe_attrs = time_utils.Timeframe(
            start=timeframe.start, end=timeframe.end, granularity=timeframe.granularity)
        self.assertIn(START, timeframe_from_exact_time_timeframe_attrs.times)

    def test_generate_fuse_log_paths(self):
        """Test that two days for timeframe overlapping midnight."""
        log_path = '/logs/ofsoptics.com/corp-ofs-pure-san01-ct0/2018_06_20'
        slash_path = '/logs/ofsoptics.com/corp-ofs-pure-san01-ct0/2018_06_20/'
        timeframe_near_midnight = time_utils.Timeframe('June 20 2018 23:00:00', 'June 21 2018 03:00:00', granularity='1h')
        expected = sorted(['/logs/ofsoptics.com/corp-ofs-pure-san01-ct0/2018_06_20',
                           '/logs/ofsoptics.com/corp-ofs-pure-san01-ct0/2018_06_21',
                           '/logs/ofsoptics.com/corp-ofs-pure-san01-ct1/2018_06_20',
                           '/logs/ofsoptics.com/corp-ofs-pure-san01-ct1/2018_06_21'])
        result = timeframe_near_midnight.generate_fuse_log_paths(log_path)
        slash_result = timeframe_near_midnight.generate_fuse_log_paths(slash_path)
        self.assertEqual(expected, result)
        self.assertEqual(expected, slash_result)

    def test_trailing_slash_log_paths(self):
        """Test that two days for timeframe overlapping midnight."""
        log_path = '/logs/ofsoptics.com/corp-ofs-pure-san01-ct0/2018_06_20/'
        timeframe_near_midnight = time_utils.Timeframe('June 20 2018 23:00:00', 'June 21 2018 03:00:00', granularity='1h')
        expected = sorted(['/logs/ofsoptics.com/corp-ofs-pure-san01-ct0/2018_06_20',
                           '/logs/ofsoptics.com/corp-ofs-pure-san01-ct0/2018_06_21',
                           '/logs/ofsoptics.com/corp-ofs-pure-san01-ct1/2018_06_20',
                           '/logs/ofsoptics.com/corp-ofs-pure-san01-ct1/2018_06_21'])
        result = timeframe_near_midnight.generate_fuse_log_paths(log_path)
        self.assertEqual(expected, result)


class GenerateFileStampsInRangeTestCase(unittest.TestCase):
    """Test generation of file timestamps from range."""

    def test_core_log_generation(self):
        """Test that we generate the right core file list with the given range."""
        expected = ['core.log-2017121916.gz',
                    'core.log-2017121917.gz',
                    'core.log-2017121918.gz',
                    'core.log-2017121919.gz',
                    'core.log-2017121920.gz']
        result = time_utils.generate_filenames_in_range(
            'core.log', '.gz',
            pandas.Timestamp('2017-12-19 16:30:05.418725'),
            pandas.Timestamp('2017-12-19 19:30:05.418725'))
        self.assertEqual(expected, result)


class TimedeltaTestCase(unittest.TestCase):
    """ Test cases to make sure timedelta object is performing as expected. """

    def test_from_years_to_seconds(self):
        """ From days to seconds. """
        self.assertEqual(31536000.0, round(time_utils.Timedelta.from_years(1).seconds, 1))

    def test_from_days_to_seconds(self):
        """ from_days to seconds. """
        self.assertEqual(86400.0, time_utils.Timedelta.from_days(1).seconds)

    def test_from_hours_to_seconds(self):
        """ from_hours to seconds. """
        self.assertEqual(3600.0, time_utils.Timedelta.from_hours(1).seconds)

    def test_from_minutes_to_seconds(self):
        """ from_minutes to seconds. """
        self.assertEqual(60.0, round(time_utils.Timedelta.from_minutes(1).seconds, 1))

    def test_from_seconds_to_seconds(self):
        """ from_seconds to seconds. """
        self.assertEqual(1.0, time_utils.Timedelta.from_seconds(1).seconds)

    def test_from_milliseconds_to_seconds(self):
        """ from_milliseconds to seconds. """
        self.assertEqual(0.001, time_utils.Timedelta.from_milliseconds(1).seconds)

    def test_from_microseconds_to_seconds(self):
        """ from_microseconds to seconds. """
        self.assertEqual(0.001, time_utils.Timedelta.from_microseconds(1000).seconds)

    def test_from_nanoseconds_to_seconds(self):
        """ from_nanoseconds to seconds. """
        self.assertEqual(0.001, time_utils.Timedelta.from_nanoseconds(1000000).seconds)

    def test_day_in_seconds(self):
        """ From day to seconds. """
        self.assertEqual(86400.0, time_utils.Timedelta('1 day').seconds)

    def test_hour_in_seconds(self):
        """ From hour to seconds. """
        self.assertEqual(3600.0, time_utils.Timedelta('1 hour').seconds)

    def test_min_in_seconds(self):
        """ From min to seconds. """
        self.assertEqual(60.0, round(time_utils.Timedelta('1 min').seconds, 1))

    def test_s_in_seconds(self):
        """ From s to seconds. """
        self.assertEqual(1.0, time_utils.Timedelta('1 s').seconds)

    def test_ms_in_seconds(self):
        """ From ms to seconds. """
        self.assertEqual(0.001, time_utils.Timedelta('1 ms').seconds)

    def test_us_in_seconds(self):
        """ From us to seconds. """
        self.assertEqual(0.001, time_utils.Timedelta('1000 us').seconds)

    def test_ns_in_seconds(self):
        """ From ns to seconds. """
        self.assertEqual(0.001, time_utils.Timedelta('1000000 ns').seconds)

    def test_str_with_days(self):
        """Test using input which contains a 'd:h:m:s' notation."""
        day_delta = '1d:23h:05m:23s'
        hr_delta = '47h:05m:23s'
        self.assertEqual(time_utils.Timedelta(day_delta), time_utils.Timedelta(hr_delta))


class TestGetTimestampFromLine(unittest.TestCase):
    """Unit tests for get_timestamp_from_line."""

    def test_good_timestamps(self):
        """Test using valid timestamps."""
        line1 = '2019 Jan 17 00:16:32.000 and more line'
        line2 = 'Jan 17 00:16:32.000 and more line'
        line3 = 'Jan 17 00:16:32 and more line'
        line4 = '2019 Jan 17 00:16:32 and more line'
        line1_expected = time_utils.Timestamp('2019 Jan 17 00:16:32.000')
        line2_expected = time_utils.Timestamp('Jan 17 00:16:32.000')
        line3_expected = time_utils.Timestamp('Jan 17 00:16:32')
        line4_expected = time_utils.Timestamp('2019 Jan 17 00:16:32')
        self.assertEqual(time_utils.get_timestamp_from_line(line1), line1_expected)
        self.assertEqual(time_utils.get_timestamp_from_line(line2), line2_expected)
        self.assertEqual(time_utils.get_timestamp_from_line(line3), line3_expected)
        self.assertEqual(time_utils.get_timestamp_from_line(line4), line4_expected)

    def test_bad_timestamp(self):
        """Test using a bad timestamp."""
        bad_line = 'Just a line with no stamp.'
        self.assertEqual(time_utils.get_timestamp_from_line(bad_line), time_utils.INVALID_TIMESTAMP)

    def test_multi_timestamp(self):
        """Test with multiple timestamps in a single line."""
        line = '2019 Jan 17 00:16:32.000 and more line 2019 Jan 18 00:16:32.000'
        expected = time_utils.Timestamp('2019 Jan 17 00:16:32.000')
        self.assertEqual(time_utils.get_timestamp_from_line(line), expected)


class ToEpochTimeTestCase(unittest.TestCase):
    """Unit tests for to_epoch_time."""
    ts_obj = time_utils.Timestamp('Thursday, April 19, 2018 10:04:05 PM')

    def test_invalid_timzone(self):
        """Test a valid Timestamp, but an invalid timezone string."""
        with self.assertRaises(pytz.UnknownTimeZoneError):
            time_utils.to_epoch_time(self.ts_obj, 'Fake Timezone')

    def test_utc_tz(self):
        """Test with a UTC timezone."""
        expected = 1524175445
        result = time_utils.to_epoch_time(self.ts_obj, 'UTC')
        self.assertEqual(expected, result)

    def test_valid_tz(self):
        """Test with a valid timezone that is not UTC."""
        expected = 1524193445
        result = time_utils.to_epoch_time(self.ts_obj, 'America/Chicago')
        self.assertEqual(expected, result)


class GenerateTimeFrameTestCase(unittest.TestCase):
    """Unit tests for generate_timeframe."""

    def test_ident_and_start_end(self):
        """Test when we have an ident with a log_path and start/end dates given (PT-2174)."""
        # We should use the manual start/end dates.
        ident = array_utils.ArrayIdent(log_path='/logs/domain.com/array-ct0/2018_12_25')
        expected = (time_utils.Timestamp('2018-12-20 10:00:01'), time_utils.Timestamp('2018-12-20 11:00:01'))
        result = time_utils.generate_timeframe(start='2018-12-20 10:00:01', end='2018-12-20 11:00:01', ident=ident)
        self.assertEqual(expected, (result.start, result.end))

    def test_start_no_end(self):
        """Test with a start, but no end."""
        expected = time_utils.Timeframe(start='2018-12-19 10:00:01', end='2018-12-20 10:00:01')
        result = time_utils.generate_timeframe(start='2018-12-19 10:00:01', from_latest='1d')
        self.assertEqual(expected, result)

    def test_end_no_start(self):
        """Test with an end, but no start."""
        expected = time_utils.Timeframe(start='2018-12-19 07:00:01', end='2018-12-19 10:00:01')
        result = time_utils.generate_timeframe(end='2018-12-19 10:00:01', from_latest='3h')
        self.assertEqual(expected, result)

    def test_with_dated_log_path(self):
        """Test with no start and no end; full log path on FUSE."""
        ident = array_utils.ArrayIdent(log_path='/logs/purestorage.com/slc-coz-ct1/2018_01_02')
        expected_start = time_utils.Timestamp('2018-01-02 00:00:00')
        expected_end = time_utils.Timestamp('2018-01-03 00:00:00')
        result = time_utils.generate_timeframe(ident=ident)
        assert expected_start == result.start
        assert expected_end == result.end

    def test_with_files(self):
        """Test with no start and no end, no log path, just files in the Ident."""
        # The start should be "2018-03-14 14:00".
        # The end should be "2018-03-15 15:00".
        files = ['core.log-2018031414.gz', 'core.log-2018031415.gz', 'core.log-2018031515.gz']
        ident = array_utils.ArrayIdent(files=files)
        expected_start = time_utils.Timestamp('2018-03-14 14:00:00')
        expected_end = time_utils.Timestamp('2018-03-15 15:00:00')
        result = time_utils.generate_timeframe(ident=ident)
        end = result.end
        start = result.start
        # Because we generate the start/end dynamically, we round to the nearest hour to
        # prevent erroneous failures.
        self.assertEqual(expected_end, end)
        self.assertEqual(expected_start, start)

    def test_with_non_timestamped_files(self):
        """Test that we get appropriate results with non timestamped files."""
        files = ['hardware.log.gz']
        ident = array_utils.ArrayIdent(files=files)
        expected_start = time_utils.INVALID_TIMESTAMP
        # the now() and round attributes are inherited from the pandas.Timestamp.
        # pylint: disable=no-member
        result = time_utils.generate_timeframe(ident=ident)
        expected_end = time_utils.Timestamp.now() + time_utils.Timedelta('24h')
        self.assertEqual(expected_start, result.start)
        # NOTE: Since we're getting a "now()" we want to sanity check that it's about the
        # right time, but it'll never be exactly - This may be over generous for what
        # we actually need, but f we're within a few seconds it's still way within
        # the safe zone of it generating an accurate timeframe.  The number is arbitrary.
        low_range = expected_end - time_utils.Timedelta('5s')
        high_range = expected_end + time_utils.Timedelta('5s')
        assert low_range < result.end
        assert high_range > result.end

    def test_with_mixed_date_files(self):
        """Test that we get appropriate results with mixed date files."""
        files = ['hardware.log.gz', 'core.log-2018031414.gz']
        ident = array_utils.ArrayIdent(files=files)
        result = time_utils.generate_timeframe(ident=ident)
        expected = time_utils.Timeframe(start='2018-03-14 14:00:00', end='2018-03-14 15:00:00')
        # Comparing the dict rather than the instance, since we haven't implemented rich
        # comparisons.
        self.assertEqual(result, expected)

    def test_on_box(self):
        """Test with no information except that we are on-box."""
        ymd = '%y-%m-%d'
        ident = array_utils.ArrayIdent()
        now = datetime.datetime.now()
        # Override this for the sake of testing:
        ident.on_box = True
        # pylint: disable=no-member
        expected_start = (now - time_utils.Timedelta(SETTINGS['parsers']['default_granularity'])).strftime(ymd)
        expected_end = datetime.datetime.now().strftime(ymd)
        result = time_utils.generate_timeframe(ident=ident, from_latest='1h')
        end = result.end.strftime(ymd)
        start = result.start.strftime(ymd)
        self.assertEqual(expected_end, end)
        self.assertEqual(expected_start, start)

    def test_bad_granularity(self):
        """Test validating the min/max granularity."""
        start = '2018_01_01-02'
        end = '2018_01_02-03'
        with self.assertRaises(ValueError):
            granularity = '1us'
            time_utils.Timeframe(start, end, granularity)
        with self.assertRaises(ValueError):
            granularity = '2d'
            time_utils.Timeframe(start, end, granularity)
        # Now some good granularities just to be sure we're working right:
        good_granularities = ('1ms', '1 day', '1 second', '1 minute', '30 minutes', '30 seconds')
        for granul in good_granularities:
            self.assertTrue(time_utils.Timeframe(start, end, granul))

    def test_same_result(self):
        """Ensure that we get the same result when using these various methods of generating."""
        ident1 = array_utils.ArrayIdent(files=['core.log-2018010100.gz', 'core.log-2018010200.gz'])
        expected = "Timeframe(start='2018-01-01 00:00:00', end='2018-01-02 00:00:00')"
        timeframes = [
            time_utils.generate_timeframe(start='2018_01_01-00', end='2018_01_02-00'),
            time_utils.generate_timeframe(start='2018_01_01-00', granularity='1d'),
            time_utils.generate_timeframe(end='2018_01_02-00', granularity='1d'),
            time_utils.generate_timeframe(ident=ident1),
        ]
        for index, timeframe in enumerate(timeframes):
            msg = 'Failed at index {}.  {} != {}.'.format(index, expected, str(timeframe))
            self.assertEqual(expected, str(timeframe), msg=msg)


class GetTimestampFromFilesTestCase(unittest.TestCase):
    """Unit tests for get_timestamp_from_files."""

    def test_with_duplicates(self):
        """Ensure that all duplicates are removed."""
        logs = {'core.log': ['core.log-2018031514.gz', 'core.log-2018031415.gz', 'core.log-2018031415.gz']}
        log_times = time_utils.get_timestamps_from_files(logs)
        expected = [time_utils.Timestamp('2018-03-14 15:00:00'), time_utils.Timestamp('2018-03-15 14:00:00')]
        self.assertEqual(expected, log_times)


class TestGetTimestampFromLogPath(unittest.TestCase):
    """Unit test for get_timestamp_from_log_path."""

    def test_valid_log_paths(self):
        """Test using valid log paths."""
        paths = (
            '/logs/purestorage.com/slc-coz-ct1/2018_05_09/',
            '/logs/purestorage.com/slc-coz-ct1/2018_05_09',
        )
        for log_path in paths:
            result = time_utils.get_timestamp_from_log_path(log_path)
            self.assertEqual('2018-05-09 00:00:00', str(result))


class TestScaleLatency(unittest.TestCase):
    """Unit tests for scale_latency."""

    def test_auto_scale_values(self):
        """Test auto-scaling values."""
        values = (1, 100, 1000, 1000000, 100000000)
        expected_values = {
            1: '1.00 s',
            100: '1.67 m',
            1000: '16.67 m',
            1000000: '11.57 d',
            100000000: '3.17 y',
        }
        for value in values:
            expected_value = expected_values[value]
            result = time_utils.scale_latency(value, base_unit='seconds')
            self.assertEqual(result, expected_value)

    def test_scale_to_unit(self):
        """Test scaling values to a static unit."""
        values = (1, 100, 1000, 1000000, 100000000)
        expected_values = {
            1: '0.02 m',
            100: '1.67 m',
            1000: '16.67 m',
            1000000: '16666.67 m',
            100000000: '1666666.67 m',
        }
        for value in values:
            expected_value = expected_values[value]
            result = time_utils.scale_latency(value, base_unit='seconds', display_unit='minutes')
            self.assertEqual(result, expected_value)

    def test_precision(self):
        """Test changing the precision."""
        value = 100.1234
        expected = '100.12 ms'
        result = time_utils.scale_latency(value, base_unit='milliseconds', precision=2)
        self.assertEqual(result, expected)


class TestToRawLatency(unittest.TestCase):
    """Unit tests for to_raw_latency."""

    def test_nan(self):
        """Test a numpy.nan value; this should pass through unchanged."""
        self.assertTrue(numpy.isnan(time_utils.to_raw_latency(numpy.nan, 'ms')))

    def test_unknown_base_unit(self):
        """Bad base_unit requested.  This should raise a ValueError."""
        with self.assertRaises(ValueError):
            time_utils.to_raw_latency('12345 Fake')

    def test_unknown_scale(self):
        """Bad unit found in the item.  This should raise a ValueError."""
        with self.assertRaises(ValueError):
            time_utils.to_raw_latency('12345 B', 'Fake Scale')

    def test_valid_usage(self):
        """A valid unit and item."""
        expected = 1000.0
        result = time_utils.to_raw_latency('1 second', 'ms')
        self.assertEqual(expected, result)


def test_get_start_end_from_empty_files():
    """Unit tests get_start_end_from_files."""

    # Files is an empty list
    files = []
    expected_start = time_utils.INVALID_TIMESTAMP
    # pylint: disable=no-member
    expected_end = time_utils.Timestamp.now() + time_utils.Timedelta('24h')
    start, end = time_utils.get_start_end_from_files(files, None)
    assert start == expected_start
    assert expected_end - time_utils.Timedelta('5s') < end
    assert expected_end + time_utils.Timedelta('5s') > end


def test_get_start_end_from_single():
    """Unit tests get_start_end_from_files."""

    fail_msg = 'Files has one file that\'s timestamped'
    files = ['/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010200.gz']
    expected = time_utils.Timestamp('2018-01-02 00:00:00'), time_utils.Timestamp('2018-01-02 01:00:00')
    result = time_utils.get_start_end_from_files(files, None)
    assert result == expected, fail_msg


def test_get_start_end_from_multiple_files():
    """Unit tests get_start_end_from_files."""

    fail_msg = 'Failed for multiple files that are timestamped.'
    files = [
        '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010123.gz',
        '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010200.gz',
        '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010201.gz',
    ]
    expected = time_utils.Timestamp('2018-01-01 23:00:00'), time_utils.Timestamp('2018-01-02 01:00:00')
    result = time_utils.get_start_end_from_files(files, None)
    assert result == expected, fail_msg


def test_get_start_end_from_datepath_files():
    """Unit tests get_start_end_from_files."""

    fail_msg = "Files has one file that's not timestamped with dated path"
    files = ['/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log']
    expected = time_utils.Timestamp('2018-01-02 00:00:00'), time_utils.Timestamp('2018-01-02 01:00:00')
    result = time_utils.get_start_end_from_files(files, None)
    assert result == expected, fail_msg


def test_get_start_end_from_multiple_datepath_files():
    """Unit tests get_start_end_from_files."""

    fail_msg = 'Files has multiple files that are not timestamped'
    files = [
        '/logs/purestorage.com/slc-coz-ct1/2018_01_01/core.log.gz',
        '/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log.gz',
        '/logs/purestorage.com/slc-coz-ct1/2018_01_03/core.log.gz',
    ]
    expected = time_utils.Timestamp('2018-01-01 00:00:00'), time_utils.Timestamp('2018-01-03 00:00:00')
    result = time_utils.get_start_end_from_files(files, None)
    assert result == expected, fail_msg


def test_get_start_end_from_garbage_files():
    """Unit tests get_start_end_from_files."""

    fail_msg = 'Files has mutiple garbage files.'
    files = [
        'myfile.txt',
        'log1.gz',
        'cause_misspeling_that_bothers_jhop.py'
    ]
    expected_start = time_utils.INVALID_TIMESTAMP
    # pylint: disable=no-member
    expected_end = time_utils.Timestamp.now() + time_utils.Timedelta('24h')
    start, end = time_utils.get_start_end_from_files(files, None)
    assert start == expected_start, fail_msg + '(start)'
    assert expected_end - time_utils.Timedelta('5s') < end, fail_msg + '(end range)'
    assert expected_end + time_utils.Timedelta('5s') > end, fail_msg + '(end range)'
