"""Common library for parsing the content of sas_view.py from the FlashArray."""

from __future__ import print_function

import codecs
import logging
import re
import six

from collections import defaultdict

from photon.lib import format_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import DefaultDict
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple
    from typing import Union
except ImportError:
    pass

logger = logging.getLogger(__name__)
# Setting global patterns because we only want to compile them once instead of for both controllers.
# Example: |--Port 0
SAS_PORT = re.compile(r'--Port\s+(?P<sas_port>\d+)')
# Example: | | |-Link  0: (500605b005a728d4:04)(0005), (00000, 00000, 00000, 00000) <- 6.0-> (50050cc117fab0ff:03)(0009)
PCI_SAS_ADDRS = re.compile(r'Link\s+\d+:\s+\((?P<address>\w+).*?->\s+\((?P<outgoing>\w+)')
# Example: | |-SH01, IOM 0, Incoming port: A
# Note: Shelf names ("Shelf 01" in the above example) were changed for Platinum to use
#       different prefixes to distinguish between the chassis and external shelves. There was
#       a bug in old hw_utils.py that caused it not to use these prefixes and continue using
#       "Shelf XX". This bug was fixed for Broadwell, so newer versions of Purity should
#       report the name as "CCXX" or "SHXX" instead. See MISC-2920 for more information.
SHELF_INFO = re.compile(r'(?P<shelf_id>(Shelf\s+|SH|CC)\d+),\s+IOM\s+(?P<iom>\d),\s+\w+\s+\w+:\s+(?P<port>\w+)')
# This line is to gather any IOM ports which will include 'Link down' also.
# With that we can use the next regex to get the lines that have the additional info we need.
IOM_PORT_NAME_LINE = re.compile(r'Port\s+(?P<name>\w+):\s+\((?P<address>\w+):')
# Example: | | |--Port A: (50050cc117fab0ff:08)(0009), (00000, 00000, 00000, 00000) <- 6.0-> (500605b005a728c0:03)(000a)
IOM_SAS_OUT = re.compile(r'\(\w+:\d+\).*?->\s+\((?P<outgoing>\w+)')
# Example: SH 0, IOM 0 port B: SAS IOM port is cabled to wrong IOM on next enclosure.
SHELF_SAS_ERROR = re.compile(r'SH(\s+|)(?P<shelf>\d+)(,|)\s+IOM\s+(?P<iom>\d)(,|)(\s+[pP]ort\s+(?P<port>\w)|)')
# Example1: Slot 101, port 1: SAS HBA port is cabled to wrong enclosure IOM.
# Example2: Slot 201, port 0: Unexpected enclosure ID. Enclosure ID is set to 3, and not the expected ID of 4.
CTLR_SAS_ERROR = re.compile(r'(?P<slot>Slot\s+\d+)(,|)\s+[pP]ort\s+(?P<port>\w)')


class SASView(object):
    """Container for all sas_view.py sections and details."""

    def __init__(self, sas_view_lines, controller):
        # type: (List[str], str) -> None
        """Instantiate a SASView object to present sas_view.py sections.

        Argument:
            sas_view_lines (List[str]): The output from the 'sas_view' field.
            controller (str): The FlashArray controller. (eg: 'CT0' or 'CT1')
        """
        # pylint: disable=too-many-instance-attributes
        self.controller = controller.upper()
        if self.controller not in ('CT0', 'CT1'):
            msg = 'accepted controllers "CT0" or "CT1", recieved "{}"'.format(self.controller)
            logger.exception(msg)
            raise ValueError(msg)
        logger.info('Parsing sas_view.py lines for {}.'.format(controller))
        self._section_dict = get_sasview_sections(sas_view_lines)
        self.enclosures = self._get_safe_lines('enclosures')  # type: List[str]
        self._enclosures_dict = defaultdict(list)  # type: DefaultDict[str, Any]
        self.diag_topology_all = self._get_safe_lines('diag topology all')  # type: List[str]
        if not self.diag_topology_all:
            # storage_view output removes the need for the word diag from topology all output.
            self.diag_topology_all = self._get_safe_lines('topology all')  # type: List[str]
        self._diag_topology_all_dict = defaultdict(list)  # type: DefaultDict[str, Any]
        self.config = self._get_safe_lines('config')  # type: List[str]
        self._config_dict = defaultdict(list)  # type: DefaultDict[str, Any]
        self.reset_cnts_all = self._get_safe_lines('reset_cnts all')  # type: List[str]
        self._reset_cnts_all_dict = defaultdict(list)  # type: DefaultDict[str, Any]

    @property
    def enclosures_dict(self):
        # type: () -> DefaultDict[str, Any]
        """Sas_view 'enclosures' in dictionary format."""
        if not self._enclosures_dict:
            sub_sections = [
                'Command line',
                'Revision',
                'Error information',
                'End time',
                'Start time',
            ]
            partials = ['Enclosure information']
            self._enclosures_dict = _get_sub_sections(self.enclosures, sub_sections, partials)
            keys = ['Command line', 'Revision', 'Start time', 'End time']
            self._enclosures_dict = _get_single_value_keys(self._enclosures_dict, keys)
        return self._enclosures_dict

    @property
    def diag_topology_all_dict(self):
        # type: () -> DefaultDict[str, Any]
        """Sas_view 'diag topology all' in dictionary format."""
        if not self._diag_topology_all_dict:
            sub_sections = [
                'Command line',
                'Revision',
                'Slot listing',
                'Slot summary',
                'Configuration status',
                'Error information',
                'End time',
                'Start time',
            ]
            # In storage_view output 'information' is spelled 'inforamtion'.
            partials = ['Topology information for slot', 'Topology inforamtion for slot']
            self._diag_topology_all_dict = _get_sub_sections(self.diag_topology_all, sub_sections, partials)
            keys = ['Command line', 'Revision', 'Start time', 'End time']
            self._diag_topology_all_dict = _get_single_value_keys(self._diag_topology_all_dict, keys)
        return self._diag_topology_all_dict

    @property
    def config_dict(self):
        # type: () -> DefaultDict[str, Any]
        """Sas_view 'config' in dictionary format."""
        if not self._config_dict:
            sub_sections = [
                'Command line',
                'Revision',
                'Slot listing',
                'Slot summary information',
                'Configuration status',
                'Error information',
                'End time',
                'Start time',
            ]
            self._config_dict = _get_sub_sections(self.config, sub_sections)
            keys = ['Command line', 'Revision', 'Start time', 'End time']
            self._config_dict = _get_single_value_keys(self._config_dict, keys)
        return self._config_dict

    @property
    def reset_cnts_all_dict(self):
        # type: () -> DefaultDict[str, Any]
        """Sas_view 'reset_cnts all' in dictionary format."""
        if not self._reset_cnts_all_dict:
            sub_sections = [
                'Command line',
                'Revision',
                'Slot listing',
                'End time',
                'Start time'
            ]
            # Pulls sub-section: 'Slot #: PHY error counters have been reset.'
            partials = ['Slot ']
            self._reset_cnts_all_dict = _get_sub_sections(self.reset_cnts_all, sub_sections, partials)
            keys = ['Command line', 'Revision', 'Start time', 'End time']
            self._reset_cnts_all_dict = _get_single_value_keys(self._reset_cnts_all_dict, keys)
        return self._reset_cnts_all_dict

    def _get_safe_lines(self, section):
        # type: (str) -> List[str]
        """Get the lines from the specified section if the section exists."""
        section_lines = self._section_dict.get(section, [])  # type: List[str]
        if not section_lines:
            logger.error('Unable to get "{}" lines from sasview output'.format(section))
        return section_lines

    def get_sas_topology(self):
        # type: () -> DefaultDict[str, DefaultDict[str, DefaultDict[str, Any]]]
        """Create a mapping of the SAS ports on the controller from diag_topology_all_dict."""
        topology = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))  # type: DefaultDict[str, DefaultDict[str, DefaultDict[str, Any]]]
        sas_port = None
        # Sorting the keys so that the PCI slots are in order.
        # This helps with SAS port numbers later on.
        for key in sorted(six.iterkeys(self.diag_topology_all_dict)):
            # We only need keys that start with Topology.
            # Example of the needed key: 'Topology information for slot 2'
            if not key.startswith('Topology'):
                continue
            pci_slot = 'SLOT {}'.format(key.split()[-1])
            for line in self.diag_topology_all_dict[key]:
                if not line:
                    continue
                match = SAS_PORT.search(line)
                if match:
                    sas_port = 'SAS{}'.format(match.group('sas_port'))
                    continue
                if not sas_port:
                    # There are lines that show up before the sas port. These are not needed.
                    continue
                # Each sas port has its own pci sas addresses.
                if 'pci_sas_addr' not in six.iterkeys(topology[pci_slot][sas_port]):
                    topology[pci_slot][sas_port]['pci_sas_addr'] = set()
                if 'pci_sas_out' not in six.iterkeys(topology[pci_slot][sas_port]):
                    topology[pci_slot][sas_port]['pci_sas_out'] = set()
                match = PCI_SAS_ADDRS.search(line)
                if match:
                    # Addressses to and from the shelf.
                    topology[pci_slot][sas_port]['pci_sas_addr'].add(match.group('address'))
                    topology[pci_slot][sas_port]['pci_sas_out'].add(match.group('outgoing'))
                    continue
                match = SHELF_INFO.search(line)
                if match and 'incoming' in line.lower():
                    # Replacing 'Shelf ' with 'SH' for uniform output.
                    # Most arrays in the field will not have the full word.
                    shelf_name = match.group('shelf_id').replace('Shelf ', 'SH')
                    topology[pci_slot][sas_port][shelf_name]['iom'] = 'IOM{}'.format(match.group('iom'))
                    topology[pci_slot][sas_port][shelf_name]['iom_port'] = match.group('port')
                match = IOM_PORT_NAME_LINE.search(line)
                if match:
                    # This is the name of the port: A, B, C
                    out_name = match.group('name')
                    # Create a new Set[str] for the out_name and/or the 'iom_sas_addr'.
                    # Ensures there is a new set for each shelf.
                    if 'iom_sas_addr' not in six.iterkeys(topology[pci_slot][sas_port][shelf_name]):
                        topology[pci_slot][sas_port][shelf_name]['iom_sas_addr'] = set()
                    if out_name not in six.iterkeys(topology[pci_slot][sas_port][shelf_name]):
                        topology[pci_slot][sas_port][shelf_name][out_name] = set()
                    # Adding items to the set where applicable.
                    topology[pci_slot][sas_port][shelf_name]['iom_sas_addr'].add(match.group('address'))
                    match = IOM_SAS_OUT.search(line)
                    if match:
                        topology[pci_slot][sas_port][shelf_name][out_name].add(match.group('outgoing'))
        return topology


class SASCabling(object):
    """Parse output of sas_view.py to create a mapping of ports on controllers and shelves."""

    # Any line with the conn_str indicates a connection from [C:0.0:A] <---> [B:1.0:A*.
    conn_str = ' <---> '
    # HBAs example: '2.0]' OR '2.1*'
    hba_regex = re.compile(r'(?P<hba>\d+\.\d)(\]|\*)')
    # HBA to ignore: '[3.0'  (These are the same as '[Unknown device')
    hba_regex_rev = re.compile(r'\[\d+\.\d')
    # Shelf and IOM example: '[C:0.0:A]' == [iom_port_in:shelf.iom:iom_port_out]
    iom_regex = re.compile(r'(?P<iom_port_in>\w):(?P<shelf>\d+).(?P<iom>\d)(:(?P<iom_port_out>\w))?')
    # Extra IOM port whih may connect to something: '\B]'
    extra_iom_regex = re.compile(r'\\(?P<ex_iom_port_out>\w)')

    def __init__(self, array_api, add_color=False):
        # type: (Any, Optional[bool]) -> None
        """Make SAS topology simple.

        Argument:
            array_api (photon.api.FlashArray): A FlashArray object to get sas_view field contents.
        """
        # pylint: disable=too-many-instance-attributes
        self._add_color = add_color
        self.array_api = array_api
        self.shelves = set()  # type: Set[str]
        # Dict of: controller -> Slot # -> Port #
        self.array_ports = defaultdict(lambda: defaultdict(set))  # type: DefaultDict[str, DefaultDict[str, Set[str]]]
        self.sas_errors = defaultdict(list)  # type: DefaultDict[str, List[str]]
        self.controllers = set()  # type: Set[str]
        self.ctlr_models = {}  # type: Dict[str, str]
        self.iom_port_num = {
            'IOM0': {'A': 'SAS0', 'B': 'SAS1', 'C': 'SAS2'},
            'IOM1': {'A': 'SAS5', 'B': 'SAS4', 'C': 'SAS3'},
        }  # type: Dict[str, Dict[str, str]]
        # ctlr_port_num is built out based on the array ports.
        # It is in the same format as iom_port_num.
        self.ctlr_port_num = defaultdict(lambda: defaultdict(dict))  # type: DefaultDict[str, DefaultDict[str, Dict[str, str]]]
        self._from_ports = set()  # type: Set[str]
        self.parsed_errors = defaultdict(list)  # type: DefaultDict[str, List[str]]
        self.sasview = {}  # type: Dict[str, Any]
        self.sas_cabling_map = []  # type: List[Dict[str, str]]
        self.visual = []  # type: List[str]
        self.ha_sas = defaultdict(dict)  # type: DefaultDict[str, Dict[str, Any]]
        self.hba_chain_map = {}  # type: Dict[str, List[str]]

    def get_array_topology(self, sas_view_df=None):
        # type: (Optional[Any]) -> List[Dict[str, str]]
        """Generate the SAS cabling topology for the FlashArray controllers.

        Argument:
            sas_view_df (pandas.DataFrame): DataFrame with required fields. [for test cases]
        """
        if sas_view_df is None:
            sas_view_df = self.array_api.get_fields(['sas_view', 'controller_model'])
        if sas_view_df['sas_view'].dropna().empty:
            msg = 'Unable to locate any sas_view/storage_view output.'
            logger.exception(msg)
            raise ValueError(msg)
        # Reversing the DataFrame order to get the latest sas_view/storage_view data first.
        sas_view_df = sas_view_df.iloc[::-1]
        for row in sas_view_df[['controller_model', 'controller']].dropna().itertuples():
            controller = row.controller
            if controller in six.iterkeys(self.ctlr_models):
                # Skip if controller already processed.
                continue
            model = row.controller_model
            self.ctlr_models[controller] = model.get(controller)
        # When asking for different fields there can be NaN rows.
        for row in sas_view_df[['sas_view', 'controller']].dropna().itertuples():
            controller = row.controller
            if controller in self.controllers:
                # Skip if controller already processed.
                continue
            sas_view_lines = row.sas_view
            self.controllers.add(controller)
            logger.debug('Creating SASView object for {}.'.format(controller))
            self.sasview[controller] = SASView(sas_view_lines, controller)
            logger.info('Processing sas topology for {}.'.format(controller))
            self._get_errors(controller)
            config_dict = self.sasview[controller].config_dict
            slot_summary = config_dict.get('Slot summary information', [])
            self._parse_slot_summary(slot_summary, controller)
        return self.sas_cabling_map

    def _get_errors(self, controller):
        # type: (str) -> List[str]
        """Collect all errors from the different sections and add them to self.sas_errors."""
        info_dicts = [
            self.sasview[controller].config_dict,
            self.sasview[controller].enclosures_dict,
            self.sasview[controller].diag_topology_all_dict,
        ]
        for info in info_dicts:
            errors = info.get('Error information')
            if errors:
                # Removing empty lines from the output.
                # The below output is expected when there are no errors.
                # It is better to have an empty list than one reporting no errors.
                safe_lines = ['No errors detected', 'Attached device is unknown']
                error_info = []
                for line in errors:
                    if not line or any(safe in line for safe in safe_lines):
                        continue
                    error_info.append(line)
                self.sas_errors[controller].extend(error_info)
        return self.sas_errors

    def _parse_slot_summary(self, lines, controller):
        # type: (List[str], str) -> Dict[str, Dict[str, Union[List[str], str]]]
        """Parse the Slot Summary from sasview config or topology."""
        bad_conn_str = ' <-!-> '
        good_conn_str = ' <---> '
        current_hba = None
        out_conn = None
        ctlr_hbas = {}  # type: Dict[str, Dict[str, Union[List[str], str]]]
        # Keeping track of how many ports per controller. Used to make SAS# for visual.
        port_num = 0
        for line in lines:
            # There are things that can be ignored.
            # Empty lines.
            # The index and spacer whose line starts with ('s.p ' or '-').
            # And Slot 0 which is a chassis shelf and has no SAS.
            # And ct0.eth0 lines are not SAS so they are ignored.
            if not line or line.startswith(('s.p ', '-', '0.', 'ct')):
                continue
            if bad_conn_str in line:
                conn_str = bad_conn_str
            else:
                conn_str = good_conn_str
            hba_match = self.hba_regex.search(line)
            # If no connections found then the line is ignored.
            # Only ports with connections are tracked. Any other port is implicitly not connected.
            if hba_match or conn_str in line:
                if hba_match:
                    # Matches the below possible types of lines.
                    # hba.port*
                    # hba.port] <---> iom1
                    # hba.port] <---> iom1 <---> iom2
                    hba = hba_match.group('hba')
                    if current_hba != hba:
                        current_hba = hba
                        slot_name, port_name = self._add_array_port(hba, controller, port_num)
                        ctlr_hbas[current_hba] = {
                            'slot': slot_name,
                            'port': port_name,
                            'chain': [],
                            'conn': [],
                        }
                        port_num += 1
                        out_conn = None
                    # Using [1:] gets everything but the HBA which is not needed here.
                    for item in line.split(conn_str)[1:]:
                        iom_match = self.iom_regex.search(item)
                        rev_hba_match = self.hba_regex_rev.match(item)
                        if iom_match:
                            out_conn = self._iom_match(iom_match, ctlr_hbas, current_hba, out_conn)
                        elif item.startswith('[Unknown device') and not rev_hba_match:
                            # This should only happen at the end of a chain.
                            # Anything that might follow this we can ignore.
                            break
                        elif rev_hba_match:
                            # ES-27129: This means there is potentially an illegal topology.
                            # More information about this can be found here:
                            # https://wiki.purestorage.com/pages/viewpage.action?pageId=46942600
                            message = 'Possible illegal topology on {}!! Consult PSE for guidance.'.format(current_hba)
                            self.parsed_errors[controller].append(message)
                else:
                    # Can only get here if we already have current_hba set.
                    #   iom1 <---> iom3
                    #   |  iom2 <---> iom3
                    offset = line.count('|')
                    items = re.split(conn_str, line.strip('| \t'))
                    if current_hba not in ctlr_hbas:
                        raise KeyError('current_hba "{}" not found in ctlr_hbas dict.'.format(current_hba))
                    prev_port = ctlr_hbas[current_hba]['conn'][offset]
                    if not prev_port:
                        raise ValueError('prev_port not found on {}'.format(current_hba))
                    for item in items:
                        iom_match = self.iom_regex.search(item)
                        rev_hba_match = self.hba_regex_rev.match(item)
                        if iom_match:
                            out_conn = self._iom_match(iom_match, ctlr_hbas, current_hba, out_conn)
                        elif item.startswith('[Unknown device') and not rev_hba_match:
                            break
                        elif rev_hba_match:
                            # See previous comment about this situation for more information.
                            message = 'Possible illegal topology on {}!! Consult PSE for guidance.'.format(current_hba)
                            self.parsed_errors[controller].append(message)
                        else:
                            extra_conn = self.extra_iom_regex.search(item)
                            if extra_conn and not item.endswith('*'):
                                out_conn = '.'.join([prev_port, extra_conn.group('ex_iom_port_out')])
        if ctlr_hbas:
            self._build_sas_cabling_map(ctlr_hbas, controller)
        return ctlr_hbas

    def _add_array_port(self, hba_port, controller, port_num):
        # type: (str, str, int) -> Tuple[str, str]
        """Add the HBAs and HBA ports to each controller."""
        slot, port = hba_port.split('.')
        slot_name = 'SLOT {}'.format(slot)
        port_name = 'SAS{}'.format(port_num)
        # Creating a mapping for controller ports to be referenced later when building the visual.
        # This is also used when parsing the error messages.
        self.ctlr_port_num[controller][slot_name][port] = port_name
        # Adding the nice port name to the nice slot name on the specific controller to make
        # building the visual easier.
        self.array_ports[controller][slot_name].add(port_name)
        return slot_name, port_name

    def _iom_match(self, iom_match, ctlr_hbas, current_hba, out_conn):
        # type: (Any, Dict[str, Dict[str, Union[List[str], str]]], Optional[str], Optional[str]) -> Optional[str]
        """Get the matching Shelf##.IOM#.Port connection."""
        # iom_match is the result of a regex_pattern.search(line) using the self.iom_regex pattern.
        if current_hba not in ctlr_hbas:
            raise KeyError('current_hba "{}" not found in ctlr_hbas dict.'.format(current_hba))
        shelf_num = iom_match.group('shelf')
        # Converting single digit values to be padded with a leading zero for uniformity.
        shelf_num = '{:0>2}'.format(shelf_num)
        shelf = ''.join(['SH', shelf_num])
        # Building the IOM# text.
        iom_num = iom_match.group('iom')
        iom = ''.join(['IOM', iom_num])
        # Building the in and out connections.
        in_port = iom_match.group('iom_port_in')
        out_port = iom_match.group('iom_port_out')
        connection = '.'.join([shelf, iom, in_port])
        # Indicating what shelf connections there are on this line.
        # This is used later for the trailing '\B]' connections.
        sh_conn = '.'.join([shelf, iom])
        # Using "type: ignore" as MyPy cannot infer Dict[str, Union[List[str], str]] to allow the
        # use of append on keys that only ever List[str].
        if sh_conn not in ctlr_hbas[current_hba]['conn']:
            ctlr_hbas[current_hba]['conn'].append(sh_conn)  # type: ignore
        # The out_conn can be None which means it has not been set yet.
        # We add it to the chain if it has been set.
        if out_conn:
            ctlr_hbas[current_hba]['chain'].append(out_conn)  # type: ignore
        ctlr_hbas[current_hba]['chain'].append(connection)  # type: ignore
        # Update the out_conn from what it was to what the current iom_match says it is now.
        out_conn = '.'.join([shelf, iom, out_port])
        return out_conn

    def _build_sas_cabling_map(self, ctlr_hbas, controller):
        # type: (Dict[str, Dict[str, Union[List[str], str]]], str) -> List[Dict[str, str]]
        """Build the sas_cabling_map which is used to map ports in the visual."""
        for key in sorted(ctlr_hbas):
            # Using "type: ignore" due to previously mentioned issues in MyPy.
            chain = ctlr_hbas[key]['chain']  # type: ignore
            # Setting the below to strings because MyPy complains if not done.
            slot = str(ctlr_hbas[key]['slot'])
            port = str(ctlr_hbas[key]['port'])
            shelf_connections = {
                'controller': controller,
                'slot': slot,
            }
            # How this works:
            # chain == [Conn1, Conn2, Conn3]
            # Conn1 is connected to the controller.
            # Conn2 is connected to Conn3.
            # NOTE: There should only be two shelves connected to a single HBA port.
            chain_leng = 0
            for index, item in enumerate(chain):
                nice_name = self._convert_name(item)
                # If the index is 0 it means that the previous connection is the controller port.
                # Using the below example the first item in the chain is connected to 100.0 which
                # is a controller port.
                # '100.0': defaultdict(list, {
                #    'chain': ['SH01.IOM1.C', 'SH01.IOM1.B', 'SH03.IOM1.A'],
                #    'conn': ['SH01.IOM1', 'SH03.IOM1'],
                #    'slot': 'SLOT 100',
                #    'port': 'SAS0'}),
                if index == 0:
                    ctlr_port = '.'.join([controller, port])
                    self.hba_chain_map[ctlr_port] = [nice_name]
                    shelf_connections['from'] = ctlr_port
                    shelf_connections['to'] = nice_name
                    shelf_connections['shelf_conn'] = item
                # Everything else in the chain is a shelf-to-shelf connection.
                else:
                    if not shelf_connections.get('from'):
                        shelf_connections['from'] = nice_name
                    elif shelf_connections.get('from') and not shelf_connections.get('to'):
                        shelf_connections['to'] = nice_name
                        shelf_connections['shelf_conn'] = item
                # Only add the connections if they are not already in the map.
                # Shelf to shelf mappings show up on both controllers and we only need one map.
                if shelf_connections.get('from') and shelf_connections.get('to'):
                    if shelf_connections not in self.sas_cabling_map:
                        self.sas_cabling_map.append(shelf_connections)
                        self.hba_chain_map[ctlr_port].append(shelf_connections['from'])
                        self.hba_chain_map[ctlr_port].append(shelf_connections['to'])
                        chain_leng += 1
                    # It is possible to have multiple connections in a single line.
                    # Resetting the shelf_connections to add a new connection.
                    shelf_connections = {
                        'controller': controller,
                        'slot': slot,
                    }
                    continue
            if chain_leng >= 3:
                message = 'Found "{}" connections on {}. Only two shelves allowed per chain.'.format(chain_leng, port)
                self.parsed_errors[controller].append(message)
        return self.sas_cabling_map

    def _convert_name(self, item):
        # type: (str) -> str
        """Convert 'SH01.IOM1.C' to 'SH01.SAS3' for visualization."""
        shelf, iom, port = item.split('.')
        # Building out the shelves that the array is connected to.
        self.shelves.add(shelf)
        sas_port = self.iom_port_num[iom].get(port, 'UNKN')
        nice_name = '.'.join([shelf, sas_port])
        return nice_name

    def generate_visual(self):
        # type: () -> List[str]
        """Generate the sas cabling visual based on the topology per controller sas_view."""
        # Setting up formatted tables.
        box_line = '+{}+'.format('-' * 79)
        line_fmt = '|  {:<75}  |'
        slot_fmt = '{:^13}'
        title_fmt = '[ {} ]'
        blank_line = line_fmt.format('')
        # The below SH00 example indicates how IOM ports are layed out.
        iom0_args = {'name': '0', 'p0': '0', 'p1': '1', 'p2': '2'}
        iom1_args = {'name': '1', 'p0': '3', 'p1': '4', 'p2': '5'}
        iom_fmt = 'IOM {name}  SAS{p0}:[{conn0}]  SAS{p1}:[{conn1}]  SAS{p2}:[{conn2}]'
        # Add an empty string to add padding around the output.
        logger.info('Building SAS cabling visual.')
        # Create formatted output for each shelf:
        # SH00
        # +-------------------------------------------------------------------------------+
        # |  IOM 0  SAS0:[  CT0.SAS0   ]  SAS1:[  SH02.SAS1  ]  SAS2:[  CT1.SAS3   ]      |
        # |                                                                               |
        # |  IOM 1  SAS3:[  CT0.SAS2   ]  SAS4:[  SH02.SAS4  ]  SAS5:[  CT1.SAS1   ]      |
        # +-------------------------------------------------------------------------------+
        for shelf in sorted(self.shelves, reverse=True):
            self.visual.append(title_fmt.format(shelf))
            self.visual.append(box_line)
            connected_ports = self._get_connections(shelf)
            iom0_args['conn0'] = slot_fmt.format(connected_ports.get('SAS0', ''))
            iom0_args['conn1'] = slot_fmt.format(connected_ports.get('SAS1', ''))
            iom0_args['conn2'] = slot_fmt.format(connected_ports.get('SAS2', ''))
            parts = iom_fmt.format(**iom0_args)
            self.visual.append(line_fmt.format(parts))
            # Adding a blank_line for visual spacing.
            self.visual.append(blank_line)
            iom1_args['conn0'] = slot_fmt.format(connected_ports.get('SAS3', ''))
            iom1_args['conn1'] = slot_fmt.format(connected_ports.get('SAS4', ''))
            iom1_args['conn2'] = slot_fmt.format(connected_ports.get('SAS5', ''))
            parts = iom_fmt.format(**iom1_args)
            self.visual.append(line_fmt.format(parts))
            self.visual.append(box_line)
            self.visual.append('')
        # Create formatted output for each controller:
        # CT0 - FA-m20r2
        # +-------------------------------------------------------------------------------+
        # |  SLOT 2  SAS0:[  SH00.SAS0  ]  SAS1:[  SH01.SAS5  ]                           |
        # |                                                                               |
        # |  SLOT 3  SAS2:[  SH00.SAS3  ]  SAS3:[  SH01.SAS2  ]                           |
        # +-------------------------------------------------------------------------------+
        sas_conn = '{port}:[{conn:^13}]'
        for ctlr in ('CT0', 'CT1'):
            if ctlr not in self.ctlr_models:
                logger.warning('Controller {} not found.')
                continue
            ctlr_info = ' - '.join([ctlr, self.ctlr_models[ctlr]])
            self.visual.append(title_fmt.format(ctlr_info))
            self.visual.append(box_line)
            connected_ports = self._get_connections(ctlr)
            prev_line = box_line
            if not self.array_ports[ctlr]:
                self.visual.append(line_fmt.format('< NO SAS CONNECTIONS FOUND >'))
            for slot, ports in sorted(six.iteritems(self.array_ports[ctlr])):
                sas_slot_items = [slot]
                for port in sorted(ports):
                    sas_port = sas_conn.format(port=port, conn=connected_ports.get(port, ''))
                    sas_slot_items.append(sas_port)
                # Creating a line of text with 2 spaces between each slot item.
                line = '  '.join(sas_slot_items)
                # Comparing the previous line to known spacing lines to make sure
                # not to add too much spacing to the visual.
                if prev_line not in (blank_line, box_line):
                    # An empty line for spacing.
                    self.visual.append(blank_line)
                self.visual.append(line_fmt.format(line))
                prev_line = line
            self.visual.append(box_line)
            self.visual.append('')
        return self.visual

    def _get_connections(self, name):
        # type: (str) -> Dict[str, str]
        """Get SAS connections to and from shelves."""
        conn_ports = {}
        for connection in self.sas_cabling_map:
            conn_to = connection['to']
            conn_from = connection['from']
            if conn_to.startswith(name):
                # Getting the sas port to map it to an address.
                sas_port = conn_to.split('.')[1]
                # Getting the from address: CT0.SAS0
                conn_ports[sas_port] = conn_from
            elif conn_from.startswith(name):
                # Getting the sas port to map it to an address.
                sas_port = conn_from.split('.')[1]
                # Getting the to address: SH00.SAS4
                conn_ports[sas_port] = conn_to
        return conn_ports

    def parse_errors(self):
        # type: () -> DefaultDict[str, List[str]]
        """Parse the error messages and determine the problem ports."""
        # TODO: PT-2097 - Break up this function for easier troubleshooting.
        # The errors indicate where the problem is reported.
        # Line Example: 'SH 0, IOM 0 port B: SAS IOM port is cabled to wrong IOM on next enclosure.'
        # Output Example: 'SH00.SAS1 is cabled to wrong IOM on next enclosure.'
        ctlr_errors = [
            'cabled to wrong enclosure IOM',
            'Unexpected enclosure ID',
            'enclosure with incorrect ID',
            'Connectivity errors detected',
        ]
        # Following regex matches the portion before the colon in the below line and lines like it.
        # PCI Slot 101, Port 1: Connectivity errors detected on SAS link.
        ctlr_port_regex = re.compile(r'(PCI\s|)Slot\s+\d+(,|)\s+[pP]ort\s+\w')
        logger.info('Processing SAS errors.')
        for ctlr, errors in six.iteritems(self.sas_errors):
            for line in errors:
                if SHELF_SAS_ERROR.match(line):
                    match = SHELF_SAS_ERROR.search(line)
                    if not match:
                        self.parsed_errors[ctlr].append(line)
                        continue
                    sh_num = match.group('shelf')
                    # The shelf number represented in sas_view is usually double digits.
                    # If the number is less than 10, the warning messages show them as single
                    # digits. This is to ensure they show up with the same format as the table.
                    sh_num = '{:0>2}'.format(sh_num)
                    shelf = 'SH{}'.format(sh_num)
                    iom = 'IOM{}'.format(match.group('iom'))
                    # Matches: SH01, IOM 1, Port C: Blah blah blah.
                    if re.match(r'SH(\s+|)\d+(,|)\s+IOM\s+\d(,|)(\s+|)[pP]ort\s+\w', line):
                        # Having 'port' in the line indicates that it can be converted.
                        # Conversion: 'SH 0, IOM 0 port A' -> 'SH00.SAS0'
                        port = match.group('port')
                        sas_port = self.iom_port_num[iom].get(port, 'UNKN')
                        connection = '.'.join([shelf, sas_port])
                        self._from_ports.add(connection)
                        regex = SHELF_SAS_ERROR
                    else:
                        # This just fixes the line to make it easier to read.
                        # Conversion: 'SH 0, IOM 0' -> 'SH00.IOM0'
                        connection = ' '.join([shelf, iom])
                        regex = r'SH\s+\d+(,|)\s+IOM\s+\d'
                    message = re.sub(regex, connection, line)
                    self.parsed_errors[ctlr].append(message)
                elif any(err in line for err in ctlr_errors):
                    match = CTLR_SAS_ERROR.search(line)
                    if not match:
                        self.parsed_errors[ctlr].append(line)
                        continue
                    slot = match.group('slot').upper()
                    port = match.group('port')
                    sas_port = self.ctlr_port_num[ctlr].get(slot, {}).get(port, 'UNKN')
                    connection = '.'.join([ctlr, sas_port])
                    self._from_ports.add(connection)
                    # CAVEAT: PT-2347 - Do not overwrite messages as a whole with an else statement.
                    if ctlr_port_regex.search(line):
                        edited_msg = re.sub(ctlr_port_regex, connection, line)
                        self.parsed_errors[ctlr].append(edited_msg)
                    else:
                        # Any lines that do not match the regex for whatever reason, we add here.
                        self.parsed_errors[ctlr].append(line)
                else:
                    # Not all errors have regexes but still need to be printed.
                    # The lines not captured by the regex patterns are just added to the list.
                    self.parsed_errors[ctlr].append(line)
        if self.parsed_errors:
            logger.info('Verifying shelf SAS HA state.')
            connections = _get_connections(self.sas_cabling_map)
            for controller in self.controllers:
                self._check_sas_cable_ha(controller, connections)
        if self._add_color:
            self._apply_colors()
        return self.parsed_errors

    def get_error_table(self):
        # type: () -> List[str]
        """Print the error messages from sas_view config."""
        self.parse_errors()
        header = '+---[ {} {} ]{}+'
        footer = '+{}+'.format('-' * 79)
        error_table = []
        non_ha = ['red', 'bold']
        for ctlr, errors in sorted(six.iteritems(self.parsed_errors)):
            # If the controller does not have errors, it is not added.
            # It is better to return an empty error_table than one with controllers and no content.
            if not errors:
                continue
            if not self.ha_sas[ctlr]['is_ha']:
                error_table.append(header.format(ctlr, 'HA Issue', '-' * 60))
                error_table.append('SAS cabling not HA Reason:')
                for reason in self.ha_sas[ctlr]['reasons']:
                    text = format_utils.text_fmt(non_ha, reason)
                    error_table.append(text)
                error_table.append(footer)
                error_table.append('')
            error_table.append(header.format(ctlr, 'Errors', '-' * 62))
            for error in errors:
                # Making each error message bold so it stands out a bit.
                font_fmt = ['bold']
                # Illegal cabling will be in red bold as they are quite serious.
                if 'illegal' in error:
                    font_fmt.append('red')
                error_table.append(format_utils.text_fmt(font_fmt, error))
            error_table.append(footer)
            error_table.append('')
        return error_table

    def _apply_colors(self):
        # type: () -> List[str]
        """Apply colors to the visual."""
        colored_visual = []
        bad_conn = set()
        txt_fmt = ['red', 'bold']
        for conn in self.sas_cabling_map:
            from_port = conn.get('from', 'UNKN')
            to_port = conn.get('to', 'UNKN')
            if from_port in self._from_ports:
                bad_conn.add(from_port)
                bad_conn.add(to_port)
        for line in self.visual:
            if not line:
                colored_visual.append(line)
                continue
            for port in bad_conn:
                if port in line:
                    colored_text = format_utils.text_fmt(txt_fmt, port)
                    line = line.replace(port, colored_text)
            colored_visual.append(line)
        self.visual = colored_visual
        return colored_visual

    def _check_sas_cable_ha(self, controller, connections):
        # type: (str, DefaultDict[str, DefaultDict[str, List[str]]]) -> DefaultDict[str, Dict[str, Any]]
        """Check sas_cabling_map to validate HA controllers."""
        # TODO: PT-2097 - Break up this function for easier troubleshooting.
        self.ha_sas[controller]['is_ha'] = True
        self.ha_sas[controller]['reasons'] = []
        logger.debug(str(connections[controller]))
        for shelf in sorted(self.shelves):
            # Potentially there could be multiple reasons for non-HA configurations.
            # Pulling out what reason each shelf finds.
            reason = []
            shelf_paths = []
            shelf_ha = True
            for iom in ('IOM0', 'IOM1'):
                iom_path = []
                for port in ('A', 'B', 'C'):
                    name = '.'.join([shelf, iom, port])
                    if name in connections[controller]:
                        iom_path.append(connections[controller][name])
                # There should be one and only one path to each IOM.
                if len(iom_path) != 1:
                    self.ha_sas[controller]['is_ha'] = False
                    shelf_ha = False
                    if iom_path:
                        message = 'Too many paths to {} on {}.'
                    else:
                        message = 'No connection to {} on {}.'
                    reason.append(message.format(iom, shelf))
                    reason.append('There should be one path to each IOM per controller.')
                    message = ' '.join(reason)
                    self.ha_sas[controller]['reasons'].append(message)
                    break
                shelf_paths.extend(iom_path)
            # To show all reasons for non-HA SAS cabling we look at each shelf.
            # Continuing if shelf has already proven to be non-HA due to iom_path issues.
            if not shelf_ha:
                continue
            # If iom_path state passes then check for other possible non-HA situations.
            paths_len = len(shelf_paths)
            # Each shelf should have paths to both IOMs from each controller.
            if paths_len != 2:
                self.ha_sas[controller]['is_ha'] = False
                reason.append('This controller should have paths to both IOMs on {}.'.format(shelf))
                if paths_len > 2:
                    message = '{} has too many connections from this controller.'
                elif paths_len == 1:
                    message = '{} does not have enough connections from this controller.'
                else:
                    message = '{} has no paths from this controller.'
                reason.append(message.format(shelf))
                message = ' '.join(reason)
                self.ha_sas[controller]['reasons'].append(message)
                continue
            # Overlap happens when both IOMs on a shelf are connected to the same HBA.
            overlap = set(shelf_paths[0]).intersection(set(shelf_paths[1]))
            if overlap and '405' not in self.ctlr_models[controller]:
                # The FA-405 only has a single HBA, as such this check does not apply.
                self.ha_sas[controller]['is_ha'] = False
                hba = ', '.join(overlap)
                reason.append('Overlapping HBAs on {} from {}'.format(shelf, hba))
                message = ' '.join(reason)
                self.ha_sas[controller]['reasons'].append(message)
        logger.debug(str(self.ha_sas))
        return self.ha_sas


def _get_connections(sas_cabling_map):
    # type: (List[Dict[str, str]]) -> DefaultDict[str, DefaultDict[str, List[str]]]
    """Get the shelf connections per controller to help determine HA connections."""
    # connections example: {
    #     'CT0': defaultdict(list, {
    #         'SH00.IOM0.A': ['SLOT 100', 'SH00.SAS0'],
    #         'SH00.IOM1.C': ['SLOT 100', 'SH00.SAS3'],
    #     }),
    #     'CT1': defaultdict(list, {
    #         'SH00.IOM0.A': ['SLOT 100', 'SH00.SAS0'],
    #         'SH00.IOM1.C': ['SLOT 100', 'SH00.SAS3'],
    #     })
    # }
    connections = defaultdict(lambda: defaultdict(list))  # type: DefaultDict[str, DefaultDict[str, List[str]]]
    for info in sas_cabling_map:
        # Examples of info:
        # Controller: {
        #     'controller': 'CT1',
        #     'from': 'CT1.SAS0',
        #     'shelf_conn': 'SH01.IOM1.C',
        #     'slot': 'SLOT 100',
        #     'to': 'SH01.SAS3',
        # }
        # Shelf: {
        #     'controller': 'CT1',
        #     'from': 'SH00.SAS4',
        #     'shelf_conn': 'SH02.IOM0.C',
        #     'slot': 'SLOT 201',
        #     'to': 'SH02.SAS2',
        # }
        ctlr = info['controller']
        shelf_conn = info['shelf_conn']
        connections[ctlr][shelf_conn].append(info['slot'])
        connections[ctlr][shelf_conn].append(info['to'])
        # The controller port itself is not needed so it is skipped.
        if not info['from'].startswith('CT'):
            connections[ctlr][shelf_conn].append(info['from'])
    return connections


def get_sasview_sections(sas_view_lines):
    # type: (Any) -> DefaultDict[str, Any]
    """Iterate over the sas_view lines and provide a dict of commands with lines.

    Argument:
        sas_view_lines (List[str]): Lines pulled from the sas_view file in hardware.log

    Return:
        sections (defaultdict[str, List[str]]): Sectioned representation of sas_view by command.
    """
    sections = defaultdict(list)  # type: DefaultDict[str, List[str]]
    command = 'Other info'
    for line in sas_view_lines:
        # Because python3 sucks at strings vs bytes and strings are more useful here.
        line = codecs.decode(line, 'utf-8')
        # Strip unwanted leading/trailing newlines from the line.
        line = line.replace('\n', '')
        if 'Command line:' in line:
            # Turns this: "Command line: ['/opt/Purity/bin/sas_view.py', 'config']"
            # Into this: 'config'
            for item in ('\'', '[', ']'):
                line = line.replace(item, '')
            command = ' '.join([item.strip() for item in line.split(',')[1:]])
        sections[command].append(line)
    return sections


def _get_sub_sections(lines, sections, partials=None):
    # type: (List[str], List[str], Optional[List[str]]) -> DefaultDict[str, Any]
    """Iterate over the lines to create a dict of sub-sections within sas_view sections."""
    sub_sections = defaultdict(list)  # type: DefaultDict[str, List[str]]
    # The 'Other info' key should rarely, if ever, get used because the first line should be the
    # 'Command line' key and that will overwrite it.
    if not partials:
        partials = []
    key = 'Other info'
    for line in lines:
        # Ensure all lines are checked for headers so that none are missed.
        section_header = line.split(':', 1)
        # Setting a potential key to see if we need to add it as a key in the dict.
        _key = section_header[0]
        # Search sections for the exact key match or partial match.
        # Majority of items we need for key are exact matches.
        if _key and (_key in sections or [part for part in partials if part in _key]):
            key = _key
            # Some items are 'Section name: section values'. This captures those values.
            if len(section_header) >= 2:
                sub_sections[key].append(' '.join(section_header[1:]))
            continue
        sub_sections[key].append(line)
    return sub_sections


def _get_single_value_keys(section_dict, keys):
    # type: (DefaultDict[str, Any], List[str]) -> DefaultDict[str, Any]
    """Parse single value keys, clean them up and return them as strings.

    Some sections have single result and do not need a list of values for the user to look over.
    This function takes these sections and makes them into a single string.
    """
    for key in keys:
        value = section_dict[key]
        # Join everything and drop empty strings.
        joined = ' '.join([val for val in value if val])
        if key == 'Command line':
            # Turns this: '/opt/Purity/bin/sas_view.py, config'
            # Into this: '/opt/Purity/bin/sas_view.py config'
            joined = joined.replace(',', '')
        section_dict[key] = joined.strip()
    return section_dict
