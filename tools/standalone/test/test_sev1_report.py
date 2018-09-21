"""Unit tests for sev1_report.py."""

import pytest

from photon.tools.standalone import sev1_report

# This is the state of the check that needs to be run.
# It is used by offline_run_command to determine which command dict to use.
STATE = None
# A command/output dict to make these tests work.
HEALTHY_CMD_OUTPUT = {
    '/opt/Purity/bin/unix_peer.py get':
        ['fe80::f652:1403:90:9fe1%8'],
    'ping6 -c 1 fe80::f652:1403:90:9fe1%8':
        'PING fe80::f652:1403:90:9fe1%8(fe80::f652:1403:90:9fe1) 56 data bytes\n64 bytes from fe80::f652:1403:90:9fe1: icmp_seq=1 ttl=64 time=0.068 ms\n\n--- fe80::f652:1403:90:9fe1%8 ping statistics ---\n1 packets transmitted, 1 received, 0% packet loss, time 0ms\nrtt min/avg/max/mdev = 0.068/0.068/0.068/0.000 ms\n',
    '/opt/Purity/sbin/purearray list --controller':
        ['Name  Mode       Model   Version  Status',
         'CT0   primary    FA-405  4.7.6    ready ',
         'CT1   secondary  FA-405  4.7.6    ready '],
    '/opt/Purity/bin/pureadm status':
        ['Process status:',
         'purity start/running',
         'lio-drv start/running',
         'cached start/running, process 33905',
         'foed start/running, process 33915',
         'platform start/running, process 33214',
         'gui start/running, process 33261',
         'rest start/running, process 33226',
         'monitor start/running, process 33222',
         'iostat start/running, process 14901',
         'statistics start/running, process 33224',
         'middleware start/running, process 33270',
         'platform working',
         'foed working',
         'gui working',
         'platform_env working',
         'foed_env working',
         'remote_patch working',
         'driver working',
         'san working',
         'health working',
         'lio-drv working',
         'middleware working'],
    'ls /var/log/purity/core.log* /var/log/purity/platform.log* /var/log/purity/hardware.log*':
        ['/var/log/purity/core.log-00.gz',
         '/var/log/purity/core.log-01.gz',
         '/var/log/purity/platform.log-00.gz',
         '/var/log/purity/platform.log-01.gz',
         '/var/log/purity/hardware.log-00.gz'],
    'zgrep -h " K " /var/log/purity/core.log-00.gz /var/log/purity/core.log-01.gz':
        [],
    'zgrep -h "(release) uptime" /var/log/purity/core.log-00.gz /var/log/purity/core.log-01.gz':
        ['Jan 17 07:08:21.125 000000000C94 I      osenv.jobs Purity 4.10.6 201709261730+804621d-410e (release) uptime 98d:23h:0m:42s',
         'Jan 17 07:13:21.459 000000000C8E I      osenv.jobs Purity 4.10.6 201709261730+804621d-410e (release) uptime 98d:23h:5m:42s',
         'Jan 17 07:18:21.881 000000000C7D I      osenv.jobs Purity 4.10.6 201709261730+804621d-410e (release) uptime 98d:23h:10m:43s'],
    'zgrep -E "Primary|Secondary|Takeover|Giveback" /var/log/purity/platform.log-00.gz /var/log/purity/platform.log-01.gz':
        [],
}
WARNING_CMD_OUTPUT = {
    '/opt/Purity/bin/unix_peer.py get':
        ['fe80::f652:1403:90:9fe1%8'],
    'ping6 -c 1 fe80::f652:1403:90:9fe1%8':
        'PING fe80::f652:1403:90:9fe1%8(fe80::f652:1403:90:9fe1) 56 data bytes\n--- fe80::f652:1403:90:9fe1%8 ping statistics ---\n1 packets transmitted, 0 received, 100% packet loss, time 0ms\nrtt min/avg/max/mdev = 0.068/0.068/0.068/0.000 ms\n',
    '/opt/Purity/sbin/purearray list --controller':
        ['Name  Mode       Model   Version  Status',
         'CT0   primary    FA-405  4.7.6    ready ',
         'CT1   secondary  FA-405  4.7.6    unknown '],
    'ls /var/log/purity/core.log* /var/log/purity/platform.log* /var/log/purity/hardware.log*':
        ['/var/log/purity/core.log-00.gz',
         '/var/log/purity/core.log-01.gz',
         '/var/log/purity/platform.log-00.gz',
         '/var/log/purity/platform.log-01.gz',
         '/var/log/purity/hardware.log-00.gz'],
    'zgrep -h "(release) uptime" /var/log/purity/core.log-00.gz /var/log/purity/core.log-01.gz':
        ['Jan 17 07:08:21.125 000000000C94 I      osenv.jobs Purity 4.10.6 201709261730+804621d-410e (release) uptime 0d:23h:0m:42s',
         'Jan 17 07:13:21.459 000000000C8E I      osenv.jobs Purity 4.10.6 201709261730+804621d-410e (release) uptime 0d:23h:5m:42s',
         'Jan 17 07:18:21.881 000000000C7D I      osenv.jobs Purity 4.10.6 201709261730+804621d-410e (release) uptime 0d:23h:10m:43s'],
    'zgrep -E "Primary|Secondary|Takeover|Giveback" /var/log/purity/platform.log-00.gz /var/log/purity/platform.log-01.gz':
        ['P1 ->  Mar 18 20:51:43.285 7F01F7249700 B         storage.failover [platform_framework] Primary -> Giveback',
         'P1 ->  Mar 18 20:51:43.291 7F01F7249700 B         storage.failover [platform_framework] Giveback -> Secondary'],
}
ERROR_CMD_OUTPUT = {
    '/opt/Purity/bin/pureadm status':
        ['Process status:',
         'purity start/running',
         'lio-drv start/running',
         'cached start/running, process 33905',
         'foed start/running, process 33915',
         'platform start/running, process 33214',
         'gui start/running, process 33261',
         'rest start/running, process 33226',
         'monitor start/running, process 33222',
         'iostat start/running, process 14901',
         'statistics start/running, process 33224',
         'middleware start/running, process 33270',
         'platform working',
         'foed working',
         'gui working',
         'platform_env working',
         'foed_env working',
         'remote_patch not responding',
         'driver working',
         'san working',
         'health working',
         'lio-drv working',
         'middleware working'],
}
CRITICAL_CMD_OUTPUT = {
    'zgrep -h " K " /var/log/purity/core.log-00.gz /var/log/purity/core.log-01.gz':
        ['Aug  5 04:11:04.040 7F4609DF7700 K     vol.au.rpt We should always have a mask of some form that covers cbmap tuple: ((10088804, 30339452672), 7, 67430), (((8796, 4, 326), 31), 32, 9168)'],
    'ls /var/log/purity/core.log* /var/log/purity/platform.log* /var/log/purity/hardware.log*':
        ['/var/log/purity/core.log-00.gz',
         '/var/log/purity/core.log-01.gz',
         '/var/log/purity/platform.log-00.gz',
         '/var/log/purity/platform.log-01.gz',
         '/var/log/purity/hardware.log-00.gz'],
}
CMD_DICT = {
    'HEALTHY': HEALTHY_CMD_OUTPUT,
    'WARNING': WARNING_CMD_OUTPUT,
    'ERROR': ERROR_CMD_OUTPUT,
    'CRITICAL': CRITICAL_CMD_OUTPUT,
}


def offline_run_command(command, on_peer=False, shell=False, splitlines=True):
    """Run commands on current or peer controller.

    Arguments:
        command (str/list): The command to be run.
        on_peer (bool): Indicates if the command is run on the local controller or the peer. [UNUSED]
        shell (bool): The shell value to pass to subprocess. [UNUSED]

    Return:
        output (list): Simulated output from the command line.
    """
    if isinstance(command, list):
        # To make the look-up easier.
        command = ' '.join(command)
    output = CMD_DICT[STATE][command]
    return output


def offline_zgrep(args, on_peer=False):
    """An offline version of the zgrep function.

    Arguments:
        args (list): Online fuction needs the arg [UNUSED]
        on_peer (bool): Indicates if the command is run on the local controller or the peer. [UNUSED]

    Return:
        output (list): Simulated output from the command line.
    """
    zgrep = ['zgrep'] + args
    return offline_run_command(zgrep, on_peer=on_peer)


@pytest.fixture(autouse=True)
def offline_functs(monkeypatch):
    """Replace online functs with offline functs."""
    monkeypatch.setattr(sev1_report, 'run_command', offline_run_command)
    monkeypatch.setattr(sev1_report, 'zgrep', offline_zgrep)
    monkeypatch.setattr(sev1_report, 'get_ctlr_name', lambda: 'fake-host-ct0')


def test_peer_connection_green():
    """Test the PeerConnection health check."""
    global STATE
    STATE = 'HEALTHY'
    health_check = sev1_report.PeerConnection()
    expected = ['HEALTHY', 'Peer Connectivity', 'Connection to peer controller is up.']
    result = health_check.run_check()
    # Verify that peer_reachable was set.
    assert sev1_report.PEER_REACHABLE
    # Validate that the results are what we expect.
    assert result == expected


def test_controller_status_green():
    """Test the ControllerStatus health check."""
    # A lot of information is gathered in this check to populate peer and local dicts.
    global STATE
    STATE = 'HEALTHY'
    health_check = sev1_report.ControllerStatus()
    expected = ['HEALTHY', 'Controller Status', 'Both controllers are up and in the Ready status.']
    result = health_check.run_check()
    # Ensure that the dicts are not the same.
    assert health_check.ctlr_x != health_check.ctlr_y
    assert sev1_report.LOCAL_CTLR != sev1_report.PEER_CTLR
    # Ensure we get the local and peer ctlr dicts populated.
    assert len(sev1_report.LOCAL_CTLR.keys()) >= 1
    assert len(sev1_report.PEER_CTLR.keys()) >= 1
    # Validate that the results are what we expect.
    assert result == expected


def test_pureadm_status_green():
    """Test the PureadmStatus health check."""
    global STATE
    STATE = 'HEALTHY'
    health_check = sev1_report.PureadmStatus()
    expected = [
        ['HEALTHY', 'local: pureadm status', 'Both controllers have all services fully running'],
        ['HEALTHY', ' peer: pureadm status', 'Both controllers have all services fully running']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_controller_version_match_green():
    """Test the ControllerVersionMatch health check."""
    global STATE
    STATE = 'HEALTHY'
    health_check = sev1_report.ControllerVersionMatch()
    expected = ['HEALTHY', 'Matching Versions', 'Purity versions match: CT0:4.7.6 | CT1:4.7.6']
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_corruption_crumb_green():
    """Test the CorruptionCrumb health check."""
    global STATE
    STATE = 'HEALTHY'
    health_check = sev1_report.CorruptionCrumb()
    expected = [
        ['HEALTHY', 'local: Corruption Cumbs', 'No Corruption crumbs found.'],
        ['HEALTHY', ' peer: Corruption Cumbs', 'No Corruption crumbs found.']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_foed_uptime_green():
    """Test the FoedUptime health check."""
    global STATE
    STATE = 'HEALTHY'
    health_check = sev1_report.FoedUptime()
    expected = [
        ['HEALTHY', 'local: Foed Uptime', 'Controller uptime is 98 Days 23 Hours 10 Minutes.'],
        ['HEALTHY', ' peer: Foed Uptime', 'Controller uptime is 98 Days 23 Hours 10 Minutes.']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_controller_state_changes_green():
    """Test the ControllerStateChanges health check."""
    global STATE
    STATE = 'HEALTHY'
    health_check = sev1_report.ControllerStateChanges()
    expected = [
        ['HEALTHY', 'local: State Changes', 'No controller state changes found.'],
        ['HEALTHY', ' peer: State Changes', 'No controller state changes found.']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_rename_me():
    """Test the rename_me function."""
    ctlr_name = sev1_report.rename_me('Test Me', on_peer=False)
    assert ctlr_name == 'local: Test Me'
    ctlr_name = sev1_report.rename_me('Test Me', on_peer=True)
    assert ctlr_name == ' peer: Test Me'


def test_print_results():
    """Test the print_results function."""
    test_table = [
        ['Header1', 'Header2', 'Header3'],
        ['thing1', 'other thing', 'longer text in column3']
    ]
    expected = [
        '| Header1 | Header2     | Header3                |',
        '| thing1  | other thing | longer text in column3 |'
    ]
    output = sev1_report.print_results(test_table)
    assert output == expected


def test_get_results():
    """Test that the final results are all green after above tests are run."""
    results = sev1_report.SOSHealthCheck.get_results()
    expected = [
        ['Check State', 'Check Name', 'Information'],
        ['HEALTHY', 'Peer Connectivity', 'Connection to peer controller is up.'],
        ['HEALTHY', 'Controller Status', 'Both controllers are up and in the Ready status.'],
        ['HEALTHY', 'local: pureadm status', 'Both controllers have all services fully running'],
        ['HEALTHY', ' peer: pureadm status', 'Both controllers have all services fully running'],
        ['HEALTHY', 'Matching Versions', 'Purity versions match: CT0:4.7.6 | CT1:4.7.6'],
        ['HEALTHY', 'local: Corruption Cumbs', 'No Corruption crumbs found.'],
        ['HEALTHY', ' peer: Corruption Cumbs', 'No Corruption crumbs found.'],
        ['HEALTHY', 'local: Foed Uptime', 'Controller uptime is 98 Days 23 Hours 10 Minutes.'],
        ['HEALTHY', ' peer: Foed Uptime', 'Controller uptime is 98 Days 23 Hours 10 Minutes.'],
        ['HEALTHY', 'local: State Changes', 'No controller state changes found.'],
        ['HEALTHY', ' peer: State Changes', 'No controller state changes found.'],
    ]
    assert results == expected


def test_peer_connection_yellow():
    """Test the PeerConnection health check."""
    global STATE
    STATE = 'WARNING'
    health_check = sev1_report.PeerConnection()
    expected = ['WARNING', 'Peer Connectivity', 'Unable to communicate with the "peer" controller.']
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_controller_status_yellow():
    """Test the ControllerStatus health check."""
    # A lot of information is gathered in this check to populate peer and local dicts.
    global STATE
    STATE = 'WARNING'
    health_check = sev1_report.ControllerStatus()
    expected = ['WARNING', 'Controller Status', 'Secondary controller not ready. CT0:ready | CT1:unknown']
    result = health_check.run_check()
    # Ensure that the dicts are not the same.
    assert health_check.ctlr_x != health_check.ctlr_y
    assert sev1_report.LOCAL_CTLR != sev1_report.PEER_CTLR
    # Ensure we get the local and peer ctlr dicts populated.
    assert len(sev1_report.LOCAL_CTLR.keys()) > 1
    assert len(sev1_report.PEER_CTLR.keys()) > 1
    # Validate that the results are what we expect.
    assert result == expected


def test_foed_uptime_yellow():
    """Test the FoedUptime health check."""
    global STATE
    STATE = 'WARNING'
    health_check = sev1_report.FoedUptime()
    expected = [
        ['WARNING', 'local: Foed Uptime', 'Controller uptime is 23 hours.'],
        ['WARNING', ' peer: Foed Uptime', 'Controller uptime is 23 hours.']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_controller_state_changes_yellow():
    """Test the ControllerStateChanges health check."""
    global STATE
    STATE = 'WARNING'
    health_check = sev1_report.ControllerStateChanges()
    expected = [
        ['WARNING', 'local: State Changes', 'Controller state changes detected. See details section below.'],
        ['WARNING', ' peer: State Changes', 'Controller state changes detected. See details section below.']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_pureadm_status_red():
    """Test the PureadmStatus health check."""
    global STATE
    STATE = 'ERROR'
    health_check = sev1_report.PureadmStatus()
    expected = [
        ['ERROR', 'local: pureadm status', 'Processes in unexpected state: remote_patch'],
        ['ERROR', ' peer: pureadm status', 'Processes in unexpected state: remote_patch']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_controller_version_match_red():
    """Test the ControllerVersionMatch health check."""
    global STATE
    STATE = 'ERROR'
    health_check = sev1_report.ControllerVersionMatch()
    # Injecting some mismatched purity versions to ensure we fail here.
    sev1_report.LOCAL_CTLR['version'] = '4.10.1'
    sev1_report.PEER_CTLR['version'] = '5.1.0'
    expected = ['ERROR', 'Matching Versions', 'Purity version mismatch: CT0:4.10.1 | CT1:5.1.0']
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected


def test_corruption_crumb_black():
    """Test the CorruptionCrumb health check."""
    global STATE
    STATE = 'CRITICAL'
    health_check = sev1_report.CorruptionCrumb()
    expected = [
        ['CRITICAL', 'local: Corruption Cumbs', 'Corruption crumbs found! See details section below.'],
        ['CRITICAL', ' peer: Corruption Cumbs', 'Corruption crumbs found! See details section below.']
    ]
    result = health_check.run_check()
    # Validate that the results are what we expect.
    assert result == expected
