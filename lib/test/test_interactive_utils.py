"""Unit tests for interactive_utils."""

import argparse
import pytest
import unittest

from photon.lib import interactive_utils

@pytest.fixture(scope='class')
def simple_parser():
    parser = argparse.ArgumentParser(description='This is fake!')
    parser.add_argument('--required-arg', action='store_true', required=True)
    parser.add_argument('--not-required', action='store_true', required=False)
    return parser

@pytest.fixture(scope='class')
def default_photon_parser():
    return interactive_utils.photon_argparse()

@pytest.mark.usefixtures("simple_parser")  
class TestChangeRequired(unittest.TestCase):
    """Unit tests for ChangeRequired custom argparse action."""

    def test_required_missing(self):
        """Test that we fail when required argument is missing."""
        parser = simple_parser()
        parser.add_argument('--to-modify', action=interactive_utils.ChangeRequired, changes={'required_arg': False, 'not_required': True})
        with self.assertRaises(SystemExit):
            parser.parse_args(['--not-required'])

    def test_altered_required(self):
        """Test that we pass when we modify the required argument."""
        parser = simple_parser()
        parser.add_argument('--to-modify', action=interactive_utils.ChangeRequired, changes={'required_arg': False, 'not_required': True})
        expected = argparse.Namespace(not_required=True, required_arg=False, to_modify=True)
        result = parser.parse_args(['--not-required', '--to-modify'])

    def test_altered_non_required(self):
        """Test that we raise SystemExit if non-required that was modified isn't there."""
        parser = simple_parser()
        parser.add_argument('--to-modify', action=interactive_utils.ChangeRequired, changes={'required_arg': True, 'not_required': True})
        with self.assertRaises(SystemExit):
            parser.parse_args(['--required-arg', '--to-modify'])

    def test_invalid_required_fails(self):
        """Test that we raise SystemExit if we're given an invalid required value."""
        parser = simple_parser()
        parser.add_argument('--to-modify', action=interactive_utils.ChangeRequired, changes={'required_arg': None, 'not_required': True})
        with self.assertRaises(SystemExit):
            parser.parse_args(['--required-arg', '--to-modify'])

    def test_invalid_dest_fails(self):
        """Test that we raise SystemExit if we're given an invalid destination."""
        parser = simple_parser()
        parser.add_argument('--to-modify', action=interactive_utils.ChangeRequired, changes={'doesnt_exist': True, 'required_arg': False})
        with self.assertRaises(SystemExit):
            parser.parse_args(['--required-arg', '--to-modify'])



@pytest.mark.usefixtures("default_photon_parser")
class TestPhotonArgparse(unittest.TestCase):
    """Unit tests for the default photon argparse."""

    def test_mutex_ident_args(self):
        parser = default_photon_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(['--fqdn', '--log_path'])

    def test_mutex_output_args(self):
        parser = default_photon_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(['--csv', '--json'])