"""Unit tests for WFS checks."""

import argparse
import sys
import unittest
from collections import OrderedDict

from photon.tools.standalone import wfs_checks

# This is for compatibility since python2 doesn't have mock.
if sys.version_info[0] >= 3:
    # pylint:disable=no-name-in-module,import-error
    from unittest.mock import patch
else:
    from mock import patch


# This is the full example string
# pylint: disable=line-too-long
def return_fake_configured_lines(*args, **kwargs):
    """Fake purenetwork list."""
    # pylint: disable=unused-argument
    return 'Name      Enabled  Subnet  Address         Mask           Gateway       MTU   MAC                Speed       Services     Slaves\nct0.eth0  True     -       10.204.112.150  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:dd  1.00 Gb/s   management   -     \nct0.eth1  False    -       -               -              -             1500  24:a9:37:00:20:dc  1.00 Gb/s   replication  -     \nct0.eth2  False    -       -               -              -             1500  24:a9:37:00:20:de  10.00 Gb/s  iscsi        -     \nct0.eth3  False    -       -               -              -             1500  24:a9:37:00:20:df  10.00 Gb/s  iscsi        -     \nct0.eth6  True     -       10.204.121.24   255.255.252.0  10.204.120.1  1500  90:e2:ba:d7:ea:65  10.00 Gb/s  iscsi        -     \nct0.eth7  True     -       10.204.121.25   255.255.252.0  10.204.120.1  1500  90:e2:ba:d7:ea:64  10.00 Gb/s  iscsi        -     \nct0.eth8  True     -       192.168.26.58   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:95  10.00 Gb/s  iscsi        -     \nct0.eth9  True     -       192.168.26.59   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:94  10.00 Gb/s  iscsi        -     \nct1.eth0  True     -       10.204.112.155  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:47  1.00 Gb/s   management   -     \nct1.eth1  False    -       -               -              -             1500  24:a9:37:00:20:46  1.00 Gb/s   replication  -     \nct1.eth2  False    -       -               -              -             1500  24:a9:37:00:20:48  10.00 Gb/s  iscsi        -     \nct1.eth3  False    -       -               -              -             1500  24:a9:37:00:20:49  10.00 Gb/s  iscsi        -     \nct1.eth6  True     -       10.204.121.26   255.255.252.0  10.204.120.1  1500  90:e2:ba:c7:70:d5  10.00 Gb/s  iscsi        -     \nct1.eth7  True     -       10.204.121.27   255.255.252.0  10.204.120.1  1500  90:e2:ba:c7:70:d4  10.00 Gb/s  iscsi        -     \nct1.eth8  True     -       192.168.26.60   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:21  10.00 Gb/s  iscsi        -     \nct1.eth9  True     -       192.168.26.61   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:20  10.00 Gb/s  iscsi        -     \nreplbond  False    -       10.204.112.151  255.255.255.0  10.204.112.1  1500  ba:97:86:38:12:62  0.00 b/s    replication  -     \nvir0      True     -       10.204.112.159  255.255.255.0  10.204.112.1  1500  24:a9:37:fb:ea:2c  1.00 Gb/s   management   -     \nvir1      False    -       -               -              -             1500  62:c8:f0:25:b6:00  1.00 Gb/s   management   -     \n'


def return_fake_nonconfigured_lines(*args, **kwargs):
    """Fake purenetwork list."""
    # pylint: disable=unused-argument
    return 'Name      Enabled  Subnet  Address         Mask           Gateway       MTU   MAC                Speed       Services     Slaves\nct0.eth0  True     -       10.204.112.150  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:dd  1.00 Gb/s   management   -     \nct0.eth1  False    -       -               -              -             1500  24:a9:37:00:20:dc  1.00 Gb/s   replication  -     \nct0.eth2  False    -       -               -              -             1500  24:a9:37:00:20:de  10.00 Gb/s  iscsi        -     \nct0.eth3  False    -       -               -              -             1500  24:a9:37:00:20:df  10.00 Gb/s  iscsi        -     \nct0.eth6  True     -       -               -              -             1500  90:e2:ba:d7:ea:65  10.00 Gb/s  iscsi        -     \nct0.eth7  True     -       -               -              -             1500  90:e2:ba:d7:ea:64  10.00 Gb/s  iscsi        -     \nct0.eth8  True     -       192.168.26.58   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:95  10.00 Gb/s  iscsi        -     \nct0.eth9  True     -       192.168.26.59   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:94  10.00 Gb/s  iscsi        -     \nct1.eth0  True     -       10.204.112.155  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:47  1.00 Gb/s   management   -     \nct1.eth1  False    -       -               -              -             1500  24:a9:37:00:20:46  1.00 Gb/s   replication  -     \nct1.eth2  False    -       -               -              -             1500  24:a9:37:00:20:48  10.00 Gb/s  iscsi        -     \nct1.eth3  False    -       -               -              -             1500  24:a9:37:00:20:49  10.00 Gb/s  iscsi        -     \nct1.eth6  True     -       -               -              -             1500  90:e2:ba:c7:70:d5  10.00 Gb/s  iscsi        -     \nct1.eth7  True     -       -               -              -             1500  90:e2:ba:c7:70:d4  10.00 Gb/s  iscsi        -     \nct1.eth8  True     -       192.168.26.60   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:21  10.00 Gb/s  iscsi        -     \nct1.eth9  True     -       192.168.26.61   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:20  10.00 Gb/s  iscsi        -     \nreplbond  False    -       10.204.112.151  255.255.255.0  10.204.112.1  1500  ba:97:86:38:12:62  0.00 b/s    replication  -     \nvir0      True     -       10.204.112.159  255.255.255.0  10.204.112.1  1500  24:a9:37:fb:ea:2c  1.00 Gb/s   management   -     \nvir1      False    -       -               -              -             1500  62:c8:f0:25:b6:00  1.00 Gb/s   management   -     \n'


class TestBuildPingCommand(unittest.TestCase):
    """Unit tests for building the ping command."""
    def test_good_local_ping(self):
        """Test using a good ping command format."""
        interface_dict = {'ct0.eth6': '0.0.0.0', 'ct1.eth6': '0.0.0.0'}
        expected = ['ping', '-I', '0.0.0.0', '-c', '3', '-i', '3', '-s', '1472', '-Mdo', '10.204.112.11']
        result = wfs_checks.build_ping_command('ct0.eth6', '10.204.112.11', interface_dict, 1500, 3, 3, 'ct0')
        self.assertEqual(expected, result)

    def test_good_peer_ping(self):
        """Test where we would create a peer ping commmand."""
        interface_dict = {'ct0.eth6': '0.0.0.0', 'ct1.eth6': '0.0.0.0'}
        expected = ['ssh', 'peer', 'ping -I 0.0.0.0 -c 3 -i 3 -s 1472 -Mdo 10.204.112.11']
        result = wfs_checks.build_ping_command('ct0.eth6', '10.204.112.11', interface_dict, 1500, 3, 3, 'ct1')
        self.assertEqual(expected, result)

    def test_bad_interface_dict(self):
        """Test with a bad interface dict."""
        with self.assertRaises(KeyError):
            wfs_checks.build_ping_command('eth6', '10.204.112.11', {}, 1500, 3, 3, 'ct0')


class TestBuildCommandFromArgs(unittest.TestCase):
    """Unit test for building the command string from args."""
    args = argparse.Namespace(dns='10.204.112.11',
                              domain_controller='10.204.112.11',
                              gateway='10.204.120.1',
                              interfaces=['ETH6', 'ETH7'],
                              ip_addresses=['10.204.121.24', '10.204.121.25',
                                            '10.204.121.26', '10.204.121.27'],
                              interactive=False,
                              subnet_mask='255.255.252.0')

    def test_args(self):
        """Test that we get the correct args back from the namespace."""
        # pylint: disable=line-too-long
        expected = '--dns 10.204.112.11 --domain-controller 10.204.112.11 --gateway 10.204.120.1 --interfaces ETH6 ETH7 --ip-addresses 10.204.121.24 10.204.121.25 10.204.121.26 10.204.121.27 --subnet-mask 255.255.252.0'
        results = wfs_checks.build_command_from_args(self.args)
        self.assertEqual(expected, results)


class TestBuildInterfaceCommands(unittest.TestCase):
    """Test build_interface command for up, leave_up, and down."""
    def test_build_interface_up(self):
        """Test building interface up commands."""
        args = argparse.Namespace(gateway='10.204.120.1',
                                  interfaces=['ETH6', 'ETH7'],
                                  ip_addresses=['10.204.121.24', '10.204.121.25',
                                                '10.204.121.26', '10.204.121.27'],
                                  subnet_mask='255.255.252.0')
        # pylint: disable=line-too-long
        expected = [['purenetwork', 'setattr', 'ct0.eth6', '--address', '10.204.121.24', '--gateway', '10.204.120.1', '--netmask', '255.255.252.0'],
                    ['purenetwork', 'setattr', 'ct0.eth7', '--address', '10.204.121.25', '--gateway', '10.204.120.1', '--netmask', '255.255.252.0'],
                    ['purenetwork', 'setattr', 'ct1.eth6', '--address', '10.204.121.26', '--gateway', '10.204.120.1', '--netmask', '255.255.252.0'],
                    ['purenetwork', 'setattr', 'ct1.eth7', '--address', '10.204.121.27', '--gateway', '10.204.120.1', '--netmask', '255.255.252.0']]
        # pylint doesn't understand Namespaces, so it complains.
        # pylint: disable=no-member
        # We're specifically testing the protected method.
        # pylint: disable=protected-access
        result = wfs_checks._build_interface_commands(args.interfaces,
                                                      args.ip_addresses,
                                                      args.gateway,
                                                      args.subnet_mask)
        self.assertEqual(expected, result)

    def test_build_interface_down(self):
        """Test build interface downing commands."""
        # pylint doesn't understand Namespaces, so it complains.
        # pylint: disable=no-member
        args = argparse.Namespace(interfaces=['ETH6', 'ETH7'])
        expected = [['purenetwork', 'setattr', 'ct0.eth6', '--address', '', '--gateway', '', '--netmask', ''],
                    ['purenetwork', 'setattr', 'ct0.eth7', '--address', '', '--gateway', '', '--netmask', ''],
                    ['purenetwork', 'setattr', 'ct1.eth6', '--address', '', '--gateway', '', '--netmask', ''],
                    ['purenetwork', 'setattr', 'ct1.eth7', '--address', '', '--gateway', '', '--netmask', '']]
        # We're specifically testing the protected method.
        # pylint: disable=protected-access
        result = wfs_checks._build_interface_commands(args.interfaces,
                                                      bring_up=False)
        self.assertEqual(expected, result)

    def test_get_nice_interfaces(self):
        """Test getting nice interface names."""
        # pylint doesn't understand Namespaces, so it complains.
        # pylint: disable=no-member
        args = argparse.Namespace(interfaces=['ETH6', 'ETH7'])
        expected = ['ct0.eth6', 'ct0.eth7', 'ct1.eth6', 'ct1.eth7']
        # We're specifically testing the protected method.
        # pylint: disable=protected-access
        result = wfs_checks._get_nice_interfaces(args.interfaces)
        self.assertEqual(expected, result)


class TestTableUtils(unittest.TestCase):
    """Various table testing."""
    MYLIST = [['Name', 'Enabled', 'Subnet', 'Address', 'Mask', 'Gateway', 'MTU'],
              ['ct0.eth6', True, '-', '10.204.121.24', '255.255.252.0', '10.204.120.1', '1500'],
              ['ct0.eth7', True, '-', '10.204.121.25', '255.255.252.0', '10.204.120.1', '1500'],
              ['ct1.eth6', True, '-', '10.204.121.26', '255.255.252.0', '10.204.120.1', '1500'],
              ['ct1.eth7', True, '-', '10.204.121.27', '255.255.252.0', '10.204.120.1', '1500']]

    def test_get_table_info(self):
        """Test get_table_info."""
        expected = OrderedDict([(0, 8), (1, 7), (2, 6), (3, 13), (4, 13), (5, 12), (6, 4)])
        result = wfs_checks.get_table_info(self.MYLIST)
        self.assertEqual(expected, result)

    def test_get_normal_separator(self):
        """Test building a normal separator from table info."""
        table_info = wfs_checks.get_table_info(self.MYLIST)
        expected = ['+----------',
                    '+---------',
                    '+--------',
                    '+---------------',
                    '+---------------',
                    '+--------------',
                    '+------',
                    '+']
        result = wfs_checks.create_separator(table_info)
        self.assertEqual(expected, result)

    def test_get_header_separator(self):
        """Test building a header separator from table_info."""
        table_info = wfs_checks.get_table_info(self.MYLIST)
        expected = ['+==========',
                    '+=========',
                    '+========',
                    '+===============',
                    '+===============',
                    '+==============',
                    '+======',
                    '+']
        result = wfs_checks.create_separator(table_info, header=True)
        self.assertEqual(expected, result)

    def test_get_normal_table(self):
        """Test building a normal table with no args."""
        expected = ['+==========+=========+========+===============+===============+==============+======+',
                    '| Name     | Enabled | Subnet | Address       | Mask          | Gateway      | MTU  |',
                    '+==========+=========+========+===============+===============+==============+======+',
                    '| ct0.eth6 | True    | -      | 10.204.121.24 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '| ct0.eth7 | True    | -      | 10.204.121.25 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '| ct1.eth6 | True    | -      | 10.204.121.26 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '| ct1.eth7 | True    | -      | 10.204.121.27 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+']
        result = wfs_checks.create_table(self.MYLIST)
        self.assertEqual(expected, result)

    def test_get_normal_sep_no_header(self):
        """Test build with no header."""
        expected = ['+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| Name     | Enabled | Subnet | Address       | Mask          | Gateway      | MTU  |',
                    '| ct0.eth6 | True    | -      | 10.204.121.24 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '| ct0.eth7 | True    | -      | 10.204.121.25 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '| ct1.eth6 | True    | -      | 10.204.121.26 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '| ct1.eth7 | True    | -      | 10.204.121.27 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+']
        result = wfs_checks.create_table(self.MYLIST, header=False)
        self.assertEqual(expected, result)

    def test_get_vert_sep_with_header(self):
        """Test build with vertical separator."""
        expected = ['+==========+=========+========+===============+===============+==============+======+',
                    '| Name     | Enabled | Subnet | Address       | Mask          | Gateway      | MTU  |',
                    '+==========+=========+========+===============+===============+==============+======+',
                    '| ct0.eth6 | True    | -      | 10.204.121.24 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| ct0.eth7 | True    | -      | 10.204.121.25 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| ct1.eth6 | True    | -      | 10.204.121.26 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| ct1.eth7 | True    | -      | 10.204.121.27 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+']
        result = wfs_checks.create_table(self.MYLIST, header=True, vertical_sep=True)
        self.assertEqual(expected, result)

    def test_get_vertical_sep_no_header(self):
        """Test build with vertical separator and no header."""
        expected = ['+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| Name     | Enabled | Subnet | Address       | Mask          | Gateway      | MTU  |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| ct0.eth6 | True    | -      | 10.204.121.24 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| ct0.eth7 | True    | -      | 10.204.121.25 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| ct1.eth6 | True    | -      | 10.204.121.26 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+',
                    '| ct1.eth7 | True    | -      | 10.204.121.27 | 255.255.252.0 | 10.204.120.1 | 1500 |',
                    '+----------+---------+--------+---------------+---------------+--------------+------+']
        result = wfs_checks.create_table(self.MYLIST, header=False, vertical_sep=True)
        self.assertEqual(expected, result)


class TestCheckConfiguredInterfaces(unittest.TestCase):
    """Test For configured interface function."""
    @patch('subprocess.check_output', return_fake_configured_lines)
    def test_configured_interfaces(self):
        """Test that we get back configured interfaces if they exist."""
        args = argparse.Namespace(interfaces=['ETH6', 'ETH7'], ping_only=False)
        results = wfs_checks.interfaces_configured(args)
        # pylint: disable=line-too-long
        expected = True
        self.assertEqual(results, expected)

    @patch('subprocess.check_output', return_fake_nonconfigured_lines)
    def test_no_interfaces(self):
        """Test that we get an empty list if there are no configured interfaces from our interface list."""
        args = argparse.Namespace(interfaces=['ETH6', 'ETH7'])
        results = wfs_checks.interfaces_configured(args)
        expected = False
        self.assertEqual(results, expected)


class TestVersion(unittest.TestCase):
    """Unittests for the Version class.

    These aren't super in depth as it's a direct copypasta from distutils.version LooseVersion and Version
    classes - Only testing the portions where I've modified from the standard library.
    """

    def test_equal(self):
        """Test that equal asserts true."""
        version1 = wfs_checks.Version('1.1.1')
        version2 = wfs_checks.Version('1.1.1')
        self.assertTrue(version1 == version2)
        self.assertFalse(version1 != version2)
        self.assertTrue(version1 <= version2)
        self.assertTrue(version1 >= version2)
        self.assertFalse(version1 > version2)
        self.assertFalse(version1 < version2)

    def test_major(self):
        """Test that equal asserts true."""
        version1 = wfs_checks.Version('2.1.1')
        version2 = wfs_checks.Version('1.1.1')
        self.assertFalse(version1 == version2)
        self.assertTrue(version1 != version2)
        self.assertFalse(version1 <= version2)
        self.assertTrue(version1 >= version2)
        self.assertTrue(version1 > version2)
        self.assertFalse(version1 < version2)

    def test_major_minor(self):
        """Test that equal asserts true."""
        version1 = wfs_checks.Version('2.2.1')
        version2 = wfs_checks.Version('1.1.1')
        self.assertFalse(version1 == version2)
        self.assertTrue(version1 != version2)
        self.assertFalse(version1 <= version2)
        self.assertTrue(version1 >= version2)
        self.assertTrue(version1 > version2)
        self.assertFalse(version1 < version2)

    def test_major_minor_maint(self):
        """Test that equal asserts true."""
        version1 = wfs_checks.Version('2.2.2')
        version2 = wfs_checks.Version('1.1.1')
        self.assertFalse(version1 == version2)
        self.assertTrue(version1 != version2)
        self.assertFalse(version1 <= version2)
        self.assertTrue(version1 >= version2)
        self.assertTrue(version1 > version2)
        self.assertFalse(version1 < version2)

    def test_minor_maint(self):
        """Test that equal asserts true."""
        version1 = wfs_checks.Version('1.2.2')
        version2 = wfs_checks.Version('1.1.1')
        self.assertFalse(version1 == version2)
        self.assertTrue(version1 != version2)
        self.assertFalse(version1 <= version2)
        self.assertTrue(version1 >= version2)
        self.assertTrue(version1 > version2)
        self.assertFalse(version1 < version2)

    def test_maint(self):
        """Test that equal asserts true."""
        version1 = wfs_checks.Version('1.1.2')
        version2 = wfs_checks.Version('1.1.1')
        self.assertFalse(version1 == version2)
        self.assertTrue(version1 != version2)
        self.assertFalse(version1 <= version2)
        self.assertTrue(version1 >= version2)
        self.assertTrue(version1 > version2)
        self.assertFalse(version1 < version2)

    def test_minor(self):
        """Test that equal asserts true."""
        version1 = wfs_checks.Version('1.2.1')
        version2 = wfs_checks.Version('1.1.1')
        self.assertFalse(version1 == version2)
        self.assertTrue(version1 != version2)
        self.assertFalse(version1 <= version2)
        self.assertTrue(version1 >= version2)
        self.assertTrue(version1 > version2)
        self.assertFalse(version1 < version2)

    def test_gt_bad_version(self):
        """Test that equal asserts true."""
        with self.assertRaises(wfs_checks.VersionError):
            wfs_checks.Version('1.1.1.beta')


class TestTableToDict(unittest.TestCase):
    """Unit tests for table_to_dict()."""

    def test_non_vertical_table(self):
        """Test a non-vertical separated table."""
        purenetwork_lines = ['Domain               Nameservers  ',
                             'slc.purestorage.com  10.204.112.11']
        result = wfs_checks.table_to_dict(purenetwork_lines)
        expected = [{'domain': 'slc.purestorage.com', 'nameservers': '10.204.112.11'}]
        self.assertEqual(result, expected)

    def test_vertical_table(self):
        """Test a vertically separated table with a delimiter."""
        lines = ['+===========+===============+=============+==================+=======+',
                 '| Interface | Target        | Number Sent | Packets Lost (%) | Time  |',
                 '+===========+===============+=============+==================+=======+',
                 '| ct0.eth8  | 192.168.26.59 | 1           | 0%               | 0.00s |',
                 '| ct0.eth8  | 192.168.26.60 | 1           | 0%               | 0.00s |',
                 '| ct0.eth8  | 192.168.26.61 | 1           | 0%               | 0.00s |',
                 '| ct0.eth9  | 192.168.26.58 | 1           | 0%               | 0.00s |',
                 '| ct0.eth9  | 192.168.26.60 | 1           | 0%               | 0.00s |']
        expected = [{'interface': 'ct0.eth8', 'number_sent': '1', 'packets_lost': '0%', 'target': '192.168.26.59', 'time': '0.00s'},
                    {'interface': 'ct0.eth8', 'number_sent': '1', 'packets_lost': '0%', 'target': '192.168.26.60', 'time': '0.00s'},
                    {'interface': 'ct0.eth8', 'number_sent': '1', 'packets_lost': '0%', 'target': '192.168.26.61', 'time': '0.00s'},
                    {'interface': 'ct0.eth9', 'number_sent': '1', 'packets_lost': '0%', 'target': '192.168.26.58', 'time': '0.00s'},
                    {'interface': 'ct0.eth9', 'number_sent': '1', 'packets_lost': '0%', 'target': '192.168.26.60', 'time': '0.00s'}]
        # re.split() takes a string, not regex?  Don't know why, but this is intentional
        # backslash in non r'' string.
        # pylint: disable=anomalous-backslash-in-string
        result = wfs_checks.table_to_dict(lines, delimiter='\|')
        self.assertEqual(result, expected)


class TestCheckHardware(unittest.TestCase):
    """Unit tests for check_hardware."""

    def test_good_hardware(self):
        """Test with supported hardware."""
        local_hardware = 'FA-m20'
        peer_hardware = 'FA-m20'
        expected = [['Hardware', 'PASS', "Controller models are FA-m20's"]]
        result = wfs_checks.check_hardware(local_hardware, peer_hardware)
        self.assertEqual(result, expected)

    def test_bad_hardware(self):
        """Test with unsupported hardware."""
        local_hardware = 'FA-450'
        peer_hardware = 'FA-450'
        expected = [['Hardware', 'FAIL', 'Local model FA-450 or peer model FA-450 not supported.']]
        result = wfs_checks.check_hardware(local_hardware, peer_hardware)
        self.assertEqual(result, expected)

    def test_mismatched_hardware(self):
        """Test with mismatched hardware."""
        local_hardware = 'FA-m20'
        peer_hardware = 'FA-m50'
        expected = [['Hardware', 'FAIL', 'Models do not match - Local: FA-m20, Peer: FA-m50']]
        result = wfs_checks.check_hardware(local_hardware, peer_hardware)
        self.assertEqual(result, expected)

    def test_partial_hardware(self):
        """Test with mismatched hardware."""
        local_hardware = None
        peer_hardware = 'FA-m50'
        expected = [['Hardware', 'FAIL', 'Could not verify both controllers.']]
        result = wfs_checks.check_hardware(local_hardware, peer_hardware)
        self.assertEqual(result, expected)


class TestCheckVersions(unittest.TestCase):
    """Unittests for check_versions."""

    def test_good_versions(self):
        """Test good versions."""
        local_version = '5.1.3'
        peer_version = '5.1.3'
        expected = [['Version', 'PASS', 'Both controllers are running 5.1.3']]
        result = wfs_checks.check_versions(local_version, peer_version)
        self.assertEqual(expected, result)

    def test_bad_versions_beta(self):
        """Test bad version with beta string."""
        local_version = '5.1.3.beta'
        peer_version = '5.1.3'
        expected = [['Version', 'FAIL', 'Unable to determine controller Purity Version.  MANUAL CHECK REQUIRED!']]
        result = wfs_checks.check_versions(local_version, peer_version)
        self.assertEqual(expected, result)

    def test_bad_versions_low(self):
        """Test bad version that's unsupported."""
        local_version = '4.8.1'
        peer_version = '4.8.1'
        expected = [['Version', 'FAIL', 'Array is running 4.8.1, below supported threshold.']]
        result = wfs_checks.check_versions(local_version, peer_version)
        self.assertEqual(expected, result)

    def test_mismatched_versions(self):
        """Test mismatched versions."""
        local_version = '5.1.3'
        peer_version = '5.1.4'
        expected = [['Version', 'FAIL', 'Purity version mismatch between controllers!']]
        result = wfs_checks.check_versions(local_version, peer_version)
        self.assertEqual(expected, result)


class TestCheckISCSIPorts(unittest.TestCase):
    """Unittests for check_iscsi_ports."""

    def test_configured_iscsi(self):
        """Test that we succeed when more than 4 ports"""
        good_iscsi_purenetwork = """Name      Enabled  Subnet  Address         Mask           Gateway       MTU   MAC                Speed       Services     Slaves
                            @offload.data0  True     -       10.204.112.143  255.255.255.0  10.204.112.1  1500  52:54:30:81:b3:3f  10.00 Gb/s  app          replbond
                            ct0.eth0  True     -       10.204.112.150  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:dd  1.00 Gb/s   management   -
                            ct0.eth1  False    -       -               -              -             1500  24:a9:37:00:20:dc  1.00 Gb/s   replication  -
                            ct0.eth2  False    -       -               -              -             1500  24:a9:37:00:20:de  10.00 Gb/s  iscsi        -
                            ct0.eth3  False    -       -               -              -             1500  24:a9:37:00:20:df  10.00 Gb/s  iscsi        -
                            ct0.eth6  True     -       -               -              -             1500  90:e2:ba:d7:ea:65  10.00 Gb/s  iscsi        -
                            ct0.eth7  True     -       -               -              -             1500  90:e2:ba:d7:ea:64  10.00 Gb/s  iscsi        -
                            ct1.eth0  True     -       10.204.112.155  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:47  1.00 Gb/s   management   -
                            ct1.eth1  False    -       -               -              -             1500  24:a9:37:00:20:46  1.00 Gb/s   replication  -
                            ct1.eth2  False    -       -               -              -             1500  24:a9:37:00:20:48  10.00 Gb/s  iscsi        -
                            ct1.eth3  False    -       -               -              -             1500  24:a9:37:00:20:49  10.00 Gb/s  iscsi        -
                            ct1.eth6  True     -       -               -              -             1500  90:e2:ba:c7:70:d5  10.00 Gb/s  iscsi        -
                            ct1.eth7  True     -       -               -              -             1500  90:e2:ba:c7:70:d4  10.00 Gb/s  iscsi        -
                            replbond  False    -       10.204.112.151  255.255.255.0  10.204.112.1  1500  ba:97:86:38:12:62  0.00 b/s    replication  -
                            vir0      True     -       10.204.112.159  255.255.255.0  10.204.112.1  1500  24:a9:37:fb:ea:2c  1.00 Gb/s   management   -     """

        expected = [['ISCSI', 'PASS', 'Four valid 10.00GB/s iSCSI Ports required, 8 found: ct0.eth2, ct0.eth3, ct0.eth6, ct0.eth7, ct1.eth2, ct1.eth3, ct1.eth6, ct1.eth7']]
        result = wfs_checks.check_iscsi_ports(good_iscsi_purenetwork)
        self.assertEqual(expected, result)

    def test_unconfigured_iscsi(self):
        """Test that we fail when not enough 10g ports"""
        bad_iscsi_purenetwork = """ Name      Enabled  Subnet  Address         Mask           Gateway       MTU   MAC                Speed       Services     Slaves
                            @offload.data0  True     -       10.204.112.143  255.255.255.0  10.204.112.1  1500  52:54:30:81:b3:3f  10.00 Gb/s  app          replbond
                            ct0.eth0  True     -       10.204.112.150  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:dd  1.00 Gb/s   management   -
                            ct0.eth1  False    -       -               -              -             1500  24:a9:37:00:20:dc  1.00 Gb/s   replication  -
                            ct0.eth2  False    -       -               -              -             1500  24:a9:37:00:20:de  1.00 Gb/s  iscsi        -
                            ct0.eth3  False    -       -               -              -             1500  24:a9:37:00:20:df  1.00 Gb/s  iscsi        -
                            ct0.eth6  True     -       -               -              -             1500  90:e2:ba:d7:ea:65  1.00 Gb/s  iscsi        -
                            ct0.eth7  True     -       -               -              -             1500  90:e2:ba:d7:ea:64  1.00 Gb/s  iscsi        -
                            ct0.eth8  True     -       192.168.26.58   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:95  1.00 Gb/s  iscsi        -
                            ct0.eth9  True     -       192.168.26.59   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:94  1.00 Gb/s  iscsi        -
                            ct1.eth0  True     -       10.204.112.155  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:47  1.00 Gb/s   management   -
                            ct1.eth1  False    -       -               -              -             1500  24:a9:37:00:20:46  1.00 Gb/s   replication  -
                            ct1.eth2  False    -       -               -              -             1500  24:a9:37:00:20:48  1.00 Gb/s  iscsi        -
                            ct1.eth3  False    -       -               -              -             1500  24:a9:37:00:20:49  1.00 Gb/s  iscsi        -
                            ct1.eth6  True     -       -               -              -             1500  90:e2:ba:c7:70:d5  1.00 Gb/s  iscsi        -
                            ct1.eth7  True     -       -               -              -             1500  90:e2:ba:c7:70:d4  1.00 Gb/s  iscsi        -
                            ct1.eth8  True     -       192.168.26.60   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:21  1.00 Gb/s  iscsi        -
                            ct1.eth9  True     -       192.168.26.61   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:20  1.00 Gb/s  iscsi        -
                            replbond  False    -       10.204.112.151  255.255.255.0  10.204.112.1  1500  ba:97:86:38:12:62  0.00 b/s    replication  -
                            vir0      True     -       10.204.112.159  255.255.255.0  10.204.112.1  1500  24:a9:37:fb:ea:2c  1.00 Gb/s   management   -     """

        expected = [['ISCSI', 'FAIL', 'Four valid 10.00GB/s iSCSI Ports required, 0 found']]
        result = wfs_checks.check_iscsi_ports(bad_iscsi_purenetwork)
        self.assertEqual(expected, result)

    def test_four_iscsi(self):
        """Test that we succeed when just enough 10g ports"""
        four_iscsi_purenetwork = """ Name      Enabled  Subnet  Address         Mask           Gateway       MTU   MAC                Speed       Services     Slaves
                            @offload.data0  True     -       10.204.112.143  255.255.255.0  10.204.112.1  1500  52:54:30:81:b3:3f  10.00 Gb/s  app          replbond
                            ct0.eth0  True     -       10.204.112.150  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:dd  1.00 Gb/s   management   -
                            ct0.eth1  False    -       -               -              -             1500  24:a9:37:00:20:dc  1.00 Gb/s   replication  -
                            ct0.eth6  True     -       -               -              -             1500  90:e2:ba:d7:ea:65  1.00 Gb/s  iscsi        -
                            ct0.eth7  True     -       -               -              -             1500  90:e2:ba:d7:ea:64  10.00 Gb/s  iscsi        -
                            ct0.eth8  True     -       192.168.26.58   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:95  10.00 Gb/s  iscsi        -
                            ct0.eth9  True     -       192.168.26.59   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:94  1.00 Gb/s  iscsi        -
                            ct1.eth0  True     -       10.204.112.155  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:47  1.00 Gb/s   management   -
                            ct1.eth1  False    -       -               -              -             1500  24:a9:37:00:20:46  1.00 Gb/s   replication  -
                            ct1.eth6  True     -       -               -              -             1500  90:e2:ba:c7:70:d5  10.00 Gb/s  iscsi        -
                            ct1.eth7  True     -       -               -              -             1500  90:e2:ba:c7:70:d4  10.00 Gb/s  iscsi        -
                            ct1.eth8  True     -       192.168.26.60   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:21  1.00 Gb/s  iscsi        -
                            ct1.eth9  True     -       192.168.26.61   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:20  1.00 Gb/s  iscsi        -
                            replbond  False    -       10.204.112.151  255.255.255.0  10.204.112.1  1500  ba:97:86:38:12:62  0.00 b/s    replication  -
                            vir0      True     -       10.204.112.159  255.255.255.0  10.204.112.1  1500  24:a9:37:fb:ea:2c  1.00 Gb/s   management   -     """

        expected = [['ISCSI', 'PASS', 'Four valid 10.00GB/s iSCSI Ports required, 4 found: ct0.eth7, ct0.eth8, ct1.eth6, ct1.eth7']]
        result = wfs_checks.check_iscsi_ports(four_iscsi_purenetwork)
        self.assertEqual(expected, result)

    def test_two_iscsi(self):
        """Test that we succeed when just enough 10g ports"""
        four_iscsi_purenetwork = """ Name      Enabled  Subnet  Address         Mask           Gateway       MTU   MAC                Speed       Services     Slaves
                            ct0.eth0  True     -       10.204.112.150  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:dd  1.00 Gb/s   management   -
                            ct0.eth1  False    -       -               -              -             1500  24:a9:37:00:20:dc  1.00 Gb/s   replication  -
                            ct0.eth6  True     -       -               -              -             1500  90:e2:ba:d7:ea:65  1.00 Gb/s  iscsi        -
                            ct0.eth7  True     -       -               -              -             1500  90:e2:ba:d7:ea:64  10.00 Gb/s  iscsi        -
                            ct0.eth8  True     -       192.168.26.58   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:95  1.00 Gb/s  iscsi        -
                            ct0.eth9  True     -       192.168.26.59   255.255.255.0  192.168.26.2  9000  90:e2:ba:6b:17:94  1.00 Gb/s  iscsi        -
                            ct1.eth0  True     -       10.204.112.155  255.255.255.0  10.204.112.1  1500  24:a9:37:00:20:47  1.00 Gb/s   management   -
                            ct1.eth1  False    -       -               -              -             1500  24:a9:37:00:20:46  1.00 Gb/s   replication  -
                            ct1.eth6  True     -       -               -              -             1500  90:e2:ba:c7:70:d5  1.00 Gb/s  iscsi        -
                            ct1.eth7  True     -       -               -              -             1500  90:e2:ba:c7:70:d4  10.00 Gb/s  iscsi        -
                            ct1.eth8  True     -       192.168.26.60   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:21  1.00 Gb/s  iscsi        -
                            ct1.eth9  True     -       192.168.26.61   255.255.255.0  192.168.26.2  9000  90:e2:ba:5b:f4:20  1.00 Gb/s  iscsi        -
                            replbond  False    -       10.204.112.151  255.255.255.0  10.204.112.1  1500  ba:97:86:38:12:62  0.00 b/s    replication  -
                            vir0      True     -       10.204.112.159  255.255.255.0  10.204.112.1  1500  24:a9:37:fb:ea:2c  1.00 Gb/s   management   -     """

        expected = [['ISCSI', 'FAIL', 'Four valid 10.00GB/s iSCSI Ports required, 2 found: ct0.eth7, ct1.eth7']]
        result = wfs_checks.check_iscsi_ports(four_iscsi_purenetwork)
        self.assertEqual(expected, result)


class TestCheckSyncrep(unittest.TestCase):
    """"Unit tests for check_syncrep."""

    def test_not_set(self):
        """Test syncrep tunable unset."""
        version = '4.1.2'
        tunables = "PS_IRIS_FALLBACK=1 # PURE-83805\nPS_QOS_CHUNKY_RESOURCE_FULL_THRESHOLD=1024 # Set during upgrade to 5.0.2\nPS_DEDUP_INLINE_LOOKUP_PAGE_LIMIT=2 # Set during upgrade to 5.0.2\nCRAWLER_HASH_PULL_SPACE_BITS=2 # Set during upgrade to 5.0.2\nCRAWLER_MAX_AUTO_TUNE_RANGE_SEQ=8192000 # Set during upgrade to 5.0.2\nPS_SAN_ISCSI_ID=8386741441960291893 # SLC-LAB\nPS_SAN_ARRAY_ID=15602849 # SLC-LAB\nPS_NETWORK_ARRAY_ID=3391063 # SLC-LAB\nPURITY_START_ON_BOOT=1 # \nPS_VM_ATTACHED_INTERFACES='eth7' # "
        expected = [['Syncrep', 'PASS', 'ActiveCluster tunable is not set.']]
        results = wfs_checks.check_syncrep(version, tunables)
        self.assertEqual(expected, results)

    def test_set_bad_version(self):
        """Test syncrep tunable set but on unsupported version."""
        version = '4.1.2'
        tunables = "PS_SYNCREP_ENABLED=1 # FAKE-123\nPS_IRIS_FALLBACK=1 # PURE-83805\nPS_QOS_CHUNKY_RESOURCE_FULL_THRESHOLD=1024 # Set during upgrade to 5.0.2\nPS_DEDUP_INLINE_LOOKUP_PAGE_LIMIT=2 # Set during upgrade to 5.0.2\nCRAWLER_HASH_PULL_SPACE_BITS=2 # Set during upgrade to 5.0.2\nCRAWLER_MAX_AUTO_TUNE_RANGE_SEQ=8192000 # Set during upgrade to 5.0.2\nPS_SAN_ISCSI_ID=8386741441960291893 # SLC-LAB\nPS_SAN_ARRAY_ID=15602849 # SLC-LAB\nPS_NETWORK_ARRAY_ID=3391063 # SLC-LAB\nPURITY_START_ON_BOOT=1 # \nPS_VM_ATTACHED_INTERFACES='eth7' # "
        expected = [['Syncrep', 'FAIL', 'ActiveCluster is enabled']]
        results = wfs_checks.check_syncrep(version, tunables)
        self.assertEqual(expected, results)

    def test_set_good_version(self):
        """Test syncrep tunable set but on supported version."""
        version = '5.1.2'
        tunables = "PS_SYNCREP_ENABLED=1 # FAKE-123\nPS_IRIS_FALLBACK=1 # PURE-83805\nPS_QOS_CHUNKY_RESOURCE_FULL_THRESHOLD=1024 # Set during upgrade to 5.0.2\nPS_DEDUP_INLINE_LOOKUP_PAGE_LIMIT=2 # Set during upgrade to 5.0.2\nCRAWLER_HASH_PULL_SPACE_BITS=2 # Set during upgrade to 5.0.2\nCRAWLER_MAX_AUTO_TUNE_RANGE_SEQ=8192000 # Set during upgrade to 5.0.2\nPS_SAN_ISCSI_ID=8386741441960291893 # SLC-LAB\nPS_SAN_ARRAY_ID=15602849 # SLC-LAB\nPS_NETWORK_ARRAY_ID=3391063 # SLC-LAB\nPURITY_START_ON_BOOT=1 # \nPS_VM_ATTACHED_INTERFACES='eth7' # "
        expected = [['Syncrep', 'PASS', '5.1.2 Allows ActiveCluster and WFS to run concurrently.']]
        results = wfs_checks.check_syncrep(version, tunables)
        self.assertEqual(expected, results)


class TestGetInterfaceDict(unittest.TestCase):
    """Test get interface dict."""

    @patch('subprocess.check_output', return_fake_configured_lines)
    def test_get_interface_dict(self):
        """Test a full interface dict."""
        result = wfs_checks.get_interface_dict(['eth6', 'eth7'])
        expected = {'ct0.eth6': '10.204.121.24',
                    'ct0.eth7': '10.204.121.25',
                    'ct1.eth6': '10.204.121.26',
                    'ct1.eth7': '10.204.121.27'}
        self.assertEqual(result, expected)

    @patch('subprocess.check_output', return_fake_configured_lines)
    def test_get_partial(self):
        """Test a partial interface dict."""
        result = wfs_checks.get_interface_dict(['eth6'])
        expected = {'ct0.eth6': '10.204.121.24',
                    'ct1.eth6': '10.204.121.26'}
        self.assertEqual(result, expected)
