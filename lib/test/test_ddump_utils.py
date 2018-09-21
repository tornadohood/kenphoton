"""Unit tests for ddump_utils.py."""

import unittest

import pandas

from photon.lib import time_utils
from photon.lib.ddump_utils import CrashIOM
from photon.lib.ddump_utils import IOMCrashProcessor


DDUMP_LINES = """Begin DDUMP of EB-2425P-E6EBD ID:001 (SN:SHG1007681G4RD4) slot 1 through /dev/sg50
Begin DDUMP of EB-2425P-E6EBD ID:001 (SN:SHG1007681G4RD4) slot 0 through /dev/sg125
Begin DDUMP of EB-2425P-E6EBD ID:000 (SN:SHG1007987G4RVW) slot 0 through /dev/sg25
Begin DDUMP of EB-2425P-E6EBD ID:000 (SN:SHG1007987G4RVW) slot 1 through /dev/sg100
Begin DDUMP of EB-2425P-E6EBD ID:002 (SN:SHG1007987G4RRX) slot 1 through /dev/sg75
Begin DDUMP of EB-2425P-E6EBD ID:002 (SN:SHG1007987G4RRX) slot 0 through /dev/sg150
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Reboot after software crash.
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Reboot after software crash.
Begin DDUMP of EB-2425P-E6EBD ID:001 (SN:SHG1007681G4RD4) slot 1 through /dev/sg50
Begin DDUMP of EB-2425P-E6EBD ID:001 (SN:SHG1007681G4RD4) slot 0 through /dev/sg125
Begin DDUMP of EB-2425P-E6EBD ID:000 (SN:SHG1007987G4RVW) slot 0 through /dev/sg25
Begin DDUMP of EB-2425P-E6EBD ID:000 (SN:SHG1007987G4RVW) slot 1 through /dev/sg100
Begin DDUMP of EB-2425P-E6EBD ID:002 (SN:SHG1007987G4RRX) slot 1 through /dev/sg75
Begin DDUMP of EB-2425P-E6EBD ID:002 (SN:SHG1007987G4RRX) slot 0 through /dev/sg150
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Reboot after software crash.
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event
EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Reboot after software crash.
""".splitlines()
DATAFRAME = pandas.DataFrame([{'Timestamp': time_utils.Timestamp('2018 Jan 25 00:00:01'), 'ddump': DDUMP_LINES}])


class TestCrashIOM(unittest.TestCase):
    """Unit tests for CrashIOM class."""

    def test_parse_beginning(self):
        # type: () -> None
        """Tests for parse_beginning() function."""
        line = 'Begin DDUMP of EB-2425P-E6EBD ID:001 (SN:SHG1007681G4RD4) slot 1 through /dev/sg50'
        iom = CrashIOM()
        iom.parse_beginning(line)
        self.assertEqual(iom.dev, 'sg50')
        self.assertEqual(iom.serial, 'SHG1007681G4RD4')
        self.assertEqual(iom.part_no, 'EB-2425P-E6EBD')
        self.assertEqual(iom.shelf, '001')
        self.assertEqual(iom.slot, '1')

    def test_parse_iom_version(self):
        # type: () -> None
        """Tests for parse_iom_version() function."""
        line = 'EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B'
        iom = CrashIOM()
        iom.parse_failed_version(line)
        self.assertEqual(iom.version, '3.5.0.22')
        self.assertEqual(iom.failed, True)

    def test_parse_reboot(self):
        # type: () -> None
        """Tests for parse_reboot() function."""
        line = 'EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Reboot after software crash.'
        iom = CrashIOM()
        iom.parse_reboot(line)
        self.assertEqual(iom.reboot_reason, 'Reboot after software crash.')
        self.assertEqual(iom.failed, True)

    def test_parse_failure_info(self):
        # type: () -> None
        """Tests for .parse_failure_info() function."""
        line = 'EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event'
        iom = CrashIOM()
        iom.parse_failure_info(line)
        self.assertEqual(iom.failure_info, 'Thread event')
        self.assertEqual(iom.failed, True)
        self.assertEqual(iom.jira, 'HW-???')

    def test_check_bitflip(self):
        # type: () -> None
        """Tests for check_bitflip() function."""
        line = 'EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event'
        iom = CrashIOM()
        iom.check_bitflip(line)
        self.assertEqual(iom.bitflip_reason, 'Address error exception (load or instruction fetch)')
        self.assertEqual(iom.was_bitflip, True)
        self.assertEqual(iom.jira, 'HW-???')


class TestIOMCrashProcessor(unittest.TestCase):
    """Unit tests for CrashIOM class."""

    def test_process_ddumps(self):
        # type: () -> None
        """Tests for process_ddumps."""
        processor = IOMCrashProcessor()
        processor.process_ddumps(DATAFRAME)
        expected = ['sg100', 'sg125', 'sg150', 'sg25', 'sg50', 'sg75']
        result = sorted(list(processor.ioms.keys()))
        self.assertEqual(expected, result)

    def process_failed_ioms(self):
        # type: () -> None
        """Tests for process_failed_ioms."""
        processor = IOMCrashProcessor()
        processor.process_ddumps(DATAFRAME)
        processor.process_failed_ioms()
        self.assertEqual(len(processor.failed_ioms), 1)
        self.assertEqual(processor.failed_ioms[0].dev, 'sg150')
        self.assertEqual(processor.failed_ioms[0].jira, 'HW-2904')
