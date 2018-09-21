"""Unit tests for apartment."""

import unittest

from photon.lib import apartment_utils
from photon.lib import drive_utils
from photon.lib import custom_errors

# TODO: Unit tests for build_apartments, build_data_packs, in_apartment, and build_write_groups.
# Ensure that we have the correct drives in each group and the correct capacity.


class ApartmentTestCase(unittest.TestCase):
    """Unit tests for Apartment."""

    test_apartment = apartment_utils.Apartment('13419475094725538408, 8251457055466146755')

    def test_build(self):
        """Test that we can instantiate an Apartment properly."""
        self.assertTrue(self.test_apartment)

    def test_add_component(self):
        """Test adding a single Write Group to the Apartment."""
        w_group = apartment_utils.WriteGroup('13419475094725538408, 8251457055466146754')
        self.test_apartment.add_component(w_group)
        self.assertEqual(len(self.test_apartment.write_groups), 1)

    def test_add_invalid_component(self):
        """Test adding a bad component to the Apartment."""
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.test_apartment.add_component(drive_utils.Drive('BAY1', 'CH0'))

    def test_add_components(self):
        """Test adding a multiple Write Group to the Apartment."""
        w_groups = (apartment_utils.WriteGroup('13419475094725538408, 8251457055466146758'),
                    apartment_utils.WriteGroup('13419475094725538407, 8251457055466146757'))
        self.test_apartment.add_components(w_groups)
        self.assertEqual(len(self.test_apartment.write_groups), 3)

    def test_add_duplicate(self):
        """Test adding a component that is already added.  This should raise a HardwareGroupError."""
        dup_group = apartment_utils.WriteGroup('13419475094725538408, 8251457055466146758')
        with self.assertRaises(custom_errors.HardwareGroupError):
            self.test_apartment.add_component(dup_group)


class DataPackTestCase(unittest.TestCase):
    """Unit tests for DataPack."""

    test_pack = apartment_utils.DataPack('datapack0', ['13419475094725538408, 8251457055466146758',
                                                       '13419475094725538407, 8251457055466146757'])

    def test_build(self):
        """Test that we can instantiate a DataPack properly."""
        self.assertTrue(self.test_pack)

    def test_add_component(self):
        """Test adding a single drive to the DataPack."""
        wgroup = apartment_utils.WriteGroup('13419475094725538407, 8251457055466146757')
        self.test_pack.add_component(wgroup)
        self.assertEqual(len(self.test_pack.write_groups), 1)

    def test_add_invalid_component(self):
        """Test adding a bad component to the DataPack."""
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.test_pack.add_component(apartment_utils.Apartment('13419475094725538408, 8251457055466146758'))

    def test_add_components(self):
        """Test adding a drives to the DataPack."""
        wgroups = [apartment_utils.WriteGroup('13419475094725538406, 8251457055466146756'),
                   apartment_utils.WriteGroup('13419475094725538408, 8251457055466146758')]
        self.test_pack.add_components(wgroups)
        self.assertEqual(len(self.test_pack.write_groups), 3)


class WriteGroupTestCase(unittest.TestCase):
    """Unit tests for WriteGroup."""

    test_write_group = apartment_utils.WriteGroup('13419475094725538408, 8251457055466146758')

    def test_build(self):
        """Test that we can instantiate a WriteGroup properly."""
        self.assertTrue(self.test_write_group)

    def test_add_component(self):
        """Test adding a single drive to the WriteGroup."""
        drive = drive_utils.SSD('BAY9', 'SH0')
        self.test_write_group.add_component(drive)
        self.assertEqual(len(self.test_write_group.drives), 1)

    def test_add_invalid_component(self):
        """Test adding a bad component to the WriteGroup."""
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.test_write_group.add_component(apartment_utils.Apartment('13419475094725538408, 8251457055466146758'))

    def test_add_components(self):
        """Test adding a drives to the WriteGroup."""
        drives = (drive_utils.SSD('BAY10', 'SH0'),
                  drive_utils.SSD('BAY11', 'SH0'))
        self.test_write_group.add_components(drives)
        self.assertEqual(len(self.test_write_group.drives), 3)


if __name__ == '__main__':
    unittest.main()
