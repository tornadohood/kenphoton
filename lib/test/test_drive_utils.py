"""Unit tests for drive_utils."""

import os
import textwrap
import unittest

import pandas

from photon.lib import drive_utils

PATH = os.path.dirname(__file__)


class BootDriveTestCase(unittest.TestCase):
    """Unit tests for BootDrive."""

    test_drive = drive_utils.BootDrive('BAY1', 'CT0', capacity='500 MB')

    def test_build(self):
        """Test that we can instantiate a drive properly."""
        self.assertTrue(self.test_drive)


class BuildDriveMapTestCase(unittest.TestCase):
    """Unit tests for build_drive_map."""

    def test_available_drives(self):
        """Test drives that are available."""
        drives = {
            'SH0.BAY0': drive_utils.SSD('BAY0', 'SH0', status='healthy', model='TOSHIBA'),
        }
        expected = """
        +----------+---------+----------+---------+---------------+
        | Name     | Status  | Capacity | Model   | Serial Number |
        | SH0.BAY0 | Healthy | 0.00 B   | TOSHIBA | -             |
        +----------+---------+----------+---------+---------------+
        """
        result = '\n' + drive_utils.build_drive_map(drives) + '\n'
        self.assertEqual(textwrap.dedent(expected), result)

    def test_degraded_drives(self):
        """Test drives that are in a degraded state."""
        drives = {
            'SH0.BAY0': drive_utils.SSD('BAY0', 'SH0', status='degraded', model='TOSHIBA'),
        }
        expected = """
        +----------+----------+----------+-------+---------------+
        | Name     | Status   | Capacity | Model | Serial Number |
        | SH0.BAY0 | Degraded | -        | -     | -             |
        +----------+----------+----------+-------+---------------+
        """
        result = '\n' + drive_utils.build_drive_map(drives) + '\n'
        print(result)
        self.assertEqual(textwrap.dedent(expected), result)

    def test_other_state(self):
        """Test drives that are in other states."""
        drives = {
            'SH0.BAY0': drive_utils.SSD('BAY0', 'SH0', status='evac',  model='TOSHIBA'),
        }
        expected = """
        +----------+--------+----------+-------+---------------+
        | Name     | Status | Capacity | Model | Serial Number |
        | SH0.BAY0 | Evac   | -        | -     | -             |
        +----------+--------+----------+-------+---------------+
        """
        result = '\n' + drive_utils.build_drive_map(drives) + '\n'
        self.assertEqual(textwrap.dedent(expected), result)

    def test_without_subslots(self):
        """Test drives that have sub-slots."""
        drives = {
            'SH0.BAY0': drive_utils.SSD('BAY0', 'SH0'),
            'SH0.BAY1': drive_utils.SSD('BAY1', 'SH0'),
            'SH0.BAY2': drive_utils.SSD('BAY2', 'SH0'),
            'SH0.BAY3': drive_utils.SSD('BAY3', 'SH0')
        }
        expected = """
        +----------+---------+----------+-------+---------------+
        | Name     | Status  | Capacity | Model | Serial Number |
        | SH0.BAY0 | Unknown | -        | -     | -             |
        | SH0.BAY1 | Unknown | -        | -     | -             |
        | SH0.BAY2 | Unknown | -        | -     | -             |
        | SH0.BAY3 | Unknown | -        | -     | -             |
        +----------+---------+----------+-------+---------------+
        """
        result = '\n' + drive_utils.build_drive_map(drives) + '\n'
        self.assertEqual(textwrap.dedent(expected), result)

    def test_with_subslots(self):
        """Test drives that have sub-slots."""
        drives = {
            'SH0.BAY0.SUBSLOT0': drive_utils.SSD('BAY0', 'SH0', subslot=0),
            'SH0.BAY0.SUBSLOT1': drive_utils.SSD('BAY0', 'SH0', subslot=1),
        }
        expected = """
        +-------------------+---------+----------+-------+---------------+
        | Name              | Status  | Capacity | Model | Serial Number |
        | SH0.BAY0.SUBSLOT0 | Unknown | -        | -     | -             |
        | SH0.BAY0.SUBSLOT1 | Unknown | -        | -     | -             |
        +-------------------+---------+----------+-------+---------------+
        """
        result = '\n' + drive_utils.build_drive_map(drives) + '\n'
        self.assertEqual(textwrap.dedent(expected), result)

    def test_mixed_drives(self):
        """Test mixed drives (with and without sub-slots)."""
        drives = {
            'SH0.BAY0.SUBSLOT0': drive_utils.SSD('BAY0', 'SH0', subslot=0),
            'SH0.BAY0.SUBSLOT1': drive_utils.SSD('BAY0', 'SH0', subslot=1),
            'SH0.BAY1': drive_utils.SSD('BAY1', 'SH0'),
        }
        expected = """
        +-------------------+---------+----------+-------+---------------+
        | Name              | Status  | Capacity | Model | Serial Number |
        | SH0.BAY0.SUBSLOT0 | Unknown | -        | -     | -             |
        | SH0.BAY0.SUBSLOT1 | Unknown | -        | -     | -             |
        | SH0.BAY1          | Unknown | -        | -     | -             |
        +-------------------+---------+----------+-------+---------------+
        """
        result = '\n' + drive_utils.build_drive_map(drives) + '\n'
        self.assertEqual(textwrap.dedent(expected), result)


class BuildDrivesTestCase(unittest.TestCase):
    """Unit tests for build_drives."""

    def test_no_drives(self):
        """Test behavior when there are no drives."""
        dataset = pandas.DataFrame({
            'puredb_list_drives': [], 'dev_info': []})
        with self.assertRaises(ValueError):
            drive_utils.build_drives(dataset)

    def test_build_unknown_drive(self):
        """Test building a drive in an '(unknown)' status."""
        dataset = pandas.DataFrame({
            'puredb_list_drives': [[
                {"boot_aus_used": "3/51", "main_aus_used": "20881/60920", "subslot": 0,
                 "gid_lo": -7619299168626311129, "id_lo": -6652477740419197291, "profile sequence": 0,
                 "last_evac_completed": 1524261140, "requires_write_token": False,
                 "handle": "(unknown)", "slot": 10, "protocol": "SAS",
                 "gid_hi": 8739760034805141431, "degraded": 0, "id_hi": -8128812461518927977,
                 "last_failure": 1524261136, "name": "SH2.DRV14",
                 "device_id": "10317931612190623639:11794266333290354325", "capacity": 511587647488,
                 "status": "healthy", "type": "SSD"}
            ]],
            'dev_info': [[
                {"dev": "10317931612190623639, 11794266333290354325", "encl": "EB-2425P-E6EBD_SHU0951731L51LD",
                 "type": "SSD", "wwn": "50025380A00073C3", "name": "(unknown)",
                 "slot": "14", "dm": "/dev/ps-L_6a8olUtv0:C4OWfVlj5cV-63",
                 "apt": "2157740730225651329, 5289128460416602601",
                 "grp": "3764930054432355813, 9643499193610507735", "subslot": "0"}
            ]],
        })
        result = sorted(drive_utils.build_drives(dataset).keys())
        expected = ['SH2.BAY14.SUBSLOT0']
        self.assertEqual(expected, result)

    def test_build_NVRAM(self):
        """Test building NVRAM-only."""
        dataset = pandas.DataFrame({
            'puredb_list_drives': [[
                {"subslot": 0, "id_lo": -5476113266549725879, "profile sequence": "-",
                 "last_evac_completed": 0, "requires_write_token": False, "name": "SH0.NVR0",
                 "handle": "Z16IZF2E_100P8_STM00017FD62", "protocol": "SAS", "system": 0, "degraded": 0,
                 "id_hi": 8326520087516037223, "last_failure": 0, "capacity": 2147483648,
                 "status": "healthy", "type": "NVRAM", "slot": 0}
            ]],
            'dev_info': [[
                {"dev": "11326294815818587360, 3163988780359044947", "encl": "EB-2425P-E6EBD_SHG0998507G4F72",
                 "type": "NVRAM", "wwn": "500253845461C6D0", "name": "Z16IZF2E_100P8_STM00017FD62",
                 "slot":"0", "dm":"\ / dev\ / ps - Cvovwg - n09T: J0vFSAuNxzg - 0",
                 "apt":"2157740730225651329, 5289128460416602601",
                 "grp":"13812416312748833459, 6743034898571968934", "subslot":"0"}
            ]],
        })
        result = list(drive_utils.build_drives(dataset, skip_nvram=False).keys())
        expected = ['SH0.NVR0.SUBSLOT0']
        self.assertEqual(expected, result)

    def test_build_SSD(self):
        """Test building SSD-only."""
        dataset = pandas.DataFrame({
            'puredb_list_drives': [[
                {"boot_aus_used": "3/51", "main_aus_used": "20881/60920", "subslot": 0,
                 "gid_lo": -7619299168626311129, "id_lo": -6652477740419197291, "profile sequence": 0,
                 "last_evac_completed": 1524261140, "requires_write_token": False,
                 "handle": "TOSHIBA_THNSNH512GCST_93IZZ070TD4Y", "slot": 14, "protocol": "SAS",
                 "gid_hi": 8739760034805141431, "degraded": 0, "id_hi": -8128812461518927977,
                 "last_failure": 1524261136, "name": "SH2.DRV14",
                 "device_id": "10317931612190623639:11794266333290354325", "capacity": 511587647488,
                 "status": "healthy", "type": "SSD"}
            ]],
            'dev_info': [[
                {"dev": "10317931612190623639, 11794266333290354325", "encl": "EB-2425P-E6EBD_SHU0951731L51LD",
                 "type": "SSD", "wwn": "50025380A00073C3", "name": "TOSHIBA_THNSNH512GCST_93IZZ070TD4Y",
                 "slot": "14", "dm": "/dev/ps-L_6a8olUtv0:C4OWfVlj5cV-63",
                 "apt": "2157740730225651329, 5289128460416602601",
                 "grp": "3764930054432355813, 9643499193610507735", "subslot": "0"}
            ]]
        })
        result = sorted(drive_utils.build_drives(dataset).keys())
        expected = ['SH2.BAY14.SUBSLOT0']
        self.assertEqual(expected, result)

    def test_build_WSSD(self):
        """Test building WSSD-only."""
        dataset = pandas.DataFrame({
            'puredb_list_drives': [[
                {"boot_aus_used": "3/51", "main_aus_used": "20881/60920", "subslot": 0,
                 "gid_lo": -7619299168626311129, "id_lo": -6652477740419197291, "profile sequence": 0,
                 "last_evac_completed": 1524261140, "requires_write_token": False,
                 "handle": "WSSD7423_00BG002TB08_qp_PFMUN17043B23", "slot": 13, "protocol": "SAS",
                 "gid_hi": 8739760034805141431, "degraded": 0, "id_hi": -8128812461518927977,
                 "last_failure": 1524261136, "name": "SH2.DRV14",
                 "device_id": "10317931612190623639:11794266333290354325", "capacity": 511587647488,
                 "status": "healthy", "type": "SSD"}
                 ]],
            'dev_info': [[
                {"dev": "10317931612190623639, 11794266333290354325", "encl": "EB-2425P-E6EBD_SHU0951731L51LD",
                 "type": "SSD", "wwn": "50025380A00073C3", "name": "WSSD7423_00BG002TB08_qp_PFMUN17043B23",
                 "slot": "13", "dm": "/dev/ps-L_6a8olUtv0:C4OWfVlj5cV-63",
                 "apt": "2157740730225651329, 5289128460416602601",
                 "grp": "3764930054432355813, 9643499193610507735", "subslot": "0"}
            ]],
        })
        result = sorted(drive_utils.build_drives(dataset).keys())
        expected = ['SH2.BAY14.SUBSLOT0']
        self.assertEqual(expected, result)

    def test_build_Mixed(self):
        """Test building SSD, WSSD, and NVRAM."""
        dataset = pandas.DataFrame({
            'puredb_list_drives': [[
                {"subslot": 0, "id_lo": -5476113266549725879, "profile sequence": "-",
                 "last_evac_completed": 0, "requires_write_token": False, "name": "SH0.DRV0",
                 "handle": "Z16IZF2E_100P8_STM00017FD62", "protocol": "SAS", "system": 0, "degraded": 0,
                 "id_hi": 8326520087516037223, "last_failure": 0, "capacity": 2147483648,
                 "status": "healthy", "type": "NVRAM", "slot": 0},
                {"boot_aus_used": "3/51", "main_aus_used": "20881/60920", "subslot": 0,
                 "gid_lo": -7619299168626311129, "id_lo": -6652477740419197291, "profile sequence": 0,
                 "last_evac_completed": 1524261140, "requires_write_token": False,
                 "handle": "WSSD7423_00BG002TB08_qp_PFMUN17043B23", "slot": 13, "protocol": "SAS",
                 "gid_hi": 8739760034805141431, "degraded": 0, "id_hi": -8128812461518927977,
                 "last_failure": 1524261136, "name": "SH2.DRV13",
                 "device_id": "10317931612190623639:11794266333290354325", "capacity": 511587647488,
                 "status": "healthy", "type": "SSD"},
                {"boot_aus_used": "3/51", "main_aus_used": "20881/60920", "subslot": 0,
                 "gid_lo": -7619299168626311129, "id_lo": -6652477740419197291, "profile sequence": 0,
                 "last_evac_completed": 1524261140, "requires_write_token": False,
                 "handle": "TOSHIBA_THNSNH512GCST_93IZZ070TD4Y", "slot": 14, "protocol": "SAS",
                 "gid_hi": 8739760034805141431, "degraded": 0, "id_hi": -8128812461518927977,
                 "last_failure": 1524261136, "name": "SH2.DRV14",
                 "device_id": "10317931612190623639:11794266333290354325", "capacity": 511587647488,
                 "status": "healthy", "type": "SSD"},
            ]],
            'dev_info': [[
                {"dev": "11326294815818587360, 3163988780359044947", "encl": "EB-2425P-E6EBD_SHG0998507G4F72",
                 "type": "NVRAM", "wwn": "500253845461C6D0", "name": "Z16IZF2E_100P8_STM00017FD62",
                 "slot": "0", "dm": "\ / dev\ / ps - Cvovwg - n09T: J0vFSAuNxzg - 0",
                 "apt": "2157740730225651329, 5289128460416602601",
                 "grp": "13812416312748833459, 6743034898571968934", "subslot": "0"},
                {"dev": "10317931612190623639, 11794266333290354325", "encl": "EB-2425P-E6EBD_SHU0951731L51LD",
                 "type": "SSD", "wwn": "50025380A00073C3", "name": "TOSHIBA_THNSNH512GCST_93IZZ070TD4Y",
                 "slot": "14", "dm": "/dev/ps-L_6a8olUtv0:C4OWfVlj5cV-63",
                 "apt": "2157740730225651329, 5289128460416602601",
                 "grp": "3764930054432355813, 9643499193610507735", "subslot": "0"},
                {"dev": "10317931612190623639, 11794266333290354325", "encl": "EB-2425P-E6EBD_SHU0951731L51LD",
                 "type": "SSD", "wwn": "50025380A00073C3", "name": "WSSD7423_00BG002TB08_qp_PFMUN17043B23",
                 "slot": "13", "dm": "/dev/ps-L_6a8olUtv0:C4OWfVlj5cV-63",
                 "apt": "2157740730225651329, 5289128460416602601",
                 "grp": "3764930054432355813, 9643499193610507735", "subslot": "0"},
            ]],
        })
        result = sorted(drive_utils.build_drives(dataset).keys())
        expected = ['SH2.BAY13.SUBSLOT0', 'SH2.BAY14.SUBSLOT0']
        self.assertEqual(expected, result)


class DriveTestCase(unittest.TestCase):
    """Unit tests for Drive."""

    test_drive = drive_utils.Drive('BAY10', 'SSD', 'CH0', capacity='100 GiB')

    def test_with_capacity(self):
        """Test converting the capacity to raw."""
        self.assertEqual(self.test_drive.capacity, 107374182400.0)

    def test_build(self):
        """Test that we can instantiate a drive."""
        self.assertTrue(self.test_drive)


class NVRAMTestCase(unittest.TestCase):
    """Unit tests for NVRAM."""

    test_drive = drive_utils.NVRAM('BAY0', 'CT0', capacity='1 TiB')

    def test_build(self):
        """Test that we can instantiate a drive properly."""
        self.assertTrue(self.test_drive)


class SortDrivesTestCase(unittest.TestCase):
    """Unit tests for sort_drives."""

    def test_no_drives(self):
        """Test behavior when there are no drives given."""
        drives = ()
        with self.assertRaises(IndexError):
            drive_utils.sort_drives(drives)

    def test_multiple_drives(self):
        """Test behavior when there are multiple drives given."""
        drives = (
            ('SH0.BAY0', drive_utils.SSD('BAY0', 'SH0')),
            ('SH0.BAY1', drive_utils.SSD('BAY1', 'SH0')),
            ('SH1.BAY0', drive_utils.SSD('BAY0', 'SH1')),
            ('SH1.BAY1', drive_utils.SSD('BAY1', 'SH1')),
        )
        expected = ['SH0.BAY0', 'SH0.BAY1', 'SH1.BAY0', 'SH1.BAY1']
        result = [drv[0] for drv in sorted(drives, key=drive_utils.sort_drives)]
        self.assertEqual(result, expected)


class SSDTestCase(unittest.TestCase):
    """Unit tests for SSD."""

    test_drive = drive_utils.SSD('BAY1', 'CT0', capacity=12345678.9)

    def test_build(self):
        """Test that we can instantiate a drive properly."""
        self.assertTrue(self.test_drive)


class WSSDTestCase(unittest.TestCase):
    """Unit tests for WSSD."""

    test_drive = drive_utils.WSSD('BAY1', 'CT0', capacity=12345678.9)

    def test_build(self):
        """Test that we can instantiate a drive properly."""
        self.assertTrue(self.test_drive)
