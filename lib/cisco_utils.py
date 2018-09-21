"""Utilities for parsing/dealing with cisco fc/eth logs."""

import logging
import re
from collections import defaultdict
from collections import namedtuple

# Disabling line-too long because all instances were valid.
# pylint: disable=line-too-long

try:
    # pylint: disable=unused-import
    from typing import DefaultDict
    from typing import Dict
    from typing import Iterator
    from typing import List
    from typing import Optional
    from typing import Union
    from typing import Tuple
except ImportError:
    pass


from photon.lib import format_utils

LOGGER = logging.getLogger(__name__)


FlogiEntry = namedtuple("FlogiEntry", ['interface', 'vsan', 'fcid', 'port_name', 'node_name', 'alias'])


class Member(object):
    """Class to contain zone member information."""

    def __init__(self, line):
        # type: (str) -> None
        """Process raw line into Member.

        Not all members have all the information we'd like.  They may or may not have
        a pwwn, an fc port, an alias name, or an fcid, etc.  Here are a few examples:

        pwwn 52:4a:93:77:6c:b9:df:02
        * fcid 0x321a00 [pwwn 21:00:00:1b:32:06:76:f0] [MFRPUXZNP16_QL_HBA1]
        pwwn 10:00:00:00:c9:4a:bd:4d [CVRPUXAPP01_DR_ELX_HBA0]
        fc1/1

        Example:
            Input Line:
                '    pwwn 10:00:00:00:c9:4a:bd:4d [CVRPUXAPP01_DR_ELX_HBA0]\n'
            Output:
                Member("    pwwn 10:00:00:00:c9:4a:bd:4d [CVRPUXAPP01_DR_ELX_HBA0]")
                member.pwwn  -> '10:00:00:00:c9:4a:bd:4d'
                member.alias -> 'CVRPUXAPP01_DR_ELX_HBA0'
        """
        self.raw = line
        self.fcid = self._get_regex_key('fcid', r'{key}\s(?P<{key}>\w+)')  # type: Optional[str]
        self.pwwn = self._get_regex_key('pwwn', r'{key}\s(?P<{key}>(\w{{2}}:){{7}}\w{{2}})')  # type: Optional[str]
        self.alias = self._get_regex_key('alias', r'\[(?P<{key}>\w+)\]')  # type: Optional[str]
        self.is_pure = self._test_purity()  # type: bool

    def __repr__(self):
        # type: () -> str
        """Return repr of raw line."""
        return 'Member("{}")'.format(self.raw)

    def __str__(self):
        # type: () -> str
        """Return string of raw line."""
        return self.raw

    def _get_regex_key(self, key, regex):
        # type: () -> Optional[str]
        """Get alias from line or return None."""
        match = re.search(regex.format(key=key), self.raw)
        result = match.group(key) if match else None
        return result

    def _test_purity(self):
        # type: () -> bool
        """Test if it's purity.  Defaults to False."""
        is_pure = False
        # This is a generic match to a Purestorage WWPN:
        # 52:4a:93:77:59:62:b2:00
        if re.search(r'\s+52:4a:93.?', self.raw.lower()):
            is_pure = True
        return is_pure

    def get_info(self, alias_dict, flogi_dict):
        # type: (Dict[str, str], Dict[str, FlogiEntry]) -> None
        """Postprocess members."""
        # Try and add additional information if possible.
        # If we don't have a wwpn, but have an alias, try and get it from the
        # alias database.
        if not self.pwwn and self.alias:
            self.pwwn = alias_dict.get(self.alias)
        # If we still don't have a wwn but we have an FCID, try to get it from
        # the flogi database.
        if not self.pwwn and self.fcid:
            for flogis in flogi_dict.values():
                for flogi_entry in flogis:
                    if flogi_entry.fcid != self.fcid:
                        continue
                    self.pwwn = flogi_entry.port_name


class Zone(object):
    """Generic class to contain Zone information."""

    def __init__(self, name, vsan):
        # type: (str, str) -> None
        """Initialize Zone object."""
        self.name = name
        self.vsan = int(vsan)
        self.members = []  # type: List[Member]

    def __repr__(self):
        # type: () -> str
        """Return repr object."""
        return "<Zone(name='{}', vsan={})>".format(self.name, self.vsan)

    def __str__(self):
        # type: () -> str
        """Return str of object."""
        return '\n'.join([str(member) for member in self.members])


class ZoneSet(object):
    """Generic class to contain Zoneset information."""

    def __init__(self, name, vsan):
        # type: (str, str) -> None
        """Initialize a ZoneSet object."""
        self.name = name
        self.vsan = int(vsan)
        self.zones = {}  # type: Dict[str, Zone]

    def __repr__(self):
        # type: () -> str
        """Return repr object."""
        return "<ZoneSet(name='{}', vsan={})>".format(self.name, self.vsan)


def _parse_io_line(val_type, line):
    # type: (str, str) -> Tuple[Optional[str], Optional[str]]
    """Parse an input or output line into a key value pair."""
    key = None
    val = None
    splitline = [item.lower() for item in line.split()]

    counter_loc = re.search(r'(?P<first>^\d+\s+\w+)|(?P<last>\w+\s+\d+$)', line)
    if counter_loc and counter_loc.group('first'):
        val = splitline[0]
        key = '{}_{}'.format(val_type, '_'.join(splitline[1:]))
    elif counter_loc and counter_loc.group('last'):
        val = splitline[1]
        key = '{}_{}'.format(val_type, '_'.join(splitline[0:]))
    return key, val


def _parse_normal_line(line):
    # type: (str) -> Dict[str, str]
    """Parse 'normal' lines into their key value pairs.

    In cisco interface output, we have lines that are 'generic', or normal to the
    interface itself.  Examples of this would be the hardware type, the last
    state change, the number of interface resets, etc.  Then there are lines that are
    input or output specific, like the counters for incoming frame crc errors vs
    outgoing crc frame errors, etc.  This function parses the former - things that are
    normal to the interface, rather than input/output specific.
    """
    results = _parse_normal_cases(line)
    if not results:
        results = _parse_special_cases(line)
    return results


def _parse_normal_cases(line):
    # type: (str) -> Dict[str, str]
    """Parse normal cases of a normal line."""
    results = {}
    normal_cases = [
        re.compile(r'(?P<key>.*) is (?P<val>.*)'),                                          # Hardware is GigabitEthernet
        re.compile(r'(?P<key>.*) are (?P<val>.*)'),                                         # snmp link state traps are enabled
        re.compile(r'(?P<key>.*): (?P<val>.*)'),                                            # Hardware: 1000/10000 Ethernet
        re.compile(r'(?P<key>.*) at (?P<val>.*)'),                                          # Interface last changed at Sun Oct  9 06:03:24 2016
        re.compile(r'(?P<val>\d+) (?P<key>interface resets$)'),                             # 12 interface resets
        re.compile(r'(?P<key>[Ll]ast link flapped) (?P<val>.*)'),                           # 'Last link flapped 13week(s) 5day(s)', '  Last link flapped never',
        re.compile(r'(?P<key>[Ll]ast clearing of "show interface" counters) (?P<val>.*)'),  # 'Last clearing of "show interface" counters never'
        re.compile(r'^(?P<key>\w+) (?P<val>\d+ \w+.*\w+)$'),                                # ['  MTU 1500 bytes', ' BW 1000000 Kbit Full Duplex', ' DLY 10 usec']
        re.compile(r'^(?P<key>\w+)\s+(?P<val>\d+/\d+)'),                                    # reliability 255/255' 'txload 1/255', 'rxload 1/255
    ]
    for search_case in normal_cases:
        match = search_case.search(line)
        if not match:
            continue
        raw_key = match.group('key')
        key = format_utils.make_snake_case(raw_key)
        val = match.group('val')
        results[key] = val
        break
    return results


def _parse_special_cases(line):
    # type: (str) -> Dict[str, str]
    """Parse special cases of a normal line.
    Arguments:
        line (str): Normal line to parse special cases from

    Returns:
        results (dict): Key/value pairs for the special cases

    Example:
        Input line:
            1 minute input rate 2736 bits/sec, 2 packets/sec
        Result Dict:
            {'1_minute_input_rate_bits_sec: 2736,
             '1_minute_input_rate_packets_sec': 2}
    """
    # So far only one special case - and that's the input/output rates.  they may or may not have the bits/sec, packets/sec
    # frames / sec, etc.
    results = {}
    special_cases = [
        # 1 minute input rate 2736 bits/sec, 2 packets/sec
        {'base_comp': re.compile(r'(?P<base>\d+ (?:minute|minutes|second|seconds) (?:input|output)) rate'),
         'values_comp': re.compile(r'(?P<val>\d+)\s+(?P<key>(?:bits|bytes|packets|frames)/sec)')
        },
    ]
    for case_dict in special_cases:
        # Typing can't infer the attributes of the re.compile() object.
        base_match = case_dict['base_comp'].search(line)  # type: ignore
        if not base_match:
            continue
        base_key = base_match.group('base')
        # Typing can't infer that this is a list of tuples of strings.
        value_matches = case_dict['values_comp'].findall(line)  # type: ignore
        if not value_matches:
            LOGGER.info('Found base match in line, but not values: {}'.format(line))
            continue
        for result in value_matches:
            key = format_utils.make_snake_case('{} {}'.format(base_key, result[1]))
            val = result[0]
            results[key] = val
    return results


def _prep_line(line):
    # type: (str) -> List[str]
    """Normalize items to have consistent spaces/commas.

    Example:
        Input string:
            "0 hello,0 there0 sally"

        Output list:
            ['0 hello', '0 there', '0 sally']
    """
    non_empty = []
    split = re.split(r'\s|,', line)
    for item in split:
        if item:
            non_empty.append(item)
    # Replace the number with comma then the number, then split on the comma if there's a
    # space before it. Add commas to items that have space in front of them.
    re_command = re.sub(r'( \d+)', r',\1', ' '.join(non_empty))
    # Now we can split on the comma reliably and strip out extra spacing
    split_val = [spaced.strip() for spaced in re_command.split(',')]
    return split_val


def _prep_lines(input_lines):
    # type: (List[str]) -> List[str]
    """Standardize commas and spacing for any lines that have multiple counters."""
    input_items = []
    for line in input_lines:
        input_items.extend(_prep_line(line))
    return input_items


def _prepare_lines_dict(separated_interface_lines):
    # type: (Dict[str, List[str]]) -> Dict[str, List[str]]
    """Create a dictionary from interface lines of input, output, and 'normal'."""
    prepped_lines_dict = {}
    prepped_lines_dict['normal'] = separated_interface_lines.get('normal', [])
    prepped_lines_dict['input'] = _prep_lines(separated_interface_lines.get('input', []))
    prepped_lines_dict['output'] = _prep_lines(separated_interface_lines.get('output', []))
    return prepped_lines_dict


def _separate_interface_lines(interface_lines):
    # type: (List[str]) -> Dict[str, List[str]]
    """Private function for splitting interface lines into input/output/generic lines.

    Arguments:
        interface_lines (list): Lines (including empty newlines) for a given interface

    Returns:
        interface_dict (dict): separated input/output/normal lines for an interface
    """
    interface_dict = defaultdict(list)  # type: DefaultDict[str, List[str]]
    # Start with the assumption that we're appending "normal" (non input/output) lines.
    append_mode = 'normal'
    # Since cisco logs are so crazy, it's easier to lambda the criteria for splitting
    # up the lines so that we can be consistent - this is because sometimes we have
    # to parse based on depth, and sometimes we have to parse based on a combination
    # of depth and contents.  This way we're consistent with a lambda.
    normal_criteria = [
        re.compile(r'^member'),                                  # member[1] : fc1/14
        re.compile(r'^interface last changed'),                  # interface last changed at sun jan 26 18:23:15 2014
        re.compile(r'^last clearing of "show interface"'),       # last clearing of "show interface" counters 30w 6d
        re.compile(r'^\d+\slow priority'),                       # 40 low priority transmit b2b credit remaining
        re.compile(r'^receive data field'),                      # receive data field size is 2112
        re.compile(r'^transmit b2b credit is data field'),       # receive data field size is 2112
        re.compile(r'^receive b2b credit is data field'),        # receive data field size is 2112
        re.compile(r'\d+.*rate'),                                # 30 seconds input rate 0 bits/sec, 0 packets/sec
                                                                 # 30 seconds output rate 0 bits/sec, 0 packets/sec
                                                                 # 5 minutes input rate 0 bits/sec, 0 packets/sec
                                                                 # 5 minutes output rate 0 bits/sec, 0 packets/sec
    ]
    input_criteria = [
        re.compile(r'^rx$'),                                     # rx / rx
        re.compile(r'^\d+\s+packets input'),                     # 11370221 packets input, 2070083644 bytes
        re.compile(r'^\d+\s+frames input'),                      # 1021993 frames input,33078709404 bytes
        re.compile(r'^\d+\s+input ols'),                         # 38 input ols,38  lrr,0 nos,0 loop inits
        re.compile(r'^(\d+\s+)?receive b2b credit remaining'),   # 32 receive b2b credit remaining / receive b2b credit is 32
    ]
    output_criteria = [
        re.compile(r'^tx$'),                                     # tx / tx
        re.compile(r'^\d+\s+packets output'),                    # 7517904 packets output, 2010548688 bytes
        re.compile(r'^\d+\s+frames output'),                     # 302772057121 frames output,501873283644288 bytes
        re.compile(r'^\d+\s+output ols'),                        # 89145 output ols,0 lrr, 44610 nos, 0 loop inits
        re.compile(r'^(\d+\s+)?transmit b2b credit remaining'),  # 32 transmit b2b credit remaining / transmit b2b credit is 32
    ]

    # Go through the lines and separate them into input/output/normal and return
    # a dictionary with input/output/normal keys and their corresponding line types
    # as a list of strings for each key
    for line in interface_lines:
        lowerline = line.lower().lstrip()
        # If we have an empty string after lower/strip, skip it.
        if not lowerline:
            continue
        if any(normal_condition.match(lowerline) for normal_condition in normal_criteria):
            LOGGER.debug('normal criteria found in {}'.format(line))
            append_mode = 'normal'
        elif any(input_condition.match(lowerline) for input_condition in input_criteria):
            LOGGER.debug('input criteria found in {}'.format(line))
            append_mode = 'input'
        elif any(output_condition.match(lowerline) for output_condition in output_criteria):
            LOGGER.debug('output criteria found in {}'.format(line))
            append_mode = 'output'

        # When we append the line, we don't want the leading indentation.
        interface_dict[append_mode].append(line.strip())
    return dict(interface_dict)


def get_interface_dict(interface_lines):
    # type: (List[str]) -> Dict[str, List[str])
    """Get a dictionary representing interface information.

    Arguments:
        interface_lines(list): Strings representing the interface information

    Returns:
        info_dict(dict): metric name and value pairs.
    """
    info_dict = {}
    separated_lines = _separate_interface_lines(interface_lines)
    prepped_and_separated = _prepare_lines_dict(separated_lines)
    info_dict.update(parse_io_lines(prepped_and_separated))
    info_dict.update(parse_normal_lines(prepped_and_separated))
    return info_dict


def parse_io_lines(separated):
    # type: () -> None
    """Parse input or output lines into key/val pairs."""
    io_dict = {}
    for val_type in ('input', 'output'):
        for line in separated.get(val_type, []):
            key, val = _parse_io_line(val_type, line)
            if key and val:
                io_dict[key] = val
    return io_dict


def parse_normal_lines(separated):
    # type: () -> None
    """Split interface lines into input/output/generic lines.

    Arguments:
        interface_lines (list): Lines (including empty newlines) for a given interface

    Returns:
        interface_dict (dict): separated input/output/normal lines for an interface
    """
    # a dictionary with those separated lines
    normal_dict = {'interface_name': separated['normal'][0].split()[0]}

    for line in separated.get('normal', []):
        if not line:
            continue
        # Cisco has multiple datapoints on the same line, but splits them
        # with a comma - so we make them into "sub lines" to parse only
        # their information.
        for subline in line.split(','):
            if not subline:
                continue
            keyval_dict = _parse_normal_line(subline.strip())
            # There's one case where the attribute name will be wrong and that's for
            # the very first line with an up/down, etc status
            # i.e. fc1/1 is upzzzzzzz
            for key, val in keyval_dict.items():
                if key == format_utils.make_snake_case(normal_dict.get('interface_name')):
                    key = 'state'
                normal_dict[key] = val
    return normal_dict


