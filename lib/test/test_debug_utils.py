"""Unit tests for lib/debug_utils."""

from __future__ import unicode_literals

import os
import unittest

try:
    import psutil
except ImportError:
    psutil = None
try:
    import tracemalloc
except ImportError:
    tracemalloc = None

from photon.lib import custom_errors
from photon.lib import debug_utils

HOME = os.path.expanduser('~')
LOGFILE = os.path.join(HOME, 'pure_tools.log')


class CProfileTestCase(unittest.TestCase):
    """Tests for cprofile_me."""

    def test_decorate(self):
        """Decorate a simple function."""
        @debug_utils.cprofile_me
        def simple_funct(first, second):
            """Do something simple."""
            return first + second
        # Run the simple funct
        simple_funct(1, 1)
        # Check for a home folder and files.
        self.assertTrue(os.path.isdir(HOME), msg='No home directory found.')
        # Assert that the file of the expected name exists:
        expected_file = 'simple_funct.cprofile'
        all_files = os.listdir(HOME)
        self.assertTrue(any(filename.endswith(expected_file) for filename in all_files))


@unittest.skipIf(not tracemalloc, 'This test is not applicable to Python 2.')
class ProfileMallocTestCase(unittest.TestCase):
    """Tests for profile_malloc."""

    def test_decorate(self):
        """Decorate a simple function."""
        @debug_utils.profile_malloc()
        def simple_funct(first, second):
            """Do something simple."""
            return first + second
        # Run the simple funct
        simple_funct(1, 1)

        # Run with input arguments
        @debug_utils.profile_malloc(10, 'traceback')
        def simple_funct2(first, second):
            """Do something simple."""
            return first + second
        # Run the simple funct2
        simple_funct2(1, 1)

        # Check for a pure_tools.log and for the expected DEBUG lines.
        self.assertTrue(os.path.isfile(LOGFILE), msg='Cannot find a pure_tools log file.')
        found_line = False
        with open(LOGFILE, 'rt') as log:
            for line in log:
                if 'Top Memory Users:' in line:
                    found_line = True
                    break
        self.assertTrue(found_line, msg='Cannot find a Memory Profile log line.')


@unittest.skipIf(not psutil, 'This test is not applicable to Python 2.')
class ProfileMemoryTestCase(unittest.TestCase):
    """Tests for profile_memory."""

    def test_decorate(self):
        """Decorate a simple function."""
        @debug_utils.profile_memory
        def simple_funct(first, second):
            """Do something simple."""
            return first + second
        # Run the simple funct
        simple_funct(1, 1)
        # Check for a pure_tools.log and for the expected DEBUG lines.
        self.assertTrue(os.path.isfile(LOGFILE), msg='Cannot find a pure_tools log file.')
        found_line = False
        with open(LOGFILE, 'rt') as log:
            for line in log:
                if 'Python memory usage during' in line:
                    found_line = True
                    break
        self.assertTrue(found_line, msg='Cannot find a Memory Profile log line.')


class ProfileRuntimeTestCase(unittest.TestCase):
    """Tests for profile_runtime."""

    def test_decorate(self):
        """Decorate a simple function."""
        @debug_utils.profile_runtime
        def simple_funct(first, second):
            """Do something simple."""
            return first + second
        # Run the simple funct
        simple_funct(1, 1)
        # Check for a pure_tools.log and for the expected DEBUG lines.
        self.assertTrue(os.path.isfile(LOGFILE), msg='Cannot find a pure_tools log file.')
        found_line = False
        with open(LOGFILE, 'rt') as log:
            for line in log:
                if 'Runtime of' in line:
                    found_line = True
                    break
        self.assertTrue(found_line, msg='Cannot find a Runtime Profile log line.')


class TimeoutTestCase(unittest.TestCase):
    """Tests for timeout."""

    def test_decorate(self):
        """Test against a never ending function."""
        @debug_utils.timeout(seconds=1, msg='Test Error Message')
        def never_ending_funct():
            """Have a function which will run forever."""
            thing = 0
            while True:
                thing += 1
        # This should raise a custom_errors.TimeoutError after 1 second
        with self.assertRaises(custom_errors.TimeoutError):
            never_ending_funct()


class ProfileAllTestCase(unittest.TestCase):
    """Tests for profile_all."""

    def test_decorate(self):
        """Decorate a simple function."""
        @debug_utils.profile_all
        def simple_funct_all(first, second):
            """Do something simple."""
            return first + second
        # Run the simple funct
        simple_funct_all(1, 1)
        # Check for a pure_tools.log and for the expected DEBUG lines.
        self.assertTrue(os.path.isfile(LOGFILE), msg='Cannot find a pure_tools log file.')
        found_memory = False
        found_runtime = False
        with open(LOGFILE, 'rt') as log:
            for line in log:
                if found_memory and found_runtime:
                    break
                elif 'Python memory usage during' in line:
                    found_memory = True
                elif 'Runtime of' in line:
                    found_runtime = True
        if psutil:
            # Only if we have the psutil module:
            self.assertTrue(found_memory, msg='Cannot find a Memory Profile log line.')
        self.assertTrue(found_runtime, msg='Cannot find a Runtime Profile log line.')
        # Check for a home folder and files.
        self.assertTrue(os.path.isdir(HOME), msg='No home directory found.')
        # Assert that the file of the expected name exists:
        expected_file = 'simple_funct_all.cprofile'
        all_files = os.listdir(HOME)
        self.assertTrue(any(filename.endswith(expected_file) for filename in all_files))


if __name__ == '__main__':
    unittest.main()
