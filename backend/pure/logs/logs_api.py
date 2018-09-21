"""Contains the FA Controller API for log locating and parsing."""

import collections
import glob
import logging
import os

import pandas

from six import iteritems

from photon.backend.pure import DataSource
# Due to PURE-123142 we cannot trust the contents of array_info.json
# from photon.backend.pure.logs import array_info_json
from photon.backend.pure.logs import bcon
from photon.backend.pure.logs import cache
from photon.backend.pure.logs import core
from photon.backend.pure.logs import core_structured
from photon.backend.pure.logs import diagnostics
from photon.backend.pure.logs import frequentdiagnostics
from photon.backend.pure.logs import kern
from photon.backend.pure.logs import middleware
from photon.backend.pure.logs import hardware
from photon.backend.pure.logs import monitor
from photon.backend.pure.logs import platform
# from photon.backend.pure.logs import playback_db
from photon.backend.pure.logs import remote_kern
from photon.backend.pure.logs import rdmaoopsd
# from photon.backend.pure.logs import sel
from photon.backend.pure.logs import stats
from photon.backend.pure.logs import syslog

from photon.lib import config_utils
from photon.lib import custom_errors
from photon.lib import file_utils
from photon.lib import parallel_utils
from photon.lib import print_utils
from photon.lib import time_utils
from photon.lib import validation_utils

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

LOGGER = logging.getLogger(__name__)  # type: logging.Logger
FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]
# The order of the parsers is important and should be maintained.
LOG_SOURCES = collections.OrderedDict([
    # ('array_info.json', array_info_json.ArrayInfoParser),
    ('bcon.log', bcon.BconParser),
    ('cache.log', cache.CacheParser),
    ('core.log', core.CoreParser),
    ('core-structured.log', core_structured.CoreStructuredParser),
    ('diagnostics.log', diagnostics.DiagnosticsParser),
    ('frequentdiagnostics.log', frequentdiagnostics.FDiagnosticsParser),
    ('host_stats.log', stats.StatsParser),
    ('kern.log', kern.KernParser),
    ('middleware.log', middleware.MiddlewareParser),
    ('hardware.log', hardware.HardwareParser),
    ('monitor.log', monitor.MonitorParser),
    ('platform.log', platform.PlatformParser),
    # ('playback_db', playback_db.PlaybackParser),
    ('remote_kern.log', remote_kern.RemoteKernParser),
    ('rdmaoopsd.log', rdmaoopsd.RdmaoopsdParser),
    # ('sel', sel.SELParser),
    ('vol_stats.log', stats.StatsParser),
    ('syslog', syslog.SyslogParser),
])  # type: collections.OrderedDict[str, DataSource]
SETTINGS = config_utils.get_settings()

# TODO: PT-1337 - Handle fields that are only on the Primary.


class Logs(DataSource):
    """An API to simplify getting data from Log Files."""

    def __init__(self, ident, timeframe, controllers=('CT0', 'CT1')):
        # type: (Any, time_utils.Timeframe, Union[Tuple[str], Tuple[str, str]]) -> None
        """Use the ArrayIdent and Timeframe to find and parse log files.

        Arguments:
                ident (ArrayIdent): An array_utils.ArrayIdent object.
                timeframe (time_utils.Timeframe): A timeframe between a start and end point at a given granularity.
                controllers (tuple): One or multiple controllers to use.
        """
        super(Logs, self).__init__(ident=ident, timeframe=timeframe, controllers=controllers)
        self.field_data = pandas.DataFrame()
        self.log_files = self._get_log_files()
        self.log_files_dict = self._get_log_files_dict()

    @staticmethod
    def is_available(ident, fields, timeframe):
        # type: (Any, List[str], time_utils.Timeframe) -> bool
        """Determine if we can use Logs as a data source."""
        try:
            # Check if the path is a FUSE base path (PT-1792):
            is_fuse_base_path = bool(validation_utils.fuse_base_path(ident.log_path, ValueError))  # type: bool
        except ValueError:
            is_fuse_base_path = False
        # TODO: PT-2133 - Check if we have the files we need to get all the requested fields.
        # This should be based upon the log_path/fqdn and Timeframe.
        return any([ident.files, ident.fqdn, is_fuse_base_path])

    def _get_log_files(self):
        # type: () -> List[str]
        """Fetch on the log files which apply to the given timeframe."""
        log_files = set()
        if self.ident.files:
            for logs_of_type in self.ident.files.values():
                for log in logs_of_type:
                    log_files.add(log)
        else:
            all_logs = []
            # TODO: How to get the log files from a live array?
            for ct_path in self.ident.ct_paths.values():
                # For each controller log path, get applicable log files:
                ct_log_dates = self.timeframe.generate_fuse_log_paths(ct_path)
                # TODO: PT-2133 - Check for missing log hours.
                for log_date in ct_log_dates:
                    # PT-2138: This will now filter all log files at once.
                    all_logs.extend(glob.glob(os.path.join(log_date, '*')))
            # Filter log files by time and then by type:
            for log in self.timeframe.filter_logs_by_time(all_logs):
                file_obj = file_utils.LogFile(log)
                # Ensure that we can get a controller name from the log path:
                if file_obj.controller not in ('CT0', 'CT1'):
                    # This logs a warning from the file_obj itself.
                    continue
                if file_obj.log_type in LOG_SOURCES:
                    log_files.add(file_obj.full_name)
        return sorted(list(log_files))

    def _get_log_files_dict(self):
        # type: () -> Dict[str, List[str]]
        """Sort log files by type."""
        # Sort the log files by type.
        log_files_dict = file_utils.group_logs_by_type(self.log_files)
        return log_files_dict

    def get_source_order(self, fields):
        # type: (Union[Set[str], List[str]]) -> Union[Set[str], List[str]]
        """Determine which log types to use to get fields, and a ranked order.

        Arguments:
            fields (list): One or more fields for which to get applicable log file sources.

        Returns:
            log_order (list): The order in which to use log files.
        """
        if not fields:
            msg = 'No fields requested.'
            LOGGER.error(msg)
            raise custom_errors.LogParserError(msg)
        else:
            fields = set(fields)
        log_ranks = {}
        field_map = self.map_fields_to_sources(fields)['logs']
        for log_type, log_fields in field_map.items():
            rank = 0
            if not log_fields:
                LOGGER.debug('Log type: "{}" had no fields.'.format(log_type))
                continue
            if log_type not in self.log_files_dict:
                LOGGER.warning('Log type: "{}" had no files.'.format(log_type))
                continue
            if len(log_fields) == len(fields):
                # This log_type can get everything!
                rank += 10
            # Increase rank based upon the number of fields it can fetch:
            rank += len(log_fields)
            # Reduce rank based upon the complexity of the log type:
            complexity = SETTINGS['log_complexity'].get(log_type, 5)
            rank -= complexity
            # Adjust rank based upon the granularity of the timeframe and log type:
            granularity = time_utils.Timedelta(SETTINGS['log_granularity'].get(log_type, '1ms'))
            if granularity == self.timeframe.granularity:
                # This log type can handle the requested granularity.
                rank += 2
            elif granularity < self.timeframe.granularity:
                # This log type is more granular than requested.
                rank += 1
            else:
                # This log type cannot get us the requested granularity, but keep it as a contingency.
                rank -= 1
            log_ranks[log_type] = rank

        # Determine if we have a parser for every field.  If not, raise an error.
        for field in fields:
            log_types = FIELD_INDEX[field]['logs']
            if not any(log_type in log_ranks for log_type in log_types):
                msg = 'Failed to fetch "{}".  Could not find any "{}" files.'.format(field, ', '.join(log_types))
                LOGGER.warning(msg)

        # To prevent ties, we will then sort by key name (log_type) to get a predictable order.
        log_order = sorted(log_ranks, key=lambda key: (int(log_ranks[key]), key), reverse=True)
        LOGGER.debug('Log Ranks: {}.'.format(log_ranks))
        LOGGER.debug('Log Order: {}'.format(', '.join(log_order)))
        return log_order

    def _get_fields_from_parsers(self, needed_fields, controllers):
        # type: (Set[str], Tuple[str, str]) -> List[pandas.DataFrame]
        """Get fields from log parsers."""
        completed_fields = set()
        frames = []
        field_map = self.map_fields_to_sources(needed_fields).get('logs')
        # TODO: What if we don't have a field_map for logs?
        for log_type in self.get_source_order(needed_fields):
            if not needed_fields:
                # We don't need any fields.
                break
            elif log_type not in self.log_files_dict:
                LOGGER.info('No "%s" files available...skipping this log type.' % log_type)
                continue
            elif log_type not in field_map:
                # This log type cannot get us the remaining fields that we need.
                continue

            # Get fields which relate to this log type; which have not been completed already.
            applicable_fields = field_map[log_type] - completed_fields
            if not applicable_fields:
                continue
            elif needed_fields == completed_fields:
                # We have all of the needed fields done.
                break
            log_files = sorted(self.log_files_dict[log_type])
            lf_count = len(log_files)
            LOGGER.info('Parsing {} {} files.'.format(lf_count, log_type))
            if SETTINGS['cpu']['serialize'] or lf_count < 2:
                for log_file in sorted(log_files):
                    print_utils.status_update('Reading %d fields from %s.' % (len(applicable_fields), log_type))
                    result = _run_parser(log_type, log_file, applicable_fields)
                    new_frames, new_completed = _process_results(result, log_file)
                    frames.extend(new_frames)
                    completed_fields = completed_fields.union(new_completed)
                    print_utils.status_update()
            else:
                tasks = []
                task_args = []
                for log_file in sorted(log_files):
                    # Don't use log files for a controller that we don't want.
                    if file_utils.LogFile(log_file).controller not in controllers:
                        continue
                    else:
                        tasks.append(_run_parser)
                        task_args.append([log_type, log_file, applicable_fields])
                print_utils.status_update('Reading %d fields from %s.' % (len(applicable_fields), log_type))
                with parallel_utils.ProcessPool(processes=lf_count / SETTINGS['cpu']['max_tasks_per_child']) as pool:
                    pool.parallelize(tasks, task_args)
                    for index, result in enumerate(pool.get_results(ordered=True)):
                        if not result:
                            continue
                        # Because the results are ordered, we can assume that the log files order will match.
                        # We get back a dictionary of fields and a list of tuples of values for each field.
                        log = log_files[index]
                        new_frames, new_completed = _process_results(result, log)
                        frames.extend(new_frames)
                        completed_fields = completed_fields.union(new_completed)
                print_utils.status_update()
        return frames

    def get_fields(self, fields, controllers=('CT0', 'CT1')):
        # type: (List[str], Tuple[str, str]) -> pandas.DataFrame
        """Get the requested fields from one or both controllers."""
        frames = []
        needed_fields = set(fields)

        # Read fields from cache:
        for field in fields:
            if field in self.field_data:
                LOGGER.info('Read "%s" from cache.' % field)
                # TODO: PT-2017 - Validate cache and determine which files don't have pre-cache.
                # Otherwise remove the files which have pre-cache, so we don't use them again.
                frames.append(self.field_data[['Timestamp', field, 'controller', 'source']])
                needed_fields.remove(field)

        # If there are fields that were not cached, get them from log parsers:
        if needed_fields:
            # This returns a list of pandas.DataFrame instances.  Instead of pre-merging them, just iterate over them
            # and whenever we have actual values for a field, add that field + metadata to be merged together.
            # This way, we don't merge multiple times and skip empty data sets.
            for frame in self._get_fields_from_parsers(needed_fields, controllers):
                for field in needed_fields:
                    if field not in frame or (field in frame and frame[field].empty):
                        continue
                    sub_frame = frame[['Timestamp', field, 'controller', 'source']]
                    frames.append(sub_frame)
                    self.field_data = self.field_data.append(sub_frame)
        # Stack everything together.
        if not frames:
            stacked = pandas.DataFrame()
        else:
            stacked = pandas.concat(frames)
            # Ensure that all timestamps are Timestamp objects:
            stacked['Timestamp'] = stacked['Timestamp'].apply(lambda ts_str: time_utils.Timestamp(ts_str))
            # Sort by time and reset the index.
            stacked.sort_values(by='Timestamp', inplace=True)
            stacked.reset_index(drop=True, inplace=True)
        return stacked


def _process_results(result, log_file):
    # type: (Dict[str, Any], str) -> Tuple[List[pandas.DataFrame], Set[str]]
    """Process results from a parser and convert to a list of pandas.DataFrames."""
    completed_fields = set()
    frames = []
    for field, field_data in iteritems(result):
        if not field_data:
            continue
        frame = pandas.DataFrame({field: [item[1] for item in field_data],
                                  'Timestamp': [item[0] for item in field_data]})
        # Set the 'source' equal to the log file's path and name.
        frame['source'] = log_file
        completed_fields.add(field)
        frame['controller'] = file_utils.LogFile(log_file).controller
        frames.append(frame)
    return frames, completed_fields


def _run_parser(log_type, log_file, fields):
    # type: (str, str, List[str]) -> Dict[str, Any]
    """Run a single log parser against a log file for the requested fields."""
    parser = LOG_SOURCES.get(log_type)
    if not parser:
        msg = 'No log parser exists for "%s".' % log_type
        raise custom_errors.LogParserError(msg)
    # Instantiate a parser and run get_fields.
    parser_inst = parser(log_file=log_file)
    return parser_inst.get_fields(fields)
