"""Unit tests for array_info_json."""

from __future__ import unicode_literals

import os
import unittest

from six import iteritems

from photon.backend.pure.logs import array_info_json

EXPECTED_TIMESTAMPS = 1
FORMS = (
    'array_id',
    'array_info',
    'array_name',
    'chassis_serial',
    'controller_name',
    'controller_serial',
    'domain_name',
    'purity_version',
)
NO_FORM_EXPECTED = (
    'array_id',
    'array_name',
    'chassis_serial',
    'controller_name',
    'controller_serial',
    'domain_name',
    'purity_version',
)
# These are okay to have no results sometimes
PATH = os.path.dirname(__file__)


class ArrayInfoFormDataTestCase(unittest.TestCase):
    """Unit tests for ArrayInfoFormData."""

    def test_build(self):
        """Ensure that this builds the forms correctly."""
        data = array_info_json.ArrayInfoFormData()
        for form in FORMS:
            if form in NO_FORM_EXPECTED:
                continue
            msg = 'Form "{}" is not defined in ArrayInfoFormData.'.format(form)
            self.assertTrue(hasattr(data, form), msg=msg)
        # Not much else to test here afaik.


class ArrayInfoParserTestCase(unittest.TestCase):
    """Unit tests for ArrayInfoParser."""
    log_file = os.path.join(PATH, 'test_files/array_info.json-test.gz')
    parser = array_info_json.ArrayInfoParser(log_file)

    def test_fields(self):
        """Ensure that Fields are well formed."""
        for datum, log_data in iteritems(self.parser.fields):
            if datum in NO_FORM_EXPECTED:
                continue
            # Assert that each fields has a defined form.
            msg = 'fields "{}" has no form.'.format(datum)
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


class FieldsTestCases(unittest.TestCase):
    """Unit tests for all fields in the ArrayInfoParser."""
    log_file = os.path.join(PATH, 'test_files/array_info.json-test.gz')
    parser = array_info_json.ArrayInfoParser(log_file)

    def test_results(self):
        """Fetch each field from the array_info.json-test.gz log file. and validate results."""
        for field in self.parser.fields:
            try:
                values = self.parser.get_field(field)
            except KeyError:
                msg = 'Field "{}" is not defined in the array_info_json log parser.'.format(field)
                raise KeyError(msg)
            # Ensure that each result has a value and not None
            self.assertIsNotNone(values)

    def test_individual_parsers(self):
        """Test the output of each parser."""
        parsers = ['get_' + form for form in FORMS]
        expected_results = {
            'get_array_info': ['chassis_sn', 'controller', 'controller_sn', 'current_datetime', 'fc_array_id',
                               'hostname', 'info_version', 'iscsi_array_id', 'middleware_api_version',
                               'middleware_version', 'net_array_id', 'purity_version'],
            'get_array_id': '782859-14778676-1975978063281993217',
            'get_array_name': 'DR-Pure3',
            'get_chassis_serial': 'PCHFS15330028',
            'get_controller_name': 'CT0',
            'get_controller_serial': 'PCTFL1631023A',
            'get_domain_name': 'paylocity.com',
            'get_purity_version': '4.10.5',
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
                value = value[0]
            # The result should be a list of tuples containing (timestamp, value_lines).
            msg = 'The Form Parser "{}" did not get the expected result.  Result was "{}".'.format(form_parser, value)
            self.assertEqual(expected_results[form_parser], value, msg=msg)


if __name__ == '__main__':
    unittest.main()
