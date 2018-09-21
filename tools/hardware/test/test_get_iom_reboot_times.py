"""Unit tests for get_iom_reboot_times.py."""

import unittest
import sys
# pylint:disable=no-name-in-module,import-error
if sys.version_info[0] >= 3:
    from unittest.mock import patch
else:
    from mock import patch

from photon import api
from photon.lib import test_utils
from photon.lib.ddump_utils import IOMCrashProcessor
from photon.tools.hardware import get_iom_reboot_times


HARDWARE_LOGS = test_utils.get_files_of_type('Uncategorized/hardware.log')


class TestBuildReport(unittest.TestCase):
    """Unit tests for build_report."""

    def test_build_report_no_jira(self):
        """Unit tests for print_report and get_iom_reboot_times are the same."""
        flasharray = api.FlashArray(files=HARDWARE_LOGS)
        iom_crash_processor = IOMCrashProcessor()
        iom_crash_processor.process_ddumps(flasharray.get_fields(['ddump']))
        iom_crash_processor.process_failed_ioms()
        result_report_list, result_jira_lines = get_iom_reboot_times.build_report(iom_crash_processor)
        expected_report_list = [['TIMESTAMP', 'SHELF', 'JIRA', 'FW', 'DETAILS'],
                                ['2018-01-15 06:05:54 GMT',
                                 'SH000_IOM0',
                                 'HW-2473',
                                 '3.5.0.22',
                                 'Reboot after software watchdog detected fault. - Heap overflow detected']]
        expected_jira_lines = []
        self.assertEqual(result_jira_lines, expected_jira_lines)
        self.assertEqual(result_report_list, expected_report_list)

    def test_build_report_jira(self):
        """Unit tests for print_report and get_iom_reboot_times are the same."""
        # We want to fake that we don't have any known jiras that match this, so we'll
        # set them to an empty dict temporarily.
        from photon.lib import ddump_utils
        sig_bak = ddump_utils.SIGNATURE_JIRAS
        ddump_utils.SIGNATURE_JIRAS = {}

        flasharray = api.FlashArray(files=HARDWARE_LOGS)
        iom_crash_processor = IOMCrashProcessor()
        iom_crash_processor.process_ddumps(flasharray.get_fields(['ddump']))
        iom_crash_processor.process_failed_ioms()
        result_report_list, result_jira_lines = get_iom_reboot_times.build_report(iom_crash_processor)
        expected_report_list = [['TIMESTAMP', 'SHELF', 'JIRA', 'FW', 'DETAILS'],
                                ['2018-01-15 06:05:54 GMT', 'SH000_IOM0', None, '3.5.0.22', '']]
        expected_jira_lines = ['No jira found for the version/cause on SH000_IOM0.  Please open a jira with the following:\n',
                               'Timestamp:     2018-01-15 06:05:54 GMT',
                               'Shelf:         000       ',
                               'Version:       3.5.0.22  ',
                               'Crash lines: ',
                               'Begin DDUMP of EB-2425P-E6EBD ID:000 (SN:SHG1007683G4XJ4) slot 0 through /dev/sg125',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:04.014; HAL; hal; 02; EBOD FW: V3.5.0.22',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:00.204; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:00.204; HAL; hal; 02; Failure info:                                                          Heap overflow detected',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:00.203; HAL; hal; 02; Reboot after software watchdog detected fault.',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:04.014; HAL; hal; 02; EBOD FW: V3.5.0.22',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:00.204; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:00.204; HAL; hal; 02; Failure info:                                                          Heap overflow detected',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:00.203; HAL; hal; 02; Reboot after software watchdog detected fault.',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:03.986; HAL; hal; 02; EBOD FW: V3.5.0.22',
                               'EB-2425P-E6EBD /dev/sg125 000.0::    0+00:00:04.017; HAL; hal; 02; EBOD FW: V3.5.0.22']
        ddump_utils.SIGNATURE_JIRAS = sig_bak
        self.assertEqual(result_jira_lines, expected_jira_lines)
        self.assertEqual(result_report_list, expected_report_list)
