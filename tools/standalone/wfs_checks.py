#!/usr/bin/env python

""" Bring up interfaces and check connectivity for WFS installs. """

from __future__ import print_function

import argparse
import collections
import fcntl
import re
import struct
import subprocess
import sys
import termios

from six import iteritems

try:
    # pylint: disable=unused-import
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Union
except ImportError:
    pass


CONNECTIVITY_FAILURES = []

# Globals, because it's a nightmare to try and get this down into
# the ping function with args that modify it.
# pylint: disable=invalid-name, global-statement
PING_COUNT = 5
PING_INTERVAL = 3

# component regex matches a digit, character, or period character as
# a valid "component" for a version string.
# Version regex matches only versions like 4.10.12 and will error for
# versions with .beta, etc.  We should fail on those anyway.
VERSION_COMPONENT_RE = re.compile(r'(\d+ | [a-z]+ | \.)', re.VERBOSE)
VERSION_RE = re.compile(r'\d+\.\d+\.\d+$')


# Argparse actions to make another argument required or not.
# Argparse actions to make another argument required or not.
class ChangeRequired(argparse.Action):
    """Store true and make "to_modify" required args.

    This defaults to True when evaluated - i.e.
    if args.change_required_arg:

    The if statement above would evaluate to True if the flag was present,
    and false if the flag is not present.
    """

    def __init__(self, *args, **kwargs):
        """Init for ChangeRequired class.

        Arguments:
            to_modify (list): destination names of the args to modify required flags for.
            target_value (bool): Value to set the arg.required attribute to.
        """
        kwargs['const'] = True
        kwargs['nargs'] = 0
        self.target_value = kwargs.pop('target_value', None)
        self.to_modify = kwargs.pop('to_modify', [])
        super(ChangeRequired, self).__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Perform these when this action is called."""
        self._modify_required(parser)
        setattr(namespace, self.dest, self.const)

    def _modify_required(self, parser):
        """Modify any actions to the required value requested."""
        # argparse doesn't currently have a "modify actions conditionally" that's
        # public, so we get to use the protected method.
        # pylint: disable=protected-access
        for action in parser._actions:
            if action.dest in self.to_modify and self.target_value:
                action.required = self.target_value


class VersionError(ValueError):
    """Custom version error for Version class parsing."""
    pass


class Version(object):
    """Basic version class for doing version comparisons."""


    def __init__(self, vstring):
        # type: (str) -> None

        if not VERSION_RE.search(vstring):
            # pylint: disable=anomalous-backslash-in-string
            message = u"Unable to accurately parse non-standard version numbers, i.e. not of the format: r'\d\.\d\.\d$'"
            raise VersionError(message)
        self.parse(vstring)

    def parse(self, vstring):
        # type: (str) -> None
        """Parse version string into components."""
        self.vstring = vstring
        # We're breaking the string into alphanumerics and digits, and then removing the periods.
        # Example: '4.1.2.beta' -> [4, 1, 2, 'beta']
        components = [x for x in VERSION_COMPONENT_RE.split(vstring) if x and x != '.']  # type: List[Any]
        for index, component in enumerate(components):
            # Try to make the numbers into ints for leveraging list comparisons.
            # i.e. ['1', '1', '1', 'beta'] -> [1, 1, 1, 'beta']
            if component.isdigit():
                components[index] = int(component)

        self.version = components

    def _cmp(self, other):
        # type: (Union[str, Version]) -> int
        """Compare version strings"""
        if isinstance(other, str):
            other = Version(other)

        if self.version == other.version:
            comparison = 0
        elif self.version < other.version:
            comparison = -1
        elif self.version > other.version:
            comparison = 1
        return comparison

    def __repr__(self):
        # type: () -> str
        """repr function"""
        return "{} ({})".format(self.__class__.__name__, self.vstring)

    def __str__(self):
        # type: () -> str
        """str function"""
        return self.vstring

    def __eq__(self, other):
        # type: (Union[str, Version]) -> bool
        """Comparison for equals"""
        if isinstance(other, str):
            other = Version(other)
        return self.vstring == other.vstring

    def __ne__(self, other):
        # type: (Union[str, Version]) -> bool
        """Comparison for equals"""
        if isinstance(other, str):
            other = Version(other)
        return self.vstring != other.vstring

    def __lt__(self, other):
        # type: (Union[str, Version]) -> bool
        """Comparison for less than"""
        comparison = self._cmp(other)
        return comparison < 0

    def __le__(self, other):
        # type: (Union[str, Version]) -> bool
        """Comparison for less than or equal"""
        comparison = self._cmp(other)
        return comparison <= 0

    def __gt__(self, other):
        # type: (Union[str, Version]) -> bool
        """Comparison for greater than"""
        comparison = self._cmp(other)
        return comparison > 0

    def __ge__(self, other):
        # type: (Union[str, Version]) -> bool
        """Comparison for greater or equal"""
        comparison = self._cmp(other)
        return comparison >= 0


def table_to_dict(lines, delimiter=None):
    # type: (List[str], Optional[str]) -> List[Dict[str, str]]
    """Turn a table into a dict.

    Arguments:
        lines (list): Table lines from any string/newline tableself.
        delimiter (str): regex friendly delimiter string to split columns on
    Returns:
        table_dict (list): list of dicts with column name as key, and value
    """
    # re.split() takes strings rather than regex for some reason.
    # pylint: disable=anomalous-backslash-in-string
    delimiter = delimiter or '\s{2,}'
    # Remove lines that have no alphanumeric characters in them.
    fixed_lines = [line for line in lines if re.search(r'\w+', line)]
    if not fixed_lines:
        raise ValueError('No lines to parse into table after filtering out non-alphanumeric lines.')
    table_dict_list = []
    keys = [thing for thing in re.split(delimiter, fixed_lines[0].lower()) if thing]
    fixed_keys = []
    for key in keys:
        # Remove non alphanumerics and spaces.
        fixed_keys.append('_'.join(x for x in key.split() if x.isalpha()))
    # Since we're parsing a table, the first line is our headers.  Skip it.
    char_in_line = re.compile(r'\w')
    for line in fixed_lines[1:]:
        if not char_in_line.search(line):
            continue
        line_dict = {}
        values = [col_val.strip() for col_val in re.split(delimiter, line.lower()) if col_val]
        for index, value in enumerate(values):
            if not value:
                continue
            key = fixed_keys[index]
            line_dict[key] = value
        table_dict_list.append(line_dict)
    return table_dict_list


def check_hardware(local_hardware, peer_hardware):
    # type: (str, str) -> List[List[str]]
    """Run hardware checks.

    Arguments:
        local_hardware (str): Hardware model, e.g. 'FA-420'.
        peer_hardware (str): Hardware model, e.g. 'FA-420'.

    Returns:
        messages (list): pass/fail result messages
    """
    unsupported_controllers = ['fa-300',
                               'fa-310',
                               'fa-320',
                               'fa-405',
                               'fa-420',
                               'fa-450',
                               'fa-m10',
                               'fa-m10r2']

    has_both_controllers = local_hardware and peer_hardware
    models_match = local_hardware == peer_hardware
    local_supported = local_hardware and local_hardware.lower() not in unsupported_controllers
    peer_supported = peer_hardware and peer_hardware.lower() not in unsupported_controllers

    if all([has_both_controllers, models_match, local_supported, peer_supported]):
        message = [['Hardware', 'PASS', 'Controller models are {}\'s'.format(local_hardware)]]
    elif not has_both_controllers:
        message = [['Hardware', 'FAIL', 'Could not verify both controllers.']]
    elif not models_match:
        mod_message = 'Models do not match - Local: {}, Peer: {}'
        message = [['Hardware', 'FAIL', mod_message.format(local_hardware, peer_hardware)]]
    elif not all([local_supported, peer_supported]):
        mod_message = 'Local model {} or peer model {} not supported.'
        message = [['Hardware', 'FAIL', mod_message.format(local_hardware, peer_hardware)]]
    else:
        message = [['Hardware', 'FAIL', 'Unable to verify supported hardware.']]
    return message


def check_versions(local_version, peer_version):
    # type: (str, str) -> List[List[str]]
    """Run version checks.

    Arguments:
        local_version (str): Local controller version.
        peer_version (str): Peer controller version.

    Returns:
        messages (list): pass/fail result messages
    """
    threshold_version = Version('4.10.7')
    try:
        localv = Version(local_version)  # type: Optional[Version]
        peerv = Version(peer_version)  # type: Optional[Version]
    except VersionError:
        localv = peerv = None
    versions = [localv, peerv]
    missing_versions = any(True for version in versions if not version)
    versions_mismatched = local_version != peer_version
    purity_5_0_x = any(version.version[0:2] == [5, 0] for version in versions if version)
    below_threshold = any(version < threshold_version for version in versions if version)
    if missing_versions:
        message = [['Version', 'FAIL', 'Unable to determine controller Purity Version.  MANUAL CHECK REQUIRED!']]
    elif versions_mismatched:
        message = [['Version', 'FAIL', 'Purity version mismatch between controllers!']]
    elif purity_5_0_x:
        message = [['Version', 'FAIL', 'Array is running {}, 5.0.x versions are not supported.'.format(localv)]]
    elif below_threshold:
        message = [['Version', 'FAIL', 'Array is running {}, below supported threshold.'.format(localv)]]
    elif not any([missing_versions, versions_mismatched, purity_5_0_x, below_threshold]):
        message = [['Version', 'PASS', 'Both controllers are running {}'.format(localv)]]
    else:
        message = [['Version', 'FAIL', 'Unable to verify version information.']]
    return message


def check_iscsi_ports(purenetwork_list):
    # type: (str) -> List[List[str]]
    """Run iSCSI checks.

    Arguments:
        purenetwork_list (str): Unsplit output from purenetwork list output.
    Returns:
        messages (list): pass or fail result messages
    """
    # re.split() takes strings rather than regex for some reason.
    # pylint: disable=anomalous-backslash-in-string
    pnl_dict_list = table_to_dict(purenetwork_list.splitlines(), delimiter='\s{2,}')
    iscsi_hbas = []

    for device in pnl_dict_list:
        if device['speed'].lower() == '10.00 gb/s' and device['services'] == 'iscsi':
            iscsi_hbas.append(device['name'])

    pass_fail = 'PASS' if len(iscsi_hbas) >= 4 else 'FAIL'
    base_message = 'Four valid 10.00GB/s iSCSI Ports required, {} found'.format(len(iscsi_hbas))
    if iscsi_hbas:
        base_message += ': {}'.format(', '.join(iscsi_hbas))
    message = [['ISCSI', pass_fail, base_message]]

    return message


def check_syncrep(local_version, tunables):
    # type: (str, str) -> List[List[str]]
    """Run syncrep checks.

    Arguments:
        local_version (str): Local controller version.
        tunables (str): Unsplit output from pureadm list-tunable output.
    Returns:
        messages (list): pass/fail result messages
    """
    localv = Version(local_version)

    ps_syncrep_enabled = [tunable for tunable in tunables.splitlines() if 'ps_syncrep_enabled' in tunable.lower()]
    if bool(ps_syncrep_enabled) and localv > Version('5.1.1'):
        message = [['Syncrep', 'PASS', '{} Allows ActiveCluster and WFS to run concurrently.'.format(localv)]]
    elif ps_syncrep_enabled:
        message = [['Syncrep', 'FAIL', 'ActiveCluster is enabled']]
    else:
        message = [['Syncrep', 'PASS', 'ActiveCluster tunable is not set.']]
    return message


def get_ctrl_num():
    # type: () -> str
    """ Get "ct0" or "ct1" from hostname. """
    hostname = subprocess.check_output(['hostname'], universal_newlines=True)
    # hostname looks like: array-name-ct0
    ct_num = str(hostname.split('-')[-1].strip())
    return ct_num


def get_interface_dict(interfaces):
    # type: (List[str]) -> Dict[str, str]
    """ Get dictionary of ctx.ethx -> IP from purenetwork list.
    Arguments:
        interfaces (list): Interfaces that have been assigned.

    Returns:
        interface_dict (dict): ctx.ethx -IP from purenetwork listself.

    Example:
        interfaces: ['ETH6', 'ETH7']

        interface_dict: {'ct0.eth6': '10.204.121.24',
                         'ct0.eth7': '10.204.121.25',
                         'ct1.eth6': '10.204.121.26',
                         'ct1.eth7': '10.204.121.27'}
    """
    unsplit_lines = subprocess.check_output(['purenetwork', 'list'], universal_newlines=True)
    purenetwork_lines = unsplit_lines.splitlines()
    interface_dict = {}

    for line in purenetwork_lines:
        for interface in interfaces:
            # pylint: disable=line-too-long
            # Example line:
            # ct0.eth8  True     -       192.168.26.58   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:95  10.00 Gb/s  iscsi        -
            # So if one of our interfaces is in the line, we'll pull out the IP address.
            # interface.lower looks like: "ct0.eth8"
            if interface.lower() in line.lower():
                split_line = line.split()
                # ct0.eth8 in the example line above
                interface_name = str(split_line[0])
                # 192.168.26.58 in the example line above
                interface_ip = str(split_line[3])
                interface_dict[interface_name] = interface_ip

    return interface_dict


def get_tty_wid():
    # type: () -> int
    """Determine the width of the current terminal."""
    try:
        _, tty_wid = struct.unpack('hh', fcntl.ioctl(2, termios.TIOCGWINSZ, '1234'))
    # Leaving the broad exception, because PowerShell.
    # pylint: disable=broad-except
    except Exception:
        # We catch all Exceptions to be safe, ignore it and use the default terminal width.
        tty_wid = 80
    # Workaround: Powershell's scroll bar may displace a character and cause word-wrap.
    # We simply remove 2 from the tty_wid to be safe.
    tty_wid -= 2
    return int(tty_wid)


def status_update(update=None, output_pipe=sys.stderr):
    # type: (Optional[str], Any) -> None
    """Print a status bar at the bottom of the screen.

    Arguments:
        update: (str) that will be printed to the output_pipe.
            NOTE: If update is None (Default), a blank line will be printed to clear the screen.
        output_pipe: (pipe) destination pipe that update will be use.
            NOTE: pipe object must have "write" and "flush" methods.
    """
    if not hasattr(output_pipe, 'write') or not hasattr(output_pipe, 'flush'):
        msg = 'Output_pipe object is missing "write" and/or "flush" methods.'
        raise TypeError(msg)
    tty_wid = get_tty_wid()
    # Write a blank line to prevent overlap with any previous update text.
    output_pipe.write('\r' + ' ' * tty_wid + '\r')
    if not update:
        return
    # Avoid word-wrap by truncating long update text strings to the tty_wid.
    update = ''.join(update[:tty_wid])
    # Print the new update and return to the beginning of the line.
    # The extra space at the beginning prevents the curser from covering cover the first letter
    output_pipe.write('\r {}\r'.format(update))
    # NOTE: This never printed a newline character, the next output will begin on the same line.
    output_pipe.flush()


def get_table_info(list_of_lists):
    # type: (List[List[str]]) -> Dict[int, int]
    """ Create table_info for making separators.
    Arguments:
        list_of_lists (list): Any list of lists that can be stringified.

    Returns:
        table_info (OrderedDict): Index and max column length for each item
                                  in my list of lists - i.e. list[:][0] has a
                                  max length of 5 characters for all lists.
    """
    table_info = collections.OrderedDict()  # type: collections.OrderedDict
    for list_item in list_of_lists:
        for index, col in enumerate(list_item):
            max_len = table_info.get(index, 0)
            # Make sure whatever it is, we try to stringify it
            # for length testing.  Formats below will take care
            # of making it a string in the end.
            str_col = str(col)
            if len(str_col) > max_len:
                table_info[index] = len(str_col)
    return dict(table_info)


def create_separator(table_info, header=False):
    # type: (Dict[int, int], bool) -> List[str]
    """ Create header and normal separators for list of lists.
    Arguments:
        table_info (OrderedDict): Index and max column length for each item
                                  in my list of lists - i.e. list[:][0] has a
                                  max length of 5 characters for all lists.
        header (bool): Whether or not the separator should be a header separatator
    Returns:
        header_sep (string): vertical separators using = for header, - for normal
        """
    sep_char = "=" if header else "-"
    separator = []
    for index, column_width in iteritems(table_info):
        column_width = table_info[index]
        # For each item, add a +==== or +----
        # | Hello |  <= Width of 5, add 2 for spaces
        # +=======   <= We only add up to the next delimiter because
        #               the next column item will add the trailing +.
        separator.append('+' + sep_char * (column_width + 2))
    # Add a trailing + to our separators to close out the last space.
    # | Hello |
    # +=======+  <= Adds this extra + at the end that wasn't taken care of yet.
    separator.append('+')
    return separator


def create_table(list_of_lists, header=True, vertical_sep=False):
    # type: (List[List[str]], bool, bool) -> List[str]
    """ Print a table based on a list of lists.
    Arguments:
        list_of_lists (list): Each item in this list is a row and should be a list
                              of values for columns
        header (bool): If true, first line will be treated as a header.
        vertical_sep (bool): If true, vertical separators will be added between rows.

    Returns:
        table_lines (list): Strings for each line in the table.
    """
    table_lines = []
    first_row = []

    # Go through and get our widths from the list of lists
    table_info = get_table_info(list_of_lists)

    # Create separators based on the widths we got.
    header_sep = create_separator(table_info, header=True)
    normal_sep = create_separator(table_info)

    # Create our first row special since it might be a header - this is done
    # whether or not we have a header, because it *might* be a header, and we have
    # to do this first if it is.
    # If it is, we'll need it before the rest of the list.  If it is not a header
    # we won't wrap it up pretty, we'll just wrap the top like a normal line with
    # or without a vertical separator, depending on your selection.
    for index, col_value in enumerate(list_of_lists[0]):
        column_width = table_info.get(index)
        formt_str = '| {{!s:{}}} '.format(column_width)
        first_row.append(formt_str.format(str(col_value)))
    first_row.append('|')

    # If it's a header, wrap it up, otherwise give it raw.
    if header:
        # +======+====+====+=======+======+
        # | Here | Is | my | first | line |
        # +======+====+====+=======+======+
        table_lines.append(''.join(header_sep))
        table_lines.append(''.join(first_row))
        table_lines.append(''.join(header_sep))
    elif vertical_sep:
        # +------+----+----+-------+------+
        # | Here | Is | my | first | line |
        # +------+----+----+-------+------+
        table_lines.append(''.join(normal_sep))
        table_lines.append(''.join(first_row))
        table_lines.append(''.join(normal_sep))
    else:
        # +------+----+----+-------+------+
        # | Here | Is | my | first | line |
        table_lines.append(''.join(normal_sep))
        table_lines.append(''.join(first_row))

    # Go through the rest and add them.
    for line in list_of_lists[1:]:
        row = []
        for index, col_value in enumerate(line):
            column_width = table_info.get(index)
            formt_str = '| {{!s:{}}} '.format(column_width)
            row.append(formt_str.format(str(col_value)))
        row.append('|')
        table_lines.append(''.join(row))
        # If we want vertical separators, add them after every row.
        if vertical_sep:
            table_lines.append(''.join(normal_sep))

    # If we aren't vertically separating, we won't have appended a separator
    # row, so add it if not vertical_sepa
    if not vertical_sep:
        table_lines.append(''.join(normal_sep))

    return table_lines


def build_table_and_print(list_of_lists, header=True, vertical_sep=False):
    # type: (List[List[str]], bool, bool) -> None
    """ Print's a table from a list of lists. """
    table = create_table(list_of_lists, header=header, vertical_sep=vertical_sep)
    for line in table:
        print(line)


# All required arguments.
# pylint: disable=too-many-arguments
def build_ping_command(interface,       # type: str
                       target,          # type: str
                       interface_dict,  # type: Dict[str, str]
                       mtu,             # type: int
                       count,           # type: int
                       interval,        # type: Union[float, int]
                       ctrl             # type: str
                      ):
                      # type: (...) -> List[str]
    """ Build a ping command for subprocess from args.
    Arguments:
        interface (str): Interface to ping from - e.g. "ct0.eth6"
        target (str): IP address to ping from the interface.
        interface_dict (dict): interface to IP information
        mtu (int): Actual MTU requested (Do not account for overhead)
        count (int): Number of times to ping the target
        interval (int): How long in seconds between pings
        ctrl (str): Which controller we are on.

    Returns:
        ping_command (list): Subprocess command for the requested args.
    """
    real_mtu = mtu - 28
    # Get the interface IP address to use due to PURE-94901
    interface_ip = interface_dict[interface]
    base_command = ['ping', '-I', interface_ip, '-c', str(count), '-i',
                    str(interval), '-s', str(real_mtu), '-Mdo', target]
    # Modify the command for peer or not based on controller of the interface.
    if ctrl in interface:
        ping_command = base_command
    else:
        ping_command = ['ssh', 'peer', ' '.join(base_command)]
    return ping_command


# All required arguments.
# pylint: disable=too-many-arguments
def ping(interface,         # type: str
         target,            # type: str
         interface_dict,    # type: Dict[str, str]
         mtu=1500           # type: int
        ):
        # type: (...) -> str
    """ Ping from a specific interface to a target IP.
    Arguments:
        interface (str): Interface to ping from - e.g. "ct0.eth6"
        target (str): IP address to ping from the interface.
        interface_dict (dict): interface to IP information
        mtu (int): Actual MTU requested (Do not account for overhead)
        count (int): Number of times to ping the target
        interval (int): How long in seconds between pings
        ctrl (str): Which controller we are on.

    Returns:
        ping_command (list): Subprocess command for the requested args.
    """
    # pylint: disable=global-statement
    global PING_COUNT
    global PING_INTERVAL
    ctrl = get_ctrl_num()
    ping_command = build_ping_command(interface, target, interface_dict, mtu, PING_COUNT, PING_INTERVAL, ctrl)
    status_update('Running command: {}'.format(' '.join(ping_command)))
    try:
        result = subprocess.check_output(ping_command, universal_newlines=True)
    except subprocess.CalledProcessError as pingout:
        result = pingout.output
        CONNECTIVITY_FAILURES.append(['Connectivity', 'FAIL', 'Failed Command: {}'.format(' '.join(ping_command))])
    return str(result)


def pretty_ping(interface, ip_addr, interface_dict):
    # type: (str, str, Dict[str, str]) -> List[str]
    """ Wrapper around default ping to parse results.
    Arguments:
        interface (str): Interface from which to ping
        ip_addr (str): IP address of the target to ping
        interface_dict (dict):

    Returns:
        result (list): Formatted parsed ping results.
    """
    results = ping(interface, ip_addr, interface_dict)
    match_dict = {'interface': interface, 'ip_addr': ip_addr}
    # Match either success or failed pings:
    # 1 packets transmitted, 1 received, 0% packet loss, time 0ms
    # 1 packets transmitted, 0 received, +1 errors, 100% packet loss, time 0ms
    # pylint: disable=line-too-long
    ping_success_regex = re.compile(r'(?P<num_transmitted>\w+) packets transmitted, (?P<num_received>\w+) received,(\s+\+(?P<errors>\w) errors,)? (?P<packet_loss>\w+)% packet loss, time (?P<time>\w+)ms')
    for line in results.splitlines():
        match_out = ping_success_regex.search(str(line))
        # If we have a match for ping_success, we want the time from it.
        if match_out:
            match_dict.update(match_out.groupdict())
            time = float(match_dict['time'])
            str_time = '{0:.2f}s'.format(time / 1000)
            match_dict['time'] = str_time
            break
    result = [match_dict.get('interface', 'ERR'), match_dict.get('ip_addr', 'ERR'), match_dict.get('num_transmitted', 'ERR'), '{}%'.format(match_dict.get('packet_loss', 'ERR')), match_dict.get('time', 'ERR')]
    return result


def ping_target(interfaces, target):
    # type: (List[str], str) -> List[List[str]]
    """ Ping a target from all interfaces. """
    interface_dict = get_interface_dict(interfaces)
    interface_dict.update({val: key for key, val in interface_dict.items()})
    ping_results = [['Interface', 'Target', 'Number Sent', 'Packets Lost (%)', 'Time']]
    for interface in interfaces:
        ping_results.append(pretty_ping(interface, target, interface_dict))
    return ping_results


def ping_peers(interfaces):
    # type: (List[str]) -> List[List[str]]
    """ Ping peer interfaces from each interface. """
    interface_dict = get_interface_dict(interfaces)
    ping_results = [['Interface', 'Target', 'Number Sent', 'Packets Lost (%)', 'Time']]

    for from_interface in sorted(interface_dict):
        for to_interface in sorted((set(interface_dict) - set([from_interface]))):
            to_ip = interface_dict[to_interface]
            ping_results.append(pretty_ping(from_interface, to_ip, interface_dict))

    return ping_results


def parse_interfaces_result(interfaces_result):
    # type: (str) -> List[List[str]]
    """ Returns a printable result from the output of the up/down_interfaces commands. """
    results_list = []
    # Add the first line titles
    if interfaces_result:
        # pylint: disable=line-too-long
        # We only need the first 7 columns of the interface result, so range(7)
        # 0         1        2       3              4              5             6
        # Name      Enabled  Subnet  Address        Mask           Gateway       MTU   MAC                Speed       Services  Slaves
        # ct0.eth6  True     -       10.204.121.24  255.255.252.0  10.204.120.1  1500  90:e2:ba:d7:ea:65  10.00 Gb/s  iscsi     -
        results_list.append([interfaces_result[0].split()[i] for i in range(7)])
    # Add the rest of the lines data
    for line in interfaces_result:
        split_line = line.splitlines()[1].split()
        results_list.append([split_line[i] for i in range(7)])
    return results_list


def _get_nice_interfaces(interfaces):
    """Get a ctX.ethX from a list of ethx."""
    nice_interfaces = []
    str_interf = '{}.{}'
    for ctrl in ('ct0', 'ct1'):
        for interface in interfaces:
            nice_interface = str_interf.format(ctrl.lower(), interface.lower())
            nice_interfaces.append(nice_interface)
    return nice_interfaces


def enable_interfaces(interfaces):
    """Enable all interfaces in a list of ethx."""
    command_results = []
    nice_interfaces = _get_nice_interfaces(interfaces)
    for ct_eth in nice_interfaces:
        command = ['purenetwork', 'enable', ct_eth]
        result = subprocess.check_output(command, universal_newlines=True)
        command_results.append(result)
    return command_results


def disable_interfaces(interfaces):
    """Disable all interfaces in a list of ethx."""
    # Note: This is for utility when testing only - we shouldn't be downing interfaces
    # via code in prod at all in this scripting.
    command_results = []
    nice_interfaces = _get_nice_interfaces(interfaces)
    for ct_eth in nice_interfaces:
        command = ['purenetwork', 'disable', ct_eth]
        result = subprocess.check_output(command, universal_newlines=True)
        command_results.append(result)
    return command_results


def _build_interface_commands(interfaces, ip_addresses=None, gateway=None, subnet_mask=None, bring_up=True):
    """ Builds the command lists for bringing up the interfaces.
        Arguments:
            interfaces (list): Interfaces to bring up.
            ip_addresses (list): string IP addresses to configure in order
            gatway (str): IP address of the gatway to configure
            subnet_mask (str): IP address of the subnet mask to configure
        Returns:
            commands (list): command list for subprocess
    """
    commands = []
    nice_interfaces = _get_nice_interfaces(interfaces)
    for index, ct_eth in enumerate(nice_interfaces):
        # ct_eth = nice_interfaces[index]
        if bring_up:
            address = ip_addresses[index]
            command = ['purenetwork', 'setattr', ct_eth, '--address', str(address),
                       '--gateway', str(gateway), '--netmask', str(subnet_mask)]
        else:
            command = ['purenetwork', 'setattr', ct_eth, '--address', '', '--gateway', '', '--netmask', '']
        commands.append(command)
    return commands


def up_interfaces(interfaces, ip_addresses, gateway, subnet_mask):
    """ Bring up the requested interfaces via purenetwork setattr.
    Arguments:
        tester (network_utils.NetworkTester): NetworkTester for running the commands.
        interfaces (list): ETH[num] interfaces that the IP's should be assigned to.
        ip_addresses (list): IP Addresses that are needed to be brought up.
        gateway (str): IP address of the local gateway the interfaces should be assigned.
        subnet_mask (str): Subnet mask the interfaces should be assigned.

    Returns:
        command_results (dict): Commands with return statuses.
    """
    commands = _build_interface_commands(interfaces, ip_addresses, gateway, subnet_mask)
    command_results = []
    for command in commands:
        status_update(' '.join(command))
        result = subprocess.check_output(command, universal_newlines=True)
        command_results.append(result)
    return parse_interfaces_result(command_results)


def down_interfaces(interfaces, execute=True):
    """ Bring up the requested interfaces via purenetwork setattr.
    Arguments:
        tester (network_utils.NetworkTester): NetworkTester for running the commands.
        interfaces (list): ETH[num] interfaces that the IP's should be assigned to.

    Returns:
        command_results (dict): Commands with return statuses.
    """
    commands = _build_interface_commands(interfaces, bring_up=False)
    command_results = []
    for command in commands:
        status_update(' '.join(command))
        if execute:
            result = subprocess.check_output(command, universal_newlines=True)
            command_results.append(result)
    return parse_interfaces_result(command_results)


def test_connectivity(args):
    """ Bring up interfaces, run tests, and reset them. """
    nice_interfaces = _get_nice_interfaces(args.interfaces)

    if not args.ping_only:
        status_update("\nBringing up and enabling interfaces:\n")
        up_interfaces_result = up_interfaces(args.interfaces, args.ip_addresses, args.gateway, args.subnet_mask)
        # The interfaces will either already be enabled, and this won't matter, or
        # will need to be enabled and this will enable them.
        enable_interfaces(args.interfaces)
    ping_gateway_results = ping_target(nice_interfaces, args.gateway)
    ping_dns_results = ping_target(nice_interfaces, args.dns)
    ping_peers_results = ping_peers(args.interfaces)
    if args.leave_up:
        # This will print the commands but not run them.
        down_interfaces(args.interfaces, execute=False)
    elif args.ping_only:
        # If we ping only we don't want to do anything with interfaces or print anything.
        pass
    else:
        status_update("Bringing down interfaces")
        down_interfaces_result = down_interfaces(args.interfaces)
    status_update()
    print("CONNECTIVITY RESULTS\n")
    if not args.ping_only:
        build_table_and_print(up_interfaces_result)
    build_table_and_print(ping_gateway_results)
    build_table_and_print(ping_dns_results)
    build_table_and_print(ping_peers_results)
    if not args.leave_up and not args.ping_only:
        build_table_and_print(down_interfaces_result)

    if CONNECTIVITY_FAILURES:
        messages = CONNECTIVITY_FAILURES
    else:
        messages = [['Connectivity', 'PASS', 'No connectivity issues']]
    return messages


def test_config():
    """Test configuration settings for pass/fail."""
    messages = []
    # Get hardware models from both controllers
    local_hardware = subprocess.check_output(['hwconfig', '-m'], universal_newlines=True).strip()
    peer_hardware = subprocess.check_output(['ssh', 'peer', 'hwconfig -m'], universal_newlines=True).strip()
    # Get local and peer version strings
    local_version_out = subprocess.check_output(['pureversion'], universal_newlines=True)
    peer_version_out = subprocess.check_output(['ssh', 'peer', 'pureversion'], universal_newlines=True)
    # pureversion output looks like: Purity Version: 4.3.1 - we want the last half stripped.
    local_version = local_version_out.split(':')[-1].strip()
    peer_version = peer_version_out.split(':')[-1].strip()
    # Get purenetwork list output
    pnl = subprocess.check_output(['purenetwork', 'list'], universal_newlines=True)
    # Get tunables output
    tunables = subprocess.check_output(['pureadm', 'list-tunable'], universal_newlines=True)

    messages.extend(check_hardware(local_hardware, peer_hardware))
    messages.extend(check_versions(local_version, peer_version))
    messages.extend(check_iscsi_ports(pnl))
    messages.extend(check_syncrep(local_version, tunables))
    return messages


def interfaces_configured(args):
    """Check if interfaces requested already have configurations."""
    configured_interfaces = []
    # Get purenetwork list lines
    purenetwork_list = subprocess.check_output(['purenetwork', 'list'], universal_newlines=True)
    # Go through PNL lines and if our interfaces are in there, check for
    # an IP and mask.  The assumption is that if either of those are longer
    # than a "-" mark for unconfigured, we add it to the "configured interfaces"
    # list.
    for line in purenetwork_list.splitlines():
        for interface in args.interfaces:
            interface_lower = interface.lower()
            if interface_lower in line.lower():
                interface, _, _, ip_addr, netmask = line.split()[0:5]
                if len(ip_addr) > 1 or len(netmask) > 1:
                    configured_interfaces.append(line)

    if configured_interfaces and not args.ping_only:
        print("FOUND CONFIGURED INTERFACES!  PLEASE CONFIRM YOU'RE USING THE CORRECT INTERFACES!")
        for interface in configured_interfaces:
            print(interface)
        has_configured = True
    else:
        has_configured = False
    return has_configured


def build_command_from_args(args):
    """ Build the bash command flags based on argparse args. """
    command = []
    for arg, value in args.__dict__.items():
        if arg == "interactive":
            continue
        formatted_arg = arg.replace('_', '-')
        if value is False:
            continue
        elif value is True:
            command.append(('--{}'.format(formatted_arg)))
        else:
            if isinstance(value, list):
                values = ' '.join(value)
            else:
                values = value
            command.append(('--{} {}'.format(formatted_arg, values)))
    # Sort the commands for consistency in return order.
    return ' '.join(sorted(command))


def parse_args():
    """ Parse args for wfs_checks.py. """
    # pylint: disable=line-too-long
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--ip-addresses', nargs=4, help='Four IPv4 IP addresses that will be used for the ETH interfaces.', required=True)
    parser.add_argument('--subnet-mask', nargs='?', help='Subnet mask fo the IP addresses that will be used for ETH interfaces (e.g. 255.255.252.0)', required=True)
    parser.add_argument('--gateway', nargs='?', help='IP address of the local gateway (e.g. 10.204.112.150)', required=True)
    parser.add_argument('--dns', nargs='?', help='IP address of the domain name server (e.g. 10.204.112.150)', required=True)
    parser.add_argument('--interfaces', nargs='*', help='ETH interfaces that will be used, if not specified by tunables. (e.g. ETH6 ETH7)', required=True)
    parser.add_argument('--interactive', action=ChangeRequired, help='Enter intformation interactively as prompted!', to_modify=['ip_addresses', 'subnet_mask', 'gateway', 'dns', 'interfaces'], target_value=False)
    parser.add_argument('--leave-up', action='store_true', help='Leave the interfaces up and print the commands to reset them.')
    parser.add_argument('--ping-only', action='store_true', help='Do not modify interfaces - only run ping tests.')
    parser.add_argument('--fast-ping', action='store_true', help=argparse.SUPPRESS)

    exclusive_parsers = parser.add_mutually_exclusive_group(required=False)
    exclusive_parsers.add_argument('--connectivity-only', action=ChangeRequired, help='Only perform connectivity tests.', to_modify=['ip_addresses', 'subnet_mask', 'gateway', 'dns', 'interfaces'], target_value=True)
    exclusive_parsers.add_argument('--config-only', action=ChangeRequired, help='Only perform configuration tests.', to_modify=['ip_addresses', 'subnet_mask', 'gateway', 'dns', 'interfaces'], target_value=False)

    return parser.parse_args()


def get_network_input(message, validation_regex, warning_message=None):
    """ Get input for an IP address with some validation. """
    warning = warning_message or 'Please enter a valid response: '

    tries = 3
    validated = False
    while tries > 0:
        # Added for python2/3 compatibility
        try:
            test_input = raw_input(message)
        except NameError:
            test_input = input(message)
        if not validation_regex.search(test_input):
            message = warning
            tries -= 1
        else:
            validated = True
            break
    if not validated:
        print('Sorry, you entered invalid information too many times!')
    return test_input


def get_args_interactive(args):
    """ Interactively retrieve information for argparse args. """
    ip_regex = re.compile(r'\w+\.\w+\.\w+\.\w+')
    eth_regex = re.compile(r'[Ee][Tt][Hh]\w+')

    # Required external network information
    args.gateway = get_network_input('Please enter the gateway IP address: ', ip_regex)
    args.dns = get_network_input('Please enter the DNS IP address: ', ip_regex)

    # Subnet mask will be applied to all interfaces stood up.
    args.subnet_mask = get_network_input('Please enter the subnet mask (255.255.255.0 format): ', ip_regex)

    # IP addresses that will be assigned.
    first_ip = get_network_input('Please enter the first interface IP address: ', ip_regex)
    second_ip = get_network_input('Please enter the second interface IP address: ', ip_regex)
    third_ip = get_network_input('Please enter the third interface IP address: ', ip_regex)
    fourth_ip = get_network_input('Please enter the fourth interface IP address: ', ip_regex)
    args.ip_addresses = [first_ip, second_ip, third_ip, fourth_ip]

    # Eth interfaces that will be used.
    first_interface = get_network_input('Please enter the first interface (ETHX): ', eth_regex)
    second_interface = get_network_input('Please enter the second interface (ETHX): ', eth_regex)
    args.interfaces = [first_interface, second_interface]

    print('\nFlags for generating the same command:\n')
    print('{} {}'.format(__file__, build_command_from_args(args)))
    print()
    return args


def main():
    """ Run tests for WFS installs. """
    args = parse_args()
    # Various checks to make sure input is solid.
    if args.interactive:
        args = get_args_interactive(args)
    # If we want this to go quick, we may fail erroneously sometimes, but it's super fast.
    if args.fast_ping:
        global PING_COUNT
        global PING_INTERVAL
        PING_COUNT = 1
        PING_INTERVAL = 0.25

    # Process the checks.
    results = []
    if args.connectivity_only and not interfaces_configured(args):
        results.extend(test_connectivity(args))
    elif args.config_only:
        results.extend(test_config())
    elif not interfaces_configured(args):
        results.extend(test_connectivity(args))
        results.extend(test_config())
    # These are sorted by check name
    results = sorted(results)
    results.insert(0, ['CHECK', 'STATUS', 'DESCRIPTION'])
    print('\nTEST RESULTS:\n')
    build_table_and_print(results)


if __name__ == '__main__':
    main()
