"""Unit tests for lib/env_utils."""

from __future__ import unicode_literals

import os
import unittest

from six import string_types

from photon.lib import env_utils
from photon.lib import test_utils

PATH = os.path.dirname(__file__)

# TODO: PT-1327 - Unit tests for get_tty_wid, is_onbox, and is_fuse.


class TestGetDistro(unittest.TestCase):
    """ Tests for the get_distro() function. """
    default_location = '/etc/lsb-release'

    def test_get_distro_type(self):
        """Test the type return of get_distro."""
        self.assertIsInstance(env_utils.get_distro(self.default_location), string_types)

    def test_get_distro_purity(self):
        """Expect Purity as return from purity lsb."""
        expected = 'Purity'
        files = [test_utils.get_files_of_type('Uncategorized/purity_lsb')[0]]
        result = env_utils.get_distro(files[0])
        self.assertEqual(expected, result)

    def test_get_distro_fuse(self):
        """Expect Ubuntu as return from fuse lsb."""
        expected = 'Ubuntu'
        files = [test_utils.get_files_of_type('Uncategorized/fuse_lsb')[0]]
        result = env_utils.get_distro(files[0])
        self.assertEqual(expected, result)

    def test_get_distro_non_existent(self):
        """Test default to Ubuntu for bad lsb."""
        expected = 'other'
        files = [test_utils.get_files_of_type('Uncategorized/bad_lsb')[0]]
        result = env_utils.get_distro(files[0])
        self.assertEqual(expected, result)
