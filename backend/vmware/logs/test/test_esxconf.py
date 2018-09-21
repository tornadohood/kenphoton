"""Unit tests for esxconf.py."""

from __future__ import unicode_literals

import unittest
import os

from photon.backend.vmware.logs import esxconf

# Get the directory base path one directory back from where this file resides.
PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/esx.conf')


class EsxconfParserTestCase(unittest.TestCase):
    """Unit tests for Esxconf Parser."""
    parser = esxconf.EsxconfParser(LOG_FILE)

    def test_get_ats_offload(self):
        """Get form lines for ats_offload"""
        expected = ['0']
        result = self.parser.get_ats_offload()
        self.assertEqual(expected, result)

    def test_get_disk_max_io_size(self):
        """Get form lines for disk_max_io_size"""
        expected = ['4096']
        result = self.parser.get_disk_max_io_size()
        self.assertEqual(expected, result)

    def test_get_wsame_offload(self):
        """Get form lines for wsame_offload"""
        expected = ['0']
        result = self.parser.get_wsame_offload()
        self.assertEqual(expected, result)

    def test_get_xcopy_offload(self):
        """Get form lines for xcopy_offload"""
        expected = ['0']
        result = self.parser.get_xcopy_offload()
        self.assertEqual(expected, result)

    def test_get_xcopy_offload_size(self):
        """Get form lines for xcopy_offload_size"""
        expected = ['16384']
        result = self.parser.get_xcopy_offload_size()
        self.assertEqual(expected, result)
