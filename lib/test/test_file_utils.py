"""Unit tests for lib/file_utils."""

import gzip
import os
import pytest
import tarfile
import unittest

from photon.lib import file_utils
from photon.lib import test_utils
from photon.lib import time_utils

PATH = os.path.dirname(__file__)

def test_empty_str():
    """This should raise a ValueError."""
    with pytest.raises(ValueError):
        file_utils.LogFile('')


@pytest.mark.parametrize('logfile1, logfile2, mylambda, myresult, message', [
    # Test that an equal dated logfile compares correctly.
    ('core.log-2018020100.gz', 'core.log-2018020100.gz', lambda x, y: x < y,  False,'Failed 00:00 x < y'),
    ('core.log-2018020100.gz', 'core.log-2018020100.gz', lambda x, y: x <= y, True,  'Failed 00:00 x <= y'),
    ('core.log-2018020100.gz', 'core.log-2018020100.gz', lambda x, y: x == y, True,  'Failed 00:00 x == y'),
    ('core.log-2018020100.gz', 'core.log-2018020100.gz', lambda x, y: x > y,  False, 'Failed 00:00 x > y'),
    ('core.log-2018020100.gz', 'core.log-2018020100.gz', lambda x, y: x >= y, True,  'Failed 00:00 x >= y'),
    ('core.log-2018020100.gz', 'core.log-2018020100.gz', lambda x, y: x != y, False, 'Failed 00:00 x != y'),
    # Test that an earlier dated logfile compares correctly.
    ('core.log-2018020100.gz', 'core.log-2018020101.gz', lambda x, y: x < y,  True,  'Failed 00:01 x < y'),
    ('core.log-2018020100.gz', 'core.log-2018020101.gz', lambda x, y: x <= y, True,  'Failed 00:01 x <= y'),
    ('core.log-2018020100.gz', 'core.log-2018020101.gz', lambda x, y: x == y, False, 'Failed 00:01 x <== y'),
    ('core.log-2018020100.gz', 'core.log-2018020101.gz', lambda x, y: x > y,  False, 'Failed 00:01 x > y'),
    ('core.log-2018020100.gz', 'core.log-2018020101.gz', lambda x, y: x >= y, False, 'Failed 00:01 x >= y'),
    ('core.log-2018020100.gz', 'core.log-2018020101.gz', lambda x, y: x != y, True,  'Failed 00:01 x != y'),
    # Test that a later dated logfile compares correctly.
    ('core.log-2018020101.gz', 'core.log-2018020100.gz', lambda x, y: x < y,  False, 'Failed 01:00 x < y'),
    ('core.log-2018020101.gz', 'core.log-2018020100.gz', lambda x, y: x <= y, False, 'Failed 01:00 x <= y'),
    ('core.log-2018020101.gz', 'core.log-2018020100.gz', lambda x, y: x == y, False, 'Failed 01:00 x == y'),
    ('core.log-2018020101.gz', 'core.log-2018020100.gz', lambda x, y: x > y,  True,  'Failed 01:00 x > y'),
    ('core.log-2018020101.gz', 'core.log-2018020100.gz', lambda x, y: x >= y, True,  'Failed 01:00 x >= y'),
    ('core.log-2018020101.gz', 'core.log-2018020100.gz', lambda x, y: x != y, True,  'Failed 01:00 x != y'),
])
def test_logfile_comparisons(logfile1, logfile2, mylambda, myresult, message):
    """Test that we can properly sort LogFile objects."""
    lf1 = file_utils.LogFile(logfile1)
    lf2 = file_utils.LogFile(logfile2)
    assert mylambda(lf1, lf2) == myresult, message


def test_valid_log_times():
    """These log types should all work."""
    cur_dir = os.getcwd()
    valid_logs = (
        'kern.log-2018021211.gz',
        '/logs/domain.com/array-ct0/2018_10_11/array_info.json.gz',
        'playback_db_hourly_data.tar.gz-2018021205',
        'metrics_fill_map_3.csv-2018021200.gz',
        'pureconfig_list.log-2018021201.gz',
        'platform-legacy-err.log-2018021207.gz',
        'array_info.json-2018021203.gz',
        './monitor.log-2018021211.gz',
        'opensm.0xf45214030080b732.log-20180802.gz',
        # NOTE: PT-2326/PURE-126145 for opensm parsing.
    )
    expected = {
        '/logs/domain.com/array-ct0/2018_10_11/array_info.json.gz': {
            'file_name': 'array_info.json.gz',
            'log_path': '/logs/domain.com/array-ct0/2018_10_11',
            'start_time': time_utils.Timestamp('2018101100'),
            'end_time': time_utils.Timestamp('2018101101'),
            'log_type': 'array_info.json'},
        'kern.log-2018021211.gz': {
            'file_name': 'kern.log-2018021211.gz',
            'log_path': cur_dir,
            'start_time': time_utils.Timestamp('2018021211'),
            'end_time': time_utils.Timestamp('2018021212'),
            'log_type': 'kern.log'},
        'playback_db_hourly_data.tar.gz-2018021205': {
            'file_name': 'playback_db_hourly_data.tar.gz-2018021205',
            'log_path': cur_dir,
            'start_time': time_utils.Timestamp('2018021205'),
            'end_time': time_utils.Timestamp('2018021206'),
            'log_type': 'playback_db_hourly_data.tar',
        },
        'metrics_fill_map_3.csv-2018021200.gz': {
            'log_path': cur_dir,
            'file_name': 'metrics_fill_map_3.csv-2018021200.gz',
            'start_time': time_utils.Timestamp('2018021200'),
            'end_time': time_utils.Timestamp('2018021201'),
            'log_type': 'metrics_fill_map_3.csv'},
        'pureconfig_list.log-2018021201.gz': {
            'file_name': 'pureconfig_list.log-2018021201.gz',
            'log_type': 'pureconfig_list.log',
            'start_time': time_utils.Timestamp('2018021201'),
            'end_time': time_utils.Timestamp('2018021202'),
            'log_path': cur_dir
        },
        'platform-legacy-err.log-2018021207.gz': {
            'log_path': cur_dir,
            'log_type': 'platform-legacy-err.log',
            'start_time': time_utils.Timestamp('2018021207'),
            'end_time': time_utils.Timestamp('2018021208'),
            'file_name': 'platform-legacy-err.log-2018021207.gz'
        },
        'array_info.json-2018021203.gz': {
            'file_name': 'array_info.json-2018021203.gz',
            'log_path': cur_dir,
            'start_time': time_utils.Timestamp('2018021203'),
            'end_time': time_utils.Timestamp('2018021204'),
            'log_type': 'array_info.json'
        },
        './monitor.log-2018021211.gz': {
            'log_type': 'monitor.log',
            'file_name': 'monitor.log-2018021211.gz',
            'start_time': time_utils.Timestamp('2018021211'),
            'end_time': time_utils.Timestamp('2018021212'),
            'log_path': '.'},
        # TODO: PT-2328 -> PURE-126145: Purity is phoning home hex in opensm log names.
        # Even after we get this fixed, we'll still need to account for it so we don't throw
        # an exception - i.e. this'll need another unit test once it's "fixed" for the fixed
        # way as well.
        'opensm.0xf45214030080b732.log-20180802.gz': {
            'log_type': 'opensm.0xf45214030080b732.log',
            'file_name': 'opensm.0xf45214030080b732.log-20180802.gz',
            'start_time': time_utils.Timestamp('2018080200'),
            'end_time': time_utils.Timestamp('2018080201'),
            'log_path': cur_dir}
    }
    for filename in valid_logs:
        log = file_utils.LogFile(filename)
        result = {
            'file_name': log.file_name,
            'log_path': log.log_path,
            'start_time': log.start_time,
            'end_time': log.end_time,
            'log_type': log.log_type,
        }
        assert result == expected[filename], 'Filename "{}" did not format properly.'.format(filename)


class FileLinesGeneratorTestCase(unittest.TestCase):
    """Unit tests for file_lines_generator."""

    def test_empty(self):
        """Should raise StopIteration."""
        files = [test_utils.get_files_of_type('Uncategorized/empty_config.ini')[0]]
        file_iter = file_utils.file_lines_generator(files)
        with self.assertRaises(StopIteration):
            next(file_iter)

    def test_valid(self):
        """Should return lines from the simple_config.ini file."""
        files = [test_utils.get_files_of_type('Uncategorized/simple_config.ini')[0]]
        expected = ['[test-header]\n', 'content: item1, item2, item3  type: list\n', 'content2: item4']
        file_iter = file_utils.file_lines_generator(files)
        result = list(file_iter)
        self.assertEqual(result, expected)

    def test_gz_file(self):
        """Should return lines from a .gz file."""
        files = [test_utils.get_files_of_type('Uncategorized/simple_config.gz')[0]]
        expected = ['[test-header]\n', 'content: item1, item2, item3\n', 'content2: item4\n']
        file_iter = file_utils.file_lines_generator(files)
        self.assertEqual([line for line in file_iter], expected)


class IterFileMatchingLinesTestCase(unittest.TestCase):
    """Unit tests for iter_file_matching_lines."""

    def test_empty(self):
        """Should raise a StopIteration error."""
        files = [test_utils.get_files_of_type('Uncategorized/empty_config.ini')[0]]
        file_iter = file_utils.iter_file_matching_lines(files, [])
        with self.assertRaises(StopIteration):
            next(file_iter)

    def test_no_matches(self):
        """Test where there are lines, but no matches."""
        files = [test_utils.get_files_of_type('Uncategorized/simple_config.ini')[0]]
        file_iter = file_utils.iter_file_matching_lines(files, ['no_match'])
        self.assertEqual([line for line in file_iter], [])

    def test_with_matches(self):
        """Test where there are lines, and matches."""
        expected = ['content: item1, item2, item3  type: list\n', 'content2: item4']
        files = [test_utils.get_files_of_type('Uncategorized/simple_config.ini')[0]]
        file_iter = file_utils.iter_file_matching_lines(files, ['content'])
        self.assertEqual([line for line in file_iter], expected)


class IterMatchingLinesTestCase(unittest.TestCase):
    """Unit tests for iter_matching_lines."""

    def test_empty(self):
        """Should raise StopIteration."""
        file_iter = file_utils.iter_matching_lines([], [])
        with self.assertRaises(StopIteration):
            next(file_iter)

    def test_no_matches(self):
        """Test where there are lines, but no matches."""
        file_iter = file_utils.iter_matching_lines(['this will not match'], ['fake_pattern'])
        self.assertEqual([line for line in file_iter], [])

    def test_with_matches(self):
        """Test where there are lines, and matches."""
        expected = ['content1:', 'content2:']
        file_iter = file_utils.iter_matching_lines(['content1:', 'content2:', 'fake'], ['content'])
        self.assertEqual([line for line in file_iter], expected)


class ParallelGrepTestCase(unittest.TestCase):
    """Tests for parallel_grep."""

    def test_no_files(self):
        """Test behavior when there are no files given."""
        result = file_utils.parallel_grep([], ['content'])
        self.assertEqual(result, [])

    def test_no_patterns(self):
        """Test behavior when there are no patterns given."""
        files = [test_utils.get_files_of_type('Uncategorized/simple_config.ini')[0]]
        result = file_utils.parallel_grep(files, [])
        self.assertEqual(result, [])

    def test_no_files_no_patterns(self):
        """Test behavior when there are no patterns and no files given."""
        result = file_utils.parallel_grep([], [])
        self.assertEqual(result, [])

    def test_multiple_files(self):
        """Test behavior when multiple files are given."""
        expected = ['content2: item4']
        files = test_utils.get_files_of_type('Uncategorized/*.ini')
        result = file_utils.parallel_grep(files, ['content2'])
        self.assertEqual(result, expected)

    def test_single_file(self):
        """Test behavior with a single file."""
        with self.assertRaises(IOError):
            # This should hit an IOError; as the file won't exist for first character of the string.
            files = [test_utils.get_files_of_type('Uncategorized/simple_config.gz')[0]]
            file_utils.parallel_grep(files[0], ['content2'])


class IterLineIntervalsTestCase(unittest.TestCase):
    """Unit tests for iter_line_intervals."""

    def test_empty_lines(self):
        """Should yield an empty list."""
        lines = []
        start = ''
        end = ''
        gen = file_utils.iter_line_intervals(lines, start, end)
        self.assertEqual([inter for inter in gen], [])

    def test_no_matches(self):
        """Should yield an empty list."""
        lines = ['random', 'something', 'goes', 'here']
        start = 'start'
        end = 'end'
        gen = file_utils.iter_line_intervals(lines, start, end)
        self.assertEqual([inter for inter in gen], [])

    def test_stacktrace_match(self):
        """Should yield multiple intervals."""
        # Just do a simple opener for testing gzip.
        # stacktraces.gz contains 6 unique events (of which several have no end pattern)
        files = [test_utils.get_files_of_type('Uncategorized/stacktraces.gz')[0]]
        with gzip.open(files[0], 'rt') as log:
            lines = log.readlines()
        start = 'BEGIN STACKTRACE'
        end = 'END STACKTRACE'
        gen = file_utils.iter_line_intervals(lines, start, end)
        self.assertEqual(len([stack for stack in gen]), 6)

    def test_panic_match_not_inclusive(self):
        """Should yield multiple intervals; but don't include the start/end lines."""
        # There should b 2 distinct events in this file.
        files = [test_utils.get_files_of_type('Uncategorized/panics.gz')[0]]
        with gzip.open(files[0], 'rt') as log:
            lines = log.readlines()
        start = 'Kernel panic'
        end = '[ cut here ]'
        gen = file_utils.iter_line_intervals(lines, start, end, inclusive=False)
        self.assertEqual(len([panic for panic in gen]), 2)

    def test_regex_match(self):
        """Should yield multiple intervals; match using regex."""
        # There should be 3 unique sections in this file.
        files = [test_utils.get_files_of_type('Uncategorized/diagnostics.log-2017121100')[0]]
        with gzip.open(files[0], 'rt') as log:
            lines = log.readlines()
        start = r'(?P<timestamp>\w{3} \d{2} (\d{2}:?){3})\s+(?P<command>.*)'
        end = r'^\n'
        gen = file_utils.iter_line_intervals(lines, start, end, regex=True)
        self.assertEqual(len([sect for sect in gen]), 4)


class IterFileIntervalsTestCase(unittest.TestCase):
    """Unit tests for iter_file_intervals."""

    def test_empty_file(self):
        """Should yield an empty list."""
        start = ''
        end = ''
        files = [test_utils.get_files_of_type('Uncategorized/empty_config.ini')[0]]
        gen = file_utils.iter_file_intervals(files, start, end)
        self.assertEqual([inter for inter in gen], [])

    def test_no_matches(self):
        """Should yield an empty list."""
        start = 'start'
        end = 'end'
        files = [test_utils.get_files_of_type('Uncategorized/simple_config.ini')[0]]
        gen = file_utils.iter_file_intervals(files, start, end)
        self.assertEqual([inter for inter in gen], [])

    def test_stacktrace_match(self):
        """Should yield multiple intervals."""
        # Just do a simple opener for testing gzip.
        # stacktraces.gz contains 6 unique events (of which several have no end pattern)
        start = 'BEGIN STACKTRACE'
        end = 'END STACKTRACE'
        files = [test_utils.get_files_of_type('Uncategorized/stacktraces.gz')[0]]
        gen = file_utils.iter_file_intervals(files, start, end)
        self.assertEqual(len([stack for stack in gen]), 6)

    def test_panic_match_not_inclusive(self):
        """Should yield multiple intervals; but don't include the start/end lines."""
        # There should b 2 distinct events in this file.
        start = 'Kernel panic'
        end = '[ cut here ]'
        files = [test_utils.get_files_of_type('Uncategorized/panics.gz')[0]]
        gen = file_utils.iter_file_intervals(files, start, end, inclusive=False)
        self.assertEqual(len([panic for panic in gen]), 2)

    def test_flutter_match(self):
        """Should yield multiple flutter intervals."""
        start = 'flutter ->dump'
        end = ' flutter <-dump'
        files = [test_utils.get_files_of_type('Uncategorized/flutters.gz')[0]]
        gen = file_utils.iter_file_intervals(files, start, end, inclusive=False)
        self.assertEqual(len([flutter for flutter in gen]), 2)

    def test_regex_match(self):
        """Should yield multiple intervals; match using regex."""
        # There should be 3 unique sections in this file.
        start = r'(?P<timestamp>\w{3} \d{2} (\d{2}:?){3})\s+(?P<command>.*)'
        end = r'^\n'
        files = [test_utils.get_files_of_type('Uncategorized/diagnostics.log-2017121100')[0]]
        gen = file_utils.iter_file_intervals(files, start, end, regex=True)
        self.assertEqual(len([sect for sect in gen]), 4)


class SortLogsByTypeTestCase(unittest.TestCase):
    """Unit tests for group_logs_by_type."""

    def test(self):
        """Use a list of expected file types."""

        files = [
            'alertconfig.json.gz', 'array_info.json.gz', 'auth.log-2018010900.gz', 'auth.log-2018010901.gz',
            'auth.log-2018010902.gz', 'auth.log-2018010903.gz', 'auth.log-2018010904.gz', 'auth.log-2018010905.gz',
            'auth.log-2018010906.gz', 'auth.log-2018010907.gz', 'auth.log-2018010908.gz']
        expected = {u'array_info.json': [u'array_info.json.gz'],
                    u'alertconfig.json': [u'alertconfig.json.gz'],
                    u'auth.log': [u'auth.log-2018010900.gz', u'auth.log-2018010901.gz', u'auth.log-2018010902.gz',
                                  u'auth.log-2018010903.gz', u'auth.log-2018010904.gz', u'auth.log-2018010905.gz',
                                  u'auth.log-2018010906.gz', u'auth.log-2018010907.gz', u'auth.log-2018010908.gz']}
        result = file_utils.group_logs_by_type(files)
        self.assertEqual(expected, result)


class TarFileLinesGeneratorTestCase(unittest.TestCase):
    """Unit tests for tarfile_lines_generator."""

    def test_empty_file(self):
        """Should raise tarfile.ReadError."""
        files = [test_utils.get_files_of_type('Uncategorized/empty_config.ini')[0]]
        gen = file_utils.tarfile_lines_generator(files)
        with self.assertRaises(tarfile.ReadError):
            next(gen)

    def test_hardware_log(self):
        """Test generating multiple lines of any type of sub-file."""
        expected = 131111
        files = [test_utils.get_files_of_type('Uncategorized/hardware.log')[0]]
        gen = file_utils.tarfile_lines_generator(files)
        self.assertEqual(len([line for line in gen]), expected)

    def test_filtered_hardware_log(self):
        """Test generating lines from specific file types."""
        expected = 87371
        files = [test_utils.get_files_of_type('Uncategorized/hardware.log')[0]]
        gen = file_utils.tarfile_lines_generator(files, '*_ddump')
        result = list(gen)
        self.assertEqual(len(result), expected)


if __name__ == '__main__':
    unittest.main()
