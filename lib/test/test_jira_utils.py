"""Unit tests for jira_utils."""

import unittest

from photon.lib.custom_errors import FormatError
from photon.lib import jira_utils


class WrapInJIRATestCase(unittest.TestCase):
    """Unit tests for wrap_in_jira."""

    def test_str(self):
        """Valid usage with a single string."""
        body = 'BODY OF THE JIRA'
        expected = ['{ noformat:title=My Title }']
        expected.extend(body)
        expected.append('{ noformat }')
        self.assertEqual(jira_utils.wrap_in_jira(body, 'My Title'), expected)

    def test_lines(self):
        """Valid usage with a multiple lines of strings."""
        body = ['BODY OF THE JIRA', 'PART 2 OF THE BODY']
        expected = ['{ noformat:title=My Title }']
        expected.extend(body)
        expected.append('{ noformat }')
        self.assertEqual(jira_utils.wrap_in_jira(body, 'My Title'), expected)

    def test_empty(self):
        """Invalid usage with no lines."""
        body = []
        with self.assertRaises(FormatError):
            jira_utils.wrap_in_jira(body, 'My Title')

    def test_no_title(self):
        """Valid usage with no title."""
        title = None
        body = ['Test lines']
        expected = ['{ noformat }']
        expected.extend(body)
        expected.append('{ noformat }')
        self.assertEqual(jira_utils.wrap_in_jira(body, title), expected)

    def test_code_type(self):
        """Valid usage with code type of formatting."""
        title = None
        body = ['Test lines']
        expected = ['{ code }']
        expected.extend(body)
        expected.append('{ code }')
        self.assertEqual(jira_utils.wrap_in_jira(body, title, 'code'), expected)

    def test_color(self):
        """Valid usage adding JIRA color."""
        format_type = 'color:red'
        title = None
        body = ['Test lines']
        expected = ['{ color:red }']
        expected.extend(body)
        expected.append('{ color }')
        self.assertEqual(jira_utils.wrap_in_jira(body, title, format_type), expected)

    def test_invalid_type(self):
        """Invalid usage with an unknown code type of formatting."""
        body = ['Test lines']
        with self.assertRaises(FormatError):
            jira_utils.wrap_in_jira(body, 'My Title', 'fake_type')
