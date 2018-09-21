"""Common objects used through photon.backend.logs."""

import abc
import logging
import re

import pandas

from future.utils import with_metaclass
from six import string_types

from photon.lib import file_utils
from photon.lib import time_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import Iterator
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


# TODO: PT-1472 - Convert all of these objects to a dictionary or namedtuple...
class FormData(object):
    """Base for all objects that track forms."""

    def __getitem__(self, key):
        # type: (str) -> Any
        """Get an attribute by calling a key."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def items(self):
        # type: () -> Iterator[Tuple[Any, Any]]
        """Return key and value pairs."""
        return ((key, self[key]) for key in self.keys())

    def keys(self):
        # type: () -> Iterator[str]
        """Return available keys."""
        skip = ('keys', 'values', 'items')
        return (key for key in dir(self) if not key.startswith('_') and key not in skip)

    def values(self):
        # type: () -> Iterator[str]
        """Return values for each key."""
        keys = self.keys()
        return (self[key] for key in keys)


class GrepForm(object):
    """Base class for Grep Forms."""
    pass


class SimpleTextForm(GrepForm):
    """Grep form that only looks for single log_lines with matching text.

    Arguments:
        text_to_match (str): The Grep string to match.
        regexes (list): One or more regex patterns to match against the "grepped" lines.
        post_text_to_match (str): Get additional line(s) beyond the text_to_match.
    """

    def __init__(self, text_to_match, regexes=None, post_text_to_match=''):
        # type: (str, Dict[str, str], str) -> None
        """Create a GrepForm that looks for any lines containing a string."""
        self.text_to_match = text_to_match
        self.regexes = regexes or {}
        self.post_text_to_match = post_text_to_match


class IntervalForm(GrepForm):
    """Grep form that looks for log_lines between starting and ending strings.

    Arguments:
        text_to_match (str): The Grep string to match.
        start_text (str): A string to match as the beginning of the interval.
        end_text (str): A string to match as the ending of the interval.
        regexes (list): One or more regex patterns to match against the "grepped" lines.
        post_text_to_match (str): Get additional line(s) beyond the text_to_match.
        inclusive (bool): Include the start/end strings in the returned results.
        as_regex (bool): Treat the start_text and end_text as regex patterns.
    """

    # pylint: disable=too-many-arguments
    # All of these arguments are required.
    def __init__(self,
                 text_to_match,                 # type: str
                 start_text,                    # type: str
                 end_text,                      # type: str
                 regexes=None,                  # type: Optional[Dict[str, str]]
                 post_text_to_match=None,       # type: Optional[List[str]]
                 inclusive=True,                # type: bool
                 as_regex=False                 # type: bool
                ):                              # type: (...) -> None
        """Create a GrepForm that looks for all lines between start_text and end_text."""
        self.text_to_match = text_to_match
        self.start_text = start_text
        self.end_text = end_text
        self.regexes = regexes
        self.post_text_to_match = post_text_to_match
        self.inclusive = inclusive
        self.as_regex = as_regex


class FlutterForm(IntervalForm):
    """Forms used to get raw flutter lines."""

    def __init__(self, flut_name):
        # type: (str) -> None
        super(FlutterForm, self).__init__(
            text_to_match='flutter',
            start_text='flutter ->dump({})'.format(flut_name),
            end_text='flutter <-dump',
            regexes={},
        )


class SupportShowForm(IntervalForm):
    """Cisco form which only looks for command output in a cisco log."""

    def __init__(self, cisco_command):
        # type: (str) -> None
        super(SupportShowForm, self).__init__(
            text_to_match=None,
            start_text='`{}`'.format(cisco_command),
            end_text='`',
            inclusive=False,
        )


class TarfileForm(GrepForm):
    """Grep form which only looks for specific files within a Tar Archive."""

    def __init__(self, text_to_match, sub_file_pattern, include_filename=False):
        # type: (str, str, bool) -> None
        """Create a GrepForm that looks at all lines within a sub-file in an archive."""
        self.text_to_match = text_to_match
        self.sub_file_pattern = sub_file_pattern
        self.include_filename = include_filename


class LogData(object):
    """Base class for data that can be pulled from the logs."""

    def __init__(self, forms):
        # type: (List[Any]) -> None
        """Create an unparsed data object to track parsed values."""
        if not isinstance(forms, dict):
            raise TypeError('Expected a dict formatted as \'{form_name: GrepForm}\'')
        self.forms = forms
        self.value = None

    def __getitem__(self, key):
        # type: (str) -> Any
        """Get an attribute by calling a key."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def items(self):
        # type: () -> Iterator[Tuple[Any, Any]]
        """Return key and value pairs."""
        return ((key, self[key]) for key in self.keys())

    def keys(self):
        # type: () -> Iterator[str]
        """Return available keys."""
        skip = ('keys', 'values', 'items')
        return (key for key in dir(self) if not key.startswith('_') and key not in skip)

    def values(self):
        # type: () -> Iterator[str]
        """Return values for each key."""
        keys = self.keys()
        return (self[key] for key in keys)


class ParallelLogParser(with_metaclass(abc.ABCMeta, object)):
    """A Generic Log Parser - helper for a single log file."""

    __metaclass__ = abc.ABCMeta

    fields = abc.abstractproperty(None)  # type: Dict[str, LogData]
    forms = abc.abstractproperty(None)  # type: Dict[str, Any]

    def __init__(self, log_file):
        # type: (str) -> None
        self._form_lines = None
        self.field_data = {}  # type: Dict[str, Any]
        self.log_file = log_file
        self.text_to_match = self._get_text_to_match()
        self.controller_name = file_utils.LogFile(log_file).controller
        # TODO: PT-2131 - Multi-thread fetch_raw_lines, form_lines, get_fields?

    def _get_text_to_match(self):
        # type: () -> List[str]
        """Get all of the patterns to match in raw lines from files."""
        all_text_to_match = set()
        for form in self.forms.values():
            # All forms will have text_to_match.
            if form.text_to_match:
                all_text_to_match.add(form.text_to_match)
            # Only some will have post_text_to_match.
            if hasattr(form, 'post_text_to_match') and form.post_text_to_match:
                all_text_to_match.add(form.post_text_to_match)
        return list(all_text_to_match)

    def fetch_raw_lines(self):
        # type: () -> List[str]
        """Get all of the needed raw lines from the log files."""
        if not self.text_to_match:
            lines_gen = file_utils.file_lines_generator([self.log_file])
        else:
            lines_gen = file_utils.iter_file_matching_lines([self.log_file], self.text_to_match)
        return lines_gen

    @property
    def form_lines(self):
        # type: () -> pandas.DataFrame
        """Order raw lines into a pandas.DataFrame columns, one per form."""
        # TODO: PT-2392 - Don't run all of the forms if we don't need them.  Unless this is an ETL or interactive usage.
        # TODO: Does this mean we read every line in hardware.log and then do the generator?
        if self._form_lines is None:
            # TODO: PT-2131 - Actually use this as a generator instead of a list.
            form_lines = pandas.DataFrame(list(self.fetch_raw_lines()))
            if form_lines.empty:
                # PT-2146 - If we have no lines matched, add a placeholder column.
                for form_name in self.forms.keys():
                    form_lines[form_name] = None
            else:
                form_lines.columns = ['raw_lines']
                for form_name, form in self.forms.items():
                    # If we have a form.text_to_match we'll add a column with these form lines, otherwise
                    # we should be pointed to the raw_lines.
                    if form.text_to_match:
                        # Put placeholders in place for all rows where we don't match lines.
                        form_lines[form_name] = None
                        form_lines[form_name] = form_lines[form_lines['raw_lines'].str.contains(form.text_to_match)]
            self._form_lines = form_lines
        return self._form_lines

    def get_form_lines(self, form_name):
        # type: (str) -> List[str]
        """Fetch the form_lines for a single form."""
        if form_name not in self.forms.keys():
            msg = 'Unknown form "{}" was requested.'.format(form_name)
            LOGGER.error(msg)
            raise KeyError(msg)
        # Get our form instance and check if it has text to match.  If not, use
        # raw lines - otherwise, use the form lines from that form.
        form = self.forms[form_name]
        if not form.text_to_match:
            form_lines = self.form_lines['raw_lines']
        elif form_name not in self.form_lines:
            LOGGER.warning('No lines exist for form "{}".'.format(form_name))
            form_lines = []
        else:
            form_lines = self.form_lines[form_name].dropna()

        # TODO: PT-2392 - Store form_lines as the processed version, not the raw lines.
        if isinstance(form, IntervalForm):
            form_gen = file_utils.iter_line_intervals(lines=form_lines,
                                                      start_string=form.start_text,
                                                      end_string=form.end_text,
                                                      regex=form.as_regex,
                                                      inclusive=form.inclusive)
        elif isinstance(form, TarfileForm):
            form_gen = file_utils.tarfile_lines_generator([self.log_file],
                                                          f_type=form.sub_file_pattern,
                                                          include_filename=form.include_filename)
        else:
            form_gen = form_lines

        # TODO: PT-2131 - Actually use this as a generator instead of a list!
        form_data = list(form_gen)

        if hasattr(form, 'post_text_to_match') and form.post_text_to_match:
            if isinstance(form, IntervalForm):
                intervals = []
                for interval in form_lines:
                    post_lines = file_utils.iter_matching_lines(interval, form.post_text_to_match)
                    # TODO: PT-2131 - Actually use this as a generator instead of a list!
                    intervals.append(list(post_lines))
                form_gen = intervals
            else:
                form_gen = file_utils.iter_matching_lines(form_lines, form.post_text_to_match)
            # TODO: PT-2131 - Actually use this as a generator instead of a list!
            form_data.extend(list(form_gen))
        return form_data

    def get_field(self, field_name):
        # type: (str) -> List[Tuple[time_utils.Timestamp, Any]]
        """Get the requested field by parsing form_data."""
        if field_name not in self.field_data:
            getter_name = 'get_{}'.format(field_name)
            if not hasattr(self, getter_name):
                msg = 'The requested field "{}" does not exist.'.format(field_name)
                raise AttributeError(msg)
            getter = getattr(self, getter_name)
            result = getter()
            self.field_data[field_name] = result
        return self.field_data[field_name]

    def get_fields(self, fields):
        # type: (List[str]) -> Dict[str, List[Tuple[time_utils.Timestamp, Any]]]
        """Get the requested fields."""
        return {field_name: self.get_field(field_name) for field_name in fields}

    def regex_in_intervals(self, form_name):
        # type: (str) -> List[Any]
        """Generate the intervals for an IntervalForm, and then use regexes against the lines within each interval."""
        # These are used for generating fields... but perhaps we should have a regex form...
        form = self.forms[form_name]
        matches = []
        regexes = [re.compile(reg) for reg in form.regexes.values()]
        for interval in self.get_form_lines(form_name):
            parsed = []  # type: List[Dict[str, Any]]
            timestamp = None
            for line in interval:
                if form.start_text in line:
                    continue
                elif form.end_text in line:
                    matches.append((timestamp, parsed))
                    break
                for regex in regexes:
                    match = regex.match(line)
                    if not match:
                        continue
                    if not timestamp:
                        timestamp = match.group('timestamp')
                    parsed.append(match.groupdict())
        return matches

    def pull_from_regex(self, form, keys=None):
        # type: (str, Optional[List[str]]) -> List[Any]
        """Pull specific keys from the regex named group matches.
            A "timestamp" pattern is assumed to be part of the regex named groups.

        Arguments:
            form (str): Which form to get lines and regex patterns from.
            keys (list/set/tuple): One or more keys to pull from the regex named groups dictionary.

        Returns:
            timestamped_results (list): A list of per timestamp dictionary with a value for each requested key.
                * Example: [(Timestamp, {'purity_version': '4.10.7'}), ...]
        """
        # These are used for generating fields... but perhaps we should have a regex form...
        timestamped_results = []
        for group_dict in self._get_regex_matches_dict(form):
            timestamp = time_utils.Timestamp(group_dict['timestamp'])
            keys = keys or [key for key in list(group_dict.keys()) if key != 'timestamp']
            values = {key: group_dict.get(key) for key in keys}
            timestamped_results.append((timestamp, values))
        return timestamped_results

    def _get_regex_matches_dict(self, form_name):
        # type: (str) -> List[Any]
        """Helper function for a form's regex patterns.  Returns a list of named groups matched from lines."""
        # These are used for generating fields... but perhaps we should have a regex form...
        if form_name not in self.forms.keys():
            msg = 'The requested form "{}" does not exist.'.format(form_name)
            LOGGER.error(msg)
            raise KeyError(msg)
        form_regexes = [re.compile(regex) for regex in self.forms[form_name].regexes.values()]
        if not form_regexes:
            LOGGER.warning('No regex patterns to use!')
        matches = []
        for line in self.get_form_lines(form_name):
            if not isinstance(line, string_types):
                continue
            # Get the regex patterns applicable to this form, or return an empty list.
            for regex in form_regexes:
                match = regex.match(line)
                if match:
                    matches.append(match.groupdict())
                    break
        if not matches:
            LOGGER.warning('There were no regex matches!')
        return matches
