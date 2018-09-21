#!/usr/bin/python
"""Cisco switch log parsing health utility."""

import argparse
import collections
import logging

try:
    # pylint: disable=unused-import
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

from photon.lib import debug_utils
from photon.lib.report_utils import build_table_and_print
from photon.backend.cisco import tech_support_show

LOGGER = logging.getLogger(__name__)

# NOTE: build_fc_tables, build_gigabit_eth_tables, and build_eth_tables are very similar - there
# was a crunch for time, and this duplicity gave us the ability to implement quickly, and add the
# custom parsing we needed specifically for the build_fc_tables without getting into the weeds any
# more than we already were.  If this comes up for adjustment, this should be revisited if there is
# time and it's within scope.


def _ordered_interface_dict(interface_dict):
    """Get an ordered dict from the interface dict."""
    # We want a sorting series to use for a sorted() key that takes the card as the first sort, and
    # the port number as an int if possible as the second.  If it can't be an int for int sorting
    # behavior, then we'll use the string sorting behavior as a backup.
    # fc1/1         -> ['fc1', 1]
    # port-channel1 -> ['port-channel1']
    # fc1/a         -> ['fc1', 'a']
    # NOTE: should be getting a ('fc1/1', {}) tuple from the interface_dict.items()
    PORT_SORT_LAMBDA = lambda x: [int(string) if string.isdigit() else string for string in x[0].split('/')]
    return collections.OrderedDict(sorted(interface_dict.items(), key=PORT_SORT_LAMBDA))
    


def build_fc_tables(interface_dict, verbose):
    # type: (Dict[str, Dict[str, str]], Dict[str, cisco_utils.FlogiEntry, bool) -> List[List[str]]
    """Print the FC counter tables.

    There are lots of counters in an interface dictionary, but there are typical ones we care
    about.  Default of verbose=False will print table lines only for interfaces that are not in
    a 'down' state.  Switching this to verbose=True will print the downed interfaces, along with
    their reason for being down.

    Arguments:
        interface_dict (dict): Interface information to print to table.
        verbose (bool): Whether or not to show down ports.  Default does not show them.

    Returns:
        lines (list): Table information about the fc_interfaces
    """
    # The visual ease of correlation is more important than bad whitespace.
    # pylint: disable=bad-whitespace
    key_name_pairs = collections.OrderedDict([
        ('interface_name',                              'name'),
        ('port_wwn',                                    'port_wwpn'),
        ('connected_wwpns',                             'connected_wwpns'),
        ('speed',                                       'speed'),
        ('state',                                       'state'),
        ('fcid',                                        'fcid'),
        ('last_clearing_of_show_interface_counters',    'last cleared'),
        ('input_discards',                              'rx_disc'),
        ('input_input_ols',                             'rx_ols'),
        ('input_invalid_crc/fcs',                       'rx_crc'),
        ('input_loop_inits',                            'rx_loop'),
        ('input_lrr',                                   'rx_lrr'),
        ('input_nos',                                   'rx_nos'),
        ('input_receive_b2b_credit_remaining',          'rx_b2b_rem'),
        ('output_transmit_b2b_credit_remaining',        'tx_b2b_rem'),
        ('output_discards',                             'tx_disc'),
        ('output_errors',                               'tx_err'),
        ('output_loop_inits',                           'tx_loop'),
        ('output_lrr',                                  'tx_lrr'),
        ('output_nos',                                  'tx_nos'),
        ('output_output_ols',                           'tx_ols'),
    ])
    lines = [list(key_name_pairs.values())]
    # sort them by names, but we don't need the name.
    for interface in _ordered_interface_dict(interface_dict).values():
        line = []
        if interface.get('hardware') != 'Fibre Channel':
            continue
        # So far Fibre Channel is the only one that's needed a verbose vs. non verbose mode.
        # That may change over time.
        if not verbose and 'down' in interface.get('state'):
            continue
        connected_wwpns = interface.get('connected_wwpns')
        for key in key_name_pairs.keys():
            if key == 'connected_wwpns' and connected_wwpns:
                val = connected_wwpns[0]
            elif key == 'connected_wwpns' and not connected_wwpns:
                val = '-'
            elif key == 'state':
                # We should only get to this condition if we are using
                # verbose mode.
                state = interface.get('state')
                if 'down' in state:
                    # To keep screen real-estate preserved, we're changing this from:
                    # down (Link failure or not-connected) -> down
                    # down (SFP not present)               -> down
                    # etc.
                    val = 'down'
                else:
                    val = 'up'
            else:
                # If it's not one of our special cases above, then git'er done.
                val = interface.get(key, '-')
            line.append(val)
        lines.append(line)
        # If we have a line that has additional ports, we need to add lines that don't
        # have empty '-' placeholders - so we go through our connected wwpns that weren't
        # in our first line, and add a line of empty string placeholders with our single
        # column (connected_wwpns) that has a value.
        if len(connected_wwpns) > 1:
            for port in connected_wwpns[1:]:
                addnl_port_line = []
                for index, _ in enumerate(key_name_pairs):
                    if index != 2:
                        addnl_port_line.append('')
                    else:
                        addnl_port_line.append(port)
                lines.append(addnl_port_line)
    return lines


def build_gigabit_eth_tables(interface_dict):
    # type: (Dict[str, Dict[str, str]]) -> List[List[str]]
    """Print the FC counter tables.

    There are lots of counters in an interface dictionary, but there are typical ones we care
    about for our gigabit ethernet interfaces.  We'll print these out here.

    Arguments:
        interface_dict (dict): Interface information to print to table.

    Returns:
        lines (list): Table information about the gigabit_ethernet interfaces
    """
    # The visual ease of correlation is more important than bad whitespace.
    # pylint: disable=bad-whitespace
    key_name_pairs = collections.OrderedDict([
        ('interface_name',          'name'),
        ('state',                   'state'),
        ('mtu',                     'mtu'),
        ('input_packets_input',     'rx_#'),
        ('input_input_errors',      'rx_err'),
        ('input_fifo',              'rx_fifo'),
        ('input_overrun',           'rx_over'),
        ('output_packets_output',   'tx_#'),
        ('output_output_errors',    'tx_err'),
        ('output_fifo',             'tx_fifo'),
        ('output_underruns',        'tx_under'),
        ('output_collisions',       'tx_coll'),
        ('output_carrier_errors',   'tx_carr'),
    ])
    lines = [list(key_name_pairs.values())]
    # sort them by names, but we don't need the name.
    for interface in _ordered_interface_dict(interface_dict).values():
        if interface['hardware'] != 'GigabitEthernet':
            continue
        line = []
        for key in key_name_pairs.keys():
            val = interface.get(key, '-')
            line.append(val)
        lines.append(line)
    return lines


def build_eth_tables(interface_dict):
    # type: (Dict[str, Dict[str, str]]) -> List[List[str]]
    """Print the FC counter tables.

    There are lots of counters in an interface dictionary, but there are typical ones we care
    about for our ethernet interfaces.

    Arguments:
        interface_dict (dict): Interface information to print to table.

    Returns:
        lines (list): Table information about the ethernet interfaces
    """
    # The visual ease of correlation is more important than bad whitespace.
    # pylint: disable=bad-whitespace
    key_name_pairs = collections.OrderedDict([
        ('interface_name',                              'name'),
        ('last_clearing_of_show_interface_counters',    'cleared'),
        ('mtu',                                         'mtu'),
        ('port_mode',                                   'mode'),
        ('auto_negotiation',                            'auto'),
        ('interface_resets',                            'resets'),
        ('input_input_packets',                         'rx_#'),
        ('input_input_discard',                         'rx_disc'),
        ('input_crc',                                   'rx_crc'),
        ('input_input_error',                           'rx_err'),
        ('output_output_packets',                       'tx_#'),
        ('output_collision',                            'tx_coll'),
        ('output_output_error',                         'tx_err'),
        ('output_output_discard',                       'tx_disc'),
    ])
    lines = [list(key_name_pairs.values())]
    for interface in _ordered_interface_dict(interface_dict).values():
        if interface['hardware'] != '1000/10000 Ethernet':
            continue
        line = []
        for key in key_name_pairs.keys():
            val = interface.get(key, '-')
            line.append(val)
        lines.append(line)
    return lines


def build_switch_info(parser):
    # type: (tech_support_show.SupportShowParser) -> List[List[str]]
    """Build basic information about the switch.

    Arguments:
        parser (tech_support_show.SupportShowParser): Instantiated switch to pull information from.

    Returns:
        lines (list): Table information about the switch.
    """
    parser_info_lines = [
        ['Switch Name:', parser.get_switchname()],
        ['Switch Time:', parser.timestamp],
        ['Switch uptime:', parser.get_uptime()],
        ['Switch BIOS:', parser.get_bios()],
        ['Switch Version:', parser.get_version()],
        ['Switch Hardware:', parser.get_hardware()],
    ]
    return parser_info_lines


def mr_cisco(support_show_parser, verbose=False):
    # type: (tech_support_show.SupportShowParser, bool) -> None
    """Print the interface tables.

    Arguments:
        support_show_parser (tech_support_show.SupportShowParser): Instantiated switch to pull information from.
        verbose (bool): Print downed fc ports if true.
    """
    switch_info_lines = build_switch_info(support_show_parser)
    interface_dict = support_show_parser.get_interface_dict()
    fc_lines = build_fc_tables(interface_dict, verbose)
    gigabit_lines = build_gigabit_eth_tables(interface_dict)
    eth_lines = build_eth_tables(interface_dict)

    build_table_and_print(switch_info_lines)
    if len(gigabit_lines) > 1:
        print('\nGIGABIT ETHERNET:\n')
        build_table_and_print(gigabit_lines)
    if len(fc_lines) > 1:
        print('\nFIBRE CHANNEL:\n')
        build_table_and_print(fc_lines)
    if len(eth_lines) > 1:
        print('\nETHERNET:\n')
        build_table_and_print(eth_lines)


def parse_args():
    # type: () -> argparse.Namespace
    """Get args for mr_cisco."""
    parser = argparse.ArgumentParser(description='Process CISCO logs for basic health information.')
    parser.add_argument('--wwn', nargs='*', help="WWNs for which you'd like additional information.")
    parser.add_argument('--verbose', action='store_true', help="Display verbose port counter information.")
    parser.add_argument('logfile', nargs='?', help='Logfile of the cisco log.')
    return parser.parse_args()


#@debug_utils.debug
def main(args=None):
    # type: (Optional[argparse.Namespace]) -> None
    """Main function."""
    if not args:
        args = parse_args()
    if not args.logfile:
        print('Please provide a cisco tech-support-show log to parse.')
    else:
        parser = tech_support_show.SupportShowParser(args.logfile)
        mr_cisco(parser, verbose=args.verbose)



if __name__ == '__main__':
    main()
