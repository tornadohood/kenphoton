"""Unit tests for tech_support_show.py."""

import pytest

from photon.backend.cisco import tech_support_show
from photon.lib import cisco_utils
from photon.lib import test_utils

#pylint: disable=redefined-outer-name,protected-access

@pytest.fixture(scope='module')
def support_show_parser():
    """Return a switch object fixture."""
    logfile = test_utils.get_files_of_type('cisco_test_log')[0]
    return tech_support_show.SupportShowParser(logfile)


def test_all_parsers(support_show_parser):
    """Test that every getter has a test."""
    test_utils.all_parsers_have_test(support_show_parser, __file__)


def test__get_first_field_val(support_show_parser):
    """Test that we get the first field successfully from show_switchname."""
    result = support_show_parser._get_first_field_val('show_switchname')
    expected = 'MFXRFPEMC9513-A'
    assert result == expected


def test__get_regex_from_output(support_show_parser):
    """Test that we get a regex dict from an output."""
    result = support_show_parser._get_regex_from_output('show_version', 'BIOS:\s+version\s+(?P<bios>.*)')
    assert result == [{'bios': '1.0.10'}]


def test_get_all_fields(support_show_parser):
    """Test that we get all fields successfully."""
    result = set(support_show_parser.get_all_fields().keys())
    assert result == set(list(support_show_parser.fields) + ['Timestamp'])


def test_get_bios(support_show_parser):
    """Test that we get a bios version from a log."""
    result = support_show_parser.get_bios()
    assert result == '1.0.10'


def test_get_fields(support_show_parser):
    """Test that we get some fields properly."""
    result = support_show_parser.get_fields(['show_clock', 'show_switchname'])
    expected = {
        'show_clock': ['16:04:11.752 UTC Thu Jun 14 2018\n', 'Time source is NTP\n'],
        'show_switchname': ['MFXRFPEMC9513-A\n'],
        'Timestamp': '16:04:11.752 UTC Thu Jun 14 2018'
    }
    assert result == expected


def test_get_alias_dict(support_show_parser):
    """Test that we get an alias dict from a log."""
    result = support_show_parser.get_alias_dict()
    assert len(result.keys()) == 136
    assert result['cvrpuxsqp01a_ql'] == '21:01:00:1b:32:3a:f0:a2'
    assert result['21:01:00:1b:32:3a:f0:a2'] == 'cvrpuxsqp01a_ql'


def test_get_flogi_dict(support_show_parser):
    """Test that we get a flogi dict from a log."""
    result = support_show_parser.get_flogi_dict()
    assert result['fc1/18'] == [
        cisco_utils.FlogiEntry(interface='fc1/18', vsan='50', fcid='0x3202a0', port_name='10:00:00:90:fa:1b:32:38', node_name='20:00:00:90:fa:1b:32:38', alias=None)
    ]
    assert result['port-channel1'][0:2] == [
        cisco_utils.FlogiEntry(interface='port-channel1', vsan='50', fcid='0x3200a1', port_name='20:01:00:25:b5:a0:a1:2f', node_name='20:00:00:25:b5:a0:01:2f', alias=None),
        cisco_utils.FlogiEntry(interface='port-channel1', vsan='50', fcid='0x3200a2', port_name='20:01:00:25:b5:a0:a1:3f', node_name='20:00:00:25:b5:a0:01:3f', alias=None)
    ]


def test_get_hardware(support_show_parser):
    """Test that we get hardware model from a log."""
    result = support_show_parser.get_hardware()
    assert result == 'cisco MDS 9513 (13 Slot) Chassis ("Supervisor/Fabric-2a")'


def test_get_interface_dict(support_show_parser):
    """Test that we get interface dicts from the log."""
    result = support_show_parser.get_interface_dict()
    expected = {
        '5_minutes_input_bits_sec': '115810464',
        '5_minutes_output_bits_sec': '195751936',
        'admin_fec_state': 'down',
        'admin_port_mode': 'auto',
        'connected_wwpns': ['20:01:00:25:b5:a0:a1:2f',
        '20:01:00:25:b5:a0:a1:3f',
        '20:01:00:25:b5:a0:a1:0f',
        '20:01:00:25:b5:a0:a1:1f',
        '20:01:00:25:b5:a0:a1:2e',
        '20:01:00:25:b5:a0:a1:3e',
        '20:01:00:25:b5:a0:a1:1e',
        '20:01:00:25:b5:a0:a1:0e',
        '24:01:00:05:73:d2:59:c0'],
        'error': 'port not present',
        'hardware': 'Fibre Channel',
        'input_bytes': '293149753678128',
        'input_discards': '0',
        'input_errors': '0',
        'input_frames_input': '181200169488',
        'input_input_ols': '0',
        'input_invalid_crc/fcs': '0',
        'input_loop_inits': '0',
        'input_lrr': '0',
        'input_nos': '0',
        'input_too_long': '0',
        'input_too_short': '0',
        'input_unknown_class': '0',
        'interface_last_changed': 'Sun Jan 26 18:23:15 2014',
        'interface_name': 'port-channel1',
        'member_1': 'fc1/14',
        'member_2': 'fc1/15',
        'member_3': 'fc1/32',
        'member_4': 'fc1/33',
        'oper_fec_state': 'down',
        'output_bytes': '501873283644288',
        'output_discards': '28755',
        'output_errors': '0',
        'output_frames_output': '302772057121',
        'output_loop_inits': '0',
        'output_lrr': '0',
        'output_nos': '0',
        'output_output_ols': '0',
        'port_mode': 'F',
        'port_vsan': '50',
        'port_wwn': '24:01:00:0d:ec:3c:06:00',
        'snmp_link_state_traps': 'enabled',
        'speed': '32 Gbps',
        'state': 'up',
        'trunk_mode': 'off'
    }
    assert result['port-channel1'] == expected


def test_get_show_clock(support_show_parser):
    """Test that we get show clock output from a log."""
    support_show_parser.get_fields(['show_clock'])
    result = support_show_parser.get_fields(['show_clock'])
    expected = ['16:04:11.752 UTC Thu Jun 14 2018\n', 'Time source is NTP\n']
    assert expected == result['show_clock']
    assert len(result['show_clock']) == 2


def test_get_show_device_alias_database(support_show_parser):
    """Test that we get show device alias database output from a log."""
    result = support_show_parser.get_fields(['show_device_alias_database'])
    expected_start = [
        'device-alias name PURE_CT0_FC0 pwwn 52:4a:93:77:59:62:b2:00\n',
        'device-alias name PURE_CT0_FC2 pwwn 52:4a:93:77:59:62:b2:02\n',
        'device-alias name PURE_CT1_FC2 pwwn 52:4a:93:77:59:62:b2:12\n',
        'device-alias name Pure_CT1_FC0 pwwn 52:4a:93:77:59:62:b2:10\n',
        'device-alias name CVRPUXSQP01a_QL pwwn 21:01:00:1b:32:3a:f0:a2\n',
        'device-alias name CX480_0303_SPA2 pwwn 50:06:01:62:44:60:27:6f\n',
        'device-alias name CX480_0303_SPA4 pwwn 50:06:01:64:44:60:27:6f\n',
        'device-alias name CX480_0303_SPA6 pwwn 50:06:01:66:44:60:27:6f\n',
        'device-alias name CX480_0303_SPB2 pwwn 50:06:01:6a:44:60:27:6f\n',
        'device-alias name CX480_0303_SPB4 pwwn 50:06:01:6c:44:60:27:6f\n'
    ]
    expected_end = [
        'device-alias name MFXRFPVDIESX01_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:1f\n',
        'device-alias name MFXRFPVDIESX02_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:0f\n',
        'device-alias name MFXRFPVDIESX03_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:3f\n',
        'device-alias name MFXRFPVDIESX04_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:2f\n',
        'device-alias name MFXRFPVDIESX05_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:5f\n',
        'device-alias name MFXRFPVDIESX06_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:4f\n',
        'device-alias name MFXRFPVDIESX07_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:7f\n',
        'device-alias name MFXRFPVDIESX08_Virtual_HBA0 pwwn 20:00:00:25:b5:01:a0:6f\n',
        '\n',
        'Total number of entries = 68\n'
    ]
    assert expected_start == result['show_device_alias_database'][:10]
    assert expected_end == result['show_device_alias_database'][-10:]
    assert len(result['show_device_alias_database']) == 70


def test_get_show_flogi_database(support_show_parser):
    """Test that we get show flogi database output from a log."""
    result = support_show_parser.get_fields(['show_flogi_database'])
    expected_start = [
        '--------------------------------------------------------------------------------\n',
        'INTERFACE        VSAN    FCID           PORT NAME               NODE NAME       \n',
        '--------------------------------------------------------------------------------\n',
        'fc1/2            50    0x320300  10:00:00:00:c9:fc:15:c6 20:00:00:00:c9:fc:15:c6\n',
        '                           [MFRPNTPSSSPAPP1_ELX_HBA1]\n',
        'fc1/3            50    0x3202c0  21:00:00:24:ff:53:02:51 20:00:00:24:ff:53:02:51\n',
        '                           [MFRPESXPSS07_QL_HBA0]\n',
        'fc1/4            50    0x320280  21:00:00:24:ff:53:02:05 20:00:00:24:ff:53:02:05\n',
        '                           [MFRPESXPSS06_QL_HBA0]\n',
        'fc1/5            50    0x320220  21:00:00:24:ff:53:01:dd 20:00:00:24:ff:53:01:dd\n'
    ]
    expected_end = [
        'port-channel1    50    0x3200a6  20:01:00:25:b5:a0:a1:3e 20:00:00:25:b5:a0:01:3e\n',
        '                           [MFXRFUCSESX06_Virtual_HBA1]\n',
        'port-channel1    50    0x3200a7  20:01:00:25:b5:a0:a1:1e 20:00:00:25:b5:a0:01:1e\n',
        '                           [MFXRFUCSESX08_Virtual_HBA1]\n',
        'port-channel1    50    0x3200a8  20:01:00:25:b5:a0:a1:0e 20:00:00:25:b5:a0:01:0e\n',
        '                           [MFXRFUCSESX07_Virtual_HBA1]\n',
        'port-channel1    50    0x3200c0  24:01:00:05:73:d2:59:c0 20:32:00:05:73:d2:59:c1\n',
        '\n',
        'Total number of flogi = 38.\n',
        '\n'
    ]
    assert expected_start == result['show_flogi_database'][:10]
    assert expected_end == result['show_flogi_database'][-10:]
    assert len(result['show_flogi_database']) == 80


def test_get_show_interface(support_show_parser):
    """Test that we get show interface information from a log."""
    result = support_show_parser.get_fields(['show_interface'])
    expected_start = [
        'fc1/1 is down (Link failure or not-connected)\n',
        '    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)\n',
        '    Port WWN is 20:01:00:0d:ec:3c:06:00\n',
        '    Admin port mode is F, trunk mode is off\n',
        '    snmp link state traps are enabled\n',
        '    Port vsan is 50\n',
        '    Receive data field Size is 2112\n',
        '    Beacon is turned off\n',
        '    5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec\n',
        '    5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec\n'
    ]
    expected_end = [
        '    0 Rx pause\n',
        '  TX\n',
        '    0 unicast packets  0 multicast packets  0 broadcast packets\n',
        '    0 output packets  0 bytes\n',
        '    0 jumbo packets\n',
        '    0 output error  0 collision  0 deferred  0 late collision\n',
        '    0 lost carrier  0 no carrier  0 babble  0 output discard\n',
        '    0 Tx pause\n',
        '\n',
        '\n'
    ]
    assert expected_start == result['show_interface'][:10]
    assert expected_end == result['show_interface'][-10:]
    assert len(result['show_interface']) == 2524


def test_get_show_switchname(support_show_parser):
    """Test that we get show switchname command output from a log."""
    result = support_show_parser.get_fields(['show_switchname'])
    expected = ['MFXRFPEMC9513-A\n']
    assert expected == result['show_switchname']
    assert len(result['show_switchname']) == 1


def test_get_show_zoneset_active(support_show_parser):
    """Test that we get show zoneset active output from a log."""
    result = support_show_parser.get_fields(['show_zoneset_active'])
    expected_start = [
        'zoneset name EVEN_RFP vsan 50\n',
        '  zone name CVRPUXSQQ01a_CT0_FC0 vsan 50\n',
        '  * fcid 0x321800 [pwwn 21:00:00:e0:8b:92:ce:84] [CRPUXSQQ01a_Qlogic_HBA2]\n',
        '  * fcid 0x3201a2 [pwwn 52:4a:93:77:59:62:b2:00] [PURE_CT0_FC0]\n',
        '  \n',
        '  zone name CVRPUXSQQ01a_CT0_FC2 vsan 50\n',
        '  * fcid 0x321800 [pwwn 21:00:00:e0:8b:92:ce:84] [CRPUXSQQ01a_Qlogic_HBA2]\n',
        '  * fcid 0x320202 [pwwn 52:4a:93:77:59:62:b2:02] [PURE_CT0_FC2]\n',
        '  \n',
        '  zone name CVRPUXSQQ01a_CT1_FC0 vsan 50\n'
    ]
    expected_end = [
        '  zone name MFRPNTPSSSPSQP1_CT1_FC0 vsan 50\n',
        '  * fcid 0x320320 [pwwn 10:00:00:00:c9:fc:13:3a] [MFRPNTPSSSPSQP1_ELX_HBA1]\n',
        '  * fcid 0x320701 [pwwn 52:4a:93:77:59:62:b2:10] [Pure_CT1_FC0]\n',
        '  \n',
        '  zone name MFRPNTPSSSPSQP1_CT1_FC2 vsan 50\n',
        '  * fcid 0x320320 [pwwn 10:00:00:00:c9:fc:13:3a] [MFRPNTPSSSPSQP1_ELX_HBA1]\n',
        '  * fcid 0x320721 [pwwn 52:4a:93:77:59:62:b2:12] [PURE_CT1_FC2]\n',
        '  \n',
        '  zone name $default_zone$ vsan 50\n',
        '  * fcid 0x3200c0\n'
    ]
    assert expected_start == result['show_zoneset_active'][:10]
    assert expected_end == result['show_zoneset_active'][-10:]
    assert len(result['show_zoneset_active']) == 563


def test_get_show_version(support_show_parser):
    """Test that we get show version output from a log."""
    result = support_show_parser.get_show_version()
    expected = [
        'Cisco Nexus Operating System (NX-OS) Software\n',
        'TAC support: http://www.cisco.com/tac\n',
        'Documents: http://www.cisco.com/en/US/products/ps9372/tsd_products_support_series_home.html\n',
        'Copyright (c) 2002-2014, Cisco Systems, Inc. All rights reserved.\n',
        'The copyrights to certain works contained herein are owned by\n',
        'other third parties and are used and distributed under license.\n',
        'Some parts of this software are covered under the GNU Public\n',
        'License. A copy of the license is available at\n',
        'http://www.gnu.org/licenses/gpl.html.\n',
        '\n',
        'Software\n',
        '  BIOS:      version 1.0.10\n',
        '  loader:    version N/A\n',
        '  kickstart: version 6.2(9a)\n',
        '  system:    version 6.2(9a)\n',
        '  BIOS compile time:       01/08/09\n',
        '  kickstart image file is: bootflash:///m9500-sf2ek9-kickstart-mz.6.2.9a.bin\n',
        '  kickstart compile time:  8/20/2014 11:00:00 [10/14/2014 06:54:36]\n',
        '  system image file is:    bootflash:///m9500-sf2ek9-mz.6.2.9a.bin\n',
        '  system compile time:     8/20/2014 11:00:00 [10/14/2014 08:24:00]\n',
        '\n',
        '\n',
        'Hardware\n',
        '  cisco MDS 9513 (13 Slot) Chassis ("Supervisor/Fabric-2a")\n',
        '  Motorola, 7447A, altivec  with 2071288 kB of memory.\n',
        '  Processor Board ID JAF1647ATGK\n',
        '\n',
        '  Device name: MFXRFPEMC9513-A\n',
        '  bootflash:    1000944 kB\n',
        '  slot0:              0 kB (expansion flash)\n',
        '\n',
        'Kernel uptime is 688 day(s), 15 hour(s), 15 minute(s), 1 second(s)\n',
        '\n',
        'Last reset \n',
        '  Reason: Unknown\n',
        '  System version: 6.2(3)\n',
        '  Service: \n',
        '\n',
        'plugin\n',
        '  Core Plugin\n'
    ]
    assert result == expected


def test_get_switchname(support_show_parser):
    """Test that we get the switchname properly."""
    expected = 'MFXRFPEMC9513-A'
    assert expected == support_show_parser.get_switchname()


def test_get_uptime(support_show_parser):
    """Test that we get uptime from a log."""
    result = support_show_parser.get_uptime()
    assert result == '688 day(s), 15 hour(s), 15 minute(s), 1 second(s)'


def test_get_version(support_show_parser):
    """Test that we get version from a log."""
    result = support_show_parser.get_version()
    assert result == '6.2(3)'


def test_get_zonesets(support_show_parser):
    """Test that we get zonesets from a log."""
    result = support_show_parser.get_zonesets()
    assert result['EVEN_RFP'].name == 'EVEN_RFP'
    assert len(result['EVEN_RFP'].zones['CVRPUXSQP01a_CT1_FC2'].members) == 2
