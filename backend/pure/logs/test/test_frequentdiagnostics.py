"""Unit tests for frequentdiagnostics."""

from __future__ import unicode_literals

import os
import unittest

from six import iteritems

from photon.lib import parser_utils
from photon.backend.pure.logs import frequentdiagnostics as freq
from photon.lib import custom_errors

# The test file contains 123 unique timestamps
EXPECTED_TIMESTAMPS = 123
# These are okay to have no results sometimes
IGNORE_EMPTY = ['iqn', 'wwn']
PATH = os.path.dirname(__file__)
# TODO: Individual unit tests for each parser: PT-1171


class FDiagFormDataTestCase(unittest.TestCase):
    """Unit tests for FDiagFormData."""

    def test_build(self):
        """Ensure that this builds the SimpleTextForm correctly."""
        data = freq.FDiagFormData()
        self.assertIsInstance(data.diagnostics, parser_utils.SimpleTextForm)
        # Not much else to test here afaik.


class FDiagLogDataTestCase(unittest.TestCase):
    """Unit tests for FDiagLogData."""

    def test_build(self):
        """Ensure that this builds with the right forms and text to match."""
        log = freq.FDiagLogData(['diagnostics'])
        expected_text_to_match = '] Diagnostics: {'
        self.assertEqual(log.forms['diagnostics'].text_to_match, expected_text_to_match)
        # Not much else to test here afaik.


class FDiagnosticsParserTestCase(unittest.TestCase):
    """Unit tests for FDiagnosticsParser."""

    log_file = os.path.join(PATH, 'test_files/frequentdiagnostics-test.gz')
    parser = freq.FDiagnosticsParser(log_file)

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
            self.assertIn('diagnostics', log_data.forms, msg)
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
    """Unit tests for all fields in the FDiagnosticsParser."""

    log_file = os.path.join(PATH, 'test_files/frequentdiagnostics-test.gz')
    parser = freq.FDiagnosticsParser(log_file)

    def test_results(self):
        """Fetch each field from the frequentdiagnostics-test.gz log file. and validate results."""
        for field in self.parser.fields:
            try:
                values = self.parser.get_field(field)
            except custom_errors.LogParserError:
                msg = 'Field "{}" is unknown in frequentdiagnostics.'.format(field)
                raise KeyError(msg)
            # Ensure that each result has a value and not None
            self.assertIsNotNone(values)

    def test_individual_parsers(self):
        """Test the output of each parser."""
        # TODO: PT-2278 - Dynamically pull all "get_" methods from the parser and fail if
        # there is no test case for a method.
        expected_values = {
            'get_actual_system_space': 43608331644432,
            'get_array_id': '782859-14778676-1975978063281993217',
            'get_array_name': 'DR-Pure3',
            'get_cap_for_hidden': 48989071716353,
            'get_capacity': 114921711734966,
            'get_controller_num': 'ct0',
            'get_controller_model': 2,
            'get_controller_model_local': 'FA-m70r2',
            'get_controller_serial': 'PCTFL1631023A',
            'get_copyout_error_extents': 151950806,
            'get_data_reduction': 3.9420873925684705,
            'get_domain_name': 'paylocity.com',
            'get_eradicated_vol_phys': 147762670877,
            'get_fdiags': 55,
            'get_fdiags_unflattened': 55,
            'get_is_primary': True,
            'get_live_physical_space': 65789357335418,
            'get_local_time': '2017 Dec 18 23:19:46 CST',
            'get_logical_discrepancy': 7080202342912,
            'get_newly_written_space': 96527712256,
            'get_num_shelves': 3,
            'get_pgroup_settings': 9,
            'get_pgroup_snaps': 215,
            'get_physical_discrepancy': 1267842769464,
            'get_physical_space': 70138838894860,
            'get_pslun_names': 107,
            'get_purealert_list': 2,
            'get_pureapp_list': 4,
            # This output is different from puredrive.list due to different levels
            # of verbosity between the Purity commands.
            'get_puredb_list_drives': 140,
            'get_puredb_list_job': 42,
            'get_puredrive_list': 96,
            'get_purehw_list': 261,
            'get_puremessage_list_audit': 21,
            'get_purity_version': '4.10.5',
            'get_reclaimable_space': 15242736821322,
            'get_replbond_info': 2,
            'get_reported_pyramid': 4241548049449,
            'get_reported_raid': 99480712844,
            'get_san_targets': 2,
            'get_sas_port_info': 2,
            'get_serials': 6,
            'get_shared_space': 33120458583398,
            'get_snapshot_space': 30924537786946,
            'get_ssd_capacity': 182125403832320,
            'get_ssd_mapped': 115079697661952,
            'get_system_space': 0,
            'get_thin_provisioning': 0.48421891083853374,
            'get_total_reduction': 7.642946737301553,
            'get_triage_error': 180540609740,
            'get_unknown_space': 0,
            'get_unreachable_extent_phys': 5506081686,
            'get_unreported_pyramid': 2301593953239,
            'get_unreported_raid': 24286862921968,
            'get_unreported_ratio': 0.8865214078905119,
            'get_unreported_space': 24926948439766,
            'get_visible_system_space': 0,
            'get_vector_space': 6637273387008,
            'get_volume_space': 6093842524516,
        }
        for form_parser in sorted(expected_values.keys()):
            # The result should be a list of tuples containing (timestamp, value_lines).
            result = getattr(self.parser, form_parser)()
            # Ensure we have all the expected timestamps:
            msg = 'The Form Parser "{}" did not have all of the timestamps.'.format(form_parser)
            self.assertEqual(len(result), EXPECTED_TIMESTAMPS, msg=msg)
            # Ensure that the result value is the expected length.
            value = sorted(result)[0][1]
            if isinstance(value, dict):
                # Convert to a list for compatibility with Python 3.5+.
                value = len(list(value.keys()))
            elif isinstance(value, list):
                # PT-2160: Fixed how we parse puredb.list.drives from frequentdiagnostics.
                if form_parser == 'get_puredb_list_drives':
                    value = len(value)
                else:
                    # Just get the first result for comparison.
                    value = value[0]
            msg = 'The Form Parser "{}" did not get the expected result.  Result was: "{}".'.format(form_parser, value)
            self.assertEqual(str(expected_values[form_parser]), str(value), msg=msg)
