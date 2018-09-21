#!/usr/bin/env python
"""IOM Reboot time parser.

Parses IOM reboots/crashes from ddump files.
"""

from __future__ import print_function

import logging

# pylint: disable=unused-import
try:
    from typing import Dict
    from typing import List
    from typing import Optional
except ImportError:
    pass

from photon import api
from photon.lib import debug_utils
from photon.lib.ddump_utils import IOMCrashProcessor
from photon.lib.interactive_utils import photon_argparse
from photon.lib.report_utils import build_table_and_print

LOGGER = logging.getLogger(__name__)
# TODO: PT-2190 - A-Z testing with various argparse combinations.


def build_report(iom_crash_processor):
    # type: (IOMCrashProcessor) -> (List[List[str]], List[str])
    """Build the report table for the IOMs"""
    needs_new_jira = False
    report_lists = [['TIMESTAMP', 'SHELF', 'JIRA', 'FW', 'DETAILS']]
    for iom in iom_crash_processor.failed_ioms:
        if not iom.jira:
            needs_new_jira = True
        report_lists.append(['{} GMT'.format(iom.timestamp), str(iom), iom.jira, iom.version, iom.failure_message])

    jira_lines = []
    for iom in [iom for iom in iom_crash_processor.failed_ioms if not iom.jira]:
        if needs_new_jira:
            jira_lines.append('No jira found for the version/cause on {}.  Please open a jira with the following:\n'.format(iom))
            jira_lines.append('{:15}{:10} GMT'.format('Timestamp:', str(iom.timestamp)))
            jira_lines.append('{:15}{:10}'.format('Shelf:', iom.shelf))
            jira_lines.append('{:15}{:10}'.format('Version:', iom.version))
            jira_lines.append('Crash lines: ')
            for line in iom.jira_lines:
                jira_lines.append(line)
    return report_lists, jira_lines


def print_report(report_lists, jira_lines):
    """Print a report of IOM crashes."""
    # type: (List[List[str]], List[str]) -> None
    if len(report_lists) < 2:
        print("No IOM crashes found for this date on either controller.")
    else:
        build_table_and_print(report_lists)

    if jira_lines:
        for line in jira_lines:
            print(line)


def get_iom_reboot_times(flasharray):
    # type: (api.FlashArray) -> api.FlashArray
    """Get ddumps from flasharray object and parse them."""
    iom_crash_processor = IOMCrashProcessor()
    iom_crash_processor.process_ddumps(flasharray.get_fields(['ddump']))
    iom_crash_processor.process_failed_ioms()
    report_lists, jira_lines = build_report(iom_crash_processor)
    print_report(report_lists, jira_lines)


@debug_utils.debug
def main():
    # type: () -> None
    """Main function for parsing iom reboot times."""
    parser = photon_argparse()
    args = parser.parse_args()
    flasharray = api.FlashArray(**args)
    get_iom_reboot_times(flasharray)


if __name__ == '__main__':
    main()
