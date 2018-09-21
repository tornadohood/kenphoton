"""Contains parser definitions on how to extract data from the diagnostics log."""

import collections
import logging
import re

from dateutil.parser import parse as parse_date
from six import iteritems

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

from photon.lib import parser_utils
from photon.lib import format_utils
from photon.lib import hardware_utils
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)

# The child classes are intentionally left with no public methods.
# The parser is intentionally holding all of the parsing methods and will have a ton of them.
# It is also naming them after the command used to generate each section:
# Comments with example lines will also be present, so many long lines...
# pylint: disable=too-few-public-methods, too-many-public-methods, invalid-name, line-too-long


class DiagFormData(parser_utils.FormData):
    """Forms used by the DiagnosticsParser."""

    diagnostics = parser_utils.IntervalForm(
        text_to_match=None,
        start_text='-' * 72,
        end_text='-' * 72,
        inclusive=False,
    )


class DiagLogData(parser_utils.LogData):
    """Manage information about a piece Data from the logs."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        diag_forms = DiagFormData()
        super(DiagLogData, self).__init__({form: diag_forms[form] for form in needed_forms})


class DiagnosticsParser(parser_utils.ParallelLogParser):
    """Defines all diagnostics data sections and related functions."""
    header_reg = re.compile(r'(?P<timestamp>\w{3} \d{2} (\d{2}:?){3})\s+(?P<cmd>.*)')
    forms = DiagFormData()
    fields = {
        'apartments': DiagLogData(['diagnostics']),
        'array_name': DiagLogData(['diagnostics']),
        'capacity': DiagLogData(['diagnostics']),
        'chassis_serial': DiagLogData(['diagnostics']),
        'controller_mode':  DiagLogData(['diagnostics']),
        'controller_model': DiagLogData(['diagnostics']),
        'controller_serial': DiagLogData(['diagnostics']),
        'controller_status': DiagLogData(['diagnostics']),
        'controller_version': DiagLogData(['diagnostics']),
        'cpu_info': DiagLogData(['diagnostics']),
        'data_reduction': DiagLogData(['diagnostics']),
        'eth_counters': DiagLogData(['diagnostics']),
        'finddrive_all': DiagLogData(['diagnostics']),
        'hardware_check': DiagLogData(['diagnostics']),
        'parity': DiagLogData(['diagnostics']),
        'pgroup_snap_count': DiagLogData(['diagnostics']),
        'physical_memory': DiagLogData(['diagnostics']),
        'portal_state_info': DiagLogData(['diagnostics']),
        'purealert_list': DiagLogData(['diagnostics']),
        'purearray_list': DiagLogData(['diagnostics']),
        'purearray_list_connect': DiagLogData(['diagnostics']),
        'purearray_list_controller': DiagLogData(['diagnostics']),
        'purearray_list_ntpserver': DiagLogData(['diagnostics']),
        'purearray_list_phonehome': DiagLogData(['diagnostics']),
        'purearray_list_relayhost': DiagLogData(['diagnostics']),
        'purearray_list_sender': DiagLogData(['diagnostics']),
        'purearray_list_space': DiagLogData(['diagnostics']),
        'puredrive_list': DiagLogData(['diagnostics']),
        'puredb_dedup_version': DiagLogData(['diagnostics']),
        'puredb_list_apartment_mappings': DiagLogData(['diagnostics']),
        'puredb_list_tunable_diff': DiagLogData(['diagnostics']),
        'puredb_list_tunable_platform_diff': DiagLogData(['diagnostics']),
        'puredb_list_reservation': DiagLogData(['diagnostics']),
        'puredb_messaging_list': DiagLogData(['diagnostics']),
        'puredb_npiv_status': DiagLogData(['diagnostics']),
        'puredb_npiv_supported': DiagLogData(['diagnostics']),
        'puredb_replication_list': DiagLogData(['diagnostics']),
        'puredb_stats_crawler': DiagLogData(['diagnostics']),
        'puredns_list_all': DiagLogData(['diagnostics']),
        'puredrive_list': DiagLogData(['diagnostics']),
        'pureds_list': DiagLogData(['diagnostics']),
        'pureds_list_groups': DiagLogData(['diagnostics']),
        'purehgroup_list': DiagLogData(['diagnostics']),
        'purehgroup_list_connect': DiagLogData(['diagnostics']),
        'purehost_list': DiagLogData(['diagnostics']),
        'purehost_list_connect': DiagLogData(['diagnostics']),
        'purehw_list': DiagLogData(['diagnostics']),
        'purenetwork_list_all': DiagLogData(['diagnostics']),
        'purepgroup_list': DiagLogData(['diagnostics']),
        'purepgroup_list_retention': DiagLogData(['diagnostics']),
        'purepgroup_list_schedule': DiagLogData(['diagnostics']),
        'purepgroup_list_snap_space_total': DiagLogData(['diagnostics']),
        'purepgroup_list_snap_transfer': DiagLogData(['diagnostics']),
        'purepgroup_list_space_total': DiagLogData(['diagnostics']),
        'pureport_list': DiagLogData(['diagnostics']),
        'pureport_list_initiator': DiagLogData(['diagnostics']),
        'puresnmp_list': DiagLogData(['diagnostics']),
        'puresubnet_list': DiagLogData(['diagnostics']),
        'purevol_list': DiagLogData(['diagnostics']),
        'purevol_list_connect': DiagLogData(['diagnostics']),
        'purevol_list_snap': DiagLogData(['diagnostics']),
        'purevol_list_space_total': DiagLogData(['diagnostics']),
        'purity_version': DiagLogData(['diagnostics']),
        'security_token': DiagLogData(['diagnostics']),
        'shared_space': DiagLogData(['diagnostics']),
        'snapshot_space': DiagLogData(['diagnostics']),
        'system_space': DiagLogData(['diagnostics']),
        'ssd_capacity': DiagLogData(['diagnostics']),
        'thin_provisioning': DiagLogData(['diagnostics']),
        'timezone': DiagLogData(['diagnostics']),
        'total_reduction': DiagLogData(['diagnostics']),
        'tunables': DiagLogData(['diagnostics']),
        'volume_space': DiagLogData(['diagnostics']),
    }
    _diagnostics_sections = None

    @property
    def diagnostics_sections(self):
        # type: () -> Dict[str, Any]
        """Just get raw lines from a section of diagnostics; based upon cmd name.

        Returns:
            sections (dict): Lines for one or more matched sections.
        """
        if self._diagnostics_sections:
            return self._diagnostics_sections
        diagnostics_sections = collections.defaultdict(list)
        section_break = '*' * 72
        header_break = '-' * 72
        command = None
        timestamp = None
        for lines in self.get_form_lines('diagnostics'):
            # Each set of lines could be a command header or the command output
            if command and timestamp:
                filtered_lines = []
                for line in lines:
                    # Stop adding lines when the section break is seen
                    if line.startswith(section_break):
                        break
                    elif not line.startswith(header_break):
                        filtered_lines.append(line)
                diagnostics_sections[command].append((timestamp, filtered_lines))
                # Reset for the next section
                command = None
                timestamp = None
            else:
                for line in lines:
                    match = self.header_reg.search(line)
                    if match:
                        command = match.group('cmd')
                        timestamp = time_utils.Timestamp(parse_date(match.group('timestamp')))
        self._diagnostics_sections = dict(diagnostics_sections)
        return self._diagnostics_sections

    def _pull_from(self, section, keys=None, convert_to_raw=None):
        # type: (str, Optional[List[str]], Optional[List[str]]) -> List[Tuple[Any, Any]]
        """Pull a key from a previously parsed section.

        Arguments:
            section (str): The diagnostics section to parse.
            keys (list): One or more keys to pull from the headers of the unparsed lines/section.
            convert_to_raw (list): One or more keys to convert to raw values while parsing.

        Returns:
            results (list): A list of tuples containing (timestamp, value).
        """
        results = []
        parsed_section = self.diagnostics_sections.get(section)
        if not parsed_section:
            msg = 'The requested section "{}" does not exist.'.format(section)
            LOGGER.warning(msg)
            return results
        for timestamp, lines in parsed_section:
            parsed_dict = _parse_table_lines(lines)
            keys = keys or list(parsed_dict.keys())
            parsed_values = {}
            for key in keys:
                value = parsed_dict.get(key)
                if value and convert_to_raw and key in convert_to_raw:
                    if isinstance(value, list):
                        value = [int(format_utils.to_raw(val)) if val != '-' else 0 for val in value]
                    else:
                        value = int(format_utils.to_raw(value)) if value != '-' else 0
                parsed_values[key] = value
            # If the length of the parsed values is 1 key; then we don't need to nest this in a dictionary.
            if len(parsed_values) == 1:
                parsed_values = parsed_values[keys[0]]
            results.append((timestamp, parsed_values))
        return results

    def get_apartments(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the apartment mappings per timestamp."""
        return self._pull_from('puredb list apartment_mappings', ['Apartment'])

    def get_array_name(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array_name per timestamp."""
        return self._pull_from('purearray list', ['Name'])

    def get_capacity(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array capacity per timestamp."""
        return self._pull_from('purearray list --space', ['Capacity'], convert_to_raw=['Capacity'])

    def get_chassis_serial(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the chassis serial per timestamp."""
        serials = []
        for timestamp, values in self._pull_from('purehw list --all', keys=['Name', 'Handle']):
            # Get the index of the Controller to get the rest of its information:
            serial = None
            for index, item in enumerate(values['Name']):
                # Get 'CH0', but not 'CH0.BAY0' and similar children.
                if item.startswith('CH') and '.' not in item:
                    # Examples of a controller handle: 'PLATSASB_PCTFL16380196' or 'M_SERIES_PCHFL1634014C'
                    handle = values['Handle'][index].split('_')
                    serial = handle[-1]
                    # TODO: Add support for multi-chassis.  This just grabs the first one right now.
                    break
            serials.append((timestamp, serial))
        return serials

    def get_data_reduction(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array data_reduction per timestamp."""
        return self._pull_from('purearray list --space', keys=['Data Reduction'])

    def get_controller_mode(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the controller mode per timestamp."""
        return self._pull_from('purearray list --controller', keys=['Mode', 'Name'])

    def get_controller_model(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the controller model per timestamp."""
        return self._pull_from('purearray list --controller', keys=['Model', 'Name'])

    def get_controller_serial(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the controller serial per timestamp."""
        serials = []
        for timestamp, values in self._pull_from('purehw list --all', keys=['Name', 'Handle']):
            # Get the index of the Controller to get the rest of its information:
            serial = None
            for index, item in enumerate(values['Name']):
                if item == self.controller_name:
                    # Example of a controller handle: 'PLATSASB_PCTFL16380196'
                    handle = values['Handle'][index].split('_')
                    serial = handle[-1]
                    break
            serials.append((timestamp, serial))
        return serials

    def get_controller_status(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the controller status per timestamp."""
        return self._pull_from('purearray list --controller', keys=['Status', 'Name'])

    def get_controller_version(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the controller Purity version per timestamp."""
        return self._pull_from('purearray list --controller', keys=['Version', 'Name'])

    def get_cpu_info(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get information about the CPU model, speed, and core count."""
        hardware_sections = self.get_hardware_check()
        parsed = []
        # pylint: disable=line-too-long
        cpu_line = re.compile(r'(?P<cpu_type>.*?) CPU (?P<cpu_model>.*?) @ (?P<speed>\d+\.\d+GHz)\s+x\s+(?P<core_count>\d+)')
        for timestamp, section_dict in hardware_sections:
            # ['model name\t: Intel(R) Xeon(R) CPU E5-2698 v4 @ 2.20GHz        x 80\n']
            raw_line = section_dict['CPU'][0].split(':')[1].strip()
            match = cpu_line.match(raw_line)
            if not match:
                LOGGER.warning('Failed to parse CPU info at "{}".'.format(timestamp))
                continue
            result = match.groupdict()
            parsed.append((timestamp, result))
        return parsed

    def get_eth_counters(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get all of the counters for each Ethernet interface."""
        temp = collections.defaultdict(dict)
        # Example: 'ethtool -S eth0' -> 'eth0'
        interfaces = [key.split()[-1] for key in self.diagnostics_sections if 'ethtool' in key]
        # Combine counters from ethtool -d, -m, and -S on the interface name.
        for interface in interfaces:
            eth_s = self.diagnostics_sections.get('ethtool -S {}'.format(interface))
            eth_d = self.diagnostics_sections.get('ethtool -d {}'.format(interface))
            eth_m = self.diagnostics_sections.get('ethtool -m {}'.format(interface))
            for index, section_tuple in enumerate(eth_s):
                timestamp = section_tuple[0]
                parsed = _parse_ethtool_lines(section_tuple[1])
                if eth_d:
                    parsed.update(_parse_ethtool_lines(eth_d[index][1]))
                if eth_m:
                    parsed.update(_parse_ethtool_lines(eth_m[index][1]))
                temp[timestamp][interface] = parsed
        condensed = []
        for timestamp in temp:
            condensed.append((timestamp, temp[timestamp]))
        return condensed

    def get_finddrive_all(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get find_drive information."""
        find_drive = self.diagnostics_sections.get(r'find_drive.py all')
        parsed = []
        for timestamp, lines in find_drive:
            parsed.append((timestamp, hardware_utils.parse_finddrive(lines)))
        return parsed

    def get_hardware_check(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get hardware_check.py information."""
        checks = self.diagnostics_sections.get(r'hardware_check.py')
        parsed = []
        for timestamp, lines in checks:
            parsed.append((timestamp, hardware_utils.parse_hardware_check(lines)))
        return parsed

    def get_parity(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array parity per timestamp."""
        return self._pull_from('purearray list --space', keys=['Parity'])

    def get_portal_state_info(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'psctl -s'."""
        # Example of raw portal state information:
        # portal state = 200c6, gen = 0x214, primary = 1
        # OPEN, DEVIO_READY, RW_READY, SYS_VOL_ALLOWED
        sections = self.diagnostics_sections.get(r'psctl -s')
        parsed = []
        for timestamp, lines in sections:
            portal_state = {'info': []}
            for line in lines:
                chunks = line.split(',')
                for chunk in chunks:
                    if '-' * 72 in chunk:
                        continue
                    elif '=' in chunk:
                        name, value = chunk.split('=')
                        # TODO: PT-1794 - Create a proper portal state translator.
                        portal_state[name.strip()] = value.strip()
                    elif chunk.strip():
                        portal_state['info'].append(chunk.strip())
            parsed.append((timestamp, portal_state))
        return parsed

    def get_pgroup_snap_count(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get a count of pgroup related snapshots."""
        results = []
        pgroup_snaps = self.diagnostics_sections.get('purepgroup list --space --total')
        # The number of lines per timestamp will reflect the number of snapshots.
        # Subtract 1 due to the (total) line per timestamp.
        # Subtract 1 due to the header line.
        for timestamp, lines in pgroup_snaps:
            snapshots = _filter_stripped(lines)
            results.append((timestamp, len(snapshots) - 2))
        return results

    def get_physical_memory(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get information about the physical RAM on the controller."""
        hardware_sections = self.get_hardware_check()
        parsed = []
        for timestamp, section_dict in hardware_sections:
            # ['MemTotal:       528336320 kB\n'] -> '528336320 KB' -> 528336320000.0
            value = section_dict['RAM'][0].split(':')[1].upper()
            parsed.append((timestamp, int(format_utils.to_raw(value))))
        return parsed

    def get_purealert_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purealert list'."""
        return self._pull_from('purealert list')
    
    def get_purearray_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list'."""
        return self._pull_from(r'purearray list')

    def get_purearray_list_connect(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --connect'."""
        return self._pull_from(r'purearray list --connect')

    def get_purearray_list_controller(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --controller'."""
        return self._pull_from(r'purearray list --controller')

    def get_purearray_list_ntpserver(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --ntpserver'."""
        return self._pull_from(r'purearray list --ntpserver')

    def get_purearray_list_phonehome(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --phonehome'."""
        return self._pull_from(r'purearray list --phonehome')

    def get_purearray_list_relayhost(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --relayhost'."""
        return self._pull_from(r'purearray list --relayhost')
    
    def get_security_token(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --security-token'."""
        return self._pull_from(r'purearray list --security-token', ['Status'])
   

    def get_purearray_list_sender(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --sender'."""
        return self._pull_from(r'purearray list --sender')

    def get_purearray_list_space(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purearray list --space'."""
        keys = ['Capacity', 'Shared Space', 'Snapshots', 'System', 'Total', 'Volumes']
        return self._pull_from(r'purearray list --space', convert_to_raw=keys)

    def get_puredb_dedup_version(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb dedup version'."""
        return self._pull_from(r'puredb dedup version')

    def get_puredb_npiv_status(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb npiv status'."""
        return self._pull_from(r'puredb npiv status')

    def get_puredb_npiv_supported(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb npiv supported'."""
        return self._pull_from(r'puredb npiv supported')

    def get_puredb_stats_crawler(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb stats crawler'."""
        return self._pull_from(r'puredb stats crawler')

    def get_puredb_list_apartment_mappings(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb list apartment_mappings'."""
        return self._pull_from(r'puredb list apartment_mappings')

    def get_puredb_list_reservation(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb list reservation'."""
        return self._pull_from('puredb list reservation')

    def get_puredb_list_tunable_diff(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb list tunable --diff'."""
        return self._pull_from(r'puredb list tunable --diff')

    def get_puredb_list_tunable_platform_diff(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb list tunable --platform --diff'."""
        return self._pull_from(r'puredb list tunable --platform --diff')

    def get_puredb_messaging_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb messaging list'."""
        return self._pull_from('puredb messaging list')

    def get_puredb_replication_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredb replication list'."""
        keys = ['Bytes Received', 'Bytes Sent', 'Inline Dup Bytes', 'Physical Bytes Written',
                'Transport Dup Bytes']
        return self._pull_from(r'puredb replication list', convert_to_raw=keys)

    def get_puredns_list_all(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredns list --all'."""
        return self._pull_from('puredns list --all')

    def get_puredrive_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puredrive list --total'."""
        return self._pull_from('puredrive list --total', convert_to_raw=['Capacity'])

    def get_pureds_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'pureds list'."""
        return self._pull_from(r'pureds list')

    def get_pureds_list_groups(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'pureds list --groups'."""
        return self._pull_from(r'pureds list --groups')

    def get_purehost_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purehost list'."""
        return self._pull_from('purehost list')

    def get_purehost_list_connect(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purehost list --connect'."""
        return self._pull_from(r'purehost list --connect')

    def get_purehgroup_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purehgroup list'."""
        return self._pull_from('purehgroup list')

    def get_purehgroup_list_connect(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purehgroup list --connect'."""
        return self._pull_from(r'purehgroup list --connect')

    def get_purehw_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purehw list --all'."""
        parsed = []
        sections = self.diagnostics_sections.get(r'purehw list --all')
        for timestamp, section in sections:
            purehw_parsed = hardware_utils.parse_purehw_list(section)
            parsed.append((timestamp, purehw_parsed))
        return parsed

    def get_purenetwork_list_all(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purenetwork list --all'."""
        return self._pull_from('purenetwork list --all')

    def get_purepgroup_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purepgroup list'."""
        return self._pull_from('purepgroup list')

    def get_purepgroup_list_retention(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purepgroup list --retention'."""
        return self._pull_from('purepgroup list --retention')

    def get_purepgroup_list_schedule(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purepgroup list --schedule'."""
        return self._pull_from('purepgroup list --schedule')

    def get_purepgroup_list_snap_space_total(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purepgroup list --snap --space --total'."""
        return self._pull_from(r'purepgroup list --snap --space --total', convert_to_raw=['Snapshots'])

    def get_purepgroup_list_snap_transfer(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purepgroup list --snap --transfer'."""
        keys = ['Physical Bytes Written', 'Data Transferred']
        return self._pull_from(r'purepgroup list --snap --transfer', convert_to_raw=keys)

    def get_purepgroup_list_space_total(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purepgroup list --space --total'."""
        return self._pull_from(r'purepgroup list --space --total', convert_to_raw=['Snapshots'])

    def get_pureport_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'pureport list'."""
        return self._pull_from(r'pureport list')

    def get_pureport_list_initiator(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'pureport list --initiator'."""
        return self._pull_from(r'pureport list --initiator')

    def get_puresnmp_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puresnmp list'."""
        return self._pull_from(r'puresnmp list')

    def get_puresubnet_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'puresubnet list'."""
        return self._pull_from(r'puresubnet list')

    def get_purevol_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purevol list'."""
        return self._pull_from(r'purevol list', convert_to_raw=['Size'])

    def get_purevol_list_connect(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purevol list --connect'."""
        return self._pull_from(r'purevol list --connect', convert_to_raw=['Size'])

    def get_purevol_list_snap(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purevol list --snap'."""
        return self._pull_from(r'purevol list --snap', convert_to_raw=['Size'])

    def get_purevol_list_space_total(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the contents of 'purevol list --space --total'."""
        keys = ['System', 'Volume', 'Total', 'Shared Space', 'Snapshots', 'Size']
        return self._pull_from(r'purevol list --space --total', convert_to_raw=keys)

    def get_purity_version(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the purity_version per timestamp."""
        return self._pull_from('purearray list', ['Version'])

    def get_shared_space(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array shared_space per timestamp."""
        return self._pull_from('purearray list --space', ['Shared Space'], convert_to_raw=['Shared Space'])

    def get_snapshot_space(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array snapshot_space per timestamp."""
        return self._pull_from('purearray list --space', ['Snapshots'], convert_to_raw=['Snapshots'])

    def get_ssd_capacity(self):
        # type: () -> List[Tuple[Any, Any]]
        """Estimate ssd_capacity based upon drives in puredrive list."""
        all_ssd_capacity = []
        for timestamp, drive_info in self.get_puredrive_list():
            ssd_capacity = 0
            dtype = drive_info['Type']
            for index, device_type in enumerate(dtype):
                # Only use healthy SSD devices:
                if device_type != 'SSD' or drive_info['Status'][index] != 'healthy':
                    continue
                ssd_capacity += int(drive_info['Capacity'][index])
            all_ssd_capacity.append((timestamp, ssd_capacity))
        return all_ssd_capacity

    def get_system_space(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array system_space per timestamp."""
        return self._pull_from('purearray list --space', ['System'], convert_to_raw=['System'])

    def get_thin_provisioning(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array thin_provisioning per timestamp."""
        return self._pull_from('purearray list --space', ['Thin Provisioning'])

    def get_timezone(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array timezone."""
        parsed = []
        sections = self.diagnostics_sections.get(r'cat /etc/timezone')
        for timestamp, section in sections:
            timezone = None
            for line in section:
                timezone = line.strip()
                break
            parsed.append((timestamp, timezone))
        return parsed

    def get_total_reduction(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array total_reduction per timestamp."""
        return self._pull_from('purearray list --space', ['Total Reduction'])

    def get_tunables(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the tunables currently set on this controller."""
        pureadm = self.diagnostics_sections.get('pureadm list-tunable')
        parsed = []
        for timestamp, lines in pureadm:
            parsed.append((timestamp, _parse_tunable_lines(lines)))
        return parsed

    def get_volume_space(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the array volume_space per timestamp."""
        return self._pull_from('purearray list --space', ['Volumes'], convert_to_raw=['Volumes'])


def _parse_ethtool_lines(lines):
    # type: (List[str]) -> Dict[str, Any]
    """Parse lines from ethtool."""
    parsed = {}
    # 0x00400: TCTL (Transmit ctrl register)                0xA50400FA
    # 0x0406C: PRC1023     (Packets rx (512-1023 B) count)  0x028BB3DF
    style1 = re.compile(r'\s+?0x\w+:\s+(?P<short_name>\w+).*(?P<count>0x\w+)')
    #        Transmitter:                                   enabled
    #        Pad short packets:                             enabled
    #        Software XOFF Transmission:                    disabled
    #        Re-transmit on late collision:                 enabled
    #        rx_bytes_nic: 113596530521057
    style2 = re.compile(r'\s+?(?P<name>.*?):\s+(?P<value>enabled|disabled|\d+)')
    for line in lines:
        # ERROR: command failed with exit code 1
        # Output: Cannot get module EEPROM information: Input/output error
        if 'ERROR: command failed with exit code 1' in line:
            break
        match = style1.match(line)
        if match:
            value = match.group('value').strip()
            if '0x' in value:
                # Cut off the 0x and convert the value from hex to an int.
                value = int(value[2:], 16)
            parsed[match.group('name').strip()] = value
            continue
        match = style2.match(line)
        if match:
            value = match.group('value').strip()
            if value == 'enabled':
                value = True
            elif value == 'disabled':
                value = False
            else:
                value = int(value)
            parsed[match.group('name').strip()] = value
    return parsed


def _parse_tunable_lines(lines):
    # type: (List[str]) -> Dict[str, Any]
    """Parse tunable lines into a dictionary of tunables and their respective values."""
    parsed = {}
    # PS_POSTMAN_THREAD_FORK_ALL                boolean   1      0       Fork ASIO thread on all IO cpus
    style1 = re.compile(r'(?P<tunable>\w+)\s+(?P<type>boolean|unsigned)\s+(?P<value>\w+)')
    # PS_DEDUP_POST_UPGRADE_PER_SEG_DELAY_MSEC=500 # ES-29531
    style2 = re.compile(r'(?P<tunable>\w+)=(?P<value>\w+)\s+\#')
    for line in lines:
        match = style1.match(line)
        if match:
            value = match.group('value').strip()
            if match.group('type') == 'boolean':
                value = bool(value)
            elif value.isdigit():
                value = int(value)
            parsed[match.group('tunable').strip()] = value
            continue
        match = style2.match(line)
        if match:
            value = match.group('value').strip()
            parsed[match.group('tunable').strip()] = value
    return parsed


def _filter_stripped(lines):
    # type: (List[str]) -> List[str]
    """Filter out lines for '\n' and '' and section separators."""
    skip = (
        '-' * 72,
    )
    return [line for line in lines if line.strip() and not line.startswith(skip)]


def _parse_table_lines(lines, headers=None):
    # type: (List[str], Optional[List[str]]) -> Dict[Any]
    """Parse the lines of a diagnostics section into a dictionary.

    Arguments:
        lines (list):  A list of strings.
        headers (list): A header to use for dictionary keys (if one does not exist for this section).

    Returns:
        table (dict): The parsed section in a tabular format.
    """
    table = collections.defaultdict(list)
    # Assumption: All sections are delimited by 2 or more spaces.
    split_lines = [re.split(r'\s{2,}', line.strip()) for line in lines if line.strip()]
    if not split_lines:
        return dict(table)
    headers = headers or split_lines[0]
    # If the header was given, and not from line 0, we can't know its line location(s).
    # Create a mapping of where each header begins within the headers line:
    header_line = lines[0]
    header_loc = {header: header_line.find(header) for header in headers}

    # Now process each line by checking what data exists at that starting point; when the number of data points does
    # not match the number of headers.  Assumption: We won't accidentally have the same number in the wrong positions...
    for line_index, line in enumerate(split_lines[1:]):
        if len(line) != len(headers):
            text_line = lines[line_index + 1]
            # We need to slice this line according to the header locations:
            line = _slicer(text_line, sorted(header_loc.values()))
        for index, value in enumerate(line):
            if not value:
                continue
            table[headers[index]].append(value)

    # Flatten scalar values.
    for key, value in iteritems(table):
        if len(value) == 1:
            table[key] = value[0]
    return dict(table)


def _slicer(text, slices):
    # type: (str, List[Any]) -> List[str]
    """Slice up a string into multiple pieces defined by a list of indexes."""
    # Note it slices from 0 -> 1, from 1 -> 2, and so on.  The last one gets from itself to the end.
    pieces = []
    for index, slice_value in enumerate(slices):
        if index < len(slices) - 1:
            next_slice = slices[index + 1]
            piece = text[slice_value:next_slice]
        else:
            piece = text[slice_value:]
        value = piece.strip()
        if not value and piece != '\n':
            value = '-'
        pieces.append(value)
    return pieces
