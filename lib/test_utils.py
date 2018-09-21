"""Unit Test helpers."""

import fnmatch
import gzip
import importlib
import os
import pandas

import pytest
import ujson

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import List
except ImportError:
    pass

from photon.lib import time_utils

PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test/test_files')
VERSIONS = ('4.8', '4.10', '5.0', '5.1')


def get_all_test_files(path=PATH):
    # type: (str) -> List[str]
    """Get all of the test files within a path and its sub-directories.

    Arguments:
        path (str): The path to walk for listing files.

    Returns:
        A sorted list of unique files in the path (with full paths).
    """
    test_files = []  # type: List[str]
    for root, dirnames, filenames in os.walk(path):
        if dirnames:
            for dirname in dirnames:
                sub_files = get_all_test_files(path=os.path.join(root, dirname))  # type: List[str]
                test_files.extend(sub_files)
        else:
            test_files.extend([os.path.join(root, filename) for filename in filenames])
    return sorted(list(set(test_files)))


def get_files_of_type(sub_string, path=PATH):
    # type: (str, str) -> List[str]
    """Get all test files which contain a sub_string.

    Arguments:
        sub_string (str): A pattern to match within the full file path/name.  Don't include the full extension.
        path (str): The path to walk for files which match the pattern.

    Returns:
        A list of filenames which match the sub_string pattern.
    """
    all_files = get_all_test_files(path)  # type: List[str]
    return [filename for filename in all_files if fnmatch.fnmatch(filename, '*{}*'.format(sub_string))]


# pylint: disable=super-on-old-class, no-member
@pytest.fixture(scope='module')
def mock_api(real_api, *args, **kwargs):
    """Helper to simplify testing.

    This overrides the 'get_fields' method so we can just read from a static data set.
    """

    class MockAPI(real_api):
        """Helper class to simplify testing."""
        data_set = pandas.DataFrame()

        def __init__(self):
            super(MockAPI, self).__init__(*args, **kwargs)

        def get_fields(self, fields):
            """Helper to simplify testing."""
            result = {field: self.data_set[field] for field in fields}
            result['controller'] = self.data_set['controller']
            result['Timestamp'] = self.data_set['Timestamp']
            return pandas.DataFrame(result)

        def set_value(self, controller, key, value):
            """Set a value the given controller, automatically add a timestamp."""
            self.data_set = self.data_set.append({key: value,
                                                  'Timestamp': time_utils.Timestamp('2018 Jan 01 00:00:00'),
                                                  'controller': controller.upper().strip()},
                                                 ignore_index=True)

        def set_values(self, key, value):
            """Set the same value across both controllers."""
            for controller in ('CT0', 'CT1'):
                self.set_value(controller, key, value)

        def set_from_file(self, key, filename):
            """Set a value from a json file's contents."""
            with gzip.open(filename, 'r') as json_file:
                value = ujson.load(json_file, precise_float=True)
            self.set_value('CT0', key, value)
            self.set_value('CT1', key, value)

    return MockAPI()


@pytest.fixture(scope='module')
def mock_parser(real_parser, **kwargs):
    """Helper to simplify testing."""

    class MockParser(real_parser):
        """Helper class to simplify testing."""

        def __init__(self):
            self.form_data = self._form_data = kwargs.get('form_data', {'placeholder_for_init': None})
            if 'log_file' not in kwargs:
                kwargs['log_file'] = '/logs/domain.com/array-ct0/2018_01_01/core.log-2018010100.gz'
            super(MockParser, self).__init__(**kwargs)

        def get_form_lines(self, form):
            """Helper to simplify skipping all previous checks for files, etc."""
            return self._form_data.get(form)

    return MockParser()


def all_parsers_have_test(parser, filepath):
    # type: (parser_utils.ParallelLogParser, str) -> None
    """Test that a parser has unittests for all custom getters.

    Arguments:
        parser (photon.lib.parser_utils.ParallelLogParser): Parser class or instance to test against.
        filepath (str): Filepath of the test module for the specified parser.
    """
    splitfile = filepath.split('/')
    module_path = '.'.join(splitfile[splitfile.index('photon'):-1] + [splitfile[-1].split('.')[0]])
    mymodule = importlib.import_module(module_path)
    excluded_getters = [
        'get_form_lines',
        '_get_text_to_match',
        '_get_regex_matches_dict',
        'get_field',
    ]
    missing_tests = []
    for getter_name in dir(parser):
        if any(excluded in getter_name for excluded in excluded_getters):
            continue
        elif not 'get_' in getter_name:
            continue
        if not hasattr(mymodule, 'test_{}'.format(getter_name)):
            missing_tests.append(getter_name)
    if missing_tests:
        raise AttributeError('Getter(s) missing: {}'.format(', '.join(missing_tests)))
