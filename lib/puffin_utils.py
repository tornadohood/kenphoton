"""Utilities for working with the Puffin Infrastructure."""

from __future__ import unicode_literals

import logging
import subprocess
import re

from six import iteritems
from six import string_types

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


def _add_sub_cmd(sub_cmd, values=None):
    # type: (str, List[str]) -> List[str]
    """Helper function to add sub-commands to the cmd."""
    cmd = [str(sub_cmd)]
    if values:
        if not isinstance(values, (set, list, tuple)):
            values = [values]
        cmd.extend(values)
    return cmd


def build_cmd(**kwargs):
    # type: (**Dict[Any]) -> List[str]
    """Helper for building a command for puffin-grep on FUSE."""
    file_type = kwargs.get('file_type')
    patterns = kwargs.get('patterns')
    if not isinstance(file_type, string_types):
        msg = 'File Type must be a string.  Got a "{}" instead.'.format(type(file_type))
        LOGGER.error(msg)
        raise TypeError(msg)
    elif not isinstance(patterns, (list, set, tuple)):
        msg = 'Invalid type "{}" found for patterns.  Expected a list, set or tuple.'
        LOGGER.error(msg)
        raise TypeError(msg.format(type(patterns)))
    # TODO: Dynamically decide on which paralellism to use.
    parallelism = kwargs.get('parallelism', 16)
    cmd = ['/usr/local/bin/puffin-grep', '--file-type', file_type, '--parallelism', parallelism]
    # If stdout and wait are not explicitly set to False...
    if not kwargs.get('stdout') is False:
        cmd.append('--stdout')
    if not kwargs.get('wait') is False:
        cmd.append('--wait')
    # Add Identities to search for: array_id(s), domain(s), and/or fqdn(s).
    cmd.extend(_parse_idents(kwargs.get('array_ids'), kwargs.get('domains'), kwargs.get('fqdns')))
    # Parse time frame start and end values:
    cmd.extend(_parse_timeframe(kwargs.get('start_date_hour'), kwargs.get('end_date_hour')))
    # Add grep patterns
    for pattern in patterns:
        cmd.append(pattern)
    # Add '--' grep arguments
    cmd.extend(_parse_grep_args(kwargs.get('grep_args')))
    return cmd


def _parse_grep_args(grep_args):
    # type: (Optional[Dict[str, Any]]) -> List[str]
    """Parse the grep_args dictionary."""
    cmd = []
    if grep_args:
        cmd.append('--')
        for flag, flag_arg in iteritems(grep_args):
            # Add a '-' to the front if not given.
            cmd.append('-{}'.format(flag) if '-' not in flag else flag)
            if flag_arg:
                cmd.append(str(flag_arg))
    return cmd


def _parse_idents(array_ids, domains, fqdns):
    # type: (Optional[List[str]], Optional[List[str]], Optional[List[str]]) -> List[str]
    """Parse one or more identities."""
    cmd = []
    if array_ids:
        cmd.extend(_add_sub_cmd('--array-ids', array_ids))
    if domains:
        cmd.extend(_add_sub_cmd('--domains', domains))
    if fqdns:
        cmd.extend(_add_sub_cmd('--fqdns', fqdns))
    return cmd


def _parse_timeframe(start_date_hour, end_date_hour):
    # type: (str, str) -> List[str]
    """Parse start and end times."""
    timeframe = [start_date_hour, end_date_hour]
    # If only one is given
    if any(timeframe) and not all(timeframe):
        raise ValueError('Timeframe requires both start and end times.')
    cmd = []
    date_pattern = re.compile(r'\d{4}_(\d{2}_?){2}')  # Like: 2017_10_10 or 2017_10_10-15
    # Add the start time
    if start_date_hour:
        if not date_pattern.search(start_date_hour):
            msg = 'Invalid date format "{}" used for start_date_hour.'.format(start_date_hour)
            LOGGER.error(msg)
            raise ValueError(msg)
        cmd.append('--start-date-hour')
        if '-' not in start_date_hour:  # No hour specified
            start_date_hour += '-00'
        cmd.append(start_date_hour)
    # Add the end time
    if end_date_hour:
        if not date_pattern.search(end_date_hour):
            msg = 'Invalid date format "{}" used for end_date_hour.'.format(end_date_hour)
            LOGGER.error(msg)
            raise ValueError(msg)
        cmd.append('--end-date-hour')
        if '-' not in end_date_hour:  # No hour specified
            end_date_hour += '-00'
        cmd.append(end_date_hour)
    return cmd


def puffin_grep(config):
    # type: (Dict[str, Any]) -> List[str]
    """Simple wrapper to run puffin-grep on FUSE.

    Arguments:
        config (dict): A configuration dictionary for puffin-grep.
            Required Args:
                patterns (list/set/tuple): One or more strings to search for.
                file_type (str): A single file-type to search in.
                array_ids (list/set/tuple): One or more array ids to search in.
                domains (list/set/tuple): One or more domains to search in.  i.e. "domain.com"
                fqdns (list/set/tuple): One or more FQDNs to search in.  i.e. "array.domain.com"
                    Note: If you specify the controller it will only return from that controller
                    i.e. "array-ct0.domain.com"
            Optional Args:
                stdout (bool): Return results to stdout instead of a file.
                wait (bool):  Wait for results instead of running asynchronously.
                start_date_hour (str): A log date and hour to start searching (i.e. 2017_10_20-12)
                    Defaults to 1 week ago.
                end_date_hour (str): A log date and hour to stop searching (i.e. 2017_10_20-23)
                    Defaults to now.
                grep_args (dict): One or more arguments to pass to each grep.
                    Use like -- behavior for puffin-grep:  -- -E -o
                    Example: {'-i': None}
                    Example with flag arg: {'-A': 7}; which would be the same as "-- -A 7"
                parallelism (int): How many threads to use on Puffin.

    Returns:
        lines (list): One or more lines that matched the search patterns.
    """
    msg = 'Grepping for {} patterns in {}.'
    LOGGER.info(msg.format(len(config.get('patterns')), config.get('file_type')))
    cmd = build_cmd(**config)
    LOGGER.debug('Built puffin-grep command: "{}".'.format(' '.join(cmd)))
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    if stderr:
        LOGGER.error('Puffin-Grep Error: "{}".'.format(stderr.splitlines()))
    # First 3 lines are metadata from puffin-grep
    # ..
    #
    # puffin:{"output_version": "0.1"}
    # So start at index 4.
    return stdout.splitlines()[4:] if stdout else []
