"""Unit tests for lib/logging_utils."""

from __future__ import unicode_literals

import logging
import os
import unittest

from photon.lib import logging_utils

PATH = os.path.dirname(__file__)
# The names of these are intentional to match the functions and test cases.
# The assertRaises are also intentional; they are seen as pointless-statements because they don't return anything.
# pylint: disable=invalid-name, pointless-statement


class TestGetLoggers(unittest.TestCase):
    """ Tests for the get_loggers() function. """
    def test_get_loggers_type(self):
        """We shouldn't have other loggers in our module space."""
        self.assertIsInstance(logging_utils.get_loggers(), dict)

    def test_get_loggers_photon_exists(self):
        """Check that we get a logger for photon."""
        logger_dict = logging_utils.get_loggers()
        self.assertTrue(logger_dict['photon'])


class TestGetPhotonLoggers(unittest.TestCase):
    """ Tests for the get_photon_loggers() function. """
    def test_get_photon_loggers_type(self):
        """Check that we return a dict type."""
        result_type = type(logging_utils.get_photon_loggers())
        self.assertEqual(result_type, dict)

    def test_get_photon_loggers_photon_exists(self):
        """Test that our logger exists and is of type dict."""
        logger_dict = logging_utils.get_photon_loggers()
        self.assertTrue(logger_dict['photon'])


class TestConfigureLogger(unittest.TestCase):
    """Tests for the configure_logger function."""
    logger = logging.getLogger('photon')
    logger_dict = logging_utils.get_loggers()

    def test_configure_logger_type(self):
        """Make sure we're returning the correct logger type."""
        result_type = type(logging_utils.configure_logger('test_type_2'))
        self.assertEqual(result_type, logging.Logger)

    def test_photon_logger_exists(self):
        """Check that we instantiated a logger named photon for our base."""
        with self.assertRaises(KeyError):
            self.logger_dict['this_does_not_exist']

    def test_photon_logger_has_too_many_handlers(self):
        """Check that we have at least one handler."""
        with self.assertRaises(IndexError):
            self.logger.handlers[30]

    def test_on_box_location(self):
        """Test that our on box location is accurate."""
        expected = '/var/log/purity/pure_tools.log'
        result = logging_utils.LOCATIONS['Purity']
        self.assertEqual(expected, result)

    def test_fuse_location(self):
        """Test that our fuse location is accurate."""
        expected = '-pure_tools.log'
        result = logging_utils.LOCATIONS['Ubuntu']
        self.assertIn(expected, result)


class TestGetLogPath(unittest.TestCase):
    """ Test get_log_path function. """

    def test_get_log_path_other(self):
        """Test getting the log path for the logger on another system (like Mac OSX)."""
        expected = os.path.join(os.path.expanduser('~'), 'pure_tools.log')
        result = logging_utils.get_log_path('Mac Sucks')
        self.assertEqual(expected, result)
