"""Unit tests for the platform."""

from __future__ import unicode_literals

import unittest
import os

from photon.backend.pure.logs import platform

from six import iteritems
from six import string_types

FORMS = (
    'dev_info',
    'failovers',
    'purity_uptime',
    'purity_version',
)
NO_FORM_EXPECTED = (
    # These datum are expected to not have their own form.  These are post-processors.
    'purity_uptime',
    'purity_version',
)
PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/platform.log-test.gz')


class PlatformFormDataTestCase(unittest.TestCase):
    """Unit tests for PlatformFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        self.assertTrue(platform.PlatformFormData())


class PlatformParserTestCase(unittest.TestCase):
    """Unit tests for DiagnosticsParser."""
    parser = platform.PlatformParser(LOG_FILE)

    def test_forms(self):
        """Ensure that forms include the needed information."""
        forms = self.parser.forms
        for form in FORMS:
            if form in NO_FORM_EXPECTED:
                continue
            msg = 'Form "{}" not found, but it was expected in the PlatformParser.'.format(form)
            self.assertTrue(hasattr(forms, form), msg=msg)

    def test_fields(self):
        """Ensure that Fields are well formed."""
        # If we add any other forms besides diagnostics then this needs to be updated.
        for datum, log_data in iteritems(self.parser.fields):
            if datum in NO_FORM_EXPECTED:
                continue
            # Assert that each fields has a form
            self.assertTrue(getattr(self.parser.forms, datum))


class KnownDataTestCases(unittest.TestCase):
    """Unit tests for all Fields in the PlatformParser."""
    log_file = os.path.join(PATH, 'test_files/platform.log-test.gz')
    parser = platform.PlatformParser(log_file)

    def test_results(self):
        """Fetch each field from the platform.log-test.gz log file. and validate results."""
        for field in self.parser.fields:
            try:
                values = self.parser.get_field(field)
            except KeyError:
                msg = 'Field "{}" is not defined in the platform log parser.'.format(field)
                raise KeyError(msg)
            # Ensure that each result has a value and not None
            self.assertIsNotNone(values)

    def test_individual_parsers(self):
        """Test the output of each parser."""
        parsers = ['get_' + form for form in FORMS]
        expected_results = {
            'get_dev_info': {'slot': '18', 'dm': '/dev/ps-HrJW-8rYk6l:IBX8vQrvoh6-44',
                             'name': 'SAMSUNG_MZ7LM1T9_S2TVNX0J510014',
                             'grp': '9476305759760631028, 13421411367865042895',
                             'encl': 'EB-2425-E12EBD_SHT1019220G0YYC',
                             'dev': '9248127490348451962, 8847704025729224357',
                             'apt': '11951019079781516624, 12986023337942797145', 'wwn': '5002538C406155B5',
                             'type': 'SSD', 'subslot': '1'},
            'get_failovers': ['action', 'reason'],
            'get_purity_uptime': '139d:14h:32m:18s',
            'get_purity_version': '4.10.5',
        }
        for form_parser in parsers:
            result = getattr(self.parser, form_parser)()
            # Just test the first value in the list of results:
            value = sorted(result, key=lambda item: item[0])[0][1]
            if isinstance(value, dict):
                value = sorted(list(value.keys()))
            elif isinstance(value, list):
                value = value[0]
            # Convert any remaining long strings to a length for easier comparison.
            if isinstance(value, string_types) and len(value) > 25:
                value = len(value)
            # The result should be a list of tuples containing (timestamp, value_lines).
            msg = 'The Form Parser "{}" did not get the expected result.  Result was "{}".'.format(form_parser, value)
            self.assertEqual(expected_results[form_parser], value, msg=msg)
