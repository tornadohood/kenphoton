"""Utilities for validating types and exact matches."""

from __future__ import unicode_literals

import argparse
import functools
import logging
import os
import re

# pylint: disable=redefined-builtin
from builtins import range
from six import iteritems

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
except ImportError:
    pass

from photon.lib import config_utils
from photon.lib import custom_errors

DATA_SOURCES = ['insights', 'iris', 'logs', 'middleware', 'mr_tunable', 'pure1', 'warehouse']
LOGGER = logging.getLogger(__name__)
FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]
METRIC_INDEX = config_utils.get_metric_index()  # type: Dict[str, Any]
MONTH_NAMES = (
    'jan', 'january', 'feb', 'february', 'mar', 'march', 'apr', 'april', 'may', 'jun', 'june',
    'jul', 'july', 'aug', 'august', 'sep', 'september', 'oct', 'october', 'nov', 'november',
    'dec', 'december'
)


def str_validator(string, condition, error, message):
    # type: (str, function, Any, str) -> str
    """Validate a string against the given condition, and raise given error if not passed."""
    returned_string = string
    # We can pass an error of None if we don't want to raise, in which case we will get
    # back an empty string so that subsequent string operations will not raise errors.
    if error is not None and not condition(string):
        raise error(message)
    elif not condition(string):
        returned_string = ''
    return returned_string


def aid(aid_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given Array ID is valid."""
    # Example: nnnnnn-nnnnnnnn-nnnnnnnnnnnnnnnnnnn
    aid_reg = re.compile(r'\d{6}-\d{8}-\d{19}')
    aid_str = str_validator(aid_str, aid_reg.match, error, 'Array ID "{}" is invalid.'.format(aid_str))
    return aid_str


def chassis_name(chassis_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given shelf/chassis name is valid."""
    # Example: SH0, CH1, etc.
    chassis_str = chassis_str.upper().strip()
    chassis_reg = re.compile(r'[CS]H\d{1,2}$')
    msg = 'The Shelf/Chassis name "{}" is not valid.'.format(chassis_str)
    chassis_str = str_validator(chassis_str, chassis_reg.match, error, msg)
    return chassis_str


def ct_name(ct_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given controller number/name is valid."""
    controllers = ('ct0', 'ct1')
    # Example 'ct0' or 'CT0'
    msg = '"{}" is not a valid Pure FlashArray controller name.'.format(ct_str)
    ct_str = str_validator(ct_str, lambda name: name.lower() in controllers, error, msg)
    return ct_str


def data_source(source_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given data source exists in DATA_SOURCES."""
    source_str = source_str.strip().lower()
    msg = '"{}" is not a defined data source.'.format(source_str)
    # Example 'pure1'
    source_str = str_validator(source_str, lambda source: source in DATA_SOURCES, error, msg)
    return source_str


def date_hour(time_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the time_str is valid; convert to a datetime.datetime object."""
    # Example: YYYY_MM_DD-HH
    time_str = time_str.lower().strip()
    time_reg = re.compile(r'(?P<year>\d{4})_(?P<month>\d{2})_?(?P<day>\d{2})-(?P<hour>\d{1,2})')
    msg = '"{}" is not a valid date-hour.'.format(time_str)
    time_str = str_validator(time_str, time_reg.match, error, msg)
    groups = time_reg.match(time_str).groupdict()
    # Validate hour, day, month, and year values.
    hour(groups['hour'], error)
    day(groups['day'], error)
    month(groups['month'], error)
    year(groups['year'], error)
    return time_str


def day(day_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that a day value is between 1 and 31."""
    # Handle 0-padded and non-padded values by converting to an int.
    day_str = int(day_str.strip())
    msg = '"{}" is not between 1 and 31.'.format(day_str)
    day_str = str_validator(day_str, lambda val: val in range(1, 32), error, msg)
    return str(day_str)


def directory(dir_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the directory exists."""
    dir_str = str(dir_str).strip()
    msg = '"{}" is not a valid directory.'.format(dir_str)
    dir_str = str_validator(dir_str, os.path.isdir, error, msg)
    return dir_str


def drive(drive_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the drive name is formatted properly."""
    drive_str = drive_str.upper().strip()
    # Example: CH0.BAY10 or BAY12
    drive_reg = re.compile(r'([CS]H\d+\.)?(BAY|NVR)\d+')
    msg = '"{}" is not a valid drive name.'.format(drive_str)
    drive_str = str_validator(drive_str, drive_reg.match, error, msg)
    return drive_str


def field(field_str, error=custom_errors.LogParserError):
    # type: (str, Exception) -> str
    """Ensure that a field is defined within the FIELD_INDEX."""
    field_str = field_str.lower().strip()
    msg = 'Unknown field "{}" was requested.'.format(field_str)
    field_str = str_validator(field_str, lambda val: val in FIELD_INDEX, error, msg)
    return field_str


def filename(fname, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given file name is valid and exists."""
    fname = fname.strip()
    msg = 'File "{}" is invalid.'.format(fname)
    fname = str_validator(fname, os.path.isfile, error, msg)
    return fname


def fqdn(fqdn_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given Array FQDN is valid."""
    # Example: array.domain.com
    fqdn_reg = re.compile(r'\S+\.\S+\.\S+')
    msg = 'Array FQDN "{}" is invalid.'.format(fqdn_str)
    fqdn_str = str_validator(fqdn_str, fqdn_reg.match, error, msg)
    return fqdn_str


def fuse_base_path(path_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given log path is a valid format for FUSE."""
    # Example: /logs/domain.com/array-ct0
    path_str = path_str.strip()
    path_reg = re.compile(r'/.*?/.*?-ct\d/?')
    msg = '"{}" is not a valid FUSE base log path.'.format(path_str)
    path_str = str_validator(path_str, path_reg.match, error, msg)
    return path_str


def fuse_log_path(path_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given log path is a valid format for FUSE."""
    # Example: /logs/domain.com/array-ct0/YYYY_MM_DD
    path_str = path_str.strip()
    path_reg = re.compile(r'/.*?/.*?-ct\d/\d{4}_(\d{2}_?){2}/?$') # CAVEAT: trailing slashes should be accounted for externally.
    msg = '"{}" is not a valid FUSE log path.'.format(path_str)
    path_str = str_validator(path_str, path_reg.match, error, msg)
    return path_str


def hour(hour_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that an hour value is between 0 and 23."""
    # Handle 0-padded and non-padded values by converting to an int.
    hour_str = int(hour_str.strip())
    msg = '"{}" is not between 0 and 23.'.format(hour_str)
    hour_str = str_validator(hour_str, lambda val: val in range(24), error, msg)
    return str(hour_str)


def hw_id(id_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the given Hardware ID (Apartment ID, Write Group ID, etc.) is valid."""
    # Example: # (11951019079781516624, 12986023337942797145)
    id_reg = re.compile(r'\(?\d{15,}, \d{15,}\)?')
    id_str = str_validator(id_str, id_reg.match, error, 'The Hardware/Device ID "{}" is invalid.'.format(id_str))
    return id_str


def jira(jira_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the jira_str is valid."""
    # Example: ES-1234 or CLOUD-12345
    jira_str = jira_str.lower().strip()
    jira_reg = re.compile(r'\w{2,5}-\d+')
    msg = 'JIRA "{}" is invalid.'.format(jira_str)
    jira_str = str_validator(jira_str, jira_reg.match, error, msg)
    return jira_str


def log_date(date_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that the log date is valid."""
    # Example: YYYYMMDD
    date_str = date_str.strip()
    time_reg = re.compile(r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})')
    msg = '"{}" is not a valid log date.'.format(date_str)
    date_str = str_validator(date_str, time_reg.match, error, msg)
    groups = time_reg.match(date_str).groupdict()
    # Validate day, month, and year values.
    day(groups['day'], error)
    month(groups['month'], error)
    year(groups['year'], error)
    return date_str


def metric(metric_str, error=custom_errors.LogParserError):
    # type: (str, Exception) -> str
    """Ensure that a metric is defined within the METRIC_INDEX."""
    metric_str = metric_str.lower().strip()
    msg = 'Unknown metric "{}" was requested.'.format(metric_str)
    metric_str = str_validator(metric_str, lambda val: val in METRIC_INDEX, error, msg)
    return metric_str


def month(month_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that a month value is between 1 and 12 or by name Jan-Dec or long name."""
    if not month_str.isdigit():
        msg = 'Month "{}" is not a recognized month.'
        str_validator(month_str.lower(), lambda val: val in MONTH_NAMES, error, msg)
        return month_str
    # Handle 0-padded and non-padded values by converting to an int.
    month_str = int(month_str.strip())
    msg = '"{}" is not between 1 and 12.'.format(month_str)
    month_str = str_validator(month_str, lambda val: val in range(1, 13), error, msg)
    return str(month_str)


def wwn(wwn_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that this is a well-formed WWN address."""
    # Example: XX:XX:XX:XX:XX:XX:XX:XX
    wwn_str = wwn_str.strip().upper()
    wwn_reg = re.compile(r'(?P<wwn>(?:\w{2}:){7}\w{2})')
    msg = '"{}" is not a valid WWN.'.format(wwn_str)
    wwn_str = str_validator(wwn_str, wwn_reg.match, error, msg)
    return wwn_str


def year(year_str, error=argparse.ArgumentTypeError):
    # type: (str, Exception) -> str
    """Ensure that a year value is 4 digits and > 1970."""
    year_str = year_str.strip()
    msg = '"{}" is not a valid 4 digit year.'.format(year_str)
    str_validator(year_str, lambda val: len(val) == 4, error, msg)
    msg = '"{}" is not a valid year.'.format(year_str)
    year_str = str_validator(year_str, lambda val: int(val) >= 1970, error, msg)
    return str(year_str)


def accepts(types):
    # type: (Dict[str, Any]) -> function
    """Validator for function input.  One or more types can be specified in the order of the expected arguments.

    Arguments:
        types (dict): Per argument declaration of expected type(s).
        # Note: You must specify types=; otherwise the decorator will not use it correctly.
        # Example: @accepts(types={'arg1': int, 'arg2': str, 'arg3': (list, set, tuple)})
    """
    def validate_accepts(func):
        """Ensure that the type declarations match the function arguments."""
        func_name = func.__name__

        # Validate that we have the same number of arguments as type declarations:
        if not len(types) == func.__code__.co_argcount:
            error_msg = 'The number of type declarations does not match the arguments for "{}".'.format(func_name)
            LOGGER.exception('ValueError: %s', error_msg)
            raise ValueError(error_msg)

        # Validate the names of the type declarations against the named arguments:
        for arg_name in types:
            if arg_name not in func.__code__.co_varnames:
                error_msg = 'Argument "{}" is not defined for "{}".'.format(arg_name, func_name)
                LOGGER.exception('ValueError: %s', error_msg)
                raise ValueError(error_msg)

        @functools.wraps(func)
        def new_func(*args, **kwargs):
            # type: (*Any, **Dict[Any]) -> Any
            """Validate the argument types and then run the wrapped function."""

            # Add *args values to **kwargs:
            for index, arg_value in enumerate(args):
                arg_name = func.__code__.co_varnames[index]
                kwargs[arg_name] = arg_value

            # Validate each argument type in kwargs:
            for key, value in iteritems(kwargs):
                accepted_type = types[key]
                if not isinstance(value, accepted_type):
                    msg = 'Expected a "{}" for "{}".  Got a "{}" instead.'.format(accepted_type, key, type(value))
                    LOGGER.exception('TypeError: %s', msg)
                    raise TypeError(msg)

            # Run the function with the kwargs:
            return func(**kwargs)
        # Return the wrapped function:
        return new_func
    # Return the wrapper validator:
    return validate_accepts
