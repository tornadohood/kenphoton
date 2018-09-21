"""Unit tests for lib/array_utils."""

import os
import unittest

from photon.lib import array_utils
from photon.lib import env_utils

PATH = os.path.dirname(__file__)
MISSING_LOGS = not os.access('/logs/purestorage.com', os.R_OK)


class TestConvertFQDNToLogdir(unittest.TestCase):
    """Unit tests for convert_fqdn_to_logdir."""

    # TODO PT-1151: Add env util to check if on fuse and use it instead
    @unittest.skipIf(env_utils.get_distro('/etc/lsb-release') != "Ubuntu", "Not on Fuse")
    @unittest.skipIf(MISSING_LOGS, "Does not run if we don't have /logs mounted.")
    def test_valid_fqdn(self):
        """Test convert_fqdn_to_logdir with a valid fqdn."""
        expected = ('/logs/purestorage.com/slc-coz-ct0', '/logs/purestorage.com/slc-coz-ct1')
        result = array_utils.convert_fqdn_to_logdir('slc-coz.purestorage.com')
        self.assertIn(result, expected)

    def test_invalid_fqdn(self):
        """Test convert_fqdn_to_logdir with an invalid fqdn."""
        with self.assertRaises(ValueError):
            array_utils.convert_fqdn_to_logdir('slc-cozpurestoragecom')


class TestConvertLogdirToFQDN(unittest.TestCase):
    """Unit tests for convert_logdir_to_fqdn."""

    def test_valid_logdir(self):
        """Test convert_logdir_to_fqdn with valid log directories."""
        expected = (
            'slc-coz.purestorage.com',
            'slc-coz.purestorage.com',
            'dr-pure3.paylocity.com',
            'array-name-has-lots-of-dashes.domain.com'
        )
        log_paths = (
            '/logs/purestorage.com/slc-coz-ct0',
            '/logs/purestorage.com/slc-coz-ct1/2018_01_15',
            '/logs/paylocity.com/dr-pure3-ct0/2017_10_27',
            '/logs/domain.com/array-name-has-lots-of-dashes-ct0'
        )
        for index, log_path in enumerate(log_paths):
            result = array_utils.convert_logdir_to_fqdn(log_path)
            msg = 'Failed to convert log directory "{}" to an FQDN.'.format(log_path)
            self.assertEqual(result, expected[index], msg=msg)

    def test_invalid_logdir(self):
        """Test convert_logdir_to_fqdn with invalid log directories."""
        bad_log_paths = (
            '/logs/domain-only.com',
            '/logs/domain.com/nocontroller',
        )
        for bad_dir in bad_log_paths:
            msg = 'Bad log directory "{}" should have raised an error.'.format(bad_dir)
            with self.assertRaises(ValueError, msg=msg):
                array_utils.convert_logdir_to_fqdn(bad_dir)


class TestGetArrayAndDomainFromFqdn(unittest.TestCase):
    """Unit test for get_array_and_domain_from_fqdn."""

    # TODO PT-1151: Add env util to check if on fuse and use it instead
    @unittest.skipIf(env_utils.get_distro('/etc/lsb-release') != "Ubuntu", "Not on Fuse")
    def test_with_valid_fqdn(self):
        """Test get_array_and_domain_from_fqdn with a valid fqdn."""
        expected = 'slc-coz', 'purestorage.com'
        result = array_utils.get_array_and_domain_from_fqdn('slc-coz.purestorage.com')
        self.assertEqual(expected, result)

    def test_with_invalid_fqdn(self):
        """Test get_array_and_domain_from_fqdn with an invalid fqdn."""
        with self.assertRaises(ValueError):
            array_utils.get_array_and_domain_from_fqdn('slc-cozpurestoragecom')


class TestGetPeerPath(unittest.TestCase):
    """Unit tests for get_peer_path."""

    def test_valid_path(self):
        """Test get_peer_path using a valid log path."""
        log_paths = (
            '/logs/purestorage.com/slc-coz-ct1/2018_01_15',
            '/logs/paylocity.com/dr-pure3-ct0/2017_10_27',
            '/logs/domain.com/array-ct01der-ct1'
        )
        expected = (
            '/logs/purestorage.com/slc-coz-ct0/2018_01_15',
            '/logs/paylocity.com/dr-pure3-ct1/2017_10_27',
            '/logs/domain.com/array-ct01der-ct0',
        )
        for index, log_path in enumerate(log_paths):
            result = array_utils.get_peer_path(log_path)
            msg = 'Failed to get peer path for log directory "{}", result: {}.'.format(log_path, result)
            self.assertEqual(result, expected[index], msg=msg)

    def test_invalid_path(self):
        """Test get_peer_path using an invalid log path."""
        bad_log_paths = (
            '/logs/domain-only.com',
            '/logs/domain.com/nocontroller',
        )
        for bad_dir in bad_log_paths:
            msg = 'Bad log directory "{}" should have raised an error.'.format(bad_dir)
            with self.assertRaises(ValueError, msg=msg):
                array_utils.get_peer_path(bad_dir)


class TestArrayIdent(unittest.TestCase):
    """Unit test for ArrayIdent object."""

    def test_valid_fqdn_instantiation(self):
        """Test instantiation with a valid fqdn."""
        fqdn = 'slc-coz.purestorage.com'
        ident = array_utils.ArrayIdent(fqdn=fqdn)
        self.assertEqual(ident.fqdn, fqdn)
        self.assertEqual(ident.log_path, '/logs/purestorage.com/slc-coz-ct0')

    def test_valid_logs_instantiation(self):
        """Test instantiation with a valid log directory."""
        log_path = '/logs/purestorage.com/slc-coz-ct0/2018_01_01'
        ident = array_utils.ArrayIdent(log_path=log_path)
        self.assertEqual(log_path, ident.log_path)

    def test_invalid_fqdn_instantiation(self):
        """Test instantiation with invalid fqdns."""
        bad_fqdn = 'slc-cozpurestoragecom'
        with self.assertRaises(ValueError):
            array_utils.ArrayIdent(fqdn=bad_fqdn)

    def test_ct_paths(self):
        """Validate that the CT paths are generated properly."""
        result = array_utils.ArrayIdent(log_path='/logs/purestorage.com/slc-coz-ct0/2018_01_01').ct_paths
        expected = {
            'CT0': '/logs/purestorage.com/slc-coz-ct0/2018_01_01',
            'CT1': '/logs/purestorage.com/slc-coz-ct1/2018_01_01',
        }
        self.assertEqual(result, expected)

    def test_ct_paths_from_fqdn(self):
        """Validate that the CT paths are generated properly from an FQDN."""
        result = array_utils.ArrayIdent(fqdn='slc-coz.purestorage.com').ct_paths
        expected = {
            'CT0': '/logs/purestorage.com/slc-coz-ct0',
            'CT1': '/logs/purestorage.com/slc-coz-ct1',
        }
        self.assertEqual(result, expected)

    def test_with_files(self):
        """Test using files only."""
        result = array_utils.ArrayIdent(files=['my_file', 'another_file.gz', 'something.json.gz']).files
        expected = {u'another_file': [u'another_file.gz'],
                    u'my_file': [u'my_file'],
                    u'something.json': [u'something.json.gz']}
        self.assertEqual(result, expected)

    # TODO: PT-1147 - Add Support for Array ID
    # def test_valid_aid_instantiation(self):
    #     ident = array_utils.ArrayIdent('1093489-260039737-2123539898130037785')
    #     self.assertEqual('aid', ident.ident_type)
