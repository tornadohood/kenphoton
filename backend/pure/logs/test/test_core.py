"""Unit tests for core."""

from __future__ import unicode_literals

import unittest
import os

from photon.lib import parser_utils
from photon.backend.pure.logs import core
from photon.lib.time_utils import Timestamp

from six import iteritems

PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/core-test.gz')


class TestFlutterForm(unittest.TestCase):
    """ Test that flutterform provides expected form output. """
    flutform = parser_utils.FlutterForm('svc::postman_tcp_info_rcv_space_probe')

    def test_text_to_match(self):
        self.assertEqual(self.flutform.text_to_match, 'flutter')

    def test_start_text(self):
        self.assertEqual(self.flutform.start_text,
                         'flutter ->dump(svc::postman_tcp_info_rcv_space_probe)')

    def test_end_text(self):
        self.assertEqual(self.flutform.end_text, 'flutter <-dump')

    def test_regexes(self):
        self.assertEqual(self.flutform.regexes, {})


class CoreFormDataTestCase(unittest.TestCase):
    """Unit tests for CoreFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        data = core.CoreFormData()
        self.assertIsInstance(data.postman_tcp_info_rcv_space_probe, parser_utils.FlutterForm)


class CoreParserTestCase(unittest.TestCase):
    """Unit tests for CoreParser."""
    parser = core.CoreParser(LOG_FILE)

    def test_forms(self):
        """Ensure that forms include the needed information."""
        forms = self.parser.forms
        # Currently only requires 'diagnostics'.
        self.assertTrue(hasattr(forms, 'postman_tcp_info_rcv_space_probe'))

    def test_fields(self):
        """Ensure that Fields are well formed."""
        # If we add any other forms besides diagnostics then this needs to be updated.
        for datum, log_data in iteritems(self.parser.fields):
            # Assert that each fields has one or more valid forms.
            forms = log_data.forms.keys()
            for form in forms:
                self.assertTrue(hasattr(self.parser.forms, form))

    # TODO: PT-2096 - Need to get the field tests across all log parsers
    @unittest.skip
    def test_fields_tests(self):
        """Ensure that each item in fields has a unit test."""
        for datum in self.parser.fields:
            msg = 'Field "{}" does not have a unit test.  Please write one.'.format(datum)
            self.assertTrue('test_get_{}'.format(datum) in dir(CoreParserTestCase), msg=msg)

    def test_get_postman_tcp_info_rcv_space_probe(self):
        """Test get_postman_tcp_info_rcv_space_probe."""
        expected = {u'connection_id': u'0',
                    u'count': u'43690',
                    u'flutter_type': 'svc::postman_tcp_info_rcv_space_probe',
                    u'tcpi_rcv_space': u'34',
                    u'timestamp': Timestamp('01-28 23:17:23.545000')}
        result = self.parser.get_postman_tcp_info_rcv_space_probe()[0]
        self.assertEqual(result, expected)

    def test_get_devices_without_references(self):
        """Test get_devices_without_references."""
        expected = [(Timestamp('03-12 06:25:03.345000'),
                     {u'dev_id': '15518390543196150589, 34277887545602668'})]
        result = self.parser.get_devices_without_references()
        self.assertEqual(result, expected)

    def test_get_backlog(self):
        """Test get_backlog."""
        expected = [(Timestamp('03-12 06:25:03.346000'), 0)]
        result = self.parser.get_backlog()
        self.assertEqual(result, expected)

    def test_get_reported_pyramid(self):
        """Test get_reported_pyramid."""
        expected = [(Timestamp('03-12 06:25:03.348000'), 3391710784950.857)]
        result = self.parser.get_reported_pyramid()
        self.assertEqual(result, expected)

    def test_get_reclaimable_space(self):
        """Test get_reclaimable_space."""
        expected = [(Timestamp('03-12 06:25:03.347000'), 11553797570560.0)]
        result = self.parser.get_reclaimable_space()
        self.assertEqual(result, expected)

    # TODO: PT-1764 - Rewrite log parsers to use the test files in photon/test/test_files.
    @unittest.skip('PT-1764')
    def test_get_allocator_performance(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_backing_slabs(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_context_map_count(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_free_pool(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_malloc_stats(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_memory_contexts(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_memory_users(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_rsize(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_space_summary_dropped(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_total_memory(self):
        """Placeholder."""
        pass

    def test_get_triage_count(self):
        """Test the get_triage_count() method."""
        expected = [(Timestamp('07-24 23:18:14.682000'), 1)]
        result = self.parser.get_triage_count()
        self.assertEqual(result, expected)

    @unittest.skip('PT-1764')
    def test_get_untracked_memory(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_vsize(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_vsize_cap(self):
        """Placeholder."""
        pass

    @unittest.skip('PT-1764')
    def test_get_volume_space_report(self):
        """Placeholder."""
        pass
