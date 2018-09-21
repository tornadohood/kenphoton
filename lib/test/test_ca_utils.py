"""Unit tests for ca_utils."""

from __future__ import unicode_literals

# import socket
import unittest

from photon.lib import ca_utils
from photon.lib import custom_errors

# Try to resolve the irisdev url.
# PT-1162 Disabling this check for now.
REACHABLE = False
# try:
#    REACHABLE = socket.gethostbyname('irisdev.dev.purestorage.com')
# except socket.gaierror:
#    REACHABLE = False


AID = '1093489-260039737-2123539898130037785'
FQDN = 'slc-coz.purestorage.com'
DIAGNOSTICS_KEYS = {
    'chastity.mastership',
    'controller.info',
    'cpu.info',
    'cpu.mask',
    'cpu.util',
    'download.partition.contents',
    'enclosure.info',
    'host.fc.stats',
    'missing.path.list',
    'ntp.info',
    'partition.space',
    'process.memory',
    'purealert.list',
    'pureapp.list',
    'purearray.list',
    'purearray.list.connect',
    'purearray.list.controller',
    'purearray.list.ntpserver',
    'purearray.list.relayhost',
    'purearray.list.space',
    'purearray.test.security_token',
    'purearray_monitor',
    'puredb.check.upgrade',
    'puredb.dedup.version',
    'puredb.dump.health',
    'puredb.list.drives',
    'puredb.list.frontier_tracker_health',
    'puredb.list.job',
    'puredb.list.logbook',
    'puredb.list.mode',
    'puredb.list.nvram_throttle',
    'puredb.list.snap',
    'puredb.list.ssd_mapped',
    'puredb.npiv.supported',
    'puredb.query.catalog_size.main',
    'puredb.run.fw_upgrade_stalled',
    'puredns.list',
    'puredrive.list',
    'purehw.list',
    'puremessage_list_audit',
    'purenetwork.list',
    'purepgroup.list',
    'purepgroup.list.schedule',
    'purepgroup.list.snap',
    'pureport.list',
    'puresw.global.list',
    'puresw.list',
    'purevol.list.space',
    'rawdisk.info',
    'sel.info',
    'service.list',
    'smis.info',
    'smis.list.status',
    'task_info',
    'wwn.fcid.unique'
}
PHONEBOOK_KEYS = {
    'array_id',
    'array_sid',
    'business_unit',
    'category.cid',
    'category.editable',
    'cid',
    'cname',
    'comment',
    'customer_uid',
    'display_licensed_size',
    'domain',
    'editable',
    'for_test',
    'hidden',
    'hostname',
    'is_pure_category',
    'is_pure_org',
    'is_svar_category',
    'licensed_size',
    'licensed_size.licensed_size_id',
    'licensed_size_id',
    'location',
    'oid',
    'oname',
    'org.editable',
    'org.oid',
    'product',
    'region.rid',
    'rid',
    'rmanager_uid',
    'rname',
    'sales_oid',
    'sales_oname',
    'sales_uid',
    'sales_uname',
    'salesforce_account_id',
    'se_uid',
    'se_uname',
    'stage_id',
    'stage_name',
    'stages.stage_id',
    'vpsales_uid'
}


@unittest.skipIf(not REACHABLE, 'Does not run if Iris is not reachable.')
class GetCADiagnosticsTestCase(unittest.TestCase):
    """Unit tests for get_ca_diagnostics."""

    def test_lab_array(self):
        """Test getting information about a lab array."""
        try:
            result = ca_utils.get_ca_diagnostics(AID)
            # The array may not be phoning home all the data, or controllers may
            # be down, etc, so all we can realistically test here is that we get
            # a result from the ssh attempt.
            self.assertTrue(result)
        except custom_errors.SSHError:
            # CloudAssist is down, but DNS is up
            pass


@unittest.skipIf(not REACHABLE, 'Does not run if Iris is not reachable.')
class GetPhonebookTestCase(unittest.TestCase):
    """Unit tests for get_phonebook."""
    # TODO: Just use a simulated phonebook so we don't have to talk to Iris...

    def test_lab_aid(self):
        """Test getting information about a lab array by Array ID."""
        phonebook = ca_utils.get_phonebook(AID)
        entries = len(phonebook)
        self.assertEqual(entries, 1, msg='Got {} results for {}'.format(entries, AID))
        try:
            self.assertEqual(phonebook[0]['array_id'], AID)
        except custom_errors.SSHError:
            # CloudAssist is down, but DNS is up
            pass
        except SyntaxError:
            # Invalid data from CloudAssist
            pass


@unittest.skipIf(not REACHABLE, 'Does not run if Iris is not reachable.')
class RunSSHCmdTestCase(unittest.TestCase):
    """Unit tests for run_ssh_cmd."""

    def test_invalid_server(self):
        """Invalid remote server; should raise an SSHError."""
        with self.assertRaises(custom_errors.SSHError):
            ca_utils.run_ssh_cmd('date', server='fake_server.fake_server.fake')

    def test_invalid_command(self):
        """Invalid command."""
        with self.assertRaises(custom_errors.SSHError):
            ca_utils.run_ssh_cmd(cmd='fake_command')


if __name__ == '__main__':
    unittest.main()
