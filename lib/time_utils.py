"""Utilities to work with time related objects.
See: https://wiki.purestorage.com/display/SDT/Timeframe+Object
"""

import datetime
import logging
import os
import re

import pandas
import pytz

from dateutil import parser as date_parser
from six import iteritems
from six import string_types

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple
    from typing import Union
except ImportError:
    pass

# Importing lib avoids issues with recursive dependendies between file_utils and time_utils
from photon import lib
from photon.lib import config_utils
from photon.lib import format_utils
from photon.lib import math_utils
from photon.lib import validation_utils

DELTA_SHORT_NAMES = {
    'nanoseconds': 'ns',
    'microseconds': 'us',
    'milliseconds': 'ms',
    'seconds': 's',
    'minutes': 'm',
    'hours': 'h',
    'days': 'd',
    'years': 'y',
}
INVALID_TIMESTAMP = pandas.Timestamp('Jan 1 1970 00:00:00')
LOGGER = logging.getLogger(__name__)
# pylint: disable=line-too-long
OPTIONAL_DATE_MS = re.compile(r'(((?P<year>\d{4})\s+)?(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d+)\s+(?P<hms>\d{2}:\d{2}:\d{2}))(\.(?P<millisecond>\d+))?')
SETTINGS = config_utils.get_settings()  # type: Dict[str, Any]

# TODO: PT-2373 - Subclass better so we can override rich comparisons.
class Timestamp(pandas.Timestamp):
    """Wrapper around pandas.Timestamp which assumes the current year if not given one."""

    # pylint: disable=super-on-old-class
    def __new__(cls, timestamp=None, **kwargs):
        # type: (Any, Optional[Any], **Dict[str, Any]) -> pandas.Timestamp
        """Initialize pandas.Timestamp with additional checks.

        Arguments:
            timestamp (str/datetime/Timestamp/int/float): Just about any type of timestamp.
                # str: '2018_01_01-12' format is supported, but normal timestamps work as well.
                # datetime: A datetime.datetime object.
                # Timestamp: A pandas Timestamp object.
                # float/int: An epoch timestamp.
        """
        # If we don't supply a timestamp, try with just kwargs like pandas would.
        if not timestamp:
            try:
                return super(Timestamp, cls).__new__(cls, **kwargs)
            except TypeError:
                error_msg = 'Invalid timestamp from kwargs: "{}".'.format(kwargs)
                LOGGER.error(error_msg)
                raise TypeError(error_msg)
        else:
            if isinstance(timestamp, string_types):
                # Pandas Timestamp can't parse log dates like "2018_01_01"
                timestamp = timestamp.replace('_', '/')
                # Also add support for log_time with hour like "2018_01_01-12"
                timestamp = timestamp.replace('-', ' ')
                if timestamp.isdigit() and len(timestamp) == 10:
                    # This may be in log date format.
                    # 2017121000
                    timestamp = datetime.datetime.strptime(timestamp, '%Y%m%d%H')
            elif isinstance(timestamp, (float, int)):
                timestamp = datetime.datetime.fromtimestamp(timestamp, pytz.utc)
            # Try to instantiate the Timestamp object the way pandas would with timestamp
            try:
                return super(Timestamp, cls).__new__(cls, timestamp, **kwargs)
            # If we're passing one of our timestamps that has no year, fix it and then instantiate.
            except (pandas.errors.OutOfBoundsDatetime, ValueError):
                # If we don't have a year, we need one, so throw in the default or the supplied one.
                # Assume the current year unless given one explicitly.
                year = kwargs.get('year')
                # Dateutil parser automatically applies a year value if not found (current year)
                dt_obj = date_parser.parse(timestamp)
                # Apply the static year, if given:
                if year:
                    # pylint: disable=no-member
                    dt_obj = dt_obj.replace(year=year)
                return super(Timestamp, cls).__new__(cls, dt_obj, **kwargs)

# pylint: disable=super-on-old-class, no-member
class Timedelta(pandas.Timedelta):
    """Wrapper around pandas.Timedelta with additional conversion methods."""

    # Override pandas.Timedelta __new__ to accept more arguments:
    def __new__(cls, timedelta, *args, **kwargs):
        # type: (pandas.Timedelta, str, *List[Any], **Dict[str, Any]) -> pandas.Timedelta
        # Nothing supports days natively from a string... convert the days to hours.
        if isinstance(timedelta, string_types) and 'd:' in timedelta:
            days, hours, min_sec = timedelta.split(':', 2)
            # Cut off the 'd' or 'h': 244d -> 244
            hours = (int(days[:-1]) * 24) + int(hours[:-1])
            timedelta = '{}h:{}'.format(hours, min_sec)
        return pandas.Timedelta.__new__(cls, timedelta, *args, **kwargs)

    def __str__(self):
        # type: () -> str
        return "Timedelta('{}s')".format(self.seconds)

    @property
    def years(self):
        # type: () -> float
        """Return number of years in timedelta."""
        return math_utils.safe_divide(self.days, 365)

    @property
    def days(self):
        # type: () -> float
        """Return number of days in timedelta."""
        return math_utils.safe_divide(self.hours, 24)

    @property
    def hours(self):
        # type: () -> float
        """Return number of hours in timedelta."""
        return math_utils.safe_divide(self.minutes, 60)

    @property
    def minutes(self):
        # type: () -> float
        """Return number of minutes in timedelta."""
        return math_utils.safe_divide(self.seconds, 60)

    @property
    def seconds(self):
        # type: () -> float
        """Return number of seconds in timedelta."""
        return self.total_seconds()

    @property
    def milliseconds(self):
        # type: () -> float
        """Return number of milliseconds in timedelta."""
        return self.seconds * 1000

    @property
    def microseconds(self):
        # type: () -> float
        """Return number of microseconds in timedelta."""
        return self.milliseconds * 1000

    @property
    def nanoseconds(self):
        # type: () -> float
        """Return number of nanoseconds in timedelta."""
        return self.microseconds * 1000

    @classmethod
    def from_years(cls, years):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of years."""
        return Timedelta('{} days'.format(years * 365))

    @classmethod
    def from_days(cls, days):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of days."""
        return Timedelta('{} days'.format(days))

    @classmethod
    def from_hours(cls, hours):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of hours."""
        return Timedelta('{} hours'.format(hours))

    @classmethod
    def from_minutes(cls, minutes):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of minutes."""
        return Timedelta('{} min'.format(minutes))

    @classmethod
    def from_seconds(cls, seconds):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of seconds."""
        return Timedelta('{} s'.format(seconds))

    @classmethod
    def from_milliseconds(cls, milliseconds):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of milliseconds."""
        return Timedelta('{} ms'.format(milliseconds))

    @classmethod
    def from_microseconds(cls, microseconds):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of microseconds."""
        return Timedelta('{} us'.format(microseconds))

    @classmethod
    def from_nanoseconds(cls, nanoseconds):
        # type: (int) -> Timedelta
        """Instantiate a Timedelta from int number of nanoseconds."""
        return Timedelta('{} ns'.format(nanoseconds))


class Timeframe(object):
    """Defines the scope of time that is considered to be significant."""

    # All of these arguments are required for the functionality of this object.
    # pylint: disable=too-many-arguments
    def __init__(self,
                 start,                 # type: Union[str, Timestamp, datetime.datetime]
                 end,                   # type: Union[str, Timestamp, datetime.datetime]
                 granularity=None,      # type: Optional[str]
                 from_start=False,      # type: bool
                 date_range=None,       # type: Optional[pandas.date_range]
                 from_latest=None,      # type: Optional[Timedelta]
                ):                      # type: (...) -> None
        """Create a timeframe for use in collecting and parsing logs.

        The Timeframe object is designed for use in Photon for containerizing information about the time
        range along with the granularity that we want the analysis to be done in.
        The Timeframe object will validate that dates and frequencies are valid, and
        will create a set of times and dates within the range at the requested granularity.

        There are additional methods for creating a Timeframe from pandas.date_range, or creating a
        Timeframe around an exact time.  Input utilizes checks from pandas.to_datetime and
        pandas.to_timedelta, and times are a pandas.date_range specific to the granularity and
        start/end time requested.  "dates" is a datetime.date object.

        Arguments:
            start (str): Time that events should start being tracked.
            end (str): Time that events should no longer be tracked after.
            granularity (str): Time in pandas timedelta friendly format.
            from_start (bool): Create interval times from the start time.  Otherwise go backward from the end time.
            date_range (pandas.date_range): A previously created date_range from Pandas.
            from_latest (pandas.Timedelta): A previously created Timedelta.
        """
        self.start = Timestamp(start)
        self.end = Timestamp(end)
        self.granularity = _set_granularity(granularity)
        self.from_latest = from_latest
        self._validate_input()
        self._from_start = from_start
        self._times = date_range
        self._dates = None
        LOGGER.debug('Created a Timeframe between {} and {}.'.format(self.start, self.end))

    def __str__(self):
        # type: () -> str
        """Return str object."""
        return "Timeframe(start='{}', end='{}')".format(self.start, self.end)

    def __repr__(self):
        # type: () -> str
        """Return repr object."""
        return "Timeframe(start='{}', end='{}')".format(self.start, self.end)

    def __eq__(self, other):
        """Compare if two instances are equal."""
        # Don't try to compare if it isn't a Timeframe, just return False
        if not isinstance(other, Timeframe):
            is_equal = False
        # If the start and end are equal, return True, otherwise return false.
        else:
            is_equal = bool(self.start == other.start and self.end == other.end)
        return is_equal

    def _validate_input(self):
        # type: () -> None
        """Validate that the timeframes make sense and will be able to generate output."""
        # Make sure start is sooner than the end time
        if self.start >= self.end:
            raise ValueError('Start time must be before end time.')
        # Make sure that the frequency delta isn't greater than the total timeframe.
        total_time = self.end - self.start
        if total_time < self.granularity:
            raise ValueError('Frequency must be smaller than the total timeframe covered.')

    @property
    def dates(self):
        # type: () -> Optional[List[Timestamp]]
        """Generate the date range."""
        if self._dates:
            return self._dates
        dates = pandas.date_range(start=self.start, end=self.end)
        self._dates = [Timestamp(day.date()) for day in dates]
        return self._dates

    @property
    def times(self):
        # type: () -> Optional[List[Any]]
        """Generate interval times from the start or end."""
        if self._times:
            return self._times
        if self._from_start:
            interval_times = set()
            current_time = self.start
            while current_time <= self.end:
                interval_times.add(current_time)
                current_time += self.granularity
            interval_times.add(self.end)
        else:
            interval_times = set()
            current_time = self.end
            while current_time >= self.start:
                interval_times.add(current_time)
                current_time -= self.granularity
            interval_times.add(self.start)
        self._times = sorted(interval_times)
        return self._times

    def filter_logs_by_time(self, log_files):
        # type: (List[str], bool) -> List[str]
        """Filter out logs which are not within the range and return applicable logs.

        Arguments:
             log_files (list): One or more log files to filter by time.

        Returns:
            filtered (list): Sorted log files which are within the current timeframe.
        """
        if not log_files:
            LOGGER.warning('No log files to filter.')
            return log_files
        LOGGER.debug('Filtering {} log_files by time range.'.format(len(log_files)))
        filtered = set()
        for filename in log_files:
            log_obj = lib.file_utils.LogFile(filename)
            # Logs with have "no log date" should be included.  We default
            # these to epoch 0, so that's what we'll check for.
            if log_obj.start_time == INVALID_TIMESTAMP:
                filtered.add(filename)
            elif log_obj.log_type in SETTINGS['filter_exceptions']['daily_logs']:
                if self.start.date() <= log_obj.start_time.date() <= self.end.date():
                    filtered.add(filename)
                elif self.end.date() >= log_obj.end_time.date() >= self.start.date():
                    filtered.add(filename)
            # If start time is after timeframe start but before timeframe end
            elif log_obj.start_time >= self.start and log_obj.start_time <= self.end:
                filtered.add(filename)
            # If end time is before timeframe end but after timeframe start
            elif log_obj.end_time <= self.end and log_obj.end_time >= self.start:
                filtered.add(filename)

        if not filtered:
            LOGGER.warning('No log files remaining after filtering by time.')
        else:
            LOGGER.warning('%d log files remain after filtering.', len(list(filtered)))
        return sorted(list(filtered))

    def generate_interval(self, granularity=None):
        # type: (str) -> List[Any]
        """Generate an interval from the current start/end times with a different frequency.

        Arguments:
            granularity (int): The frequency/granularity of the intervals to generate.

        Returns:
            A list of intervals between the start and end time at the given granularity.
        """
        if not granularity:
            granularity = self.granularity
        return [Timestamp(timestamp) for timestamp in pandas.date_range(start=self.start,
                                                                        end=self.end,
                                                                        freq=granularity)]

    def generate_filenames(self, filename_base, extension='.gz', start=None, end=None):
        # type: (str, str, Optional[Any], Optional[Any]) -> List[str]
        """Generate file names from the time frame.

        Arguments:
            filename_base (str): The prefix of the file name.  e.g. 'core.log'
            extension (str): The suffix/extension type of the file.  e.g. '.gz'
            start (str/datetime/Timestamp): The beginning of the time range.
            end (str/datetime/Timestamp): The ending of the time range.

        Returns:
            A sorted list of file names of the specified type/base.
            * i.e. ['core.log-2018010100.gz', ...]
        """
        start = start or self.start
        end = end or self.end
        return generate_filenames_in_range(filename_base, extension, start, end)

    def generate_fuse_log_paths(self, log_path):
        # type: (str) -> List[str]
        """Generate FUSE log paths based upon the base log path.

        Arguments:
            log_path (str): The base log path on FUSE for an array.

        Returns:
            A list of all log paths (with dates) which are within the current timeframe.
        """
        try:
            # /logs/domain.com/array-ct0/2018_10_10
            # /logs/domain.com/array-ct0/2018_10_10/
            validation_utils.fuse_log_path(log_path, ValueError)
            # Remove trailing slashes
            log_path = log_path.rstrip('/')
            # Remove the date (last folder in path)
            log_path = os.path.dirname(log_path)
        except ValueError:
            # /logs/domain.com/array-ct0
            validation_utils.fuse_base_path(log_path, ValueError)
        days = self.generate_interval()
        log_paths = set()
        for day in days:
            # We need to generate a logfile for both controllers when we
            # look at the fuse base path, not just one.
            day_path = os.path.join(log_path, day.strftime('%Y_%m_%d'))
            other_ctrl = '-ct0/' if '-ct1/' in day_path else '-ct1/'
            peer_path = re.sub(r'-ct\d/', other_ctrl, day_path)
            log_paths.add(day_path)
            log_paths.add(peer_path)
        LOGGER.debug('log_paths: {}'.format(log_paths))
        return sorted(list(log_paths))

    @property
    def exportable(self):
        # type: () -> Dict[str, Any]
        """Export start/end/granularity metadata in order to re-create this timeframe."""
        return {'start': self.start, 'end': self.end, 'granularity': self.granularity}

    @classmethod
    def from_exportable(cls, exported_timeframe):
        # type: (Any, Dict[str, Any]) -> Timeframe
        """Return a Timeframe object from the exportable dictionary.

        Arguments:
            exported_timeframe (dict): A dictionary containing a start, end, and granularity.

        Returns:
            A Timeframe object based upon the supplied information.
        """
        return Timeframe(**exported_timeframe)

    @classmethod
    def from_exact_time(cls, exact_time, buffer_time, granularity):
        # type: (Any, Any, Any, str) -> Timeframe
        """Generate a start_time and end_time for a range around an exact time.

        Arguments:
            exact_time (datetime.datetime/Timestamp): A datetime object for the exact time of an event.
            buffer_time (Timedelta): How much time to get before and after the event.
            granularity (str): The granularity of data to gather around the exact (incident) time.

        Returns:
             timeframe (Timeframe): A Timeframe object of this exact timestamp range.
        """
        lower_time = exact_time - buffer_time
        upper_time = exact_time + buffer_time
        upper_range = set(pandas.date_range(start=exact_time, end=upper_time, freq=granularity))
        lower_range = set(pandas.date_range(start=lower_time, end=exact_time, freq=granularity))
        sorted_time_set = sorted(set.union(upper_range, lower_range))
        timeframe = cls.from_pandas_date_range(sorted_time_set, granularity=granularity)
        return timeframe

    @classmethod
    def from_pandas_date_range(cls, date_range, granularity='60s'):
        # type: (Any, List[Any], str) -> Timeframe
        """Generate a Timeframe object from a date_range - does not generate it's own date_range.

        Arguments:
            date_range (list): A start -> end range of time.
            granularity (str): The granularity of the time range.

        Returns:
            A Timeframe object of the range of time.
        """
        # We shouldn't assume the date_range is sorted.
        sorted_range = sorted(date_range)
        start = sorted_range[0]
        end = sorted_range[-1]
        return cls(start=start, end=end, granularity=granularity, date_range=sorted_range)


def _set_granularity(granularity):
    # type: (Optional[Timedelta]) -> Timedelta
    """Set the granularity, after validating it is within an acceptable range."""
    granularity = Timedelta(granularity or SETTINGS['parsers']['default_granularity'])
    min_granularity = Timedelta(SETTINGS['parsers']['min_granularity'])
    max_granularity = Timedelta(SETTINGS['parsers']['max_granularity'])
    if granularity > max_granularity:
        error_msg = 'The requested granularity "{}" is greater than the maximum of 1 day.'.format(granularity)
        raise ValueError(error_msg)
    elif granularity < min_granularity:
        error_msg = 'The requested granularity "{}" is less than the minimum of 1 second.'.format(granularity)
        raise ValueError(error_msg)
    return granularity


def generate_filenames_in_range(filename_base, extension, start_time, end_time):
    # type: (str, str, Timestamp, Timestamp) -> List[str]
    """Generate a list of strings to look for in log files in a given time range.

    Arguments:
        filename_base (str): The base file type; e.g. 'core.log'.
        extension (str): The extension of the file; e.g. '.gz'.
        start_time (Timestamp): A Timestamp object to use as the beginning of files to generate.
        end_time (Timestamp): A Timestamp object to use as the ending of files to generate.

    Returns:
        A sorted list of file names for the relevant hours.
    """
    if not extension.startswith('.'):
        extension = '.{}'.format(extension)
    interval_time = pandas.Timedelta(hours=1)
    # If the start minute is after 20 minutes (A little wiggle room for the :17 after rotation time)
    # then subtract an interval from the start time to make sure we go one more log back and get all
    # the possible logs in the timeframe - otherwise we run the risk of having our first logfile not
    # be early enough to catch the timeframe we want.
    if start_time.minute >= 20:
        start_time -= interval_time
    needed_hourstamps = set()
    # timetuple()[:4] is the year, month, day, and hour - so while our start_time is less than the
    # end time, add it to our set (Which excludes duplicates for us).
    while start_time.timetuple()[:4] <= end_time.timetuple()[:4]:
        start_time += interval_time
        needed_hourstamps.add('{}{}{}'.format(filename_base,
                                              start_time.strftime('-%Y%m%d%H'),
                                              extension))
    return sorted(needed_hourstamps)


def generate_timeframe(start=None,              # type: Optional[Union[str, Timestamp, datetime.datetime]]
                       end=None,                # type: Optional[Union[str, Timestamp, datetime.datetime]]
                       granularity=None,        # type: Optional[str]
                       from_latest=None,        # type: Optional[Timedelta]
                       ident=None               # type: Optional[Any]
                      ):                        # type: (...) -> Timeframe
    """Dynamically generate a Timeframe object when we may not have all of the information provided.

        Arguments:
            start (str/datetime/Timestamp/int): When the time range should begin.
            end (str/datetime/Timestamp/int): When the time range should end.
            granularity (str): How granular we want results to be.
                Note: This should be in a timedelta friendly format; like '1d' meaning 1 day.
            from_latest (str): How long from start or end (if we are missing one of them).
                Note: This should be in a timedelta friendly format; like '1d' meaning 1 day.
            ident (array_utils.ArrayIdent): An array identity instance.

        Returns:
            timeframe (Timeframe): An instance of Timeframe based upon the known information.
    """
    # JIRA: PT-2374 - Clean up generate_timeframe - still too complicated.
    if from_latest:
        from_latest = Timedelta(from_latest)
    if ident and not (start and end):
        if ident.on_box:
            # If we are Live, then use array's current timestamp as the end time.
            start, end = _get_start_end_from_now(from_latest)
            # NOTE: This logline is just used to differentiate which logical branch we used.
            LOGGER.info('Using from_latest from on-box to generate timeframe.')
        elif ident.files:
            # NOTE: This logline is just used to differentiate which logical branche we used.
            LOGGER.info('Using files from ident to generate timeframe.')
            # If we have given log files, use them as the range of time:
            logfiles = [filename for filelist in ident.files.values() for filename in filelist]
            start, end = get_start_end_from_files(logfiles, from_latest)
            # CAVEAT: logfiles start/end time will make filtering overlap
            # When using files to generate your start and end, if I have a file for core.log-00
            # hour, the 00 hour has a range of 00-01 - and the end timestamp of 01 gets included.
            # Since we filter based on this full timerange for things that could be within the
            # start or the end of the time range, we need to remove that trailing hour to filter
            # properly.
        elif ident.log_path:
            # NOTE: This logline is just used to differentiate which logical branche we used.
            LOGGER.info('Using log path from ident to generate timeframe.')
            start, end = get_start_end_from_path(ident.log_path, from_latest)
    elif start and not end:
        # NOTE: This logline is just used to differentiate which logical branche we used.
        LOGGER.debug('Using start value to generate timeframe.')
        end = Timestamp(start) + (Timedelta(from_latest or SETTINGS['parsers']['time_range']))
    elif end and not start:
        # NOTE: This logline is just used to differentiate which logical branche we used.
        LOGGER.debug('Using end value to generate timeframe.')
        start = Timestamp(end) - Timedelta(from_latest or SETTINGS['parsers']['time_range'])
    if not start and not end:
        # pylint: disable=no-member
        start = Timestamp.now()
        end = start + Timedelta(from_latest or SETTINGS['parsers']['time_range'])
    granularity = Timedelta(granularity or SETTINGS['parsers']['default_granularity'])
    timeframe = Timeframe(start=start, end=end, granularity=granularity)
    LOGGER.info('Using Timeframe: {} -> {}.'.format(timeframe.start, timeframe.end))
    return timeframe


def get_start_end_from_files(files, from_latest):
    # type: (List[str], bool) -> Tuple[time_utils.Timestamp, time_utils.Timestamp]
    """Get a start and end date from a log path with logs in it."""
    start = None
    end = None
    temp_log_times = set()
    logfiles = [lib.file_utils.LogFile(logfile) for logfile in files]
    for logfile in logfiles:
        # We're adding the log time to the set
        temp_log_times.add(logfile.start_time)
        temp_log_times.add(logfile.end_time)
    # Since we could have invalid timestamps, and those aren't valid for generating a range from things here
    # We want to remove them.
    log_times = sorted(temp_log_times - set([INVALID_TIMESTAMP]))
    if len(log_times) > 1:
        start = log_times[0]
        end = log_times[-1]
    LOGGER.info('Start/End from files - Start: {}, End: {}'.format(start, end))
    if start is None and end is None:
        start = INVALID_TIMESTAMP
        # CAVEAT - Account for time zone differences
        # In some cases on fuse we might get logs from the "future", like from
        # Australia, but the "now()" is in the past, like Utah time.  We need
        # to account for that when we don't know what timestamps to work with.
        # pylint: disable=no-member
        end = Timestamp.now() + Timedelta('24h')
        LOGGER.info('No timestamps found from files.  Defaulting to everything.')
    # CAVEAT: Don't include additional hour timestamps.
    # Right now we'll use the end timestamp of the "latest" log, but we don't
    # want to be overly inclusive - for instance, if we look for a time range
    # of 00-01, the logfile of 01 would have a start of 01 and an end of 02.
    # because we assume that our timeframe will include this log because it
    # spans the 01:00 timestamp, we don't want it to include the timestamp of
    # 02:00.
    else:
        end -= Timedelta('1h')
    # If our start and end are the same, we still need it to be a range, so
    # we default to a one hour timeframe to match the default log timeframe.
    if start == end:
        end += Timedelta('1h')
    if from_latest:
        # JIRA: PT-2375 - this needs to account for post process filtering
        # when it's added.
        start = end - from_latest
        LOGGER.info('From latest: {}, {}'.format(start, end))
    return start, end


def get_start_end_from_path(log_path, from_latest):
    # type: (str, bool) -> Tuple[time_utils.Timestamp, time_utils.Timestamp]
    """Get a start and end time from a log path."""
    path = format_utils.get_newest_log_date(log_path)
    start, end = get_start_end_from_files(os.listdir(path), from_latest)
    end += Timedelta('1h')
    return start, end


def get_timestamps_from_files(log_files):
    # type: (Dict[str, str]) -> List[Timestamp]
    """Generate a Timestamp using the files within a given log path or dict of files.

    Arguments:
        log_files (dict): One or more files sorted by type (key) to use for discerning a timestamp range.

    Returns:
        log_times (list): A sorted and unique collection of all of the log dates from the files.
    """
    log_times = set()
    for logs in log_files.values():
        for logfile in logs:
            log_times.add(lib.file_utils.LogFile(logfile).start_time)

    # Remove invalid timestamps from our sets.
    return sorted(log_times - set([INVALID_TIMESTAMP]))


def get_timestamp_from_log_path(log_path):
    # type: (str) -> Timestamp
    """Get the timestamp from a FUSE log path.

    Arguments:
        log_path (str): A full fuse log path to parse for a log date.

    Returns:
        A Timestamp object for the log date.
    """
    # Validate the log path:
    log_path = validation_utils.fuse_log_path(log_path, ValueError)
    log_path = os.path.normpath(log_path)
    log_time = log_path.rsplit(os.sep, 1)[-1]
    return Timestamp(log_time)


def _get_start_end_from_now(from_latest):
    # type: (Timedelta) -> Tuple[Any, Any]
    """Generate start and end times based upon the current server time.

    Arguments:
        from_latest (Timedelta): How long the range of time should be.

    Returns:
        start (Timestamp): The start time.
        end (Timestamp): The end time.
    """
    # pylint: disable=no-member
    end = datetime.datetime.now()
    start = end - from_latest
    return start, end


def get_timestamp_from_line(line):
    # type: (str) -> Optional[Timestamp]
    """Return a Timestamp object from a line.

    Arguments:
        line (str): A log line to parse for a timestamp.

    Returns:
         timestamp (Timestamp): The parsed timestamp as a Timestamp object.
    """
    timestamp_match = OPTIONAL_DATE_MS.match(line)
    if timestamp_match:
        # The function is designed to pull the first timestamp, not subsequent ones.
        # If multiple timestamps exist, we would assert, so we use groups()[0] to
        # get just the first one.
        timestamp_str = timestamp_match.group()
        timestamp = Timestamp(timestamp_str)
    else:
        timestamp = INVALID_TIMESTAMP
    return timestamp


def _get_highest_latency_unit(latency_value):
    # type: (Timedelta) -> str
    """Determine which latency whole unit to scale to."""
    use_scale = 'nanoseconds'
    # Start from the biggest and work down until there is a whole number.
    scales = ('years', 'days', 'hours', 'minutes', 'seconds', 'milliseconds', 'microseconds', 'nanoseconds')
    for scale in scales:
        if getattr(latency_value, scale) >= 1:
            use_scale = scale
            break
    return use_scale


def scale_latency(value, base_unit, display_unit=None, precision=2):
    # type: (Union[str, int, float], str, Optional[str], int) -> str
    """Auto-scale a latency value to the greatest whole unit or specified 'to_unit'."""
    from_method = 'from_{}'.format(base_unit)
    # Get the from_ method applicable to this base unit.  i.e. Timedelta.from_seconds
    delta = getattr(Timedelta, from_method)(value)
    # Convert to the requested display unit:
    display_unit = display_unit or _get_highest_latency_unit(delta)
    display = getattr(delta, display_unit)
    # Convert the long name to a short name for display purposes:  'milliseconds' -> 'ms'
    short_name = DELTA_SHORT_NAMES[display_unit]
    return '{:.{}f} {}'.format(display, precision, short_name)


def to_epoch_time(timestamp, timezone):
    # type: (Timestamp, str) -> int
    """Convert the Timestamp to Epoch time.

    Arguments:
        timestamp (Timestamp): A Timestamp to convert to Epoch time.
        timezone (str): A Timezone name for the timestamp to convert to Epoch time.
            Example: Timestamp.tz_localize(tz='America/Chicago')

    Returns:
        epoch_time (int): The Timestamp converted to seconds since Epoch (Jan 1 1970 00:00:00).
    """
    timestamp = timestamp.tz_localize(tz=timezone)
    # If it's not UTC, then convert it to UTC.
    if timestamp.tz.zone != 'UTC':
        timestamp = timestamp.tz_convert('UTC')
    epoch_start = pandas.Timestamp('Jan 1 1970', tz='UTC')
    epoch_diff = (timestamp - epoch_start).total_seconds()
    return int(epoch_diff)


def to_raw_latency(value, base_unit='microseconds', precision=2):
    # type: (str, str, int) -> float
    """Convert a latency value to raw.  The lowest/base_unit will be applied.

    See DELTA_SHORT_NAMES for available base_unit options.
    """
    if isinstance(value, (int, float)):
        raw_delta = value
    else:
        for long_name, short_name in iteritems(DELTA_SHORT_NAMES):
            if base_unit == short_name:
                base_unit = long_name
                break
        inst = Timedelta(value)
        raw_delta = getattr(inst, base_unit)
    return round(raw_delta, precision)
