"""Contains parser definitions on how to extract data from the bcon.log."""

from __future__ import unicode_literals

import unittest
import os

from six import iteritems

from photon.backend.pure.logs import bcon

PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/bcon-test.gz')


@unittest.skip('Not Implemented Yet.')
class BconFormDataTestCase(unittest.TestCase):
    """Unit tests for BconFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        self.assertTrue(bcon.BconFormData())


@unittest.skip('Not Implemented Yet.')
class BconParserTestCase(unittest.TestCase):
    """Unit tests for BconParser."""
    parser = bcon.BconParser(LOG_FILE)

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
            self.assertTrue('test_get_{}'.format(datum) in dir(BconParserTestCase), msg=msg)

    # Add tests for each function definition.
