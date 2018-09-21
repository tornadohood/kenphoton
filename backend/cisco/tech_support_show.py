"""Contains parser definitions on how to extract data from a cisco tech-support show log ."""

import collections
import logging
import re

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import DefaultDict
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

from photon.lib import cisco_utils
from photon.lib import parser_utils

LOGGER = logging.getLogger(__name__)


class SupportShowParserFormData(parser_utils.FormData):
    """Forms used by the SupportShowParser."""

    show_clock = parser_utils.SupportShowForm('show clock')
    show_device_alias_database = parser_utils.SupportShowForm('show device-alias database')
    show_flogi_database = parser_utils.SupportShowForm('show flogi database')
    show_interface = parser_utils.SupportShowForm('show interface')
    show_switchname = parser_utils.SupportShowForm('show switchname')
    show_version = parser_utils.SupportShowForm('show version')
    show_zoneset_active = parser_utils.SupportShowForm('show zoneset active vsan 1-4093')


class SupportShowParserLogData(parser_utils.LogData):
    """Manage forms for raw information to retrieve from support show logs."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        support_show_forms = SupportShowParserFormData()
        super(SupportShowParserLogData, self).__init__({form: support_show_forms[form] for form in needed_forms})


# TODO: PT-2311 - Make this report API friendly
class SupportShowParser(parser_utils.ParallelLogParser):
    """Defines all hardware data parsing functions."""

    forms = SupportShowParserFormData()
    fields = {
        'alias_dict': SupportShowParserLogData(['show_device_alias_database']),
        'bios': SupportShowParserLogData(['show_version']),
        'flogi_dict': SupportShowParserLogData(['show_flogi_database']),
        'hardware': SupportShowParserLogData(['show_version']),
        'interface_dict': SupportShowParserLogData(['show_interface', 'show_flogi_database']),
        'show_clock': SupportShowParserLogData(['show_clock']),
        'show_device_alias_database': SupportShowParserLogData(['show_device_alias_database']),
        'show_flogi_database': SupportShowParserLogData(['show_flogi_database']),
        'show_interface': SupportShowParserLogData(['show_interface']),
        'show_switchname': SupportShowParserLogData(['show_switchname']),
        'show_version': SupportShowParserLogData(['show_version']),
        'show_zoneset_active': SupportShowParserLogData(['show_zoneset_active']),
        'switchname': SupportShowParserLogData(['show_version']),
        'uptime': SupportShowParserLogData(['show_version']),
        'version': SupportShowParserLogData(['show_version']),
        'zonesets': SupportShowParserLogData(['show_zoneset_active']),
    }

    def __init__(self, *args, **kwargs):
        """Initialize a SupportShowParser."""
        # Cisco logs will only have one timestamp, so we don't need to pass that around.
        # Default is epoch 0.
        super(SupportShowParser, self).__init__(*args, **kwargs)
        self._timestamp = None

    @property
    def timestamp(self):
        # type: () -> str
        """Get the timestamp from the show_clock output."""
        # NOTE: We need this so that we don't have to use a "get_form_lines" within get_form_lines
        # and call itself recursively.  Instead it will call it separately when we actually
        # need to use this.
        # Example of show clock output:
        # `show clock`
        # 16:04:11.752 UTC Thu Jun 14 2018
        # Time source is NTP
        if self._timestamp:
            return self._timestamp
        clock_lines = self.get_form_lines('show_clock')
        if not clock_lines:
            self._timestamp = 'Jan 1 1900 00:00:00'
        else:
            self._timestamp = clock_lines[0].strip()  # For this, we don't need the time source, just the timestamp.
        return self._timestamp

    def get_fields(self, fields):
        # type: (List[str]) -> Dict[str, List[str]]
        """Get fields and add timestamp."""
        # TODO: PT-2297 - if we get no results for any commands, we should warn the user with a friendly
        # message to verify that this is actually a cisco logfile.
        # NOTE: For cisco, we don't have timestamped loglines, we only have one
        # timestamp, and that comes from the `show clock` command.  We don't want to parse
        # that timestamp every time, so we parse it once with the timestamp property call
        # and then can append it to any get_fields request.
        result = super(SupportShowParser, self).get_fields(fields)
        result['Timestamp'] = self.timestamp
        return result

    def get_form_lines(self, form_name):
        # type (str) -> Optional[List[str]]
        """Get form lines from the parser for the requested field."""
        result = super(SupportShowParser, self).get_form_lines(form_name)
        # NOTE: We just want to return the inner list since we default to
        # a list of lists if there are non-empty values, but an empty
        # list if we don't.
        if result:
            result = result[0]
        return result

    def get_all_fields(self):
        # () -> Dict[str, List[str]]
        """Get all available fields from the logfile."""
        fields = self.fields.keys()
        return self.get_fields(fields)

    def _get_first_field_val(self, field_name):
        # type: (str) -> Optional[str]
        r"""Get only the first field value from a field result.

        Example:
            get_form_lines(show_clock)
                <timestamp>\n
                <time source>\n
            returns <timestamp>
        """
        results = self.get_form_lines(field_name)
        val = results[0].rstrip() if results else None
        return val

    # TODO: PT-2303
    def _get_regex_from_output(self, field, regex_string, use_match=False):
        # type: (str, str, bool) -> List[Dict[str, str]]
        """Get a regex dicts from the results of a field result."""
        re_matches = []
        regex = re.compile(regex_string)
        # We default to using regex.search(), but can override to use regex.match()
        search_func = regex.match if use_match else regex.search
        field_lines = self.get_form_lines(field)
        for line in field_lines:
            result = search_func(line)
            if result:
                re_matches.append(result.groupdict())
        return re_matches

    def get_alias_dict(self):
        # type: () -> Dict[str, str]
        """Get dictionary of alias to wwn and wwn to alias."""
        device_alias_database_lines = self.get_form_lines('show_device_alias_database')
        # Example lines from `show device alias database`:
        #  0            1    2            3    4
        # 'device-alias name PURE_CT0_FC0 pwwn 52:4a:93:77:59:62:b2:00\n',
        wwn_col = 4
        name_col = 2
        alias_dict = {}
        for alias_line in device_alias_database_lines:
            if 'name' in alias_line:
                alias_cols = alias_line.split()
                wwn = alias_cols[wwn_col].lower()
                name = alias_cols[name_col].lower()
                alias_dict[name] = wwn
                alias_dict[wwn] = name
        return alias_dict

    def get_bios(self):
        # type: () -> str
        """Get bios information from a cisco log."""
        # Example lines from `show version`:
        # '  BIOS compile time:       01/08/09\n',
        bios = 'N/A'
        bios_dict_list = self._get_regex_from_output('show_version', 'BIOS:\s+version\s+(?P<bios>.*)')
        if bios_dict_list:
            bios = bios_dict_list[0]['bios']
        return bios

    def get_flogi_dict(self):
        # type: () -> Dict[str, List[cisco_utils.FlogiEntry]]
        """Parse flogi entries into namedtuples."""
        flogi_list = self.get_form_lines('show_flogi_database')
        # Example lines from `show flogi database`:
        # Skipping header line and wrapper line above/below header
        # -------------------------------------------------------------------------
        # INTERFACE        VSAN    FCID           PORT NAME               NODE NAME
        # -------------------------------------------------------------------------
        # fc1/2            50    0x320300  10:00:00:00:c9:fc:15:c6 20:00:00:00:c9:fc:15:c6',
        # [MFRPNTPSSSPAPP1_ELX_HBA1]
        # Bridged ports can have more than one flogi, so for consistency, we're going to use a list for each interface.
        flogi_entries = collections.defaultdict(list)  # type: DefaultDict[str, List[cisco_utils.FlogiEntry]]
        # Skip the first three lines that are headers.
        for line in flogi_list[3:]:
            splitline = line.split()
            # If the length is less than 5, it's not one of our data lines.
            if len(splitline) < 5:
                continue
            # Some lines are empty, and some are the right length, but not our huckleberry.  Filter them out.
            if splitline and 'Total' not in splitline:
                interface = splitline[0]
                vsan = splitline[1]
                fcid = splitline[2]
                port_name = splitline[3]
                node_name = splitline[4]
                flogi = cisco_utils.FlogiEntry(interface=interface, vsan=vsan, fcid=fcid, port_name=port_name,
                                               node_name=node_name, alias=None)
                # Since there can be multiple flogis for bridged ports, they're always going to be a list per interface.
                flogi_entries[interface].append(flogi)
        # No longer want defaultdict functionality, so we'll make it back into a dict.
        return dict(flogi_entries)

    def get_hardware(self):
        # type: () -> str
        """Get hardware model from a cisco log."""
        # Example lines from `show version`:
        # 'Hardware\n',
        # '  cisco MDS 9513 (13 Slot) Chassis ("Supervisor/Fabric-2a")\n',
        hardware = 'N/A'
        hardware_next_line = False
        hardware_lines_list = self.get_form_lines('show_version')
        for line in hardware_lines_list:
            # Since hardware is a line on it's own and we don't know the hardware
            # type, we just know we want the line after it.
            if 'hardware' in line.lower():
                hardware_next_line = True
                continue
            elif hardware_next_line:
                hardware = line.strip()
                break
        return hardware

    def get_interface_dict(self):
        # type: () -> Dict[str, cisco_utils.Interface]
        """Parse interface lines into dictionaries with their attributes."""
        # Example lines from `show interface`:
        # 'fc1/1 is down (Link failure or not-connected)\n',
        # '    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)\n',
        # '    Port WWN is 20:01:00:0d:ec:3c:06:00\n',
        # '    Admin port mode is F, trunk mode is off\n',
        # '    snmp link state traps are enabled\n',
        # '    Port vsan is 50\n',
        # '    Receive data field Size is 2112\n',
        # '    Beacon is turned off\n',
        # '    5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec\n',
        # '    5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec\n',
        # '      0 frames input,0 bytes\n',
        # '        0 discards,0 errors\n',
        # '        0 invalid CRC/FCS,0 unknown class \n',
        # '        0 too long,0 too short\n',
        # '      0 frames output,0 bytes\n',
        # '        0 discards,0 errors\n',
        # '      0 input OLS,0  LRR,0 NOS,0 loop inits\n',
        # '      0 output OLS,0 LRR, 0 NOS, 0 loop inits\n',
        # '    Interface last changed at Mon Feb  8 19:56:00 2016\n',
        # '\n',
        # '    Last clearing of "show interface" counters 30w 6d\n',
        interfaces = collections.defaultdict(list)  # type: DefaultDict[str, List[str]]
        interface = ''
        interface_lines = self.get_form_lines('show_interface')
        flogi_database_dict = self.get_flogi_dict()
        for interface_line in interface_lines:
            # Interface lines are tab delineated - if there are no spaces at the start
            # of the line, then it means we're a new interface.
            if re.match(r'^\w', interface_line) and 'admin state' not in interface_line:
                interface = interface_line.split()[0]
            elif not interface:
                continue
            interfaces[interface].append(interface_line)
        interface_dict = {}  # type: Dict[str, cisco_utils.Interface]
        for interface_name, interface_lines in interfaces.items():
            interface_dict[interface_name] = cisco_utils.get_interface_dict(interface_lines)
        # Add connection information - i.e. who's logged into this port.
        for interface_name, interface in interface_dict.items():
            connected_ports = [flogi.port_name for flogi in flogi_database_dict.get(interface_name, [])]
            interface['connected_wwpns'] = connected_ports
        return interface_dict

    def get_show_clock(self):
        """Get 'show clock' command output from logs."""
        lines = self.get_form_lines('show_clock')
        return lines

    def get_show_device_alias_database(self):
        """Get 'show device alias database' command output from logs."""
        lines = self.get_form_lines('show_device_alias_database')
        return lines

    def get_show_flogi_database(self):
        """Get 'show flogi database' command output from logs."""
        lines = self.get_form_lines('show_flogi_database')
        return lines

    def get_show_interface(self):
        """Get 'show interface' command output from logs."""
        lines = self.get_form_lines('show_interface')
        return lines

    def get_show_switchname(self):
        """Get 'show switchname' command output from logs."""
        lines = self.get_form_lines('show_switchname')
        return lines

    def get_show_version(self):
        """Get 'show version' command output from logs."""
        lines = self.get_form_lines('show_version')
        return lines

    def get_show_zoneset_active(self):
        """Get 'show zoneset active' command output from logs."""
        lines = self.get_form_lines('show_zoneset_active')
        return lines

    def get_switchname(self):
        lines = self.get_form_lines('show_switchname')
        return lines[0].strip()

    def get_uptime(self):
        # type: (CiscoParser) -> str
        """Get uptime switch log."""
        # Example lines from `show clock`:
        # 16:04:11.752 UTC Thu Jun 14 2018
        # Time source is NTP
        uptime = 'N/A'
        uptime_search = 'Kernel uptime is (?P<uptime>.*)'
        uptime_dict = self._get_regex_from_output('show_version', uptime_search)
        # This returns a list of dicts, of which we always want the first one.
        if uptime_dict:
            uptime = uptime_dict[0]['uptime']
        return uptime

    def get_version(self):
        """Get Cisco software version output from logs."""
        # type: () -> str
        # Example lines from `show version`:
        # system:    version 6.2(9a)
        version = 'N/A'
        versions_dict_list = self._get_regex_from_output('show_version', '\s+version:\s+(?P<version>.*)')
        if versions_dict_list:
            version = versions_dict_list[0]['version']
        return version

    def get_zonesets(self):
        # type: () -> Dict[str, cisco_utils.ZoneSet]
        """Parse zonesets from 'show zoneset active <vsan>' commands."""
        zonesets = {}
        zoneset_name = None
        zone_name = None
        current_zone = None
        current_zoneset = None

        # Example zoneset lines:
        # `show zoneset active vsan 1-4093`
        # zoneset name EVEN_RFP vsan 50
        #   zone name CVRPUXSQQ01a_CT0_FC0 vsan 50
        #   * fcid 0x321800 [pwwn 21:00:00:e0:8b:92:ce:84] [CRPUXSQQ01a_Qlogic_HBA2]
        #   * fcid 0x3201a2 [pwwn 52:4a:93:77:59:62:b2:00] [PURE_CT0_FC0]
        zname_reg = re.compile(r'zone\s+name\s(?P<name>\S+)\s+vsan\s+(?P<vsan_num>\d+)')
        zsetname_reg = re.compile(r'zoneset\s+name\s(?P<name>\S+)\s+vsan\s+(?P<vsan_num>\d+)')
        zoneset_active_lines = self.get_form_lines('show_zoneset_active')
        alias_dict = self.get_alias_dict() or {}
        flogi_dict = self.get_flogi_dict() or {}

        for line in zoneset_active_lines:
            if not line.strip():
                continue
            if 'zoneset name' in line:
                match = zsetname_reg.search(line)
                if match:
                    match_dict = match.groupdict()
                    zoneset_name = match_dict['name']
                    vsan = match_dict['vsan_num']
                    current_zoneset = cisco_utils.ZoneSet(zoneset_name, vsan)
                if current_zoneset:
                    zonesets[zoneset_name] = current_zoneset
            elif 'zone name' in line:
                if current_zoneset and current_zone:
                    current_zoneset.zones[zone_name] = current_zone
                match = zname_reg.search(line)
                if not match:
                    continue
                match_dict = match.groupdict()
                zone_name = match_dict['name']
                zone_vsan = match_dict['vsan_num']
                current_zone = cisco_utils.Zone(zone_name, zone_vsan)
            elif current_zone and current_zoneset:
                member = cisco_utils.Member(line)
                # If either the alias dict or flogi dict has info
                # get whatever missing information we can.
                if alias_dict or flogi_dict:
                    member.get_info(alias_dict, flogi_dict)

                current_zone.members.append(member)
        if all([current_zoneset, current_zone, zone_name, zoneset_name]):
            current_zoneset.zones[zone_name] = current_zone
            zonesets[zoneset_name] = current_zoneset
        return zonesets
