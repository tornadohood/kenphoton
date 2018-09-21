"""Unit tests for lib/puffin_utils."""

from __future__ import unicode_literals

import os
import unittest

from photon.lib import puffin_utils


# pylint: disable=protected-access
class AddSubCmdTestCase(unittest.TestCase):
    """Test cases for _add_sub_cmd."""

    def test_valid_usage(self):
        """Test using as intended."""
        result = puffin_utils._add_sub_cmd('--domains', ['purestorage.com'])
        self.assertEqual(result, ['--domains', 'purestorage.com'])

    def test_values_str(self):
        """Test using a str for values."""
        result = puffin_utils._add_sub_cmd('--domains', 'purestorage.com')
        self.assertEqual(result, ['--domains', 'purestorage.com'])

    def test_no_values(self):
        """Test using a valid argument, but with no values."""
        result = puffin_utils._add_sub_cmd('--wait')
        self.assertEqual(result, ['--wait'])


class BuildCmdTestCase(unittest.TestCase):
    """Test cases for build_cmd."""

    def test_str_pattern(self):
        """Test using a single str for patterns; should raise a TypeError."""
        with self.assertRaises(TypeError):
            puffin_utils.build_cmd(**{'patterns': ['shmem.res'], 'log_type': 'cache.log',
                                      'domains': ['test.com']})

    def test_multiple_patterns(self):
        """Test using a list of patterns."""
        expected = ['/usr/local/bin/puffin-grep', '--file-type', 'cache.log', '--parallelism', 1, '--stdout', '--wait',
                    '--domains', 'test.com', 'shmem.res', 'flutter']
        args = {'patterns': ['shmem.res', 'flutter'], 'file_type': 'cache.log',
                'parallelism': 1, 'domains': ['test.com']}
        result = puffin_utils.build_cmd(**args)
        self.assertEqual(result, expected)

    def test_multiple_log_types(self):
        """Test using multiple log-types; this should raise a ValueError."""
        args = {'patterns': ['shmem.res', 'flutter'], 'file_type': ['cache.log', 'core.log'],
                'parallelism': 16, 'domains': ['test.com']}
        with self.assertRaises(TypeError):
            puffin_utils.build_cmd(**args)

    def test_date_range(self):
        """Test using a valid start and end date range."""
        expected = ['/usr/local/bin/puffin-grep', '--file-type', 'cache.log', '--parallelism', 16, '--stdout', '--wait',
                    '--domains', 'test.com', '--start-date-hour', '2017_10_10-00',
                    '--end-date-hour', '2017_10_11-23', 'shmem.res', 'flutter']
        config = {'patterns': ['shmem.res', 'flutter'], 'file_type': 'cache.log', 'parallelism': 16,
                  'domains': ['test.com'], 'start_date_hour': '2017_10_10',
                  'end_date_hour': '2017_10_11-23'}
        result = puffin_utils.build_cmd(**config)
        self.assertEqual(result, expected, msg='Date range did not apply properly to the cmd.')

    def test_date_no_end(self):
        """Test using a valid start date and no end date."""
        config = {'patterns': ['shmem.res', 'flutter'], 'file_type': 'cache.log', 'parallelism': 16,
                  'domains': ['test.com'], 'start_date_hour': '2017_10_11-23'}
        with self.assertRaises(ValueError):
            puffin_utils.build_cmd(**config)

    def test_date_no_start(self):
        """Test using a valid end date and no start date."""
        config = {'patterns': ['shmem.res', 'flutter'], 'file_type': 'cache.log', 'parallelism': 16,
                  'domains': ['test.com'], 'end_date_hour': '2017_10_11-23'}
        with self.assertRaises(ValueError):
            puffin_utils.build_cmd(**config)

    def test_invalid_date(self):
        """Test using a start/end which are not of the right pattern; should raise a ValueError."""
        kwargs = {'patterns': ['shmem.res', 'flutter'], 'file_type': 'cache.log', 'parallelism': 16,
                  'domains': ['test.com'], 'start_date_hour': '20171010',
                  'end_date_hour': '2017-10-11_23'}
        with self.assertRaises(ValueError):
            puffin_utils.build_cmd(**kwargs)

    @unittest.skipIf(not os.path.isfile('/usr/local/bin/puffin-grep'), "Puffin Grep not installed on this system.")
    def test_grep_args(self):
        """Test with passing-through grep_args."""
        expected = ['/usr/local/bin/puffin-grep', '--file-type', 'cache.log', '--parallelism', 8, '--stdout', '--wait',
                    '--domains', 'test.com', 'shmem.res', '--', '-i', '-A', '10']
        kwargs = {'patterns': ['shmem.res'], 'file_type': 'cache.log', 'domains': ['test.com'], 'parallelism': 8,
                  'grep_args': {'-i': None, '-A': 10}}
        result = puffin_utils.build_cmd(**kwargs)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
