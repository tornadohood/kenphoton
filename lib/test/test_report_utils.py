"""Unit tests for report_utils."""

import os
import unittest

import textwrap

from photon.lib.custom_errors import FormatError
from photon.lib import report_utils

PATH = os.path.dirname(__file__)


class DrawBasicTableTestCase(unittest.TestCase):
    """Unit tests for draw_basic_table."""

    def test_str_alignment(self):
        """Test using a single string alignment applied to all columns."""
        body = [['CENTER0', 'CENTER1'], ['0', 'thing']]
        expected = """
        +---------+---------+
        | CENTER0 | CENTER1 |
        +=========+=========+
        | 0       | thing   |
        +---------+---------+"""
        result = report_utils.draw_basic_table(body, alignment='center')
        self.assertEqual('\n' + result, textwrap.dedent(expected))

    def test_alignments(self):
        """Valid usage with different alignment styles."""
        body = [['LEFT', 'RIGHT', 'CENTER'], ['Some', 'Text', 'Here']]
        expected = """
        +------+-------+--------+
        | LEFT | RIGHT | CENTER |
        +======+=======+========+
        | Some |  Text |  Here  |
        +------+-------+--------+"""
        alignment = ('l', 'r', 'c')
        result = report_utils.draw_basic_table(body, alignment)
        self.assertEqual('\n' + result, textwrap.dedent(expected))

    def test_single_alignment(self):
        """Valid usage with a single alignment style applied to all columns."""
        body = [['LEFT', 'RIGHT', 'CENTER'], ['Some', 'Text', 'Here']]
        expected = """
        +------+-------+--------+
        | LEFT | RIGHT | CENTER |
        +======+=======+========+
        | Some | Text  | Here   |
        +------+-------+--------+"""
        alignment = ['left']
        result = report_utils.draw_basic_table(body, alignment)
        self.assertEqual('\n' + result, textwrap.dedent(expected))

    def test_no_header(self):
        """Valid usage with no header."""
        body = [['BODY OF THE TABLE', 'PART 2']]
        expected = """
        +-------------------+--------+
        | BODY OF THE TABLE | PART 2 |
        +-------------------+--------+"""
        result = report_utils.draw_basic_table(body, header=False)
        self.assertEqual('\n' + result, textwrap.dedent(expected))

    def test_with_header(self):
        """Valid usage with a multiple lines of strings and the first one is the header."""
        body = [['My Header'], ['BODY OF THE TABLE'], ['PART 2']]
        expected = """
        +-------------------+
        |     My Header     |
        +===================+
        | BODY OF THE TABLE |
        +-------------------+
        | PART 2            |
        +-------------------+"""
        result = report_utils.draw_basic_table(body, header=True)
        self.assertEqual('\n' + result, textwrap.dedent(expected))

    def test_empty(self):
        """Invalid usage with no lines."""
        body = []
        with self.assertRaises(FormatError):
            report_utils.draw_basic_table(body)


class WrapInBoxTestCase(unittest.TestCase):
    """Unit tests for wrap_in_box."""

    def test_with_description(self):
        """Valid usage with a custom description."""
        # ++++++++++++++++
        # My Description:
        # BODY OF THE TEXT
        # ++++++++++++++++
        body = ['BODY OF THE TEXT']
        desc = 'My Description:'
        edge = '+' * 16
        expected = [edge, desc]
        expected.extend(body)
        expected.append(edge)
        self.assertEqual(report_utils.wrap_in_box(body, '+', desc), expected)

    def test_custom_box_char(self):
        """Valid usage with a custom box character '+'."""
        # ++++++++++++++++
        # BODY OF THE TEXT
        # ++++++++++++++++
        body = ['BODY OF THE TEXT']
        edge = '+' * 16
        expected = [edge]
        expected.extend(body)
        expected.append(edge)
        self.assertEqual(report_utils.wrap_in_box(body, '+'), expected)

    def test_lines(self):
        """Valid usage with a multiple lines of strings."""
        # ================
        # BODY OF THE TEXT
        # ================
        body = ['BODY OF THE TEXT', 'PART 2']
        edge = '=' * 16
        expected = [edge]
        expected.extend(body)
        expected.append(edge)
        self.assertEqual(report_utils.wrap_in_box(body), expected)

    def test_empty(self):
        """Invalid usage with no lines."""
        body = []
        with self.assertRaises(FormatError):
            report_utils.wrap_in_box(body)
