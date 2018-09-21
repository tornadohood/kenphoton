"""Unit tests for diagnostics."""

import os
import unittest

from six import iteritems
from six import string_types

from photon.lib import parser_utils
from photon.backend.pure.logs import diagnostics as diags

PATH = os.path.dirname(__file__)
FORMS = (
    'apartments',
    'array_name',
    'capacity',
    'chassis_serial',
    'controller_mode',
    'controller_model',
    'controller_serial',
    'controller_status',
    'controller_version',
    'cpu_info',
    'data_reduction',
    'eth_counters',
    'finddrive_all',
    'hardware_check',
    'parity',
    'pgroup_snap_count',
    'physical_memory',
    'portal_state_info',
    'purealert_list',
    'purearray_list',
    'purearray_list_connect',
    'purearray_list_controller',
    'purearray_list_ntpserver',
    'purearray_list_phonehome',
    'purearray_list_relayhost',
    'purearray_list_sender',
    'purearray_list_space',
    'puredb_dedup_version',
    'puredb_list_apartment_mappings',
    'puredb_list_tunable_diff',
    'puredb_list_reservation',
    'puredb_messaging_list',
    'puredb_npiv_status',
    'puredb_npiv_supported',
    'puredb_replication_list',
    'puredb_stats_crawler',
    'puredns_list_all',
    'puredrive_list',
    'pureds_list',
    'pureds_list_groups',
    'purehgroup_list',
    'purehgroup_list_connect',
    'purehost_list',
    'purehost_list_connect',
    'purehw_list',
    'purenetwork_list_all',
    'purepgroup_list',
    'purepgroup_list_retention',
    'purepgroup_list_schedule',
    'purepgroup_list_snap_space_total',
    'purepgroup_list_snap_transfer',
    'purepgroup_list_space_total',
    'pureport_list',
    'pureport_list_initiator',
    'puresnmp_list',
    'puresubnet_list',
    'purevol_list',
    'purevol_list_connect',
    'purevol_list_snap',
    'purevol_list_space_total',
    'purity_version',
    'shared_space',
    'snapshot_space',
    'system_space',
    'ssd_capacity',
    'thin_provisioning',
    'timezone',
    'total_reduction',
    'tunables',
    'volume_space',
)
# There will be a handful of long lines due to results comparisons, this is intentional.
# pylint: disable=line-too-long


class DiagFormDataTestCase(unittest.TestCase):
    """Unit tests for DiagFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        data = diags.DiagFormData()
        self.assertIsInstance(data.diagnostics, parser_utils.IntervalForm)
        # Not much else to test here afaik.


class DiagLogDataTestCase(unittest.TestCase):
    """Unit tests for DiagLogData."""

    def test_build(self):
        """Ensure that this builds with the right forms and text to match."""
        log = diags.DiagLogData(['diagnostics'])
        self.assertIsNone(log.forms['diagnostics'].text_to_match)


class DiagnosticsParserTestCase(unittest.TestCase):
    """Unit tests for DiagnosticsParser."""
    log_file = os.path.join(PATH, 'test_files/diagnostics-test.gz')
    parser = diags.DiagnosticsParser(log_file=log_file)

    def test_forms(self):
        """Ensure that forms include the needed information."""
        forms = self.parser.forms
        # Currently only requires 'diagnostics'.
        self.assertTrue(hasattr(forms, 'diagnostics'))

    def test_fields(self):
        """Ensure that Fields are well formed."""
        # If we add any other forms besides diagnostics then this needs to be updated.
        for datum, log_data in iteritems(self.parser.fields):
            # Assert that each fields has diagnostics
            msg = 'Field "{}" has no diagnostics.'.format(datum)
            self.assertTrue('diagnostics' in log_data.forms, msg)
            # Assert that each fields has a parser
            msg = 'Datum "{}" has no parser.'.format(datum)
            self.assertTrue(hasattr(self.parser, 'get_{}'.format(datum)), msg=msg)

    def test_parsers(self):
        """Ensure that each public facing parser is defined in fields."""
        skip = ['get_form_lines', 'get_field', 'get_fields']
        getters = [atr for atr in dir(self.parser) if atr.startswith('get_') and atr not in skip]
        for getter in getters:
            # Assert that each getter has an entry in fields
            msg = 'Getter "get_{}" is not defined in fields.'.format(getter)
            self.assertTrue(getter.split('_', 1)[1] in self.parser.fields, msg=msg)

    def test_fields_tests(self):
        """Ensure that each item in fields has a unit test."""
        for datum in self.parser.fields:
            msg = 'Known Data "{}" does not have a unit test.  Please write one.'.format(datum)
            self.assertTrue(datum in DiagnosticsKnownDataTestCases.expected_results, msg=msg)


class DiagnosticsKnownDataTestCases(unittest.TestCase):
    """Unit tests for individual known datum in the DiagnosticsParser."""
    expected_results = {
        'apartments': 44,
        'array_name': 'DR-Pure3',
        'capacity': 114920955335147,
        'chassis_serial': 'PCHFS15330028',
        'controller_mode': [u'Mode', u'Name'],
        'controller_model': [u'Model', u'Name'],
        'controller_serial': 'PCTFL1631023A',
        'controller_status': ['Name', 'Status'],
        'controller_version': ['Name', 'Version'],
        'cpu_info': ['core_count', 'cpu_model', 'cpu_type', 'speed'],
        'data_reduction': '3.9 to 1',
        'eth_counters': ['eth0', 'eth1', 'eth2', 'eth3', 'haeth0'],
        'finddrive_all': ['Drive', 'Enclosure', 'Expander', 'Nodes', 'Product', 'Rev', 'SAT',
                          'SAT_Rev', 'SN', 'Slot', 'Subslot'],
        'hardware_check': ['CPU', 'FC TARGETS', 'INFINIBAND ADAPTERS', 'NON-TRANSPARENT BRIDGE',
                           'RAM', 'Results', 'STORAGE', 'iSCSI TARGETS'],
        'parity': '100%',
        'pgroup_snap_count': 9,
        'physical_memory': 1056547520000,
        'portal_state_info': ['gen', 'info', 'portal state', 'primary'],
        'purealert_list': [u'Enabled', u'Name'],
        'purearray_list': [u'ID', u'Name', u'Revision', u'Version'],
        'purearray_list_connect': [u'Connected', u'ID', u'Management Address', u'Name',
                                   u'Replication Address', u'Throttled', u'Type', u'Version'],
        'purearray_list_controller': [u'Mode', u'Model', u'Name', u'Status', u'Version'],
        'purearray_list_ntpserver': 'time.paylocity.com',
        'purearray_list_phonehome': 'enabled',
        'purearray_list_relayhost': 'mail.paylocity.com',
        'purearray_list_sender': 'paylocity.com',
        'purearray_list_space': [u'Capacity', u'Data Reduction', u'Name', u'Parity',
                                 u'Shared Space', u'Snapshots', u'System', u'Thin Provisioning',
                                 u'Total', u'Total Reduction', u'Volumes'],
        'puredb_dedup_version': '2',
        'puredb_list_apartment_mappings': [u'Apartment', u'Apt Id', u'Firewall Mark', u'Name'],
        'puredb_list_tunable_diff': [u'Description', u'Name', u'Preset', u'Type', u'Value'],
        'puredb_list_tunable_platform_diff': [],
        'puredb_list_reservation': ['Fabric', 'Initiator', 'Isid', 'Reservation Key', 'Target',
                                    'Type', 'Vol'],
        'puredb_messaging_list': ['Address', 'App', 'Connect Time', 'Id', 'Keepalive Time',
                                  'Local Endpoint', 'Port', 'Port Name', 'Received Bytes',
                                  'Remote Endpoint', 'Sent Bytes'],
        'puredb_npiv_status': 'False',
        'puredb_npiv_supported': ['Comment', 'Supported'],
        'puredb_replication_list': ['Bytes Received', 'Bytes Sent', 'Cancelled', 'Complete', 'Connection ID',
                                    'Dest Array', 'Dest Medium Id', 'Dest Vol Id', 'Diff Snap Id', 'Done', 'Id',
                                    'Inline Dup Bytes', 'Logical Content Sectors', 'Mask Count', 'Mode',
                                    'Physical Bytes Written', 'Sector', 'Sector End', 'Snapshot Id', 'Snapshot Name',
                                    'Source Array', 'Start Time', 'Transport Dup Bytes'],
        'puredb_stats_crawler': ['Crawler running', 'Current sequence', 'Dup emitter range begin time',
                                 'Dup emitter range progress', 'Dup emitter range upper sequence',
                                 'Hash matcher range begin time', 'Hash matcher range progress',
                                 'Hash matcher range upper sequence', 'Open segment sequence', 'Processed sequence'],
        'puredns_list_all': ['Domain', 'Method', 'Nameservers', 'Search'],
        'puredrive_list': ['Capacity', 'Details', 'Last Evac Completed', 'Last Failure', 'Name',
                           'Status', 'Type'],
        'pureds_list': ['Base DN', 'Bind Password', 'Bind User', 'Check Peer', 'Enabled', 'URI'],
        'pureds_list_groups': ['Array Admin Group', 'Group Base', 'Read-only Group', 'Storage Admin Group'],
        'purehgroup_list': ['Hosts', 'Name'],
        'purehgroup_list_connect': [u'Lun', u'Name', u'Vol'],
        'purehost_list': ['Host Group', 'IQN', 'Name', 'WWN'],
        'purehost_list_connect': ['Host Group', 'LUN', 'Name', 'Vol'],
        'purehw_list': ['CH0', 'CH0.BAY0', 'CH0.BAY1', 'CH0.BAY10', 'CH0.BAY11', 'CH0.BAY12', 'CH0.BAY13', 'CH0.BAY14', 'CH0.BAY15', 'CH0.BAY16', 'CH0.BAY17', 'CH0.BAY18', 'CH0.BAY19', 'CH0.BAY2', 'CH0.BAY3', 'CH0.BAY4', 'CH0.BAY5', 'CH0.BAY6', 'CH0.BAY7', 'CH0.BAY8', 'CH0.BAY9', 'CH0.NVB0', 'CH0.NVB1', 'CH0.NVB2', 'CH0.NVB3', 'CH0.PWR0', 'CH0.PWR1', 'CH0.TMP0', 'CT0', 'CT0.ETH0', 'CT0.ETH1', 'CT0.ETH2', 'CT0.ETH3', 'CT0.FAN0', 'CT0.FAN1', 'CT0.FAN2', 'CT0.FAN3', 'CT0.FAN4', 'CT0.FAN5', 'CT0.FC0', 'CT0.FC1', 'CT0.FC2', 'CT0.FC3', 'CT0.FC6', 'CT0.FC7', 'CT0.SAS0', 'CT0.SAS1', 'CT0.SAS2', 'CT0.SAS3', 'CT0.TMP0', 'CT0.TMP1', 'CT0.TMP10', 'CT0.TMP11', 'CT0.TMP12', 'CT0.TMP13', 'CT0.TMP14', 'CT0.TMP15', 'CT0.TMP16', 'CT0.TMP17', 'CT0.TMP18', 'CT0.TMP19', 'CT0.TMP2', 'CT0.TMP20', 'CT0.TMP21', 'CT0.TMP22', 'CT0.TMP23', 'CT0.TMP24', 'CT0.TMP3', 'CT0.TMP4', 'CT0.TMP5', 'CT0.TMP6', 'CT0.TMP7', 'CT0.TMP8', 'CT0.TMP9', 'CT1', 'CT1.ETH0', 'CT1.ETH1', 'CT1.ETH2', 'CT1.ETH3', 'CT1.FAN0', 'CT1.FAN1', 'CT1.FAN2', 'CT1.FAN3', 'CT1.FAN4', 'CT1.FAN5', 'CT1.FC0', 'CT1.FC1', 'CT1.FC2', 'CT1.FC3', 'CT1.FC6', 'CT1.FC7', 'CT1.SAS0', 'CT1.SAS1', 'CT1.SAS2', 'CT1.SAS3', 'CT1.TMP0', 'CT1.TMP1', 'CT1.TMP10', 'CT1.TMP11', 'CT1.TMP12', 'CT1.TMP13', 'CT1.TMP14', 'CT1.TMP15', 'CT1.TMP16', 'CT1.TMP17', 'CT1.TMP18', 'CT1.TMP19', 'CT1.TMP2', 'CT1.TMP20', 'CT1.TMP21', 'CT1.TMP22', 'CT1.TMP23', 'CT1.TMP24', 'CT1.TMP3', 'CT1.TMP4', 'CT1.TMP5', 'CT1.TMP6', 'CT1.TMP7', 'CT1.TMP8', 'CT1.TMP9', 'SH0', 'SH0.BAY0', 'SH0.BAY1', 'SH0.BAY10', 'SH0.BAY11', 'SH0.BAY12', 'SH0.BAY13', 'SH0.BAY14', 'SH0.BAY15', 'SH0.BAY16', 'SH0.BAY17', 'SH0.BAY18', 'SH0.BAY19', 'SH0.BAY2', 'SH0.BAY20', 'SH0.BAY21', 'SH0.BAY22', 'SH0.BAY23', 'SH0.BAY3', 'SH0.BAY4', 'SH0.BAY5', 'SH0.BAY6', 'SH0.BAY7', 'SH0.BAY8', 'SH0.BAY9', 'SH0.FAN0', 'SH0.FAN1', 'SH0.FAN2', 'SH0.FAN3', 'SH0.IOM0', 'SH0.IOM1', 'SH0.PWR0', 'SH0.PWR1', 'SH0.SAS0', 'SH0.SAS1', 'SH0.SAS2', 'SH0.SAS3', 'SH0.SAS4', 'SH0.SAS5', 'SH0.TMP0', 'SH0.TMP1', 'SH0.TMP2', 'SH0.TMP3', 'SH0.TMP4', 'SH0.TMP5', 'SH0.TMP6', 'SH0.TMP7', 'SH1', 'SH1.BAY0', 'SH1.BAY1', 'SH1.BAY10', 'SH1.BAY11', 'SH1.BAY12', 'SH1.BAY13', 'SH1.BAY14', 'SH1.BAY15', 'SH1.BAY16', 'SH1.BAY17', 'SH1.BAY18', 'SH1.BAY19', 'SH1.BAY2', 'SH1.BAY20', 'SH1.BAY21', 'SH1.BAY22', 'SH1.BAY23', 'SH1.BAY3', 'SH1.BAY4', 'SH1.BAY5', 'SH1.BAY6', 'SH1.BAY7', 'SH1.BAY8', 'SH1.BAY9', 'SH1.FAN0', 'SH1.FAN1', 'SH1.FAN2', 'SH1.FAN3', 'SH1.IOM0', 'SH1.IOM1', 'SH1.PWR0', 'SH1.PWR1', 'SH1.SAS0', 'SH1.SAS1', 'SH1.SAS2', 'SH1.SAS3', 'SH1.SAS4', 'SH1.SAS5', 'SH1.TMP0', 'SH1.TMP1', 'SH1.TMP2', 'SH1.TMP3', 'SH1.TMP4', 'SH1.TMP5', 'SH1.TMP6', 'SH1.TMP7', 'SH2', 'SH2.BAY0', 'SH2.BAY1', 'SH2.BAY10', 'SH2.BAY11', 'SH2.BAY12', 'SH2.BAY13', 'SH2.BAY14', 'SH2.BAY15', 'SH2.BAY16', 'SH2.BAY17', 'SH2.BAY18', 'SH2.BAY19', 'SH2.BAY2', 'SH2.BAY20', 'SH2.BAY21', 'SH2.BAY22', 'SH2.BAY23', 'SH2.BAY3', 'SH2.BAY4', 'SH2.BAY5', 'SH2.BAY6', 'SH2.BAY7', 'SH2.BAY8', 'SH2.BAY9', 'SH2.FAN0', 'SH2.FAN1', 'SH2.FAN2', 'SH2.FAN3', 'SH2.IOM0', 'SH2.IOM1', 'SH2.PWR0', 'SH2.PWR1', 'SH2.SAS0', 'SH2.SAS1', 'SH2.SAS2', 'SH2.SAS3', 'SH2.SAS4', 'SH2.SAS5', 'SH2.TMP0', 'SH2.TMP1', 'SH2.TMP2', 'SH2.TMP3', 'SH2.TMP4', 'SH2.TMP5', 'SH2.TMP6', 'SH2.TMP7'],
        'purenetwork_list_all': ['Address', 'Enabled', 'Gateway', 'MAC', 'MTU', 'Mask', 'Method',
                                 'Name', 'Services', 'Slaves', 'Speed', 'Subnet'],
        'purepgroup_list': ['Host Groups', 'Hosts', 'Name', 'Source', 'Targets', 'Volumes'],
        'purepgroup_list_retention': ['All For', 'Array', 'Days', 'Name', 'Per Day'],
        'purepgroup_list_schedule': [u'At', u'Blackout', u'Enabled', u'Frequency', u'Name',
                                     u'Schedule'],
        'purepgroup_list_snap_space_total': [u'Name', u'Snapshots'],
        'purepgroup_list_snap_transfer': [u'Completed', u'Created', u'Data Transferred', u'Name',
                                          u'Physical Bytes Written', u'Progress', u'Source',
                                          u'Started'],
        'purepgroup_list_space_total': [u'Name', u'Snapshots'],
        'pureport_list': ['Failover', 'IQN', 'Name', 'Portal', 'WWN'],
        'pureport_list_initiator': ['Failover', 'Initiator IQN', 'Initiator Portal', 'Initiator WWN', 'Target',
                                    'Target IQN', 'Target Portal', 'Target WWN'],
        'puresnmp_list': [u'Auth Passphrase', u'Auth Protocol', u'Community', u'Host', u'Name',
                          u'Privacy Passphrase', u'Privacy Protocol', u'User', u'Version'],
        'puresubnet_list': [],
        'purevol_list': [u'Created', u'Name', u'Serial', u'Size', u'Source'],
        'purevol_list_connect': ['Host', 'Host Group', 'LUN', 'Name', 'Size'],
        'purevol_list_snap': [u'Created', u'Name', u'Serial', u'Size', u'Source'],
        'purevol_list_space_total': [u'Data Reduction', u'Name', u'Shared Space', u'Size',
                                     u'Snapshots', u'System', u'Thin Provisioning', u'Total',
                                     u'Total Reduction', u'Volume'],
        'purity_version': '4.10.5',
        'shared_space': 32996343949557,
        'snapshot_space': 29840745577840,
        'system_space': 0,
        'ssd_capacity': 182109533928108,
        'thin_provisioning': '48%',
        'timezone': 'America/Chicago',
        'total_reduction': '7.5 to 1',
        'tunables': ['DEDUP_TOP_CRAWLER_DISABLED', 'PS_DEDUP_POST_UPGRADE_PER_SEG_DELAY_MSEC',
                     'PS_IRIS_FALLBACK', 'PURITY_START_ON_BOOT'],
        'volume_space': 6047313952768,
    }
    parser = diags.DiagnosticsParser(os.path.join(PATH, 'test_files/diagnostics-test.gz'))
    parser.controller_name = 'CT0'

    def test_individual_parsers(self):
        """Test the output of each parser."""
        for form_parser in FORMS:
            getter = 'get_{}'.format(form_parser)
            result = getattr(self.parser, getter)()
            # Just test the first value in the list of results:
            value = sorted(result)[0][1]
            if isinstance(value, dict):
                value = sorted(list(value.keys()))
            elif isinstance(value, list):
                if getter.startswith(('get_expander', 'get_hardware_check')):
                    # Just check the length of lines, as this should get a list of raw lines.
                    value = len(value)
                else:
                    value = value[0]
            # Convert any remaining long strings to a length for easier comparison.
            if isinstance(value, string_types) and len(value) > 25:
                value = len(value)
            # The result should be a list of tuples containing (timestamp, value_lines).
            msg = 'The Form Parser "{}" did not get the expected result.  Result was "{}".'.format(getter, value)
            self.assertEqual(self.expected_results[form_parser], value, msg=msg)


def _get_length(result):
    """Get the length of the values within the list of tuples."""
    # Get the first sub-result
    # The first index will be the datetime, the second (index 1) will be the actual lines/values.
    return len(result[0][1])
