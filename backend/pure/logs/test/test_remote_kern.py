"""Contains parser definitions on how to extract data from the remote_kern.log."""
from __future__ import unicode_literals

import unittest
import os

from six import iteritems

from photon.backend.pure.logs import remote_kern

PATH = os.path.dirname(__file__)
LOG_FILE = os.path.join(PATH, 'test_files/remote_kern-test.gz')


@unittest.skip('Not Implemented Yet.')
class RemoteKernFormDataTestCase(unittest.TestCase):
    """Unit tests for RemoteKernFormData."""

    def test_build(self):
        """Ensure that this builds the IntervalForm correctly."""
        self.assertTrue(remote_kern.RemoteKernFormData())


@unittest.skip('Not Implemented Yet.')
class RemoteKernParserTestCase(unittest.TestCase):
    """Unit tests for RemoteKernParser."""
    parser = remote_kern.RemoteKernParser(LOG_FILE)

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
        """Ensure that each item in Fields has a unit test."""
        for datum in self.parser.fields:
            msg = 'Fields "{}" does not have a unit test.  Please write one.'.format(datum)
            self.assertTrue('test_get_{}'.format(datum) in dir(RemoteKernParserTestCase), msg=msg)

    # Add tests for each function definition.
