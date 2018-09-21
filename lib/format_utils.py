"""Contains common utility functions related to formatting."""

from __future__ import unicode_literals

import logging
import os
import re

import numpy

from six import iteritems
from six import itervalues
from six import string_types

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import List
    from typing import Optional
except ImportError:
    pass

from photon.lib import custom_errors
from photon.lib import math_utils
from photon.lib import validation_utils

LOGGER = logging.getLogger(__name__)

# Useful *_JUSTIFY.format('Some text', wid=10) justification.
LEFT_JUSTIFY = '{:<{wid}}'
RIGHT_JUSTIFY = '{:>{wid}}'
CENTER_JUSTIFY = '{:^{wid}}'

UNIT_SCALES = {
    'bandwidth': {
        'base': 1000.,
        'units': ('B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s', 'PB/s', 'EB/s')
    },
    'binary_bytes': {
        'base': 1024.,
        'units': ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
    },
    'bytes': {
        'base': 1000.,
        'units': ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB')
    },
    'bits': {
        'base': 1000.,
        'units': ('b', 'Kb', 'Mb', 'Gb', 'Tb', 'Pb', 'Eb')
    },
    'iops': {
        'base': 1000,
        'units': ('', 'k', 'm', 'b', 't')
    }
}
TEXT_FORMATS = {
    'blue': '\033[94m',
    'bold': '\033[1m',
    'cyan': '\033[96m',
    'dark_cyan': '\033[36m',
    'green': '\033[92m',
    'italic': '\033[3m',
    'purple': '\033[95m',
    'red': '\033[91m',
    'underline': '\033[4m',
    'yellow': '\033[93m',
}


def auto_align_text(value, padding):
    # type: (str, int) -> str
    """Automatically align value with a set padding.

    Arguments:
        value (str): Text to align.
        padding (int): Space to add around the text based on if value is a number or not.

    Return:
        item (str): Value with padding before or after given value.
    """
    value = str(value)
    try:
        # Right justify numbers and Ratios.
        if ':' in value:
            # Attempts to check if a Ratio, like "0.03:1", should be right justified.
            nums = value.split(':')
            for num in nums:
                float(num)
        else:
            # The following will ensure that "40 TB"/"40"/"40.2" are recognized as numbers.
            float(value.split()[0].replace('%', ''))
        justify = RIGHT_JUSTIFY
    except ValueError:
        # Everything else is left justified.
        justify = LEFT_JUSTIFY
    item = justify.format(value, wid=padding)
    return item


def auto_scale(value, unit_type, precision=2):
    # type: (int, str, int) -> str
    """Scale a value to the highest whole scale where it remains a whole number.

    Arguments:
        value (int/float): A single value to unit_type.
        unit_type (str): A unit_type to use for conversion: binary_bytes, bytes, bits, or latency.
        precision (int): How many values to preserve after the decimal point.

    Returns:
        A string of the converted value with units.  i.e. '1.75 MB'
    """
    raw_value = to_raw(value)
    if unit_type not in UNIT_SCALES:
        raise IndexError('Unknown scale requested: "{}".'.format(unit_type))
    base = UNIT_SCALES[unit_type]['base']
    units = UNIT_SCALES[unit_type]['units']
    # Default to the bottom of the unit_type
    lowest_value = raw_value
    lowest_unit = units[0]
    for unit in units[1:]:
        # Move up the unit_type and determine if we stay > 1 (unit)
        raw_value = math_utils.safe_divide(raw_value, base)
        if raw_value < 1.:
            break
        lowest_value = raw_value
        lowest_unit = unit
    # i.e. '145.12 B'
    return '{:.{}f} {}'.format(lowest_value, precision, lowest_unit)


def get_newest_log_date(path):
    # type: (str) -> str
    """Clean up a path so if it's a base path or a fuse path it has dates."""
    # If we have a filename in the path, remove it.

    if path.endswith('.gz'):
        path = os.path.dirname(path)
    # Check if our path is a base path or a fuse path.
    base_path = validation_utils.fuse_base_path(path, None)
    fuse_path = validation_utils.fuse_log_path(base_path, None)
    # If it's a fuse path, we're set.
    if fuse_path:
        log_path = fuse_path
    # If it's a base path, we need to get the dates from it, and we will
    # use the most recent to generate the rest of things from.  It's your
    # own fault if you wanted a specific date and gave us a non-dated path.
    elif base_path:
        log_times = os.listdir(base_path)
        if not log_times:
            msg = 'Log path "{}" has no log dates.'.format(base_path)
            raise ValueError(msg)
        log_path = os.path.join(base_path, sorted(log_times)[-1])
    # If it's neither of those, we'll use the path explicitly and see
    # what we get.
    else:
        log_path = path
    return log_path


def convert_to_unit(value, unit, precision=2):
    # type: (int, str, int) -> str
    """Convert a value to a specific unit.

    Arguments:
        value (int/float): A value with or without units to convert it from.
        unit (str): A unit to convert it to.
        precision (int): How many values to preserve after the decimal point.

    Returns:
        scaled (str): A value scaled to a new unit.
    """
    raw_value = to_raw(value)
    for scale, scale_info in iteritems(UNIT_SCALES):
        if unit not in scale_info['units']:
            LOGGER.info('Skipped scale "{}" for unit "{}".'.format(scale, unit))
            continue
        # Divide it by the base to the power of the index of the unit in the unit_type.
        base = scale_info['base']
        power = scale_info['units'].index(unit)
        LOGGER.debug('Scale and Power.  {}^{}'.format(base, power))
        divisor = pow(base, power)
        new_value = math_utils.safe_divide(raw_value, divisor)
        scaled = '{:.{}f} {}'.format(new_value, precision, unit)
        return scaled
    msg = 'Unit "{}" is not in any known unit_type.'.format(unit)
    LOGGER.error(msg)
    raise custom_errors.FormatError(msg)


def make_snake_case(string):
    # type: (str) -> str
    """Return a string without special characters for snakecase names.

    Arguments:
        string (str): String you want snakecased.

    Returns:
        string (str): Snake cased string.
    """
    # Make sure it's lower and stripped of lead/trail spaces.
    string = string.lower().strip()
    # List of things to replace and what to replace them with.
    # This may not be all inclusive, or correct in all cases yet.
    replacements = [
        # remove these characters:
        ('@', ''),          # I don't have a use case for this, but I know it doesn't belong in a snakecase.
        (']', ''),          # member[1]     -> member_1
        (')', ''),          # hello(mike)   -> hello_mike
        ('"', ''),          # hello "mike"  -> hello_mike

        # Replace these with underscores
        ('[', '_'),         # member[1]     -> member_1
        ('(', '_'),         # hello(mike)   -> hello_mike
        ('/', '_'),         # fc1/2         -> fc1_2
        ('\\', '_'),        # \s+           -> _s_plus_
        ('-', '_'),         # mike-is-here  -> mike_is_here
        (' ', '_'),         # mike is here  -> mike_is_here

        # Replace these with special cases
        ('#', '_num_'),     # thing#2       -> thing_num_2
        ('+', '_plus_'),    # \s+           -> _s_plus_
    ]
    # Go through and replace the things that are in the replacements.
    for to_replace, replacement_val in replacements:
        string = string.replace(to_replace, replacement_val)
    # If we have two underscores together, we need to replace them after all of our other
    # modifications.
    string = string.replace('__', '_')
    # We need to remove leading and trailing underscores
    string = re.sub('^_|_$', '', string)
    return string


def make_title(name):
    # type: (str) -> str
    """Convert a string into a human readable title.

    Example:
        Transform: 'array_name' -> 'Array Name'
    """
    header_exceptions = {
        r'Ssd': 'SSD',
        r'Id(?=\s|$)': 'ID',
        r'(?<!-)Ct(?=[01\s$])': 'CT',
        r'-Ct(?=[01\s$])': '-ct',
        r'iscsi|Iscsi': 'iSCSI',
        r'Fc': 'FC',
        r'Ntp': 'NTP',
        r'Ip': 'IP',
        r'Gc': 'GC',
        r'Sas': 'SAS',
        r'Pct$': 'PCT',
        r'Mce ': 'MCE ',
        r'Sel ': 'SEL ',
    }
    name = name.replace('_', ' ')
    name = name.title()
    for bad, good in iteritems(header_exceptions):
        name = re.sub(bad, good, name)
    return name


def percentage(raw_value, precision=2):
    # type: (int, int) -> str
    """Convert a raw float to a percentage string.
    Example: This will convert 0.88 to '88.00%'.

    Arguments:
        raw_value (float/int): A raw value to convert.
        precision (int): How many values to preserve after the decimal.
            * This defaults to 2.

    Returns:
        A percentage string.
    """
    return '{:.{precision}%}'.format(float(raw_value), precision=precision)


def split_list(full_list, num_pieces=None, size=None):
    # type: (List[str], Optional[int], Optional[int]) -> List[str]
    """Split up an iterable into equally sized pieces.
    If not even, the first piece will be one larger.

    Arguments:
        full_list (list): A list to split up.
        num_pieces (int): How many pieces to create.
        size (int): How many items to include in each piece.

        *** Use pieces OR size, not both. ***

    yields:
        item (list): A sub-section of the list.
    """
    if not full_list:
        yield []
    if size and num_pieces or not (size or num_pieces):
        error_msg = 'Either size or number of pieces is required, not both.'
        LOGGER.exception('ValueError: {}'.format(error_msg))
        raise ValueError(error_msg)
    num_pieces = num_pieces or math_utils.safe_divide(len(full_list), size)
    for item in numpy.array_split(full_list, num_pieces):
        yield list(item)


def split_str(text, delim, every, reverse=False):
    # type: (str, str, int, bool) -> str
    """Split a string every 'n' characters and apply a delimiter.

    Arguments:
        text (str): The base string to be split up.
        delim (str): The character to insert into every break.
        every (int): How many characters to include in each 'chunk'.
        reverse (bool): Split in reverse (right to left).

    Returns:
        result (str): The text with delimiter every 'n' characters.
    """
    LOGGER.debug('Splitting up "{}".'.format(str(text)))
    deliminated = ''
    chunk = ''
    text = str(text)
    if reverse:
        text = text[::-1]
    for char in text:
        if len(chunk) < every:
            chunk += char
        elif not deliminated:
            deliminated += chunk
            chunk = char
        else:
            deliminated += '{}{}'.format(delim, chunk)
            chunk = char
    # If there's any remainder, then add it to the end.
    if chunk and deliminated:
        deliminated += '{}{}'.format(delim, chunk)
    # Assumption: 'text' is shorter than 'every', so return chunk.
    result = deliminated or chunk
    if reverse:
        result = result[::-1]
    LOGGER.debug('Result: "{}".'.format(result))
    return result


def text_fmt(formats, text):
    # type: (List[str], str) -> str
    """Format Text with color and/or style.

    Arguments:
        formats (List[str]): The formats you would like to use.
            NOTE: Check format_utils.TEXT_FORMATS.keys() for options.
        text (str): The string you want to wrap within the formatting.

    Return:
        formatted_text (str): Text to print with added formatting.
    """
    items = []
    for fmt in formats:
        if fmt not in TEXT_FORMATS:
            msg = 'Format option {} not found.\nValid options: {}'.format(fmt, TEXT_FORMATS.keys())
            raise ValueError(msg)
        items.append(TEXT_FORMATS[fmt])
    # Add the text and reset the formatting back to normal.
    items.extend([text, '\033[0m'])
    formatted_text = ''.join(items)
    return formatted_text


def to_raw(value, scale=None, precision=2):
    # type: (Any, Optional[str], int) -> float
    """Convert a value to raw based upon the units supplied.

    Arguments:
        value (str/float/int/nan): A value that includes a unit.  i.e. '12.07 KB'
            # Additionally, pre-parsed values will just pass through.
        scale (str): A named scale to use; otherwise this will attempt to infer the scale.
        precision (int): How many values to preserve after the decimal.

    Returns:
        The raw value (float): The value reduced to the smallest known unit.  i.e. 12070.0
    """
    # For input with or without spaces between value and unit and with or without decimal values.
    value_unit_reg = re.compile(r'(?P<number>-?\d+\.\d+|\d+)\s?(?P<unit>\w+)')
    # Remove negative signs, decimal, etc. to confirm if this string is a digit.
    if not isinstance(value, string_types) or value.replace('.', '').replace('-', '').isdigit():
        value = float(value)
        # Return the value as a float, no conversion needed.
        if numpy.isnan(value):
            value = 0.
        return value
    match = value_unit_reg.search(value)
    if not match:
        raise ValueError('Value "{}" is not in a recognized format.'.format(value))
    number = match.group('number')
    unit = match.group('unit')
    if unit in ('K', 'M', 'G', 'T', 'P' 'E'):
        # Assumption: These are units which don't have B or iB at the end.
        # Assumption: Purity puts everything into base2, even when it only shows a single character for unit.
        unit += 'iB'
    if scale:
        if scale not in UNIT_SCALES:
            raise custom_errors.FormatError('Unknown scale "{}" specified.'.format(scale))
        units = UNIT_SCALES[scale]['units']
        if unit not in units:
            msg = 'Unit "{}" is not in scale {}.'.format(unit, scale)
            LOGGER.error(msg)
            raise custom_errors.FormatError(msg)
        base = UNIT_SCALES[scale]['base']
        # Multiply the number by the base to the nth power, where n is the index of the unit.
        return float(number) * pow(base, units.index(unit))
    for scale_name in itervalues(UNIT_SCALES):
        units = scale_name['units']
        if unit not in units:
            continue
        return round(float(number) * pow(scale_name['base'], units.index(unit)), precision)
    raise custom_errors.FormatError('Unit "{}" is not in any known scale.'.format(unit))


def zero(value):
    # type: (Union[int, float]) -> int
    """If a value is less than 0, set it to 0."""
    if int(value) < 0:
        value = 0
    return int(value)
