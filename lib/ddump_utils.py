"""Ddump utilities for processing and parsing DDUMP files."""

import logging
import re
import six

# pylint: disable=unused-import
try:
    from typing import Dict
    from typing import List
    from typing import Optional
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

TIME_FORMAT1 = r'\d+-\d+-\d+ \d+:\d+:\d+(\.\d+)?'
TIME_FORMAT2 = r'\d+\+\d+:\d+:\d+(\.\d+)?'

# Begin DDUMP of EB-2425P-E6EBD ID:001 (SN:SHG1007681G4RD4) slot 1 through /dev/sg50
IOM_REGEX = re.compile(r'Begin DDUMP of (?P<part_no>(\w+-){2,}\w+)\s+ID:(?P<shelf>\d+)\s+\(SN:(?P<serial>\w+)\)\s+slot\s+(?P<slot>\d)\s+through\s+/dev/(?P<dev>\w+)')
# EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failed firmware version: 0.0.22, Code Image B
FAILED_FW_VERSION_REGEX = re.compile(r'::\s*(?P<time>{});.*?Failed firmware version: (?P<version>[\w\.]+)'.format(TIME_FORMAT2))
# EB-2425-E12EBD /dev/sg328 000.0::    0+00:00:03.706; HAL; hal; 02; EBOD FW: V4.0.0.50
VERSION_REGEX = re.compile(r'::\s+.*EBOD FW: V(?P<version>.*\d+)')
# EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event
FAILURE_INFO_REGEX = re.compile(r'::\s*(?P<time>\d+\+\d+:\d+:\d+(\.\d+)?);.*?Failure info:\s+(Cause:\s+(?P<cause>\w+).*PC:\s+(?P<pc>\w+),)?\W+(?P<reason>.*)')
# EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Reboot after software crash.
REBOOT_REGEX = re.compile(r'::\s*(?P<time>{});.*?(?P<reason>Reboot after .*)'.format(TIME_FORMAT2))
# EB-2425P-E6EBD /dev/sg29 002.1::2017-08-06 11:57:40.190; DATSTOR; ndr; 04; A soft reset is imminent
IMMINENT_RESET_REGEX = re.compile(r'::\s*(?P<time>{});.*?A soft reset is imminent'.format(TIME_FORMAT1))


# Known issue jiras -
SIGNATURE_JIRAS = {'3.5.0.22': {'Assertion failure': 'HW-2875',
                              'Client "HA Service" triggered watchdog': 'HW-2807',
                              'Client "I2C Transport.*" triggered watchdog': 'HW-2623',
                              'Hardware watchdog interrupt': 'HW-3224',
                              'Heap overflow detected': 'HW-2473',
                              'Thread BufCLI Cmd Processing': 'HW-2733',
                              'Thread RSync:Worker': 'HW-3107',
                              'Thread SCSI TM Worker': 'HW-2871',
                              'Thread System Timer Thread': 'HW-3287',
                              'Thread discovery': 'HW-2828',
                              'Thread drive_manager': 'HW-2523',
                              'Thread event': 'HW-2904',
                              'Thread i2cipcwork': 'HW-2746',
                              'Thread i2ctranwork': 'HW-2816',
                              'Thread power_manager': 'HW-3040',
                              'Thread watchdog': 'HW-2864'},
                   '2.2.17': {'Client "HA Service" triggered watchdog': 'HW-1681',
                              'Hardware watchdog interrupt': 'HW-328',
                              'Heap overflow detected': 'HW-327',
                              'Reboot after software crash': 'HW-354',
                              'Reboot after software watchdog detected fault': 'HW-2642',
                              'Thread BufCLI Cmd Processing': 'HW-353',
                              'Thread hid': 'HW-1640',
                              'Thread logging': 'HW-1541'},
                   '4.0.0.50': {'Heap overflow detected': 'HW-3007',
                                'Thread power_manager': 'HW-2853'}}

# 6G shelf  (FW 2.2.11, 3.5.22), bit flips are HW-3355.
# 12G shelf (FW 4.0.50, 4.0.125), bit flips are HW-3377.
# NOTE: On the 6G shelves, the IOM firmware version prints wrong on the failure info
# line - 0.0.22 = 3.5.22
BITFLIP_JIRAS = {'2.2.11': 'HW-3355',
                 '3.5.0.22': 'HW-3355',
                 '4.0.0.50': 'HW-3355',
                 '4.0.125': 'HW-3377'}


def decode_bitshift_cause(cause_line):
    # type: (str) -> Optional[str]
    """Parse bit flips from shelf DDUMP Failure Info lines."""
    # Example string:
    # EB-2425P-E6EBD /dev/sg150 002.0::    0+00:00:00.244; HAL; hal; 02; Failure info:                                   Cause: 30800010, PC: 9fcf7eac, . Thread event
    # Assume we have no cause string.
    cause_str = None
    decimal_val = None

    # Set our dict of possible bit flip reasons:
    flip_reasons = {2:  'TLB exception (load or instruction fetch)',
                    3:  'TLB exception (store)',
                    4:  'Address error exception (load or instruction fetch)',
                    5:  'Address error exception (store)',
                    6:  'Bus error exception (instruction fetch)',
                    7:  'Bus error exception (data reference: load or store)',
                    8:  'Syscall exception',
                    10: 'Reserved Instruction',
                    30: 'Cache Error'}

    # Extract our binary string from the cause - Example:
    # Reboot after software crash. Cause: b080001c, PC: 9fcfdae8, . Thread OSW_WorkerThread
    flip_match = re.search(r'Cause: (?P<bit_cause>\w+)', cause_line)
    # Set our cause_str if we have a match.
    if flip_match:
        cause_str = flip_match.group('bit_cause')

    # If we have a cause_str we pulled out of there, convert it to decimal with our fun
    # little bit shift operations:

    # Steps to convert:
    # 1. bitwise & operation of the hex and the mask "0x7c"
    # 2. bit shift right by two
    # 3. convert to decimal
    # 4. Match to the decimal value in the table above.

    # Example:
    # Cause: b080001c
    # In this case, the conversion is:
    # b080001c -> 11100 -> 00111 -> 7 -> Bus error exception (data reference: load or store)

    if cause_str:
        # Convert to hex, which is what it actually is even though it says binary:
        bin_str = re.sub('^b', '0x', cause_str)
        # Get an int value from our string with base 16
        int_val = int(bin_str, base=16)
        # create a mask value the same way with our mask 0x7c
        mask_val = int('0x7c', base=16)
        # We'll shift right by this number
        shift_val = 2
        # Bitwise mask operation, then shift right.
        decimal_val = (int_val & mask_val) >> shift_val

    # Return the flip reason text, or None
    return flip_reasons.get(decimal_val)


class CrashIOM(object):
    """An IOM container class for IOMs that crash."""

    def __init__(self, timestamp=None):
        # type: (Optional[str]) -> None
        """Init for a CrashIOM."""
        self.bitflip_reason = None
        self.dev = None
        self.failed = False
        self.failure_info = ''
        self.failure_message = ''
        self.jira_lines = []
        self.jira = None
        self.part_no = None
        self.reboot_reason = ''
        self.serial = None
        self.shelf = None
        self.slot = None
        self.timestamp = timestamp
        self.version = None
        self.was_bitflip = False

    def __repr__(self):
        # type: () -> str
        base = "<Class: CrashIOM(serial='{}', part_no='{}', shelf='{}', slot='{}', dev='{}')>"
        return base.format(self.serial, self.part_no, self.shelf, self.slot, self.dev)

    def __str__(self):
        # type: () -> str
        base = "SH{}_IOM{}".format(self.shelf, self.slot)
        return base.format(self.serial, self.part_no, self.shelf, self.slot, self.dev)

    def parse_beginning(self, line):
        # type: (str) -> None
        """Parses IOM information from first IOM ddump line."""
        self.jira_lines.append(line)
        match = IOM_REGEX.search(line)
        if match:
            self.serial = match.group('serial')
            self.part_no = match.group('part_no')
            self.shelf = match.group('shelf')
            self.slot = match.group('slot')
            self.dev = match.group('dev')

    def parse_failed_version(self, failed_version_line):
        # type: (str) -> None
        """Do special conditional parsing of version line."""
        # For any version that needs special conditional parsing of this version
        # line, add that logic here.
        failed_version = FAILED_FW_VERSION_REGEX.search(failed_version_line)
        if failed_version:
            self.failed = True
            self.jira_lines.append(failed_version_line)
        if not self.version and failed_version:
            fw_line_version = failed_version.group('version')
            # In the failed_version line, FW 3.5.0.22 erroneously reports itself
            # as FW 0.0.22.
            if fw_line_version == '0.0.22':
                version = '3.5.0.22'
            else:
                version = fw_line_version
            self.version = version

    def parse_iom_version(self, version_line):
        # type: (str) -> None
        """Parse a failed version line."""
        self.jira_lines.append(version_line)
        version = VERSION_REGEX.search(version_line)
        if version:
            self.version = version.group('version')

    def parse_reboot(self, reboot_line):
        # type: (str) -> None
        """Parse a reboot reason line."""
        self.jira_lines.append(reboot_line)
        reboot_reason = REBOOT_REGEX.search(reboot_line)
        if reboot_reason:
            self.reboot_reason = reboot_reason.group('reason')
            self.failed = True

    def parse_failure_info(self, failure_info_line):
        # type: (str) -> None
        """Parse a failure info line."""
        self.jira_lines.append(failure_info_line)
        failure_info = FAILURE_INFO_REGEX.search(failure_info_line)
        if failure_info:
            self.failure_info = failure_info.group('reason')
            self.failed = True
            self.check_bitflip(failure_info_line)

    def check_bitflip(self, failure_info_line):
        # type: (str) -> None
        """Parse a failed version line for bitflips."""
        self.bitflip_reason = decode_bitshift_cause(failure_info_line)
        if self.bitflip_reason:
            self.was_bitflip = True
            self.jira = BITFLIP_JIRAS.get(self.version, 'HW-???')


class IOMCrashProcessor(object):
    """Class for parsing IOM crashes."""

    def __init__(self):
        # type: () -> None
        """Init for IOMCrashProcessor."""
        self.ioms = {}  # type: Dict[str, CrashIOM]
        self.healthy_ioms = []  # type: List[CrashIOM]
        self.failed_ioms = []  # type: List[CrashIOM]

    def process_ddumps(self, dataframe):
        # type: (pandas.DataFrame) -> None
        """Process ddump lines into CrashIOMs."""
        if not hasattr(dataframe, 'ddump'):
            LOGGER.error('No ddump column in dataframe, but it\'s needed!')
            raise ValueError('Dataframe has no ddump column.')
        for row in dataframe.itertuples():
            timestamp = row.Timestamp
            for line in row.ddump:
                if 'Begin DDUMP' in line:
                    curr_iom = CrashIOM(timestamp=timestamp)
                    curr_iom.parse_beginning(line)
                    curr_iom.timestamp = timestamp
                    self.ioms[curr_iom.dev] = curr_iom
                elif 'EBOD FW' in line:
                    curr_iom.parse_iom_version(line)
                elif 'Failed firmware version' in line:
                    # We aren't going to use this line to parse version anymore
                    # but it still may be helpful for jira information.
                    curr_iom.parse_failed_version(line)
                elif 'Reboot after' in line:
                    curr_iom.parse_reboot(line)
                elif 'Failure info:' in line:
                    curr_iom.parse_failure_info(line)

    def process_failed_ioms(self):
        # type: () -> None
        """Process failed IOMs from ddumps."""
        for iom in six.itervalues(self.ioms):
            known_jira = ''
            if not iom.failed:
                self.healthy_ioms.append(iom)
                continue
            known_version = SIGNATURE_JIRAS.get(iom.version)
            if known_version:
                for failure_reason, known_jira in six.iteritems(known_version):
                    if failure_reason in iom.failure_info or failure_reason in iom.reboot_reason:
                        iom.jira = known_jira
                        iom.failure_message = '{} - {}'.format(iom.reboot_reason, iom.failure_info)
            if iom.was_bitflip:
                known_jira = BITFLIP_JIRAS.get(iom.version)
                if known_jira:
                    iom.jira = known_jira
                    iom.failure_message += '{} - {}'.format(iom.reboot_reason, iom.bitflip_reason)
            self.failed_ioms.append(iom)
