"""Unit tests for evac_health_checks."""

import unittest

import pandas

from photon.lib import apartment_utils
from photon.lib import drive_utils
from photon.lib import shelf_utils
from photon.lib import test_utils
from photon.lib import time_utils

from photon.tools.health_checks import evac_health_checks

# TODO: PT-1854 - Fixup to support Mercury and Purity 5.1.
# TODO: High level helpers to add new components to the array.
# TODO: PT-2401 - Unit tests for EvacHealthChecksAPI methods.
# Intentional naming and protected access for testing purposes.
# pylint: disable=invalid-name, protected-access, no-member


class CapacityOverrideTunableCheckTestCase(unittest.TestCase):
    """Unit tests for CapacityOverrideTunableCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.CapacityOverrideTunableCheck()

    def setUp(self):
        """Set up the test/reset default values."""
        # Example of the returned output for the 'tunables' field.
        # {'DEDUP_TOP_CRAWLER_DISABLED': '1',
        #  'PS_DEDUP_POST_UPGRADE_PER_SEG_DELAY_MSEC': '500',
        #  'PS_IRIS_FALLBACK': '1',
        #  'PURITY_START_ON_BOOT': '1'}
        # Example of the 'ssd_capacity' field: 10995116277760  # 10 TiB
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_tunable_set_high(self):
        """Test what happens when the tunable 'PS_STORAGE_CAPACITY_OVERRIDE_GB' is set >5% of capacity."""
        details = ['PS_STORAGE_CAPACITY_OVERRIDE_GB is set too high.  Open a JIRA to verify if this can be reduced.']
        self.api.set_values('ssd_capacity', 10995116277760)
        self.api.set_values('tunables', {'PS_STORAGE_CAPACITY_OVERRIDE_GB': '5500'})  # ~50% (GB)
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_tunable_set_low(self):
        """Test what happens when the tunable 'PS_STORAGE_CAPACITY_OVERRIDE_GB' is set <=5% of capacity."""
        details = ['PS_STORAGE_CAPACITY_OVERRIDE_GB is set at or below 5% of the Array capacity.']
        self.api.set_values('ssd_capacity', 182109533928108)
        self.api.set_values('tunables', {'PS_STORAGE_CAPACITY_OVERRIDE_GB': '440'})  # ~4% (GB)
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_tunable_not_set(self):
        """Test what happens when the tunable 'PS_STORAGE_CAPACITY_OVERRIDE_GB' is set to '0'."""
        details = ['PS_STORAGE_CAPACITY_OVERRIDE_GB is set at or below 5% of the Array capacity.']
        self.api.set_values('ssd_capacity', 182109533928108)
        self.api.set_values('tunables', {'PS_STORAGE_CAPACITY_OVERRIDE_GB': '0'})
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_tunable_not_present(self):
        """Test what happens when the tunable 'PS_STORAGE_CAPACITY_OVERRIDE_GB' is not even listed."""
        details = ['PS_STORAGE_CAPACITY_OVERRIDE_GB is not set.']
        self.api.set_values('ssd_capacity', 182109533928108)
        self.api.set_values('tunables', {})
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_tunable_bad_value(self):
        """Test what happens when the tunable has a bad value."""
        details = ['PS_STORAGE_CAPACITY_OVERRIDE_GB has a bad value.  Consult Escalations.']
        self.api.set_values('ssd_capacity', 182109533928108)
        self.api.set_values('tunables', {'PS_STORAGE_CAPACITY_OVERRIDE_GB': 'Bad value'})
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)


class ControllerHardwareCompatibilityTestCase(unittest.TestCase):
    """Unit tests for ControllerHardwareCompatibility."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.ControllerHardwareCompatibility()

    def setUp(self):
        """Reset testing."""
        # Reset the check and api:
        self.api.data_set = pandas.DataFrame()
        self.check.details = []
        self.api._device_map = None
        self.api._to_evac = {}

    def test_fa_300(self):
        """Test result with an FA-300 series."""
        details = ['Cannot do evacuations on FA-3XX series arrays.']
        model = 'FA-300'
        self.api.set_values('controller_model', {'Model': [model, model]})
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_fa_400(self):
        """Test results with all of the FA-400 series."""
        details = ['Consult with Escalations before proceeding.  FA-4XX series arrays have several restrictions.']
        models = ('FA-420', 'FA-450')
        for model in models:
            self.setUp()
            self.api.set_values('controller_model', {'Model': [model, model]})
            self.check.run_test(self.api)
            self.assertFalse(self.check.passed)
            self.assertEqual(self.check.details, details)

    def test_m_series(self):
        """Test results with an //m controller."""
        details = ['Controller Hardware is compatible.']
        models = ('FA-m10', 'FA-m10r2', 'FA-m20', 'FA-m20r2', 'FA-m50', 'FA-m50r2', 'FA-m70', 'FA-m70r2')
        for model in models:
            self.setUp()
            self.api.set_values('controller_model', {'Model': [model, model]})
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)
            self.assertEqual(self.check.details, details)

    def test_x_series_old_purity_no_wssd(self):
        """Test results with an //x controller, before 5.1.0."""
        details = ['No WSSD drives being evacuated.']
        models = ('FA-x10', 'FA-x10r2', 'FA-x20', 'FA-x20r2', 'FA-x50', 'FA-x50r2', 'FA-x70', 'FA-x70r2')
        for model in models:
            self.setUp()
            # Add data needed to build a drive map:
            self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
            self.api.set_from_file('puredb_list_drives',
                                   test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
            self.api.set_values('controller_model', {'Model': [model, model]})
            # //x (tungsten) is not compatible until 5.1.0, if we are evacuating WSSDs.
            self.api.set_values('purity_version', '5.0.1')
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)
            self.assertEqual(self.check.details, details)

    def test_x_series_new_purity_no_wssd(self):
        """Test results with an //x controller, after 5.1.0."""
        details = ['Evacuating WSSD is supported on this version of Purity.']
        models = ('FA-x10', 'FA-x10r2', 'FA-x20', 'FA-x20r2', 'FA-x50', 'FA-x50r2', 'FA-x70', 'FA-x70r2')
        for model in models:
            self.setUp()
            self.api.set_values('controller_model', {'Model': [model, model]})
            # //x (tungsten) is not compatible until 5.1.0, if we are evacuating WSSDs.
            # However, we have not added any WSSDs.
            self.api.set_values('purity_version', '5.1.0')
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)
            self.assertEqual(self.check.details, details)

    def test_x_series_old_purity_with_wssd(self):
        """Test results with an //x controller, before 5.1.0, with WSSDs being evacuated."""
        details = ['Cannot do in-place upgrades on WSSD and TUNGSTEN until Purity 5.1.0+.']
        models = ('FA-x10', 'FA-x10r2', 'FA-x20', 'FA-x20r2', 'FA-x50', 'FA-x50r2', 'FA-x70', 'FA-x70r2')
        _shelf = shelf_utils.Shelf('SH10')
        _wssd = drive_utils.WSSD('BAY1', 'SH10', capacity='1 TiB')
        _shelf.add_component(_wssd)
        for model in models:
            self.setUp()
            self.api._device_map = {'drives': {'SH10.BAY1': _wssd}, 'enclosures': {'SH10': _shelf}}
            self.api._to_evac = {'drives': ['SH10.BAY1']}
            self.api.set_values('controller_model', {'Model': [model, model]})
            # //x (tungsten) is not compatible until 5.1.0, if we are evacuating WSSDs.
            self.api.set_values('purity_version', '5.0.1')
            self.check.run_test(self.api)
            self.assertFalse(self.check.passed)
            self.assertEqual(self.check.details, details)

    def test_x_series_new_purity_with_wssd(self):
        """Test results with an //x controller, after 5.1.0, with WSSDs being evacuated."""
        models = ('FA-x10', 'FA-x10r2', 'FA-x20', 'FA-x20r2', 'FA-x50', 'FA-x50r2', 'FA-x70', 'FA-x70r2')
        _shelf = shelf_utils.Shelf('SH10')
        _wssd = drive_utils.WSSD('BAY1', 'SH10', capacity='1 TiB')
        _shelf.add_component(_wssd)
        for model in models:
            self.setUp()
            self.api._device_map = {'drives': {'SH10.BAY1': _wssd}, 'enclosures': {'SH10': _shelf}}
            self.api._to_evac = {'drives': ['SH10.BAY1']}
            self.api.set_values('controller_model', {'Model': [model, model]})
            # //x (tungsten) is not compatible until 5.1.0, if we are evacuating WSSDs.
            self.api.set_values('purity_version', '5.1.0')
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)

    def test_mixed(self):
        """Test results with mixed controller types."""
        self.setUp()
        self.api.set_values('controller_model', {'Model': ['FA-x20', 'FA-x50']})
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, ['The controller models are not the same.'])

    def test_mercury(self):
        """Test with a mercury controller."""
        details = ['Controller Hardware is compatible.']
        models = ('FA-X10R2', 'FA-X20R2', 'FA-X50R2', 'FA-X70R2', 'FA-X90R2')
        for model in models:
            self.setUp()
            self.api.set_values('controller_model', {'Model': [model, model]})
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)
            self.assertEqual(self.check.details, details)

    def test_unknown_model(self):
        """Test with a fake/unknown controller hardware model."""
        model = 'FA-fake70'
        details = ['Controller Hardware "{}" is unknown.'.format(model)]
        self.api.set_values('controller_model', {'Model': [model, model]})
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)


class DenyEvictionTunableCheckTestCase(unittest.TestCase):
    """Unit tests for DenyEvictionTunableCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.DenyEvictionTunableCheck()

    def setUp(self):
        """Reset test defaults."""
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_tunable_set(self):
        """Test what happens when the tunable 'PS_DENY_DRIVE_EVICTION' is set to '1'."""
        self.api.set_values('tunables', {'PS_DENY_DRIVE_EVICTION': '1'})
        details = ['PS_DENY_DRIVE_EVICTION is enabled.  Open a JIRA to verify if this can be unset']
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_tunable_not_set(self):
        """Test what happens when the tunable 'PS_DENY_DRIVE_EVICTION' is set to '0'."""
        self.api.set_values('tunables', {'PS_DENY_DRIVE_EVICTION': '0'})
        details = ['PS_DENY_DRIVE_EVICTION is not enabled.']
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_tunable_not_present(self):
        """Test what happens when the tunable 'PS_DENY_DRIVE_EVICTION' is not even listed."""
        self.api.set_values('tunables', {})
        details = ['PS_DENY_DRIVE_EVICTION is not set.']
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_tunable_bad_value(self):
        """Test what happens when the tunable has a bad value."""
        self.api.set_values('tunables', {'PS_DENY_DRIVE_EVICTION': '100'})
        details = ['PS_DENY_DRIVE_EVICTION has a bad value.  Consult Escalations.']
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)


class EarlyEvictTestCase(unittest.TestCase):
    """Unit tests for EarlyEvict."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.EarlyEvict()

    def setUp(self):
        """Reset test conditions."""
        self.check.details = []
        self.check.affected_devices = {'CT0': [], 'CT1': []}
        self.api.data_set = pandas.DataFrame()

    def test_passing_versions(self):
        """Test versions where the issue is fixed."""
        pass_versions = ('4.7.10', '4.7.11', '4.8.8', '4.8.9', '4.9.0', '4.9.1')
        for version in pass_versions:
            self.setUp()
            self.api.set_value('CT0', 'purity_version', version)
            self.api.set_value('CT1', 'purity_version', version)
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)
            self.assertEqual(self.check.details, ['Fixed in the current Purity version.'])

    def test_with_affected_devices_recent_failover(self):
        """Test the logic when we have affected device(s); but we had a recent failover."""
        # Set the array to an affected version of Purity:
        self.api.set_value('CT0', 'purity_version', '4.8.7')
        self.api.set_value('CT1', 'purity_version', '4.8.7')
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
        # Adjust the purity_uptime, so the event was before a failover.
        self.api.set_values('purity_uptime', '0h:1m:0s')
        # Add a device which are currently affected by this issue.
        reporting_devs = [(time_utils.Timestamp('Dec 31 2017 00:19:37'), '10317931612190623639:11794266333290354325'),
                          (time_utils.Timestamp('Dec 31 2017 00:19:37'), '2453046712309599423:12399270212279020088'),
                          (time_utils.Timestamp('Dec 31 2017 00:19:37'), '2770891273053211959:11195247764825511249'),
                          (time_utils.Timestamp('Dec 31 2017 00:19:37'), '15709077631348820853:15516496246155540217')]
        self.api.set_value('CT0', 'devices_without_references', reporting_devs)
        self.api.set_value('CT1', 'devices_without_references', reporting_devs)
        self.check.run_test(self.api)
        details = ['Not fixed in the current Purity version; an upgrade is recommended.',
                   'No devices are currently affected by the issue.']
        self.assertEqual(self.check.details, details)
        self.assertTrue(self.check.passed)

    def test_with_affected_devices_no_failover(self):
        """Test the logic when we have affected device(s); no recent failovers."""
        # Set the array to an affected version of Purity:
        self.api.set_value('CT0', 'purity_version', '4.8.7')
        self.api.set_value('CT1', 'purity_version', '4.8.7')
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
        self.api.set_values('purity_uptime', '244d:0h:34m:28s')
        # Add 4 devices which are currently affected by this issue.
        reporting_devs = [(time_utils.Timestamp('May 21 13:19:37.000'), '13252132058719705219, 14354154357668399567'),
                          (time_utils.Timestamp('May 21 13:19:37.000'), '9639681361185778759, 11527144135871070414'),
                          (time_utils.Timestamp('May 21 13:19:37.000'), '9784061719313512848, 10710445131617092380'),
                          (time_utils.Timestamp('May 21 13:19:37.000'), '9959553916183927681, 17344567619973432974')]
        self.api.set_values('devices_without_references', reporting_devs)
        self.check.run_test(self.api)
        details = ['Not fixed in the current Purity version; an upgrade is recommended.',
                   '4 drives are affected.  A failover is required before proceeding.']
        self.assertEqual(self.check.details, details)
        # This will fail and recommend a failover.
        self.assertFalse(self.check.passed)

    def test_with_affected_devices_few_devices(self):
        """Test the logic when we have affected device(s); no recent failovers; but with 3 or less devices."""
        # Set the array to an affected version of Purity:
        self.api.set_value('CT0', 'purity_version', '4.8.7')
        self.api.set_value('CT1', 'purity_version', '4.8.7')
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
        self.api.set_values('purity_uptime', '244d:0h:34m:28s')
        # Add a single device which are currently affected by this issue.
        reporting_devs = [(time_utils.Timestamp('May 21 13:19:37.000'), '13108390581602832870, 8935764677177590806')]
        self.api.set_value('CT0', 'devices_without_references', reporting_devs)
        self.api.set_value('CT1', 'devices_without_references', reporting_devs)
        self.check.run_test(self.api)
        # This will pass, but recommend checking for recent hardware issues.
        self.assertTrue(self.check.passed)

    def test_without_affected_devices(self):
        """Test the logic when we have no affected device(s)."""
        # Set the array to an affected version of Purity:
        self.api.set_value('CT0', 'purity_version', '4.8.7')
        self.api.set_value('CT1', 'purity_version', '4.8.7')
        # Set reporting 0 lines to empty:
        self.api.set_value('CT0', 'devices_without_references', [])
        self.api.set_value('CT1', 'devices_without_references', [])
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
        self.api.set_values('purity_uptime', '244d:0h:34m:28s')
        # No devices are currently affected by this issue.
        self.check.run_test(self.api)
        details = ['Not fixed in the current Purity version; an upgrade is recommended.',
                   'No devices are currently affected by the issue.']
        self.assertEqual(self.check.details, details)
        self.assertTrue(self.check.passed)


class EvacDevicesExistTestCase(unittest.TestCase):
    """Unit tests for EvacDevicesExist."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.EvacDevicesExist()

    def test_no_devices_to_evac(self):
        """No devices were requested to evacuate."""
        # Reset the check:
        self.check.details = []
        self.api.data_set = pandas.DataFrame()
        self.api._to_evac = {}
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, ['Found no devices to evacuate.'])

    def test_should_exist(self):
        """All of the requested devices should exist in the array."""
        # Reset the check:
        self.check.details = []
        self.api.data_set = pandas.DataFrame()
        self.api._to_evac = {'drives': ['SH0.BAY1', 'SH0.BAY2']}
        self.api.missing_devices = []
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, ['All devices were found.'])

    def test_should_not_exist(self):
        """All of the requested devices should not exist in the array."""
        # Reset the check:
        self.check.details = []
        self.api.data_set = pandas.DataFrame()
        self.api._to_evac = {'drives': ['SH10.BAY1']}
        self.api.missing_devices = ['SH10.BAY1']
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, ['Devices(s) not found: SH10.BAY1.  '])

    def test_some_exist(self):
        """Some of the requested devices should exist in the array."""
        # Reset the check:
        self.check.details = []
        self.api.data_set = pandas.DataFrame()
        self.api._to_evac = {'drives': ['SH10.BAY1', 'SH0.BAY1']}
        self.api.missing_devices = ['SH10.BAY1']
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, ['Devices(s) not found: SH10.BAY1.  '])


class EvacStallCheckTestCase(unittest.TestCase):
    """Unit tests for EvacStallCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.EvacStallCheck()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.8.9', '4.9.5', '4.10.1')
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        failing_versions = ('4.8.8', '4.9.4', '4.7.1')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.8.9', '4.9.5', '4.10.1', '5.0', '5.1')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)


class LatencyDuringRebuildCheckTestCase(unittest.TestCase):
    """Unit tests for LatencyDuringRebuildCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.LatencyDuringRebuildCheck()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.8.11', '4.9.6', '4.10.5', '5.0.0')
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        failing_versions = ('4.8.10', '4.9.5', '4.10.4', '4.7.5')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.8.11', '4.9.6', '4.10.5', '5.0.0', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)


class LongSecureEraseTestCase(unittest.TestCase):
    """Unit tests for LongSecureErase."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.LongSecureErase()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.7.10', '4.8.8', '4.9.0')
        self.api.data_set = pandas.DataFrame()
        self.check.details = []
        self.api._device_map = {}

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.7.10', '4.8.8', '4.9.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)

    def test_with_affected_drives(self):
        """We are not on a fixed Purity version and we have impacted Samsung drive(s); should fail."""
        details = ['Affected Drives: SH10.BAY1']
        # Set to an affected version:
        self.api.set_values('purity_version', '4.7.9')
        # There should be 1+ drives in the apartment whose name starts with 'SAMSUNG MZ7LM'.
        _samsung = drive_utils.SSD('BAY1', 'SH10', model='SAMSUNG MZ7LM')
        self.api._device_map = {'drives': {'SH10.BAY1': _samsung}}
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_without_affected_drives(self):
        """We are not on a fixed Purity version but we don't have any impacted Samsung drive(s); should pass."""
        details = ['There are no drives affected by PURE-73789.']
        # Set to an affected version:
        self.api.set_values('purity_version', '4.8.7')
        _ssd = drive_utils.SSD('BAY1', 'SH10', model='TOSHIBA SSD123')
        self.api._device_map = {'drives': {'SH10.BAY1': _ssd}}
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)


class KCrumbWithXTestCase(unittest.TestCase):
    """Unit tests for KCrumbWithX."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.KCrumbWithX()

    def setUp(self):
        """Reset test defaults."""
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_unaffected_purity_versions(self):
        """Test results with various versions of Purity."""
        details = ['Not on an affected Purity version.']
        passing_versions = ('4.9.10', '4.8.8', '4.7.5')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        details = ['Fixed in the current Purity version.']
        passing_versions = ('4.10.9', '5.0.0', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)

    def test_without_x(self):
        """Test Purity version affected by the issue, not on an //X controller; should pass."""
        details = ['Both controllers are compatible with evacuation.']
        affected_versions = ('4.10.6', '4.10.7', '4.10.8')
        for version in affected_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.api.set_values('controller_model', {'Model': ['FA-m70r2', 'FA-m70r2'], 'Name': ['CT0', 'CT1']})
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)
            self.assertEqual(self.check.details, details)

    def test_with_x(self):
        """Test Purity version affected by the issue, on an //X controller; should fail."""
        details = ['Evacuations on "//X" controllers are not supported before Purity 4.10.9.']
        affected_versions = ('4.10.6', '4.10.7', '4.10.8')
        for version in affected_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.api.set_values('controller_model', {'Model': ['FA-x70', 'FA-x70'], 'Name': ['CT0', 'CT1']})
            self.check.run_test(self.api)
            self.assertFalse(self.check.passed)
            self.assertEqual(self.check.details, details)


class MishomedDrivesTestCase(unittest.TestCase):
    """Unit tests for MishomedDrives."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.MishomedDrives()

    def setUp(self):
        """Reset test defaults."""
        self.api.data_set = pandas.DataFrame()
        self.check.details = []
        self.api._device_map = {'write_groups': {}}

    def test_with_mishomed_drives(self):
        """Test write groups which contain mishomed drives."""
        dev_id = '(11951019079781516624, 12986023337942797145)'
        details = ['Shelves with mishomed drives: SH0, SH1']
        _ssd1 = drive_utils.SSD('BAY0', 'SH0')
        _ssd2 = drive_utils.SSD('BAY1', 'SH1')
        _wgroup = apartment_utils.WriteGroup(dev_id)
        _wgroup.add_component(_ssd1)
        _wgroup.add_component(_ssd2)
        self.api._device_map['write_groups'][dev_id] = _wgroup
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_without_mishomed_drives(self):
        """Test write groups which don't have any mishomed drives."""
        dev_id = '(11951019079781516624, 12986023337942797145)'
        details = ['No shelves with mishomed drives found.']
        _ssd1 = drive_utils.SSD('BAY0', 'SH0')
        _ssd2 = drive_utils.SSD('BAY1', 'SH0')
        _wgroup = apartment_utils.WriteGroup(dev_id)
        _wgroup.add_component(_ssd1)
        _wgroup.add_component(_ssd2)
        self.api._device_map['write_groups'][dev_id] = _wgroup
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)


class ParallelGCFunnelsTestCase(unittest.TestCase):
    """Unit tests for ParallelGCFunnels."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.ParallelGCFunnels()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.8.11', '4.9.6', '4.10.4')
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        failing_versions = ('4.8.10', '4.9.5', '4.10.3')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.8.11', '4.9.6', '4.10.4', '5.0.0', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)


class PurityVersionCompatibilityTestCase(unittest.TestCase):
    """Unit tests for PurityVersionCompatibility."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.PurityVersionCompatibility()

    def setUp(self):
        """Reset test conditions."""
        self.check.details = []
        self.api._devices_to_evac = {}
        self.api._to_evac = {}
        self.api._device_map = {}
        self.api.data_set = pandas.DataFrame()

    def test_datapack_failing_purity_version(self):
        """Test evacuating a DataPack before 4.10.6."""
        details = ['Incompatible devices: SH0.BAY1.']
        # Add a DataPack to be evacuated:
        _pack_name = 'SH0.BAY1'
        _wgroups = ['(11951019079781516624, 12986023337942797145)']
        _pack = apartment_utils.DataPack(_pack_name, write_group_names=_wgroups)
        self.api._device_map = {'data_packs': {_pack_name: _pack}}
        self.api._to_evac = {'data_packs': [_pack_name]}
        self.api._devices_to_evac = {_pack_name: _pack}
        # Set a passing version:
        self.api.set_values('purity_version', '4.10.5')
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_datapack_incompatible_shelf(self):
        """Test evacuating a DataPack after 4.10.6 with an incompatible shelf/chassis."""
        details = ['Incompatible devices: Pack (SH0.BAY1).']
        _ssd = drive_utils.SSD('BAY1', 'SH0', capacity='1 TiB')
        # Create an incompatible shelf:
        _shelf = shelf_utils.Shelf('SH0', handle='EB-2425-E6EBD')
        _shelf.add_component(_ssd)
        # Create a WriteGroup to add to the DataPack:
        _wgroup = apartment_utils.WriteGroup('(11951019079781516624, 12986023337942797145)')
        _wgroup.add_component(_ssd)
        # Add a DataPack to be evacuated:
        _pack_name = 'SH0.BAY1'
        _pack = apartment_utils.DataPack(_pack_name, write_group_names=['(11951019079781516624, 12986023337942797145)'])
        _pack.add_component(_wgroup)
        self.api._device_map = {'data_packs': {_pack_name: _pack},
                                'drives': {'SH0.BAY1': _ssd},
                                'enclosures': {'SH0': _shelf}}
        self.api._to_evac = {'data_packs': [_pack_name]}
        # If before 4.10.6 then it is not compatible.
        self.api.set_values('purity_version', '4.10.7')
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_datapack_passing_purity_version(self):
        """Test evacuating a DataPack on 4.10.6 with a compatible shelf/chassis."""
        details = ['No incompatible devices found.']
        _ssd = drive_utils.SSD('BAY1', 'SH0', capacity='1 TiB')
        # Create a WriteGroup to add to the DataPack:
        _wgroup = apartment_utils.WriteGroup('(11951019079781516624, 12986023337942797145)')
        _wgroup.add_component(_ssd)
        # Add a DataPack to be evacuated:
        _pack_name = 'SH0.BAY1'
        _pack = apartment_utils.DataPack(_pack_name, write_group_names=['(11951019079781516624, 12986023337942797145)'])
        _pack.add_component(_wgroup)
        self.api._to_evac = {'data_packs': [_pack_name]}
        self.api.set_values('purity_version', '4.10.6')

        # Create a compatible shelf/chassis:
        handles = ('EB-2425-E12EBD', 'M_SERIES', 'TUNG', 'MERCURYA_PCHFL174100AA')
        for handle in handles:
            self.check.details = []
            _shelf = shelf_utils.Shelf('SH0', handle=handle)
            _shelf.add_component(_ssd)
            self.api._device_map = {'data_packs': {_pack_name: _pack},
                                    'drives': {'SH0.BAY1': _ssd},
                                    'enclosures': {'SH0': _shelf}}
            # Set a passing version:
            self.check.run_test(self.api)
            msg = 'Handle "{}" should have been compatible.'.format(handle)
            self.assertTrue(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)

    def test_drive_available(self):
        """Test evacuating drives when available."""
        details = ['No incompatible devices found.']
        # Add a healthy drive:
        _drive = drive_utils.SSD('BAY1', 'SH0', status='healthy')
        self.api._device_map = {'drives': {'SH0.BAY1': _drive}}
        self.api._to_evac = {'drives': ['SH0.BAY1']}
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_drive_unavailable(self):
        """Test evacuating drives when it is not available."""
        details = ['Incompatible devices: SH0.BAY1.']
        # Add a healthy drive:
        _drive = drive_utils.SSD('BAY1', 'SH0', status='empty')
        self.api._device_map = {'drives': {'SH0.BAY1': _drive}}
        self.api._to_evac = {'drives': ['SH0.BAY1']}
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_shelf_failing_purity_version(self):
        """Test evacuating a Shelf in various Purity versions."""
        details = ['Incompatible devices: CH1, SH0.']
        # Add a DataPack to be evacuated:
        _chassis_name = 'CH1'
        _chassis = shelf_utils.Chassis(_chassis_name)
        _shelf_name = 'SH0'
        _shelf = shelf_utils.Shelf(_shelf_name)
        self.api._device_map = {'enclosures': {_chassis_name: _chassis, _shelf_name: _shelf}}
        self.api._to_evac = {'enclosures': [_chassis_name, _shelf_name]}
        # If before 4.10.6 then it is not compatible.
        self.api.set_values('purity_version', '4.7.2')
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_shelf_passing_purity_version(self):
        """Test evacuating a Shelf in various Purity versions."""
        details = ['No incompatible devices found.']
        # Add a DataPack to be evacuated:
        _chassis_name = 'CH1'
        _chassis = shelf_utils.Chassis(_chassis_name)
        _shelf_name = 'SH0'
        _shelf = shelf_utils.Shelf(_shelf_name)
        self.api._device_map = {'enclosures': {_chassis_name: _chassis, _shelf_name: _shelf}}
        self.api._to_evac = {'enclosures': [_chassis_name, _shelf_name]}
        # Set a passing version:
        self.api.set_values('purity_version', '4.7.3')
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_unknown_device(self):
        """Test evacuating an unknown device type."""
        details = ['Incompatible devices: CH0.BAY21.']
        _nvram_name = 'CH0.BAY21'
        _nvram = drive_utils.NVRAM('BAY21', 'CH0')
        self.api._device_map = {'drives': {_nvram_name: _nvram}}
        self.api._to_evac = {'drives': [_nvram_name]}
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)


@unittest.skip('PT-1438')
class SASCablingTestCase(unittest.TestCase):
    """Unit tests for SASCabling."""


class SegmentGuardFailoverCheckTestCase(unittest.TestCase):
    """Unit tests for SegmentGuardFailoverCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.SegmentGuardFailoverCheck()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.8.9', '4.9.5', '4.10.1')
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        failing_versions = ('4.8.8', '4.9.4', '4.7.10')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.8.9', '4.9.5', '4.10.1', '5.0.0', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)


class ShardRebuildRiskCheckTestCase(unittest.TestCase):
    """Unit tests for ShardRebuildRiskCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.ShardRebuildRiskCheck()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('5.1.0', )
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        failing_versions = ('5.0.0', '5.0.1', '5.0.7')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.8.12', '4.9.e', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)


class SlowSANStartupCheckTestCase(unittest.TestCase):
    """Unit tests for SlowSANStartupCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.SlowSANStartupCheck()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.8.9', '4.9.5', '4.10.1')
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        failing_versions = ('4.8.8', '4.9.4', '4.10.0')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.8.9', '4.9.5', '4.10.1', '5.0.0', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)


class SystemSpaceInflationCheckTestCase(unittest.TestCase):
    """Unit tests for SystemSpaceInflationCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.SystemSpaceInflationCheck()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.8.12', '4.9.e', '4.10.6')
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        failing_versions = ('4.8.11', '4.9.d', '4.10.5')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        passing_versions = ('4.8.12', '4.9.e', '4.10.6')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)


class WSSDBadCapacityCheck(unittest.TestCase):
    """Unit tests for WSSDBadCapacityCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.WSSDBadCapacityCheck()

    def setUp(self):
        """Reset test conditions."""
        self.check.details = []
        self.api._devices_to_evac = {}
        self.api._to_evac = {}
        self.api._device_map = {}
        self.api.data_set = pandas.DataFrame()
        # Add data needed to build a drive map:
        self.api.set_from_file('dev_info', test_utils.get_files_of_type('Uncategorized/devinfo.json')[0])
        self.api.set_from_file('puredb_list_drives',
                               test_utils.get_files_of_type('Uncategorized/puredb_list_drives.json')[0])

    def test_passing_versions(self):
        """Test versions where the issue is fixed."""
        pass_versions = ('4.10.11', '5.1.0', '5.0.7')
        for version in pass_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            self.assertTrue(self.check.passed)
            self.assertEqual(self.check.details, ['Fixed in the current Purity version.'])

    def test_no_evacuations(self):
        """With no devices being evacuated, this should pass."""
        details = ['No devices are being evacuated.']
        self.api.set_values('purity_version', '4.10.10')
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_without_wssd(self):
        """With no WSSD devices, this should pass."""
        details = ['No WSSD devices found in the array.']
        self.api.set_values('purity_version', '4.10.10')
        self.api._to_evac = {'drives': ['SH0.BAY1']}
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_with_wssd_evac_non_wssd(self):
        """This should fail if a WSSD is present and we are evacuating a non-WSSD component."""
        details = ['Capacity calculations are wrong due to PURE-116769, this can cause evac to stall.',
                   'Consult Escalations to tune PS_EVAC_DATA_GC_BATCH_SZ.']
        self.api.set_values('purity_version', '4.10.10')

        # Add a fake WSSDs and shelf to put it into:
        _shelf = shelf_utils.Shelf('SH10')
        _wssd = drive_utils.WSSD('BAY1', 'SH10', capacity='1 TiB')
        _ssd = drive_utils.SSD('BAY2', 'SH10', capacity='1 TiB')
        _shelf.add_component(_wssd)
        _shelf.add_component(_ssd)
        self.api._device_map = {'drives': {'SH10.BAY1': _wssd, 'SH10.BAY2': _ssd}, 'enclosures': {'SH10': _shelf}}

        # Evacuate another drive (non-WSSD):
        self.api._to_evac = {'drives': ['SH10.BAY2']}

        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_with_wssd_evac_wssd(self):
        """If we are evacuating a WSSD, then the AU calculation issue does not apply."""
        details = ['Evacuating WSSD(s), therefore, not affected by the AU calculation bug.']
        self.api.set_values('purity_version', '4.10.10')

        # Add a fake WSSDs and shelf to put it into:
        _wssd = drive_utils.WSSD('BAY1', 'SH10', capacity='1 TiB')
        _shelf = shelf_utils.Shelf('SH10')
        _shelf.add_component(_wssd)
        self.api._device_map = {'drives': {'SH10.BAY1': _wssd}, 'enclosures': {'SH10': _shelf}}
        # Now evacuate a WSSD:
        self.api._to_evac = {'drives': ['SH10.BAY1']}

        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)


class WSSDMismatchedSegioCheckTestCase(unittest.TestCase):
    """Unit tests for WSSDMismatchedSegioCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.WSSDMismatchedSegioCheck()

    def setUp(self):
        """Reset test conditions."""
        # Fixed in versions:
        #  ('4.10.9', '5.0.5')
        self.check.details = []
        self.api._devices_to_evac = {}
        self.api._to_evac = {}
        self.api._device_map = {}
        self.api.data_set = pandas.DataFrame()

    def test_non_wssd_evac(self):
        """Test evacuating non-WSSD devices."""
        details = ['No WSSD devices are being evacuated.']
        # Add a non-WSSD:
        _ssd_name = 'SH10.BAY1'
        _ssd = drive_utils.SSD('BAY1', 'SH10')
        self.api._to_evac = {'drives': [_ssd_name]}
        self.api._device_map = {'drives': {_ssd_name: _ssd}}
        self.api._devices_to_evac = {_ssd_name: _ssd}
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_wssd_evac_passing_purity_version(self):
        """Test evacuating a WSSD in a fixed version."""
        details = ['Fixed in the current Purity version.']
        passing_versions = ('4.10.9', '5.0.5', '5.1.0')
        # Add a WSSD:
        _wssd_name = 'SH10.BAY1'
        _wssd = drive_utils.WSSD('BAY1', 'SH10')
        self.api._to_evac = {'drives': [_wssd_name]}
        self.api._device_map = {'drives': {_wssd_name: _wssd}}
        self.api._devices_to_evac = {_wssd_name: _wssd}
        for version in passing_versions:
            self.check.details = []
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)

    def test_wssd_evac_failing_purity_version(self):
        """Test evacuating a WSSD in an affected version."""
        details = ['The array is at risk of K-crumbs.  Consult escalations.']
        # Add a WSSD:
        _wssd_name = 'SH10.BAY1'
        _wssd = drive_utils.WSSD('BAY1', 'SH10')
        self.api._to_evac = {'drives': [_wssd_name]}
        self.api._device_map = {'drives': {_wssd_name: _wssd}}
        self.api._devices_to_evac = {_wssd_name: _wssd}
        self.api.set_values('purity_version', '4.10.8')
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)


class UnhealthyDrivesCheckTestCase(unittest.TestCase):
    """Unit tests for UnhealthyDrivesCheck."""
    api = test_utils.mock_api(evac_health_checks.EvacHealthChecksAPI)
    check = evac_health_checks.UnhealthyDrivesCheck()

    def test_with_unhealthy_drives(self):
        """We should find the unhealthy ones and report them."""
        # Add an unhealthy WSSD:
        _wssd_name = 'SH10.BAY1'
        _wssd = drive_utils.WSSD('BAY1', 'SH10', status='unhealthy')
        self.api._to_evac = {'drives': [_wssd_name]}
        self.api._device_map = {'drives': {_wssd_name: _wssd}}
        self.api._devices_to_evac = {_wssd_name: _wssd}
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)

    def test_without_unhealthy_drives(self):
        """Test with no unhealthy drives."""
        # Add a healthy WSSD:
        _wssd_name = 'SH10.BAY1'
        _wssd = drive_utils.WSSD('BAY1', 'SH10', status='healthy')
        self.api._to_evac = {'drives': [_wssd_name]}
        self.api._device_map = {'drives': {_wssd_name: _wssd}}
        self.api._devices_to_evac = {_wssd_name: _wssd}
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)


# Helper function tests:
class EstimateCapacityTestCase(unittest.TestCase):
    """Unit tests for estimate_capacity."""

    def test_expected_behavior(self):
        """Test using expected values."""
        device_capacity = 53687091200
        ssd_capacity = 54975581388800
        usable_capacity = 34634616274944
        expected = (34600793407488, 54921894297600)
        result = evac_health_checks.estimate_capacity(device_capacity, usable_capacity, ssd_capacity)
        self.assertEqual(expected, result)


class EstimateSystemSpaceTestCase(unittest.TestCase):
    """Unit tests for estimate_system_space."""
    # Input: unreported_space, ssd_capacity
    # Output: estimated_system
    ssd_capacity = 54975581388800

    def test_no_system_space(self):
        """A test case where there should be no System space."""
        unreported_space = 15261221393530
        expected = 0
        result = evac_health_checks.estimate_system_space(unreported_space, self.ssd_capacity)
        self.assertEqual(expected, result)

    def test_high_system_space(self):
        """A test case where there should be a lot of System space."""
        unreported_space = 47687416867546
        expected = 32426195474015
        result = evac_health_checks.estimate_system_space(unreported_space, self.ssd_capacity)
        self.assertEqual(expected, result)

    def test_low_system_space(self):
        """A test case where there should be low System space."""
        unreported_space = 28458277911697
        expected = 13197056518166
        result = evac_health_checks.estimate_system_space(unreported_space, self.ssd_capacity)
        self.assertEqual(expected, result)
