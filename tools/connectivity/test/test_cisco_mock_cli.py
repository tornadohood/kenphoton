"""Unit tests for cisco_mock_cli."""

import codecs
import sys
import unittest
import zlib

from photon.tools.connectivity import cisco_mock_cli

# Pylint complains about this depending on version, but this is for version
# compatibility.
# pylint:disable=no-name-in-module,import-error
if sys.version_info[0] >= 3:
    from unittest.mock import patch
    from unittest.mock import mock_open
else:
    from mock import patch
    from mock import mock_open


class TestFilterCommands(unittest.TestCase):
    """Tests for filter_commands."""

    def test_one_result(self):
        """Test that we get the correct result."""
        command_dict = {'test command': ['out', 'put', 'lines']}
        search_string = 'test'
        result = cisco_mock_cli.filter_commands(command_dict, search_string)
        expected = ['test command']
        self.assertEqual(expected, result)

    def test_no_result(self):
        """Test that we get no results."""
        command_dict = {'test command': ['out', 'put', 'lines']}
        search_string = 'nothing to see here'
        result = cisco_mock_cli.filter_commands(command_dict, search_string)
        expected = []
        self.assertEqual(expected, result)


class TestGetCommandDict(unittest.TestCase):
    """Test get_command_dict."""

    def test_with_results(self):
        """Test that we get results from get_command_dict."""
        test_lines = ['test-switch# show tech-support details',
                      '---- show tech-support details ----',
                      '`show switchname`',
                      'test-switch',
                      '`show interface mgmt0`',
                      'mgmt0 is up',
                      '`show version`',
                      '  BIOS:      version 1.0.10']
        expected = {'show interface mgmt0': ['mgmt0 is up'],
                    'show switchname': ['test-switch'],
                    'show version': ['  BIOS:      version 1.0.10']}
        result = cisco_mock_cli.get_command_dict(test_lines)
        self.assertEqual(expected, result)


@unittest.skipIf(sys.version_info[0] < 3, "File tests only for Python3")
class TestFileStuff(unittest.TestCase):
    """Test check_file functions."""
    @patch('builtins.open', mock_open())
    @patch('os.path.exists', lambda x: True)
    def test_check_file(self):
        """Test that we get True if path exists."""
        result = cisco_mock_cli.check_file('/my/path/not/exists/log.txt')
        expected = True
        self.assertEqual(result, expected)

    @patch('builtins.open', mock_open())
    @patch('os.path.exists', lambda x: False)
    def test_no_file(self):
        """Test that we get false if the path doesn't exist."""
        result = cisco_mock_cli.check_file('/my/path/not/exists/log.txt')
        expected = False
        self.assertEqual(result, expected)

    byte_str = codecs.encode('This is a simulated log file\n with two lines')
    compressed_data = zlib.compress(byte_str)

    @patch('builtins.open', mock_open(read_data=compressed_data))
    @patch('os.path.exists', lambda x: True)
    def test_bad_file(self):
        """Test that we get false if the path doesn't exist."""
        result = cisco_mock_cli.check_file('/my/path/not/exists/log.txt')
        expected = False
        self.assertEqual(result, expected)
