"""Unit tests for lib/parser_utils."""

from __future__ import unicode_literals

import os
import unittest

import pandas

from photon.backend.pure.logs import diagnostics
from photon.lib import parser_utils
from photon.lib import test_utils
from photon.lib import time_utils

PATH = os.path.dirname(__file__)


class FakeForm(object):
    """Created for testing purposes."""
    pass


class TestLogData(unittest.TestCase):
    """Unit tests for LogData."""

    def test_no_forms(self):
        """Should raise a TypeError."""
        with self.assertRaises(TypeError):
            parser_utils.LogData(None)

    def test_empty_forms(self):
        """Should build properly with no forms present."""
        self.assertEqual(parser_utils.LogData({}).forms, {})

    def test_valid_forms(self):
        """Should instantiate properly."""
        forms = {'simple_text': parser_utils.SimpleTextForm('grep_pattern'),
                 'interval': parser_utils.IntervalForm('grep_pattern', 'start_text', 'end_text'),
                 'grep': parser_utils.GrepForm()}
        self.assertEqual(parser_utils.LogData(forms).forms, forms)


class TestSimpleTextForm(unittest.TestCase):
    """Unit tests for SimpleTextForm."""

    def test_no_regexes(self):
        """Instantiate without regexes."""
        form = parser_utils.SimpleTextForm('text_to_match')
        self.assertEqual(form.text_to_match, 'text_to_match')
        self.assertEqual(form.regexes, {})

    def test_with_regexes(self):
        """Instantiate with regexes."""
        form = parser_utils.SimpleTextForm('text_to_match', {'regex1': r'abc123'})
        self.assertEqual(form.text_to_match, 'text_to_match')
        self.assertEqual(form.regexes, {'regex1': r'abc123'})

    def test_with_posttext(self):
        """Instantiate with post_text_to_match."""
        form = parser_utils.SimpleTextForm('text_to_match', post_text_to_match='abc123')
        self.assertEqual(form.text_to_match, 'text_to_match')
        self.assertEqual(form.regexes, {})
        self.assertEqual(form.post_text_to_match, 'abc123')


class TestIntervalForm(unittest.TestCase):
    """Unit tests for IntervalForm."""

    def test_no_regexes(self):
        """Test without regexes."""
        form = parser_utils.IntervalForm('text_to_match', 'start_text', 'end_text')
        self.assertEqual(form.text_to_match, 'text_to_match')
        self.assertEqual(form.start_text, 'start_text')
        self.assertEqual(form.end_text, 'end_text')
        self.assertIsNone(form.regexes)
        self.assertIsNone(form.post_text_to_match)

    def test_with_regexes(self):
        """Test with regexes."""
        form = parser_utils.IntervalForm('text_to_match', 'start_text', 'end_text', {'regex1': r'abc123'})
        self.assertEqual(form.text_to_match, 'text_to_match')
        self.assertEqual(form.start_text, 'start_text')
        self.assertEqual(form.end_text, 'end_text')
        self.assertEqual(form.regexes, {'regex1': r'abc123'})
        self.assertIsNone(form.post_text_to_match)

    def test_with_posttext(self):
        """Test without regexes."""
        form = parser_utils.IntervalForm('text_to_match', 'start_text', 'end_text', post_text_to_match='abc123')
        self.assertEqual(form.text_to_match, 'text_to_match')
        self.assertEqual(form.start_text, 'start_text')
        self.assertEqual(form.end_text, 'end_text')
        self.assertIsNone(form.regexes)
        self.assertEqual(form.post_text_to_match, 'abc123')


class DummyFormData(parser_utils.FormData):
    """Forms used by TestLogParser."""

    lines = parser_utils.SimpleTextForm(
        text_to_match='text_to_match',
        regexes={},
    )


class DummyLogData(parser_utils.LogData):
    """Manage test data."""

    def __init__(self, needed_forms):
        """Create an object to track needed forms."""
        forms = DummyFormData()
        super(DummyLogData, self).__init__({form: forms[form] for form in needed_forms})


class TestParallelLogParser(unittest.TestCase):
    """Unit tests for ParallelLogParser."""

    def setUp(self):
        """Reset test parameters."""
        self.api = diagnostics.DiagnosticsParser(test_utils.get_files_of_type('Uncategorized/diagnostics.log-')[0])
        self.api.data_set = pandas.DataFrame()
        self.api.field_data = {}
        self.api.fields = diagnostics.DiagnosticsParser.fields
        self._form_data = None
        self.api.forms = diagnostics.DiagnosticsParser.forms
        self.api._form_lines = None
        self.api.text_to_match = self.api._get_text_to_match()

    def test_no_fields(self):
        """Test when we have no fields in the Parser."""
        self.api.fields = {}
        expected = []
        result = self.api.get_field('controller_mode')
        self.assertEqual(expected, result)

    def test_no_forms(self):
        """Test when we have no forms in the Parser."""
        self.api.forms = {}
        with self.assertRaises(KeyError):
            self.api.get_field('controller_mode')

    def test_bad_field(self):
        """Test when we request a bad field."""
        with self.assertRaises(AttributeError):
            self.api.get_field('fake_field')

    def test_no_lines_matched(self):
        """Test if we have no lines matched (PT_2146)."""
        # Make a form which will match no lines in diagnostics.log.
        setattr(diagnostics.DiagFormData, 'test_form', parser_utils.SimpleTextForm(text_to_match='something random'))
        self.api.fields['test_field'] = diagnostics.DiagLogData(['test_form'])
        self.api.get_test_field = lambda: []
        expected = []
        result = self.api.get_field('test_field')
        self.assertEqual(expected, result)

    def test_fetch_raw_lines_no_text_to_match(self):
        """Unit tests for fetch_raw_lines with no text_to_match."""
        # Set text_to_match to None.
        self.api.text_to_match = None
        expected = 33  # There are 33 fields in diagnostics.  This will need to be updated when we add more.
        result = len(list(self.api.fetch_raw_lines()))
        self.assertEqual(expected, result)

    def test_fetch_raw_lines_with_text_to_match(self):
        """Unit tests for fetch_raw_lines with text_to_match."""
        self.api.text_to_match = ['a']
        expected = 17
        result = len(list(self.api.fetch_raw_lines()))
        self.assertEqual(expected, result)

    def test_form_lines_empty(self):
        """Unit tests for form_lines when the raw_lines result is empty."""
        # Set text_to_match to a bad pattern so we have no raw lines.
        self.api.text_to_match = ['something random']
        # We should get an empty placeholder for the forms requested.  In this case just diagnostics.
        expected = {'diagnostics': []}
        result = self.api.form_lines.to_dict('list')
        self.assertEqual(expected, result)

    def test_form_lines_text_to_match(self):
        """Unit tests for form_lines when the raw_lines has lines and a form has text_to_match."""
        self.api.text_to_match = ['a']
        expected = 17
        result = len(self.api.form_lines.index)
        self.assertEqual(expected, result)

    def test_form_lines_no_text_to_match(self):
        """Unit tests for form_lines when the raw_lines has lines and a form has no text_to_match."""
        # Set text_to_match to None, so we match every line.
        self.api.text_to_match = None
        expected = 33  # There are 33 fields in diagnostics.  This will need to be updated when we add more.
        result = len(self.api.form_lines.index)
        self.assertEqual(expected, result)

    def test_get_form_lines_bad_form(self):
        """Unit tests for get_form_lines when we have a bad form_name."""
        with self.assertRaises(KeyError):
            self.api.get_form_lines('fake_form')

    def test_get_form_lines_interval_form(self):
        """Unit tests for get_form_lines with an IntervalForm, no post_text_to_match."""
        # The generic 'diagnostics' form is an IntervalForm.
        expected = 8  # The test file only has 8 sections.  This will need to be updated when we add more.
        result = len(self.api.get_form_lines('diagnostics'))
        self.assertEqual(expected, result)

    # TODO: PT-2153 - Additional testing for get_form_lines:
    # 1) IntervalForm w/ post_text_to_match
    # 2) TarfileForm w/ and w/out post_text
    # 3) SimpleTextForm w/ and w/out post_text

    def test_get_field(self):
        """Unit tests for get_form_lines."""
        expected = [(time_utils.Timestamp('2018-12-11 00:17:14'), 'DR-Pure3')]
        result = self.api.get_field('array_name')
        self.assertEqual(expected, result)

    def test_get_fields(self):
        """Unit tests for get_form_lines."""
        expected = {'array_name': [(time_utils.Timestamp('2018-12-11 00:17:14'), 'DR-Pure3')]}
        result = self.api.get_fields(['array_name'])
        self.assertEqual(expected, result)

    # TODO: PT-2153 - Additional testing: regex_in_intervals, pull_from_regex.
