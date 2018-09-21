#!/usr/bin/env python
"""Self contained Health Check script to determine array state durring Sev1 situations."""

from __future__ import print_function

import argparse
import datetime
import os
import re
import subprocess

from collections import defaultdict

# Pre-defined array states.
UNKNOWN_STATE = 'UNKNOWN'
HEALTHY_STATE = 'HEALTHY'
WARN_STATE = 'WARNING'
ERROR_STATE = 'ERROR'
CRIT_STATE = 'CRITICAL'
# bin is used for tools such as unix_peer.py.
PURITY_BIN = '/opt/Purity/bin'
# sbin is used for Purity commands such as purearray.
PURITY_SBIN = '/opt/Purity/sbin'
# Array state variables.
ARRAY_STATE = UNKNOWN_STATE
PEER_REACHABLE = False
LOCAL_CTLR = defaultdict(list)
PEER_CTLR = defaultdict(list)


class SOSHealthCheck(object):
    """Base class for individual checks."""

    # A results_table that we can populate with results and print/return.
    results_table = [['Check State', 'Check Name', 'Information']]
    # We need a place to hold all of the check details.
    details = []

    def __init__(self, check_name=None, check_state=None, check_message=None):
        self.name = check_name
        self.state = check_state
        self.message = check_message
        self.results = []
        self.check_on_failure = None
        self.run_failure_checks = False

    @classmethod
    def get_results(cls):
        """Get the final results."""
        health_check = cls()
        return health_check.results_table

    def run_on_both_ctlrs(self, fuct):
        """Run fuct on both controllers if possible."""
        default_state = self.state
        default_msg = self.message
        fuct(on_peer=False)
        if PEER_REACHABLE:
            # In between runs of this function we need the defualts to prevent bleedover.
            self.state = default_state
            self.message = default_msg
            fuct(on_peer=True)

    def update_array_state(self):
        """Change the ARRAY_STATE and print a change message.

        Argument:
            new_state (str): New value for ARRAY_STATE to be changed to.
        """
        state_weight = {
            UNKNOWN_STATE: 0,
            HEALTHY_STATE: 1,
            WARN_STATE:    2,
            ERROR_STATE:   3,
            CRIT_STATE:    4,
        }
        global ARRAY_STATE
        if state_weight.get(self.state, 0) > state_weight.get(ARRAY_STATE, 0):
            message = 'NOTICE: Check "{}", changed the Array State: {} --> {}'
            print(message.format(self.name, ARRAY_STATE, self.state))
            ARRAY_STATE = self.state


class PeerConnection(SOSHealthCheck):
    """Check the Peer controller to see if it is reachable."""

    def __init__(self):
        # We cannot communicate with the Peer controller until proven otherwise.
        message = 'Unable to communicate with the "peer" controller.'
        super(PeerConnection, self).__init__('Peer Connectivity', WARN_STATE, message)

    def run_check(self):
        """Perform checks to determine if the peer is reachable."""
        unix_peer = os.path.join(PURITY_BIN, 'unix_peer.py')
        command = [unix_peer, 'get']
        peer_ip = run_command(command)
        details = list(peer_ip)
        if peer_ip:
            # The peer_ip should only have one entry and we need it in string format.
            peer_ip = peer_ip[0]
            if '%' in peer_ip:
                ping_response = run_command('ping6 -c 1 {}'.format(peer_ip), splitlines=False)
                details.append(ping_response)
                if '1 packets transmitted, 1 received, 0% packet loss,' in ping_response:
                    global PEER_REACHABLE
                    PEER_REACHABLE = True
                    self.state = HEALTHY_STATE
                    self.message = 'Connection to peer controller is up.'
        # Results of test.
        self.details.append((self.name, details))
        self.update_array_state()
        self.results = [self.state, self.name, self.message]
        self.results_table.append(self.results)
        return self.results


class ControllerStatus(SOSHealthCheck):
    """Check the controller status for any issues.

    Looking at output below:
    root@slc-coz-ct0:~# purearray list --controller
    Name  Mode       Model   Version  Status
    CT0   primary    FA-420  4.10.6   ready
    CT1   secondary  FA-420  4.10.6   ready
    """

    def __init__(self):
        message = 'Unable to determine controller status.'
        super(ControllerStatus, self).__init__('Controller Status', UNKNOWN_STATE, message)
        # Setting up base controller states.
        self.ctlr_x = defaultdict(list)
        self.ctlr_y = defaultdict(list)
        # Setting up checks to run if state is not HEALTHY_STATE.
        self.check_on_failure = [
            # MissingDrives(), TODO...
            PureadmStatus(),
        ]

    def run_check(self):
        """Perform the checks required to check Controller Status."""
        purearray = os.path.join(PURITY_SBIN, 'purearray')
        command = '{} list --controller'.format(purearray)
        output = run_command(command)
        ctlr_count = self._build_ctlr_parts(output)
        if self.state != UNKNOWN_STATE:
            if ctlr_count == 0:
                self.state = ERROR_STATE
                self.message = 'No controllers found!'
            elif ctlr_count == 1:
                single_ctlr = 'Only one controller, "{}", found!'.format(self.ctlr_x['name'])
                if self.ctlr_x['mode'] != "primary":
                    self.state = ERROR_STATE
                    self.message = ' '.join([single_ctlr, 'It is NOT Primary!'])
                elif self.ctlr_x['status'] != "ready":
                    self.state = ERROR_STATE
                    self.message = ' '.join([single_ctlr, 'It is Primary BUT not ready!'])
                else:
                    self.state = WARN_STATE
                    self.message = ' '.join([single_ctlr, 'It is up and Primary at this time.'])
            else:
                self._get_worst_controller_status()
        # Results of test.
        self.details.append((self.name, output))
        if self.state != HEALTHY_STATE:
            self.run_failure_checks = True
        self.update_array_state()
        self.results = [self.state, self.name, self.message]
        self.results_table.append(self.results)
        return self.results

    def _build_ctlr_parts(self, output):
        """Build the controller parts and return them with a state and message."""
        # We assume HEALTHY_STATE until proven otherwise.
        self.state = HEALTHY_STATE
        self.message = 'Both controllers are "Ready".'
        ctlr_count = 0
        headers = []
        for line in output:
            # Old output:
            # Name  Mode       Model   Version  Status
            # CT0   primary    FA-420  4.10.6   ready
            # CT1   secondary  FA-420  4.10.6   ready

            # New output:
            # Name     Type              Mode       Model   Version  Status
            # CT0      array controller  primary    FA-X70  99.9.9   ready
            # CT1      array controller  secondary  FA-X70  99.9.9   ready
            # SH9.SC0  shelf controller  -          DFSC1   1.0.0    -
            # SH9.SC1  shelf controller  -          DFSC1   1.0.0    -

            # For uniformity, removing the word controller.
            line = line.replace('controller', '')
            if 'Name' in line:
                # Header examples:
                # OLD: ['Name', 'Mode', 'Model', 'Version', 'Status']
                # NEW: ['Name', 'Type', 'Mode', 'Model', 'Version', 'Status']
                headers = [item.lower() for item in line.split()]
            elif 'CT' in line:
                # Examples:
                # OLD: ['CT0', 'primary', 'FA-420', '4.10.6', 'ready']
                # NEW: ['CT0', 'array', 'primary', 'FA-X70', '99.9.9', 'ready']
                parts = line.split()
                if len(parts) != len(headers):
                    # This means that somehow the output is malformed.
                    self.state = UNKNOWN_STATE
                    self.message = 'Unable to determine controller status.'
                    break
                # Now that we have verified that headers and parts have the same count
                # we build out the dict contents.
                if not self.ctlr_x['name']:
                    ctlr_dict = self.ctlr_x
                else:
                    ctlr_dict = self.ctlr_y
                for index, part in enumerate(parts):
                    ctlr_dict[headers[index]] = part
                ctlr_count += 1
        # Determine which controller is local if we are able to.
        ctlr_name = get_ctlr_name().strip().lower()
        global LOCAL_CTLR
        global PEER_CTLR
        if self.ctlr_x.get('name') and ctlr_name.endswith(self.ctlr_x.get('name').lower()):
            LOCAL_CTLR = self.ctlr_x
            PEER_CTLR = self.ctlr_y
        elif self.ctlr_y.get('name') and ctlr_name.endswith(self.ctlr_y.get('name').lower()):
            LOCAL_CTLR = self.ctlr_y
            PEER_CTLR = self.ctlr_x
        return ctlr_count

    def _get_worst_controller_status(self):
        """Check controllers for the worst status and return it."""
        self.state = HEALTHY_STATE
        self.message = 'Both controllers are up and in the Ready status.'
        if self.ctlr_x['mode'] == 'primary' and self.ctlr_y['mode'] == 'primary':
            self.state = CRIT_STATE
            self.message = 'Split Brain! {}'.format(compare_values('status'))
        elif self.ctlr_x['mode'] != 'primary' and self.ctlr_y['mode'] != 'primary':
            self.state = ERROR_STATE
            self.message = 'No Primary found! {}'.format(compare_values('mode'))
        elif (self.ctlr_x['mode'] == 'primary' and self.ctlr_x['status'] != 'ready') or \
             (self.ctlr_y['mode'] == 'primary' and self.ctlr_y['status'] != 'ready'):
            self.state = ERROR_STATE
            self.message = 'Primary not ready! {}'.format(compare_values('status'))
        elif self.ctlr_x['mode'] != 'secondary' and self.ctlr_y['mode'] != 'secondary':
            self.state = WARN_STATE
            self.message = 'No secondary controller. {}'.format(compare_values('mode'))
        elif (self.ctlr_x['mode'] == 'secondary' and self.ctlr_x['status'] != 'ready') or \
             (self.ctlr_y['mode'] == 'secondary' and self.ctlr_y['status'] != 'ready'):
            self.state = WARN_STATE
            statuses = compare_values('status')
            self.message = 'Secondary controller not ready. {}'.format(statuses)


class PureadmStatus(SOSHealthCheck):
    """Check pureadm status to determine what services are not running.

    Looking at output below:
    root@SLC-405-2-ct0:~# pureadm status
    Process status:
        purity start/running
        lio-drv start/running
        cached start/running, process 33905
        foed start/running, process 33915
        platform start/running, process 33214
        gui start/running, process 33261
        rest start/running, process 33226
        monitor start/running, process 33222
        iostat start/running, process 34702
        statistics start/running, process 33224
        middleware start/running, process 33270
        platform working
        foed working
        gui working
        platform_env working
        foed_env working
        remote_patch working
        driver working
        san working
        health working
        lio-drv working
        middleware working
    """

    def __init__(self):
        # We are in a HEALTHY_STATE until proven otherwise.
        message = 'Both controllers have all services fully running'
        super(PureadmStatus, self).__init__('Pureadm Status', HEALTHY_STATE, message)

    def run_check(self):
        """Get pureadm status for both controllers."""
        self.run_on_both_ctlrs(self.check_pureadm_status)
        return self.results

    def check_pureadm_status(self, on_peer):
        """Check pureadm status to determine what services are not running."""
        # Setting the state that we want to stay in.
        bad_processes = []
        pureadm = os.path.join(PURITY_BIN, 'pureadm')
        command = [pureadm, 'status']
        ctlr_name = rename_me('pureadm status', on_peer)
        details = []
        if on_peer and not PEER_REACHABLE:
            self.state = UNKNOWN_STATE
            self.message = 'Peer not reachable to perform check.'
        else:
            output = run_command(command, on_peer=on_peer)
            details.extend(output)
            for line in output:
                # We do not need to look at the 'Process status:' line so we continue.
                if 'status:' in line:
                    continue
                split_line = line.split()
                process_name = split_line[0]
                status = split_line[1]
                # Removing the comma from the status for uniformity.
                status = status.replace(',', '')
                # Status should be 'working' or 'running' anything else is unexpected.
                if status not in ('working', '\x1b[34;32mworking\x1b[0m', 'start/running'):
                    bad_processes.append(process_name)
            if bad_processes:
                self.state = ERROR_STATE
                self.message = 'Processes in unexpected state: {}'.format(', '.join(bad_processes))
        # Results of test.
        self.details.append((ctlr_name, details))
        self.update_array_state()
        result = [self.state, ctlr_name, self.message]
        self.results_table.append(result)
        self.results.append(result)


class ControllerVersionMatch(SOSHealthCheck):
    """Check the versions on both controllers to verify that they match."""

    def __init__(self):
        # We are in a HEALTHY_STATE until proven otherwise.
        message = 'Purity versions match: {}'
        super(ControllerVersionMatch, self).__init__('Matching Versions', HEALTHY_STATE, message)

    def run_check(self):
        """Verify purity versions match."""
        # We use the .get() method to ensure we do not crash if values did not get set.
        details = []
        if LOCAL_CTLR.get('version') and PEER_CTLR.get('version'):
            versions = compare_values('version')
            details.append(versions)
            if LOCAL_CTLR['version'] != PEER_CTLR['version']:
                self.state = ERROR_STATE
                self.message = 'Purity version mismatch: {}'.format(versions)
            else:
                self.message = self.message.format(versions)
        else:
            local_version = LOCAL_CTLR.get('version', 'UNKNOWN')
            peer_version = PEER_CTLR.get('version', 'UNKNOWN')
            details.append('LOCAL:{} | PEER:{}'.format(local_version, peer_version))
            self.state = UNKNOWN_STATE
            self.message = 'Not enough information to compare Purity versions.'
        # Results of test.
        self.details.append((self.name, details))
        self.update_array_state()
        self.results = [self.state, self.name, self.message]
        self.results_table.append(self.results)
        return self.results


class CorruptionCrumb(SOSHealthCheck):
    """Check for corruption crumbs on available controller(s)."""

    def __init__(self):
        # We are in a HEALTHY_STATE until proven otherwise.
        super(CorruptionCrumb, self).__init__('Corruption Cumbs', HEALTHY_STATE, 'No Corruption crumbs found.')

    def run_check(self):
        """Look for corruption crumbs."""
        self.run_on_both_ctlrs(self.check_corruption_crumbs)
        return self.results

    def check_corruption_crumbs(self, on_peer):
        """Check for corruption crumbs on available controller(s)."""
        ctlr_dict = get_latest_logs(on_peer)
        latest_cores = _get_latest_logs_by_type(ctlr_dict, 'core.log')
        ctlr_name = rename_me(self.name, on_peer)
        args = ['-h', '" K "'] + latest_cores
        k_crumbs = zgrep(args, on_peer=on_peer)
        if k_crumbs:
            self.state = CRIT_STATE
            # TODO: It would be helpful to see what types of K crumbs were found.
            # TODO: Find a way to consistantly pull this info from the lines.
            # https://support.purestorage.com/FlashArray/PurityFA/PurityFA_Alerts/Internal_Alerts/Alert_0032_-_Foed_Error_Detected
            self.message = 'Corruption crumbs found! See details section below.'
        # Results of test.
        self.details.append((self.name, k_crumbs))
        self.update_array_state()
        result = [self.state, ctlr_name, self.message]
        self.results_table.append(result)
        self.results.append(result)


class FoedUptime(SOSHealthCheck):
    """Determine Foed uptime of the controllers."""

    def __init__(self):
        # We are in a HEALTHY_STATE until proven otherwise.
        super(FoedUptime, self).__init__('Foed Uptime', HEALTHY_STATE, 'Controller uptime is {}.')
        # Setting up checks to run if state is not HEALTHY_STATE.
        self.check_on_failure = [
            ControllerStateChanges(),
        ]

    def run_check(self):
        """Check the Foed uptime on both controllers."""
        self.run_on_both_ctlrs(self.check_foed_uptime)
        return self.results

    def check_foed_uptime(self, on_peer):
        """Return the foed uptime as a timedelta object."""
        ctlr_dict = get_latest_logs(on_peer)
        latest_cores = _get_latest_logs_by_type(ctlr_dict, 'core.log')
        ctlr_name = rename_me(self.name, on_peer)
        # Example line:
        # Dec  9 07:18:56.563 7FEB77BEE700 I     osenv.jobs Purity 4.1.8 201507311732+4873eaf-41x (release) uptime 71d:5h:56m:37s
        # Dec  1 17:14:48.794 000000000C82 I     osenv.jobs Purity 4.10.6 201709261730+804621d-410e (release) uptime 52d:9h:7m:10s
        args = ['-h', '"(release) uptime"'] + latest_cores
        output = zgrep(args, on_peer=on_peer)
        pattern = re.compile(r'\(release\)\s+uptime\s+(?P<days>\d+)d:(?P<hours>\d+)h:(?P<mins>\d+)m:\d+s')
        # We need the last uptime.
        # Looking through output in reverse allows us to find the latest uptime from the logs.
        days = hours = mins = 0
        for line in sorted(output, reverse=True):
            match = pattern.search(line)
            if match:
                days = int(match.group('days'))
                hours = int(match.group('hours'))
                mins = int(match.group('mins'))
                break
        timedelta = datetime.timedelta(days=days, hours=hours, minutes=mins)
        total_hours = int(timedelta.total_seconds() / 3600)
        if not output:
            # This is expected for the secondary controller unless an HA event occurred.
            self.message = 'No uptime lines found for this controller.'
        elif total_hours < 24:
            self.state = WARN_STATE
            self.message = 'Controller uptime is {} hours.'.format(total_hours)
        else:
            time = '{} Days {} Hours {} Minutes'.format(days, hours, mins)
            self.message = self.message.format(time)
        # Results of test.
        self.details.append((ctlr_name, output))
        if self.state not in (HEALTHY_STATE, UNKNOWN_STATE):
            self.run_failure_checks = True
        self.update_array_state()
        result = [self.state, ctlr_name, self.message]
        self.results_table.append(result)
        self.results.append(result)


class ControllerStateChanges(SOSHealthCheck):
    """Show controller state changes."""

    def __init__(self):
        # We are in a HEALTHY_STATE until proven otherwise.
        message = 'No controller state changes found.'
        super(ControllerStateChanges, self).__init__('State Changes', HEALTHY_STATE, message)

    def run_check(self):
        """Determine all state changes of the controller(s)."""
        self.run_on_both_ctlrs(self.get_ctlr_state_changes)
        return self.results

    def get_ctlr_state_changes(self, on_peer):
        """Get controller state changes from logs."""
        ctlr_dict = get_latest_logs(on_peer)
        latest_platforms = _get_latest_logs_by_type(ctlr_dict, 'platform.log')
        ctlr_name = rename_me(self.name, on_peer)
        args = ['-E', '"Primary|Secondary|Takeover|Giveback"'] + latest_platforms
        output = zgrep(args, on_peer=on_peer)
        if output:
            self.state = WARN_STATE
            self.message = 'Controller state changes detected. See details section below.'
        # Results of test.
        self.details.append((ctlr_name, output))
        self.update_array_state()
        result = [self.state, ctlr_name, self.message]
        self.results_table.append(result)
        self.results.append(result)


def rename_me(check_name, on_peer):
    """Determine if local or peer controller based on on_peer value.

    Arguments:
        check_name (str): The self.name of the check that is running.
        on_peer (bool): Indicates if the command is run on the local controller or the peer.

    Return:
        ctlr_name (str): Renamed check name with peer/local based on on_peer value.
    """
    where = 'local'
    if on_peer:
        # A space at the beginning of peer to help align with local.
        where = ' peer'
    ctlr_name = ': '.join([where, check_name])
    return ctlr_name


def compare_values(key):
    """To help illustrate where problems are we compare values from both controllers.

    Argument:
        key (str): Dictionary found in LOCAL_CTLR and PEER_CTLR.

    Return:
        result (str): Combined values for LOCAL_CTLR and PEER_CTLR.
    """
    # Example: 'CT0:primary | CT1:secondary'
    local_ctlr = ':'.join([LOCAL_CTLR['name'], LOCAL_CTLR[key]])
    peer_ctlr = ':'.join([PEER_CTLR['name'], PEER_CTLR[key]])
    result = ' | '.join([local_ctlr, peer_ctlr])
    return result


def get_latest_logs(on_peer):
    """Collect the latest logs from local or peer controller.

    Argument:
        on_peer (bool): Indicates if the command is run on the local controller or the peer.

    Return:
        (dict): LOCAL_CTLR or PEER_CTLR based on value of on_peer
    """
    log_loc = '/var/log/purity/{}*'
    required_logs = ('core.log', 'platform.log', 'hardware.log')
    needed_files = [log_loc.format(log) for log in required_logs]
    ls_logs_cmd = 'ls {}'.format(' '.join(needed_files))
    files = run_command(ls_logs_cmd, on_peer=on_peer)
    # ctlr_dict is just a pointer to LOCAL_CTLR/PEER_CTLR dict.
    ctlr_dict = get_ctlr_dict(on_peer)
    for log_file in sorted(files):
        for log_type in required_logs:
            # The check to make sure files are not already in the ctlr_dict is to not end up with
            # duplicate file names under the log_type. This is to allow unit tests to only need
            # a single controller.
            if log_type in log_file and log_file not in ctlr_dict[log_type]:
                ctlr_dict[log_type].append(log_file)
    return ctlr_dict


def get_ctlr_dict(on_peer):
    """Provide a pointer to the dictionary of local/peer controller.

    Argument:
        on_peer (bool): Indicates if the command is run on the local controller or the peer.

    Return:
        (dict): LOCAL_CTLR or PEER_CTLR based on value of on_peer
    """
    if on_peer:
        return PEER_CTLR
    return LOCAL_CTLR


def _get_print_text(line, max_column_widths):
    """Get the formatted text."""
    print_line = []
    for index, item in enumerate(line):
        pattern = '{:<{wid}}'
        print_line.append(pattern.format(item, wid=max_column_widths[index]))
    return print_line


def print_results(results_table):
    """Print results_table in a pretty table that's easy to read in terminal and JIRA.

    Argument:
        results_table (list): This should be a list of lists so we can print a JIRA friendly table.

    Return:
        final_output (list): A list of strings for testing purposes.
    """
    final_output = []
    max_column_widths = []
    color_reset = '\x1b[39;49;00m'
    print_colors = {
        UNKNOWN_STATE: '\x1b[0;35;40m',  # MAGENTA foreground
        HEALTHY_STATE: '\x1b[0;32;40m',  # GREEN foreground
        WARN_STATE:    '\x1b[0;33;40m',  # YELLOW foreground
        ERROR_STATE:   '\x1b[0;31;40m',  # RED foreground
        CRIT_STATE:    '\x1b[1;37;41m',  # WHITE foreground, RED background
    }
    for col_num in range(len(results_table[0])):
        max_column_widths.append(max([len(line[col_num]) for line in results_table]))
    print()  # Giving us a newline before our results table.
    for line in results_table:
        print_line = _get_print_text(line, max_column_widths)
        if 'Check State' in line:
            # This changes the headers line into a table header within JIRA.
            middle = ' ||'.join(print_line)
            line_text = ''.join(['||', middle, '||'])
        else:
            middle = ' | '.join(print_line)
            line_text = ''.join(['| ', middle, ' |'])
        final_output.append(line_text)
        # Add some colors based on the state.
        for state, color in print_colors.items():
            if state in line_text:
                color_text = ''.join([color, state, color_reset])
                line_text = line_text.replace(state, color_text)
                break
        print(line_text)
    return final_output


def _print_details(contents):
    """Print the contents of the details from all run checks."""
    spacer = '=' * 79
    header = '\n{{noformat:title={} Details}}'
    for name, info in contents:
        print(header.format(name))
        print(spacer)
        if not info:
            print('*** NOTHING TO REPORT HERE ***')
        else:
            for line in info:
                print(line)
        print('\n', spacer)
        print('{noformat}')


def run_command(command, on_peer=False, splitlines=True):
    """Run commands on current or peer controller.

    Arguments:
        command (str/list): The command to be run.
        on_peer (bool): Indicates if the command is run on the local controller or the peer.
        splitlines (bool): If set to False the lines will be returned back in string format.

    Return:
        output (list): STDOUT from the command that was run.
    """
    cmd, shell = _prepare_command(command, on_peer)
    try:
        output = subprocess.check_output(cmd, shell=shell)
        if splitlines:
            output = output.splitlines()
    except subprocess.CalledProcessError as err:
        # If something prevents the command from finishing we hopefully will get something
        # that we can return. The caller must be able to handle empty output.
        print('Command {} exited with code {},'.format(err.cmd, err.returncode))
        output = err.output
    return output


def zgrep(args, on_peer=False):
    """Wrapper for the oft-troublesome zgrep command.

    Handles:
        1) normal non-zero exit codes indicating no matches were found
        2) 'unexpected end of file' errors from gunzip and higher-level commands like zgrep

    Arguments:
        args (list): zgrep arguments to be used.
        on_peer (bool): Indicates if the command is run on the local controller or the peer.

    Return:
        output (list): STDOUT from the zgrep that was run.
    """
    whitelist = ['unexpected end of file']
    cmd = ['zgrep'] + args
    command, shell = _prepare_command(cmd, on_peer)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    output, err = proc.communicate()
    # Stripping out any ampty lines from the STDERR.
    errlines = filter(None, map(str.strip, err.splitlines()))
    return_code = proc.returncode
    # Code 0 means matches found and no error
    # Code 1 means at least one file had no matches. We are happy to return all the other matches.
    if return_code not in (0, 1):
        # We are OK as long as all errors are on our whitelist.
        for line in errlines:
            if not any(wl in line for wl in whitelist):
                raise subprocess.CalledProcessError(return_code, command, output=output)
    return output.splitlines()


def _prepare_command(command, on_peer):
    """Take command and on_peer to build the command and shell values we need."""
    shell = True
    if not isinstance(command, list):
        if on_peer:
            shell = False
            command = ['ssh', 'peer', command]
    else:
        shell = False
        if on_peer:
            command = ['ssh', 'peer'] + command
    return command, shell


def _get_latest_logs_by_type(ctlr_dict, log_type):
    """Get the latest log types."""
    latest_logs = []
    # We need the last two core.log files for this test.
    if log_type in ctlr_dict[log_type]:
        # In older Purity versions we write to a core.log file with no date and not gzipped.
        latest_logs.append(log_type)
        latest_logs.append(sorted(ctlr_dict[log_type])[-1:])
    else:
        # In some versions of Purity we have unzipped files with dates.
        # This will capture those files.
        latest_logs.extend(sorted(ctlr_dict[log_type])[-2:])
    return latest_logs


def get_ctlr_name():
    """Get the name of the local controller."""
    command = 'uname -n'
    ctlr_name = run_command(command, splitlines=False)
    return ctlr_name


def parse_args():
    """Argument parser."""
    # TODO: Fix the epilog to point to a KB that talks about this SOS report.
    epi = 'https://wiki.purestorage.com/display/psw/SEV-1+Emergency+Playbook'
    parser = argparse.ArgumentParser(description=__doc__, epilog=epi)
    parser.add_argument('--simple', '-s', action='store_true', help='Removes the details section.')
    # TODO: Add arg(s) that allow running only specific health checks.
    return parser.parse_args()


def main():
    """Self contained Health Check script to be run on the FlashArray."""
    args = parse_args()
    checklist = [
        PeerConnection(),
        ControllerStatus(),
        ControllerVersionMatch(),
        CorruptionCrumb(),
        FoedUptime(),
    ]
    for check in checklist:
        print(check.name)
        check.run_check()
        if check.run_failure_checks:
            for additional_check in check.check_on_failure:
                additional_check.run_check()
    # The last check will contain all the values we need to print the results_table.
    print_results(check.results_table)
    if not args.simple:
        _print_details(check.details)


if __name__ == '__main__':
    main()
