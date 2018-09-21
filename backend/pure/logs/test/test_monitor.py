"""Contains parser definitions on how to extract data from the monitor.log."""

from __future__ import unicode_literals

import unittest
import os

from photon.backend.pure.logs import monitor
from photon.lib.time_utils import Timestamp

FORMS = ('alerts', 'messages')
PATH = os.path.dirname(__file__)
# TODO: Multiple version tests, multiple controller tests.
LOG_FILE = os.path.join(PATH, 'test_files/monitor-test.gz')

# pylint: disable=line-too-long


class MonitorFormDataTestCase(unittest.TestCase):
    """Unit tests for MonitorFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        self.assertTrue(monitor.MonitorFormData())


class MonitorParserTestCase(unittest.TestCase):
    """Unit tests for MonitorParser."""
    parser = monitor.MonitorParser(LOG_FILE)

    def test_forms(self):
        """Ensure that forms include the needed information."""
        forms = self.parser.forms
        for form in FORMS:
            self.assertTrue(hasattr(forms, form))

    def test_fields(self):
        """Ensure that Fields are well formed."""
        # If we add any other forms besides diagnostics then this needs to be updated.
        for field in self.parser.fields:
            # Assert that each fields has a form
            self.assertTrue(getattr(self.parser.forms, field))

    def test_fields_tests(self):
        """Ensure that each item in Fields has a unit test."""
        for datum in self.parser.fields:
            msg = 'Field "{}" does not have a unit test.  Please write one.'.format(datum)
            self.assertTrue('test_get_{}'.format(datum) in dir(MonitorParserTestCase), msg=msg)

    def test_get_alerts(self):
        """Test get_alerts."""
        expected = (Timestamp('2018-05-31 00:00:26'),
                    {'body': "Health check found some unexpected health metrics\n\nSeverity: Warning \nUTC Time: 2018 May 31 05:00:24\nArray Time: 2018 May 31 00:00:24 CDT\nArray Name: DR-Pure3\nDomain: paylocity.com\nSuggested Action: Contact Pure Storage Support. Have the text of the electronic mail or SNMP trap available. \n\nPurity Version: 4.10.5\nArray ID: b4379f6c-4703-4b59-a5da-8c88aa4b0550\nCA Array ID: 782859-14778676-1975978063281993217\nController Name: ct0\nController Serial: PCTFL1631023A \nChassis Serial: PCHFS15330028\nUUIDs: ['3c824d8586414b4ba311033fb8e57de6']\nVariables: (below)\nreplication.replication_target_memory:                       9745104128 (1527742816)\n",
                     'audience': 'pure', 'severity': 'Warning', 'reminder': False, 'version': '4.10.5',
                     'category': 'array', 'generator': 'local', 'alert_code': 98, 'self_help': False,
                     'subject': 'Replication health check failure [98]', 'tags': [],
                     'description': 'Health check found some unexpected health metrics',
                     'uuids': ['3c824d8586414b4ba311033fb8e57de6'], 'local_time': '2018 May 31 00:00:24 CDT'})
        result = self.parser.get_alerts()[0]
        self.assertEqual(result, expected)

    def test_get_messages(self):
        """Test get_messages."""
        expected = (Timestamp('2018-05-31 00:13:41'),
                    {'utc_time': 1527718420, 'uuid': '9dbc721bbe4542198ffb7bfab545db20', 'recently_notified': False,
                     'id': 12232360, 'error_code': 1, 'gen': 227225, 'current_severity': 'hidden',
                     'updated': 1527056289, 'closed': 1527718419, 'audience': 'pure', 'details': '', 'expected': None,
                     'update_timelimit': 432000, 'archived': False, 'code': 2000, 'recently_updated': False,
                     'actual': None, 'component_type': 'controller', 'opened': 1524261129, 'highest_severity': 'hidden',
                     'count': 43, 'category': 'array', 'recently_closed': True, 'component_name': 'phonehomelegacy',
                     'event': 'misconfiguration', 'notified': 0, 'flagged': True})
        result = self.parser.get_messages()[0]
        self.assertEqual(result, expected)
