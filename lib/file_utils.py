"""Contains utilities related to file manipulations."""

import codecs
import collections
import fnmatch
import gzip
import logging
import os
import re
import tarfile

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import Generator
    from typing import List
    from typing import Optional
except ImportError:
    pass

# Importing lib avoids issues with recursive dependendies between file_utils and time_utils
from photon import lib
from photon.lib import config_utils
from photon.lib import parallel_utils

LOGGER = logging.getLogger(__name__)
SETTINGS = config_utils.get_settings()


class LogFile(object):
    """Parse a Log File name/path into a simplified object."""

    def __init__(self, full_name):
        # type: (str) -> None
        if not full_name:
            error_msg = 'The given log_name "{}" is invalid.'.format(full_name)
            raise ValueError(error_msg)
        self._complexity = None
        self._controller = None
        self.full_name = full_name.strip()
        self._file_name = None
        self._log_path = None
        self._log_time = None
        self._log_type = None
        self._granularity = None
        self._start_time = None
        self._end_time = None
        # CAVEAT: End time is not actual log end time
        # it's an end time that's based on the log filename. If the logs contained the
        # actual timestamps they say they do, they'd be offset by ~15-20 minutes from
        # the hour.  We use this for filtering.
        # NOTE: time_delta depends on if we can parse an hour from the logfile name.
        self.time_delta = lib.time_utils.Timedelta('1h')

    def __ge__(self, other):
        # type: (Any) -> bool
        if self.log_type != other.log_type:
            return self.log_type >= other.log_type
        return self.start_time >= other.start_time

    def __gt__(self, other):
        # type: (Any) -> bool
        if self.log_type != other.log_type:
            return self.log_type > other.log_type
        return self.start_time > other.start_time

    def __le__(self, other):
        # type: (Any) -> bool
        if self.log_type != other.log_type:
            return self.log_type <= other.log_type
        return self.start_time <= other.start_time

    def __lt__(self, other):
        # type: (Any) -> bool
        if self.log_type != other.log_type:
            return self.log_type < other.log_type
        return self.start_time < other.start_time

    def __eq__(self, other):
        # type: (Any) -> bool
        return self.file_name == other.file_name

    def __ne__(self, other):
        # type: (Any) -> bool
        return self.file_name != other.file_name

    def __repr__(self):
        # type: () -> str
        return "{}('{}')".format(self.__class__.__name__, self.full_name)

    @property
    def complextity(self):
        # type: () -> int
        """Return the log file's complexity score."""
        if self._complexity:
            return self._complexity
        if self.log_type in SETTINGS['log_complexity']:
            complexity = int(SETTINGS['log_complexity'][self.log_type])
        else:
            # Assign the highest complexity:
            complexity = 5
        self._complexity = complexity
        return self._complexity

    @property
    def controller(self):
        # type: () -> str
        """Determine which controller this log file belongs to, based upon the log path."""
        # '/logs/domain/array-ct#'
        if not self._controller:
            ctlr = re.search(r'.*?\w+\-(?P<ctlr>ct(?:0|1))', self.full_name)
            if not ctlr:
                msg = 'Cannot determine the controller of log file "{}".  Defaulting to CT0.'.format(self.full_name)
                LOGGER.debug(msg)
                self._controller = 'CT0'
            else:
                self._controller = ctlr.group('ctlr').upper()
        return self._controller

    @property
    def file_name(self):
        # type: () -> str
        """Return just the log's file name, no path."""
        if self._file_name:
            return self._file_name
        self._file_name = os.path.basename(self.full_name)
        return self._file_name

    @property
    def granularity(self):
        # type: () -> str
        """Return the granularity of the log file."""
        if self._granularity:
            return self._granularity
        if self.start_time == lib.time_utils.INVALID_TIMESTAMP:
            # There is no log date on this, assume it is a daily file.
            granularity = '1d'
        elif self.log_type in SETTINGS['log_granularity']:
            granularity = SETTINGS['log_granularity'][self.log_type]
        else:
            LOGGER.warning('No granularity found for "{}".'.format(self.full_name))
            granularity = None
        self._granularity = granularity
        return self._granularity

    @property
    def log_path(self):
        # type: () -> str
        """Generate the log path based upon the given log_name."""
        if self._log_path:
            return self._log_path
        self._log_path = os.path.dirname(self.full_name).strip() or os.getcwd()
        return self._log_path

    @property
    def start_time(self):
        # type: () -> time_utils.Timestamp().date()
        """Generate the log date based upon the given log_name."""
        if self._start_time:
            return self._start_time

        # Try to get the date from the filename.
        # e.g. core.log-2017121007.gz
        match = re.findall(r'(?P<date>\d{8,10})', self.file_name)
        if match:
            # NOTE: PT-2326 - We use findall due to PURE-126145 where we may
            # match the regex poorly because someone put a hex value in the
            # log name, so we want the *last* match of date, not just assume
            # there's only one.
            raw_time = match[-1]
            if len(raw_time) == 8:
                # Append a placeholder hour.
                raw_time += '00'
            self._start_time = lib.time_utils.Timestamp(raw_time)
        else:
            # Try to get it from the log path.
            match = re.search(r'(?P<date>\d{4}\_\d{2}\_\d{2})', self.log_path)
            if match:
                # If we match based on the date, this is a daily log or we can't
                # parse the time - so the time range for this log is 24h.
                self._start_time = lib.time_utils.Timestamp(match.group('date'))
            else:
                LOGGER.debug('Unable to find nor infer a log date for "{}".'.format(self.full_name))
                self._start_time = lib.time_utils.INVALID_TIMESTAMP
                self.time_delta = lib.time_utils.Timedelta('0s')

        return self._start_time

    @property
    def end_time(self):
        # type: () -> time_utils.Timestamp().date()
        """Generate the log date based upon the given log_name."""
        if not self._end_time:
            self._end_time = self.start_time + self.time_delta
        return self._end_time

    @property
    def log_type(self):
        # type: () -> str
        """Generate the log type."""
        if self._log_type:
            return self._log_type
        # core-err.log-2018021211.gz -> core-err.log
        # kern.log-2018021211.gz -> kern.log
        # Get everything up until the date stamp of the log file:
        dated_log = re.compile(r'(?P<log_type>.+)(?:\-\d{8,10})')
        match = dated_log.match(self.file_name)
        if match:
            log_name = match.group('log_type')
        else:
            # Assumes that this is a non-dated log file.
            log_name = self.file_name
        # array_info.json.gz -> array_info.json
        self._log_type = log_name.strip().replace('.gz', '')
        return self._log_type


def file_lines_generator(files, mode='rb'):
    # type: (List[str], str) -> Generator[str]
    """Open a file and yield it's lines.

    Arguments:
        files (list/set/tuple): One or more files to open.
        mode (str): File open mode.

    Yields:
        line (str): A single IO buffered line.
    """
    opener_types = {'.gz': gzip.open}
    for filename in files:
        LOGGER.debug('Reading file: "{}".'.format(filename))
        ext = os.path.splitext(filename)[1]
        opener = opener_types.get(ext, open)
        with opener(filename, mode) as open_file:
            try:
                for line in open_file:
                    # CAVEAT: PT-2343 - python3.x gzip libraries aren't created equal.
                    # If you're expecting gzip to reliably handle the conversion
                    # of the raw bytes, you may be in for a bad time.  We had an
                    # instance where we fail to decode due to an invalid start byte
                    # and it craps the bed for the rest of the file.  Just continuing
                    # on a UnicodeDecodeError didn't handle it. Using codecs.decode to ignore
                    # lines that fail decode works.
                    # Example of the error we weren't handling:
                    # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf4 in position 5120: invalid continuation byte
                    yield codecs.decode(line, 'utf-8', 'ignore')
            # Workaround for EOF not present in "open" files.
            except EOFError as err:
                LOGGER.exception(err)
                continue


def group_logs_by_type(logs):
    # type: (List[str]) -> Dict[str, List[str]]
    """Get logs in a directory sorted by type."""
    log_types = collections.defaultdict(list)
    for log in logs:
        logfile = LogFile(log)
        log_types[logfile.log_type].append(logfile.full_name)
    return dict(log_types)


def iter_file_intervals(files, start_string, end_string, inclusive=True, regex=False):
    # type: (List[str], str, str, bool, bool) -> List[str]
    """Open a file and yield intervals between start and end strings.

    Arguments:
        files (list/set/tuple): One or more line files to search in.
        start_string (str): A pattern which indicates the start of the interval.
        end_string (str): A pattern which indicates the end of an interval.
        inclusive (bool): Include the start/end lines in the interval.
        regex (bool): Use start/end as regex instead of just simple line comparison.

    Yields:
         interval (list): All lines between start and end string (inclusive or not).
    """
    lines = file_lines_generator(files)
    for interval in iter_line_intervals(lines, start_string, end_string, inclusive, regex):
        yield interval


def iter_file_matching_lines(files, patterns):
    # type: (List[str], List[str]) -> str
    """Open a file and yield matching lines.

    Arguments:
        files (list/set/tuple): One or more files to open.
        patterns (list/set/tuple): One or more grep patterns to match lines.
            # Not regex, just simple in line comparison (grep).

    Yields:
        line (tuple): A tuple of (pattern, line) for matching lines.
    """
    lines = file_lines_generator(files)
    for line in iter_matching_lines(lines, patterns):
        yield line


def iter_matching_lines(lines, patterns):
    # type: (List[str], List[str]) -> str
    """Get all matching lines in lines.

    Arguments:
        lines (list/set/tuple): One or more lines to search.
        patterns (list/set/tuple): One or more patterns to match.

    Yields:
        line (str): A tuple of (pattern, line) for matching lines.
    """
    for line in lines:
        for pattern in patterns:
            if pattern in line:
                yield line


# pylint: disable=too-many-branches
def iter_line_intervals(lines, start_string, end_string, inclusive=True, regex=False):
    # type: (List[str], str, str, bool, bool) -> str
    """Yield intervals between start and end strings.

    Arguments:
        lines (list/set/tuple): One or more line strings to search in.
        start_string (str): A pattern which indicates the start of the interval.
        end_string (str): A pattern which indicates the end of an interval.
        inclusive (bool): Include the start/end lines in the interval.
        regex (bool): Use start/end as regex instead of just simple line comparison.

    Yields:
        interval (list): A collection of lines between start and end strings.
    """
    interval_started = False
    interval = []
    if regex:
        start_reg = re.compile(start_string)
        end_reg = re.compile(end_string)
    else:
        start_reg = end_reg = None
    for line in lines:
        if interval and not interval_started:
            # Reset the interval, assume this was already yielded.
            interval = []
        if isinstance(line, float):
            # Skip nan lines.
            continue
        if start_string in line or (start_reg and start_reg.search(line)):
            if interval_started:
                yield interval
                interval = [line]
            else:
                interval_started = True
                if inclusive:
                    interval.append(line)
        elif (end_string in line or (end_reg and end_reg.search(line))) and interval_started:
            interval_started = False
            if inclusive:
                interval.append(line)
            yield interval
            interval = [line]
        elif interval_started:
            interval.append(line)
        else:
            if interval:
                yield interval
    if interval and len(interval) != 1:
        # If we have an interval with no end that is longer than just the previous line.
        yield interval


def parallel_grep(files, patterns, **pool_kwargs):
    # type: (List[str], List[str], **Dict[Any]) -> List[str]
    """Grep for the requested patterns in one or more files.

    Arguments:
        files (list/set/tuple): The full or relative paths to one or more files.
        patterns (list/set/tuple): One or more patterns to search for.
        pool_kwargs (dict): Pass-through arguments for 'parallel_utils.ProcessPool'.

    Returns:
         results (list): All of the matching lines.
    """
    results = []
    if not (files and patterns):
        return results
    functs = []
    funct_args = []
    for filename in files:
        LOGGER.debug('Mapping {} to parallel pool.'.format(filename))
        funct_args.append((iter_file_matching_lines, [filename], patterns))
        functs.append(unpack)
    with parallel_utils.ProcessPool(**pool_kwargs) as pool:
        pool.parallelize(functs, funct_args)
    for result in pool.get_results(True):
        results.extend(result)
    return results


def tarfile_lines_generator(files, f_type=None, include_filename=False):
    # type: (List[str], Optional[str], bool) -> str
    """Read a tar file without unpacking, one line at a time.

    Arguments:
        files (list/set/tuple): One or more tarball archives.
        f_type (str): One pattern for which archived files to read.
        include_filename (bool): Also include the filename with each yield.

    Yields:
        A single line (str) from the archived file(s).
    """
    for filename in files:
        LOGGER.debug('Reading (Tar) archived file: "{}".'.format(filename))
        with tarfile.open(filename) as archive:
            if f_type:
                # Only get files of the specified type(s)
                sub_file_names = fnmatch.filter([os.path.basename(fname.name)  # Get the base filename.
                                                 for fname in archive.getmembers()], f_type)
                sub_files = [fname for fname in archive.getmembers() if os.path.basename(fname.name) in sub_file_names]
            else:
                # Get all archived files
                sub_files = archive.getmembers()
            if not sub_files:
                LOGGER.warning('No files of type "{}" within Tar file "{}".'.format(f_type, filename))
            for sub_file in sub_files:
                if not sub_file.isfile():
                    # Skip directories
                    continue
                # Temporarily unpack the file for reading
                unpacked_file = archive.extractfile(sub_file.name)
                lines = unpacked_file.readlines()
                filename_given = False
                for line in lines:
                    if include_filename:
                        if not filename_given:
                            yield sub_file.name
                            filename_given = True
                    # Decode binary lines to UTF-8.
                    if hasattr(line, 'decode'):
                        try:
                            line = line.decode('utf-8')
                        except UnicodeDecodeError:
                            LOGGER.debug('Failed to decode a line from "{}".'.format(sub_file.name))
                    yield str(line)


def unpack(funct, filename, patterns):
    # type: (function, str, List[str]) -> List[str]
    """Simple helper to unpack the generator while in the parallel pool."""
    return [item for item in funct(filename, patterns)]
