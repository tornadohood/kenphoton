"""Unit tests for hardware."""

from __future__ import unicode_literals

import os
import unittest

from six import iteritems
from six import string_types

from photon.backend.pure.logs import hardware

EXPECTED_TIMESTAMPS = 1
FORMS = (
    'bmc_info',
    'controller_info',
    'controller_mode',
    'controller_model',
    'controller_status',
    'controller_version',
    'cpu_interrupts',
    'cpu_throttle',
    'ddump',
    'df',
    'dmi',
    'domain_name',
    'drive_smart',
    'expander_counters',
    'expander_show_logs',
    'expander_show_trace',
    'finddrive_all',
    'fru',
    'hardware_check',
    'ipmi_sensors',
    # 'ls_pci',
    'ls_scsi',
    'ls_usb',
    'mce',
    'meminfo',
    'pci_train',
    'purechassis',
    'purehw_list',
    'purity_version',
    'raw_hw_logs',
    'sas_view',
    'sel',
    'uptime',
)
NO_FORM_EXPECTED = (
    'controller_info',
    'controller_mode',
    'controller_model',
    'controller_status',
    'controller_version',
    'domain_name',
    'purity_version',
    'sel_critical_events',
    'uptime',
)
# These are okay to have no results sometimes
PATH = os.path.dirname(__file__)


class HardwareFormDataTestCase(unittest.TestCase):
    """Unit tests for HardwareFormData."""

    def test_build(self):
        """Ensure that this builds the forms correctly."""
        data = hardware.HardwareFormData()
        for form in FORMS:
            if form in NO_FORM_EXPECTED:
                continue
            msg = 'Form "{}" is not defined in HardwareFormData.'.format(form)
            self.assertTrue(hasattr(data, form), msg=msg)
        # Not much else to test here afaik.


class FDiagnosticsParserTestCase(unittest.TestCase):
    """Unit tests for HardwareParser."""
    log_file = os.path.join(PATH, 'test_files/hardware.log-test.gz')
    parser = hardware.HardwareParser(log_file)

    def test_fields(self):
        """Ensure that Fields are well formed."""
        for datum, log_data in iteritems(self.parser.fields):
            if datum in NO_FORM_EXPECTED:
                continue
            # Assert that each fields has a defined form.
            msg = 'Field "{}" has no form.'.format(datum)
            self.assertIn(datum, log_data.forms, msg)
            # Assert that each fields has a parser
            msg = 'Datum "{}" has no parser.'.format(datum)
            self.assertTrue(hasattr(self.parser, 'get_{}'.format(datum)), msg=msg)

    def test_parsers(self):
        """Ensure that each public facing parser is defined in fields."""
        skip = ['get_form_lines', 'get_field', 'get_fields']
        getters = [atr for atr in dir(self.parser) if atr.startswith('get_') and atr not in skip]
        for getter in getters:
            # Assert that each getter has an entry in fields
            msg = 'Getter "{}" is not defined in fields.'.format(getter)
            self.assertIn(getter.split('_', 1)[1], self.parser.fields, msg=msg)


class KnownDataTestCases(unittest.TestCase):
    """Unit tests for all fields in the HardwareParser."""
    log_file = os.path.join(PATH, 'test_files/hardware.log-test.gz')
    parser = hardware.HardwareParser(log_file)

    def test_results(self):
        """Fetch each field from the hardware.log-test.gz log file. and validate results."""
        for field in self.parser.fields:
            try:
                values = self.parser.get_field(field)
            except KeyError:
                msg = 'Field "{}" is not defined in the hardware log parser.'.format(field)
                raise KeyError(msg)
            # Ensure that each result has a value and not None
            self.assertIsNotNone(values)

    def test_individual_parsers(self):
        """Test the output of each parser."""
        parsers = ['get_' + form for form in FORMS]
        expected_results = {
            'get_bmc_info': ['Additional Device Support', 'Aux Firmware Rev Info', 'Device Available', 'Device ID',
                             'Device Revision', 'Firmware Revision', 'IPMI Version', 'Manufacturer ID',
                             'Manufacturer Name', 'Product ID', 'Product Name', 'Provides Device SDRs'],
            'get_controller_info': ['CT0', 'CT1'],
            'get_controller_mode': ['CT0', 'CT1'],
            'get_controller_model': ['CT0', 'CT1'],
            'get_controller_status': ['CT0', 'CT1'],
            'get_controller_version': ['CT0', 'CT1'],
            'get_cpu_interrupts': 893,
            'get_cpu_throttle': 71,
            'get_ddump': 70,
            'get_df': 66,
            'get_dmi': '# dmidecode 2.12\n',
            'get_drive_smart': 67,
            'get_domain_name': 'paylocity.com',
            'get_expander_counters': 47,
            'get_expander_show_logs': 215,
            'get_expander_show_trace': 393,
            'get_finddrive_all': 132,
            'get_fru': 51,
            'get_hardware_check': 33,
            'get_ipmi_sensors': 130,
            # The test hardware log has no lspci file(s).
            # 'get_ls_pci': 0,
            'get_ls_scsi': 74,
            'get_ls_usb': 'lsusb -a::\n',
            'get_mce': 'mce::\n',
            'get_meminfo': 30,
            'get_pci_train': 71,
            'get_purechassis': 135,
            'get_purehw_list': 169,
            'get_purity_version': '4.10.5',
            'get_raw_hw_logs': 71,
            'get_sas_view': 32,
            'get_sel': 30,
            # TODO: PT-2067 - Put critical events in the test log.
            'get_sel_critical_events': None,
            'get_uptime': '117 days, 16:09:49.830000',
        }
        for form_parser in parsers:
            result = getattr(self.parser, form_parser)()
            msg = 'The Form Parser "{}" did not have the expected timestamps.'.format(form_parser)
            self.assertEqual(len(result), EXPECTED_TIMESTAMPS, msg=msg)
            # Just test the first value in the list of results:
            value = sorted(result)[0][1]
            if isinstance(value, dict):
                value = sorted(list(value.keys()))
            elif isinstance(value, list):
                if form_parser.startswith(('get_expander', 'get_hardware_check')):
                    # Just check the length of lines, as this should get a list of raw lines.
                    value = len(value)
                else:
                    value = value[0]
            # Convert any remaining long strings to a length for easier comparison.
            if isinstance(value, string_types) and len(value) > 25:
                value = len(value)
            # The result should be a list of tuples containing (timestamp, value_lines).
            msg = '"{}":\nResult was "{}".\nExpected "{}".'.format(form_parser, value, expected_results[form_parser])
            self.assertEqual(expected_results[form_parser], value, msg=msg)


if __name__ == '__main__':
    unittest.main()
