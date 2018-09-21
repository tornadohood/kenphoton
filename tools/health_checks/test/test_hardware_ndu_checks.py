"""Unit tests for hardware_ndu_checks."""

import unittest

import pandas

from photon.lib import test_utils
from photon.tools.health_checks import hardware_ndu_checks


class MinimumNDUVersionCheckTestCase(unittest.TestCase):
    """Unit tests for MinimumNDUVersionCheck."""
    api = test_utils.mock_api(hardware_ndu_checks.HardwareNDUAPI)
    check = hardware_ndu_checks.MinimumNDUVersionCheck()

    def setUp(self):
        """Reset test defaults."""
        # Fixed in versions:
        # ('4.5.5', )
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_failing_purity_versions(self):
        """Test results with various versions of Purity."""
        details = ['Hardware NDU is not supported until Purity 4.5.5 or later.']
        failing_versions = ('4.5.4', )
        for version in failing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on Purity version: "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)

    def test_passing_purity_versions(self):
        """Test results with various versions of Purity."""
        details = ['Hardware NDU is supported.']
        passing_versions = ('4.5.5', '4.6.0', '4.7.0', '4.8.0', '4.10.0', '5.0.0', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on Purity version: "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)


class MixedControllerTypesCheckTestCase(unittest.TestCase):
    """Unit tests for MixedControllerTypesCheck."""
    api = test_utils.mock_api(hardware_ndu_checks.HardwareNDUAPI)
    check = hardware_ndu_checks.MixedControllerTypesCheck()

    def setUp(self):
        """Reset test defaults."""
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_with_mercury_shelves(self):
        """Test results when there are mercury shelves."""
        details = ['Controller models are FA-X70R2 and FA-X70R2.']
        self.api.set_values('controller_model', {'Model': ['FA-X70R2', 'FA-X70R2', 'DFSC1', 'DFSC1']})
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_mixed_controller_models(self):
        """Test results when the controller models are different."""
        details = ['Controller models are not the same!']
        self.api.set_values('controller_model', {'Model': ['FA-X70R2', 'FA-m10']})
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_same_controller_models(self):
        """Test results when the controller models are different."""
        details = ['Controller models are FA-m10 and FA-m10.']
        self.api.set_values('controller_model', {'Model': ['FA-m10', 'FA-m10']})
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)


class NewHardwareCheckTestCase(unittest.TestCase):
    """Unit tests for NewHardwareCheck."""
    api = test_utils.mock_api(hardware_ndu_checks.HardwareNDUAPI)
    check = hardware_ndu_checks.NewHardwareCheck()

    def setUp(self):
        """Reset test defaults."""
        self.api.data_set = pandas.DataFrame()
        self.check.details = []
        self.api.new_hardware = None

    def test_no_new_hardware(self):
        """Test result when we have no 'new_hardware' attribute specified."""
        details = ['No target hardware specified.']
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_no_check_found(self):
        """Test result when no check is found for the new hardware."""
        self.api.new_hardware = 'FA-FakeHardware'
        details = ['Failed to locate a check for the new hardware "{}".'.format(self.api.new_hardware)]
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)


class WFSCompatibilityCheckTestCase(unittest.TestCase):
    """Unit tests for WFSCompatibilityCheck."""
    api = test_utils.mock_api(hardware_ndu_checks.HardwareNDUAPI)
    check = hardware_ndu_checks.WFSCompatibilityCheck()

    def setUp(self):
        """Reset test defaults."""
        self.api.data_set = pandas.DataFrame()
        self.check.details = []

    def test_wfs_not_enabled(self):
        """Test when WFS related tunables are not enabled."""
        details = ['WFS is not enabled.']
        self.api.set_values('tunables', {})
        self.check.run_test(self.api)
        self.assertTrue(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_with_mercury(self):
        """Test results when we have Mercury controllers."""
        details = ['The Virtual File Server Role needs to be moved off the controller being replaced.']
        self.api.set_values('tunables', {'PURITY_APPS_ENABLED': '1', 'PS_APPS_AUX_INTERFACE': 'ISCSI_3'})
        self.api.set_values('controller_model', {'Model': ['FA-X70R2', 'FA-X70R2']})
        self.check.run_test(self.api)
        self.assertFalse(self.check.passed)
        self.assertEqual(self.check.details, details)

    def test_failing_versions(self):
        """Test results when we do not have Mercury controllers and on a failing version of Purity."""
        details = ['Hardware NDU is not supported with WFS until Purity 4.10.7+.']
        failing_versions = ('4.10.6', '4.9.0', '4.8.0')
        for version in failing_versions:
            self.setUp()
            self.api.set_values('tunables', {'PURITY_APPS_ENABLED': '1', 'PS_APPS_AUX_INTERFACE': 'ISCSI_3'})
            self.api.set_values('controller_model', {'Model': ['FA-x70r2', 'FA-x70r2']})
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have failed on version "{}".'.format(version)
            self.assertFalse(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)

    def test_passing_versions(self):
        """Test results when we do not have Mercury controllers and on a passing version of Purity."""
        details = ['Hardware NDU is supported.']
        passing_versions = ('4.10.7', '5.0.0', '5.1.0')
        for version in passing_versions:
            self.setUp()
            self.api.set_values('tunables', {'PURITY_APPS_ENABLED': '1', 'PS_APPS_AUX_INTERFACE': 'ISCSI_3'})
            self.api.set_values('controller_model', {'Model': ['FA-x70r2', 'FA-x70r2']})
            self.api.set_values('purity_version', version)
            self.check.run_test(self.api)
            msg = 'Should have passed on version "{}".'.format(version)
            self.assertTrue(self.check.passed, msg=msg)
            self.assertEqual(self.check.details, details)
