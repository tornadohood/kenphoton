"""Unit tests for shelf_utils."""

import os
import unittest

from photon.lib import shelf_utils

PATH = os.path.dirname(__file__)
# TODO: Test to ensure we have all the drives in all of the places they should be:
#  Apartments, WriteGroups, DataPacks, Enclosures, etc.


@unittest.skip('Not Completed')
class BuildEnclosuresTestCase(unittest.TestCase):
    """Unit tests for build_enclosures."""

    def test_enclosure_capacity(self):
        """Ensure that the capacity and usable capacity of each enclosure is correct."""
        pass


@unittest.skip('Not Completed')
class EnclosureTestCase(unittest.TestCase):
    """Unit tests for Enclosure."""

    test_enclosure = shelf_utils.Enclosure('CH0')

    def test_empty_capacity(self):
        """Test getting the capacity."""
        pass

    def test_build(self):
        """Test that we can instantiate an enclosure."""
        pass


@unittest.skip('Not Completed')
class ChassisTestCase(unittest.TestCase):
    """Unit tests for Chassis."""

    test_chassis = shelf_utils.Chassis('CH0')

    def test_empty_capacity(self):
        """Test getting the capacity."""
        pass

    def test_build(self):
        """Test that we can instantiate a chassis."""
        pass

    def test_add_drive(self):
        """Test that we can add a drive."""
        pass


@unittest.skip('Not Completed')
class ShelfTestCase(unittest.TestCase):
    """Unit tests for Shelf."""

    test_shelf = shelf_utils.Shelf('CH0')

    def test_empty_capacity(self):
        """Test getting the capacity."""
        pass

    def test_build(self):
        """Test that we can instantiate a shelf."""
        pass


if __name__ == '__main__':
    unittest.main()
