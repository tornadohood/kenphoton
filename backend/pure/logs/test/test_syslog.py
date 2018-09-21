""" Unit tests for syslog.py"""

from __future__ import unicode_literals

import unittest
import os

from six import iteritems
from photon.lib import parser_utils
from photon.backend.pure.logs import syslog
from photon.lib.time_utils import Timestamp

PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/syslog-test.gz')


class SyslogParserTestCase(unittest.TestCase):
    """Unit tests for SyslogParser."""
    parser = syslog.SyslogParser(LOG_FILE)

    # TODO: PT-2096 - Need to get the field tests across all log parsers
    @unittest.skip
    def test_fields(self):
        for datum in self.parser.fields:
            msg = 'Field "{}" does not have a unit test.  Please write one.'.format(datum)
            self.assertTrue('test_get_{}'.format(datum) in dir(SyslogParserTestCase), msg=msg)

    def test_get_abort_cmd_found(self):
        """Get form lines for abort_cmd_found."""
        expected = [(Timestamp('2018-01-19 17:09:47'),
                     {'cdb': '0x2a',
                      'cmd': 'ffff8806a262dc20',
                      'desc': 'Found iSCSI ',
                      'fabric_state': '6',
                      'flags': '0x40109',
                      'lba': '0xa803e90',
                      'length': '0x20000',
                      'lun': '12',
                      'pr_key': '0x00000000000000',
                      'psop': '1',
                      'session': 'ffff881ff01df380',
                      't_state': '5',
                      'tag': '0x245d3300',
                      'tas': '0',
                      'transport_state': '0x82'})]
        result = self.parser.get_abort_cmd_found()
        self.assertEqual(expected, result)

    def test_get_ce_events(self):
        """Test the get_ce_events method."""
        expected = [(Timestamp('2018-01-19 14:30:00'), {'ce_mem_count': '2'})]
        result = self.parser.get_ce_events()
        self.assertEqual(expected, result)

    def test_get_els_notify(self):
        """Get form lines for els_notify."""
        expected = [(Timestamp('2018-01-19 16:20:01'),
                     {'ctrl': 'ct0',
                      'els': '0x03',
                      'exch': '0x11a1e0',
                      'loop_id': '0x0002',
                      'nport_valid': '0',
                      'ox_id': '0x1c',
                      'pci_addr': '0000:82:00',
                      's_id': '01:08:00',
                      'wwn': '10:00:00:00:c9:f3:a7:da'})]
        result = self.parser.get_els_notify()
        self.assertEqual(expected, result)

    def test_get_fc_firmware_dump(self):
        """Get form lines for fc_firmware_dump."""
        expected = [(Timestamp('2018-01-19 23:34:49'),
                     {'pci_addr': '0000:03:00',
                      'port': '3',
                      'tmp_buffer': '30/ffffc94160397000'})]
        result = self.parser.get_fc_firmware_dump()
        self.assertEqual(expected, result)

    def test_get_fc_loop_up(self):
        """Get form lines for fc_loop_up."""
        expected = [(Timestamp('2018-01-19 18:36:56'),
                     {'ctrl': 'ct1',
                      'pci_addr': '0000:06:00',
                      'speed': '8 Gbps'})]
        result = self.parser.get_fc_loop_up()
        self.assertEqual(expected, result)

    def test_get_fc_port_down(self):
        """Get form lines for fc_port_down."""
        expected = [(Timestamp('2018-01-19 16:15:22'),
                     {'ctrl': 'ct0',
                      'pci_addr': '0000:82:00',
                      'wwn': '52:4a:93:72:42:36:4a:01'})]
        result = self.parser.get_fc_port_down()
        self.assertEqual(expected, result)

    def test_get_fc_port_gone(self):
        """Get form lines for fc_port_gone."""
        expected = [(Timestamp('2018-01-19 16:17:23'),
                     {'ctrl': 'ct0',
                      'fc4_type': '0x0',
                      'flags': '0x3',
                      'pci_addr': '0000:82:00',
                      'port_state': '0x1',
                      'scan_state': '1',
                      'wwn': '10:00:00:00:c9:f3:a7:da'})]
        result = self.parser.get_fc_port_gone()
        self.assertEqual(expected, result)

    def test_get_fc_port_updates(self):
        """Get form lines for fc_port_updates."""
        expected = [(Timestamp('2018-01-19 01:00:18'),
                     {'action': 'PLOGI',
                      'pci_addr': '0000:03:00',
                      'port': '1',
                      'port_state': '0x4',
                      'reason': 'PRLI received',
                      'reason_code': '0x600'})]
        result = self.parser.get_fc_port_updates()
        self.assertEqual(expected, result)

    def test_get_fc_rscn_changes(self):
        """Get form lines for fc_rscn_changes."""
        expected = [(Timestamp('2018-01-19 01:59:17'),
                     {'pci_addr': '0000:82:00',
                      'port': '1',
                      'source_id':
                      '99:08:08'})]
        result = self.parser.get_fc_rscn_changes()
        self.assertEqual(expected, result)

    def test_get_fc_session_added(self):
        """Get form lines for fc_session_added."""
        expected = [(Timestamp('2018-01-19 14:03:31'),
                     {'ctrl': 'ct0',
                      'pci_addr': '0000:05:00',
                      's_id': '3:d:0',
                      'sess': 'ffff883fc55cc240',
                      'wwn': '21:00:00:24:ff:50:a8:a1'})]
        result = self.parser.get_fc_session_added()
        self.assertEqual(expected, result)

    def test_get_fc_qlt_free(self):
        """Get form lines for fc_qlt_free."""
        expected = [(Timestamp('2018-01-19 22:57:36'),
                     {'ctrl': 'ct1',
                      'loop_id': '0x0e',
                      'pci_addr': '0000:03:00',
                      'port': '3',
                      's_id': '01:02:00',
                      'se_sess': 'ffff889b01eca240',
                      'sess': 'ffff88fe6c6ba240',
                      'wwn': '21:00:00:24:ff:59:bd:de'})]
        result = self.parser.get_fc_qlt_free()
        self.assertEqual(expected, result)

    def test_get_gather_hw_logs(self):
        """Get form lines for gather_hw_logs."""
        expected_ts = Timestamp('2018-01-19 00:05:02')
        expected_first = 'Jan 19 00:05:02 SLC-X70-ct1 logger: gather_hw_logs: process (pid 35176) is starting.\n'
        # pylint: disable=line-too-long
        expected_third = 'Jan 19 00:05:02 SLC-X70-ct1 logger: gather_hw_logs: Running: /opt/Purity/sbin/purehw list --all\n'
        expected_last = 'Jan 19 00:09:22 SLC-X70-ct1 logger: gather_hw_logs: process (pid 35176) has completed.\n'
        result = self.parser.get_gather_hw_logs()
        # Since this is an interval form, we get a list of lists of strings,
        # not a list of strings, so we need to use result[0] to access it.
        timestamp = result[0][0]
        vals = result[0][1]
        self.assertEqual(expected_first, vals[0])
        self.assertEqual(expected_third, vals[2])
        self.assertEqual(expected_last, vals[-1])
        self.assertEqual(expected_ts, timestamp)

    def test_get_mce_counts(self):
        """Test the get_mce_counts method."""
        expected = [(Timestamp('2018-01-19 14:30:00'), 2), (Timestamp('2018-01-19 14:31:00'), 1)]
        result = self.parser.get_mce_counts()
        self.assertEqual(expected, result)

    def test_get_mce_events(self):
        """Test the get_mce_events method."""
        expected = [(Timestamp('2018-01-19 14:31:00'),
                     'Jan 19 14:31:00 S01PURE1-ct0 kernel: [13897063.755982,00] sbridge: HANDLING MCE MEMORY ERROR\n')]
        result = self.parser.get_mce_events()
        self.assertEqual(expected, result)

    def test_get_offline_memory(self):
        """Test the get_offline_memory method."""
        expected = [(Timestamp('2018-05-01 11:40:20'), 28000.0)]
        result = self.parser.get_offline_memory()
        self.assertEqual(expected, result)

    def test_get_session_map(self):
        """Get form lines for session_map."""
        expected = [(Timestamp('2018-01-19 14:29:25'),
                     {'ctrl': 'ct1',
                      'pci_addr': '0000:03:00',
                      'port': '1',
                      's_id': '46:00:01',
                      'se_sess': 'ffff88180f1e0580',
                      'sess': 'ffff88300eef9980',
                      'wwn': '20:00:00:25:b5:20:00:7f'})]
        result = self.parser.get_session_map()
        self.assertEqual(expected, result)
