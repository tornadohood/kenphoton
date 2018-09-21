"""Contains parser definitions on how to extract data from the cache.log."""

from __future__ import unicode_literals

import unittest
import os

from six import iteritems

from photon.backend.pure.logs import cache

PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/cache-test.gz')


@unittest.skip('Not Implemented Yet.')
class CacheFormDataTestCase(unittest.TestCase):
    """Unit tests for CacheFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        self.assertTrue(cache.CacheFormData())


@unittest.skip('Not Implemented Yet.')
class CacheParserTestCase(unittest.TestCase):
    """Unit tests for CacheParser."""
    parser = cache.CacheParser(LOG_FILE)

    def test_forms(self):
        """Ensure that forms include the needed information."""
        pass
        # forms = self.parser.forms
        # Do this for each form.
        # self.assertTrue(hasattr(forms, 'postman_tcp_info_rcv_space_probe'))

    def test_fields(self):
        """Ensure that Fields are well formed."""
        # If we add any other forms besides diagnostics then this needs to be updated.
        for datum, log_data in iteritems(self.parser.fields):
            # Assert that each fields has a form
            self.assertTrue(getattr(self.parser.forms, datum))

    def test_fields_tests(self):
        """Ensure that each item in fields has a unit test."""
        for datum in self.parser.fields:
            msg = 'Field "{}" does not have a unit test.  Please write one.'.format(datum)
            self.assertTrue('test_get_{}'.format(datum) in dir(CacheParserTestCase), msg=msg)

    # Add tests for each function definition.
