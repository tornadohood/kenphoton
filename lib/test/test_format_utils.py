"""Unit tests for format_utils."""

from __future__ import unicode_literals

import pytest
import unittest

from numpy import nan

from photon.lib import format_utils
from photon.lib.custom_errors import FormatError


class TestAutoAlignText(unittest.TestCase):
    """Unit tests for auto_align_text function."""

    def test_numbers(self):
        """Test with different numbers and number formats."""
        test = [
            (1.0, '       1.0'),
            (3000, '      3000'),
            ('30 TiB', '    30 TiB'),
            ('0.83:1', '    0.83:1'),
        ]
        msg = 'Result did not match expected: {} != {}'
        for value, expected in test:
            result = format_utils.auto_align_text(value, padding=10)
            self.assertEqual(result, expected, msg=msg.format(result, expected))

    def test_strings(self):
        """Test with different strings."""
        test = [
            ('10Number', '10Number  '),
            ('This-Thing', 'This-Thing'),
        ]
        msg = 'Result did not match expected: {} != {}'
        for value, expected in test:
            result = format_utils.auto_align_text(value, padding=10)
            self.assertEqual(result, expected, msg=msg.format(result, expected))


class TextFormatTestCase(unittest.TestCase):
    """Unit tests for text_fmt function."""

    def test_format(self):
        """Test that it formats properly."""
        text = 'Stuff to stylize'
        expected = '\x1b[91m\x1b[1mStuff to stylize\x1b[0m'
        result = format_utils.text_fmt(['red', 'bold'], text)
        self.assertEqual(expected, result)


class SplitListTestCase(unittest.TestCase):
    """Unit tests for split_list."""

    def test_empty_list(self):
        """Test behavior with an empty list; numpy will raise a ValueError."""
        # This will yield an empty list 7 times.
        expected = [[], [], [], [], [], [], [], []]
        result = list(format_utils.split_list([], num_pieces=7))
        self.assertEqual(result, expected)

    def test_by_pieces(self):
        """Test splitting via the pieces argument."""
        # This will split it into 2 even pieces.
        expected = [[0, 1, 2], [3, 4, 5]]
        result = list(format_utils.split_list(range(6), num_pieces=2))
        self.assertEqual(result, expected)

    def test_by_size(self):
        """Test splitting via the size argument."""
        # This will split it into 'n' (3 in this case) pieces of size 2.
        expected = [[0, 1], [2, 3], [4, 5]]
        result = list(format_utils.split_list(range(6), size=2))
        self.assertEqual(result, expected)

    def test_by_both(self):
        """Test using both args; this should raise a ValueError."""
        with self.assertRaises(ValueError):
            list(format_utils.split_list(range(6), size=2, num_pieces=2))

    def test_by_neither(self):
        """Test using neither args; this should raise a ValueError."""
        with self.assertRaises(ValueError):
            list(format_utils.split_list(range(6)))

    def test_uneven_split(self):
        """Test an uneven split, the first yield should be the 1 larger."""
        expected = [[0, 1, 2], [3, 4], [5, 6]]
        result = list(format_utils.split_list(range(7), size=2))
        self.assertEqual(result, expected)


class SplitStrTestCase(unittest.TestCase):
    """Unit tests for split_str."""

    def test_empty_str(self):
        """Test behavior with an empty string."""
        expected = ''
        result = format_utils.split_str('', '', 1)
        self.assertEqual(result, expected)

    def test_small_str(self):
        """Test a string smaller than the 'every' argument."""
        expected = 'test'
        result = format_utils.split_str('test', ':', 5)
        self.assertEqual(result, expected)

    def test_wwn_str(self):
        """Test using a simulated WWN address."""
        wwn = '500277A4100C4E21'
        expected = '50:02:77:A4:10:0C:4E:21'
        result = format_utils.split_str(wwn, ':', 2)
        self.assertEqual(result, expected)

    def test_number_str(self):
        """Test using a very large number to string format like '1,000'."""
        expected = '1,000,000'
        result = format_utils.split_str(1000000, ',', 3, True)
        self.assertEqual(result, expected)


@pytest.mark.parametrize('before, after', [
    ['array_id', 'Array ID'],
    ['billy bob', 'Billy Bob'],
    ['ssd', 'SSD'],
    ['id', 'ID'],
    ['ct0', 'CT0'],
    ['-ct1', '-ct1'],
    ['Iscsi', 'iSCSI'],
    ['Fc', 'FC'],
    ['Ntp', 'NTP'],
    ['Ip', 'IP'],
    ['CT0 Mce Counts', 'CT0 MCE Counts'],
    ['CT1 Sel Critical Events', 'CT1 SEL Critical Events'],
])
def test_make_title(before, after):
    """Test make_title."""
    result = format_utils.make_title(before)
    assert result == after, '"{}" did not convert properly.'.format(before)


class AutoScaleTestCase(unittest.TestCase):
    """Unit tests for auto_scale."""

    def test_nan(self):
        """Test a numpy.nan value."""
        self.assertEqual(format_utils.auto_scale(nan, 'bytes'), '0.00 B')

    def test_value_with_units(self):
        """Test a value with units being converted to it's highest scale."""
        before = ('1000MB', '102233.2 KB', 10.7, '11.4B')
        after = ('1.00 GB', '102.23 MB', '10.70 B', '11.40 B')
        for index, value in enumerate(before):
            result = format_utils.auto_scale(value, 'bytes')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)

    def test_bytes(self):
        """Test a series of to bytes auto-scale conversions."""
        before = (0, 100.7, 1000.0, 23423423.723423, 1e+15)
        after = ('0.00 B', '100.70 B', '1.00 KB', '23.42 MB', '1.00 PB')
        for index, value in enumerate(before):
            result = format_utils.auto_scale(value, 'bytes')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)

    def test_bits(self):
        """Test a series of to bits auto-scale conversions."""
        before = (0, 100.7, 1000.0, 23423423.723423, 1e+15)
        after = ('0.00 b', '100.70 b', '1.00 Kb', '23.42 Mb', '1.00 Pb')
        for index, value in enumerate(before):
            result = format_utils.auto_scale(value, 'bits')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)

    def test_binary_bytes(self):
        """Test a series of to binary bytes auto-scale conversions."""
        before = (0, 1098.7, 1024.0, 23423423.723423, 1e+15)
        after = ('0.00 B', '1.07 KiB', '1.00 KiB', '22.34 MiB', '909.49 TiB')
        for index, value in enumerate(before):
            result = format_utils.auto_scale(value, 'binary_bytes')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)

    def test_bandwidth(self):
        """Test bandwidth values."""
        before = (0, 100.7, 1000.0, 23423423.723423, 1e+15)
        after = ('0.00 B/s', '100.70 B/s', '1.00 KB/s', '23.42 MB/s', '1.00 PB/s')
        for index, value in enumerate(before):
            result = format_utils.auto_scale(value, 'bandwidth')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)


class ConvertToUnitTestCase(unittest.TestCase):
    """Unit tests for convert_to_unit."""

    def test_unknown_unit(self):
        """Test a fake unit, this should raise a ValueError."""
        with self.assertRaises(FormatError):
            format_utils.convert_to_unit(10, 'Fake Unit')

    def test_units(self):
        """Test a series of conversions."""
        before = 1024.0
        after = ('1024.00 B', '1.00 KiB', '1.02 KB', '0.00 MB', '0.00 PB')
        units = ('B', 'KiB', 'KB', 'MB', 'PB')
        for index, unit in enumerate(units):
            result = format_utils.convert_to_unit(before, unit)
            msg = '"{}" did not scale correctly.  The result was: "{}", expected "{}".'
            self.assertEqual(result, after[index], msg=msg.format(unit, result, after[index]))

    def test_custom_precision(self):
        """Test using a custom precision."""
        before = 1024.0
        after = '1.00 KiB'
        result = format_utils.convert_to_unit(before, 'KiB')
        self.assertEqual(result, after)

    def test_to_lower_unit(self):
        """Test converting to a lower scale."""
        before = '1 GB'
        after = '1000.00 MB'
        result = format_utils.convert_to_unit(before, 'MB')
        self.assertEqual(result, after)


class ToRawTestCase(unittest.TestCase):
    """Unit tests for to_raw."""

    def test_nan(self):
        """Test a numpy.nan value."""
        self.assertEqual(format_utils.auto_scale(nan, 'bytes'), '0.00 B')

    def test_bytes(self):
        """Test a series of to bytes auto-scale conversions."""
        after = (0, 100.7, 1000.0, 23420000.0, 1e+15)
        before = ('0.00B', '100.70 B', '1.00 KB', '23.42 MB', '1.00PB')
        for index, value in enumerate(before):
            result = format_utils.to_raw(value, 'bytes')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)

    def test_bits(self):
        """Test a series of to bits auto-scale conversions."""
        after = (0, 100.7, 1000.0, 23420000.0, 1e+15)
        before = ('0.00b', '100.70 b', '1.00Kb', '23.42 Mb', '1.00 Pb')
        for index, value in enumerate(before):
            result = format_utils.to_raw(value, 'bits')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)

    def test_binary_bytes(self):
        """Test a series of to binary bytes auto-scale conversions."""
        after = (0, 1095.68, 1024.0, 23425187.84, 999994830345994.2, 12864286044979.2)
        before = ('0.00B', '1.07 KiB', '1.00 KiB', '22.34 MiB', '909.49TiB', '11.7 T')
        for index, value in enumerate(before):
            result = format_utils.to_raw(value, 'binary_bytes')
            msg = '"{}" did not auto-scale correctly.  The result was: "{}".'.format(value, result)
            self.assertEqual(result, after[index], msg=msg)

    def test_non_string_value(self):
        """This should raise a TypeError."""
        self.assertEqual(format_utils.to_raw(-7.5), -7.5)

    def test_unknown_unit(self):
        """Bad unit in the value.  This should raise a ValueError."""
        with self.assertRaises(FormatError):
            format_utils.to_raw('12345 Fake')

    def test_unknown_scale(self):
        """Bad scale manually specified.  This should raise a ValueError."""
        with self.assertRaises(FormatError):
            format_utils.to_raw('12345 B', 'Fake Scale')

    def test_manual_unknown_unit(self):
        """Manual scale with a bad unit.  This should raise a ValueError."""
        with self.assertRaises(FormatError):
            format_utils.to_raw('12345 Fake', 'bytes')

    def test_custom_precision(self):
        """Verify that custom precision values work as expected."""
        expected = 10123.45679
        result = format_utils.to_raw('10.123456789 KB', precision=5)
        self.assertEqual(expected, result)


class PercentageTestCase(unittest.TestCase):
    """Unit tests for percentage."""

    def test_invalid_input(self):
        """Test string input; should raise a ValueError."""
        with self.assertRaises(ValueError):
            format_utils.percentage('moo')

    def test_valid_input(self):
        """Test float/int input."""
        good_values = (
            (0.88, '88.00%'),
            (-.75129, '-75.13%'),
            (1, '100.00%')
        )
        for raw, expected in good_values:
            result = format_utils.percentage(raw)
            self.assertEqual(expected, result)

    def test_custom_precision(self):
        """Test changing the precision."""
        self.assertEqual(format_utils.percentage(1.75, precision=0), '175%')


class ZeroTestCase(unittest.TestCase):
    """Unit tests for zero."""

    def test_positive(self):
        """A positive value should be returned unchange."""
        self.assertEqual(10, format_utils.zero('10'))

    def test_negative(self):
        """A negative value should be returned as 0."""
        self.assertEqual(0, format_utils.zero('-11'))

    def test_zero(self):
        """Zero should be returned as 0."""
        self.assertEqual(0, format_utils.zero(0))


@pytest.mark.parametrize('path, expected', [
    ('/logs/purestorage.com/slc-coz-ct1/2018_01_02/core.log-2018010123.gz', '/logs/purestorage.com/slc-coz-ct1/2018_01_02'),
    ('/logs/purestorage.com/slc-coz-ct1/2018_01_02/', '/logs/purestorage.com/slc-coz-ct1/2018_01_02/'),
    ('/logs/purestorage.com/slc-coz-ct1/2018_01_02', '/logs/purestorage.com/slc-coz-ct1/2018_01_02'),
    ('/logs/purestorage.com/slc-coz-ct1/', '/logs/purestorage.com/slc-coz-ct1/2018_01_04'),
    ('/logs/purestorage.com/slc-coz-ct1', '/logs/purestorage.com/slc-coz-ct1/2018_01_04'),
    ('/my_dir/is/here/', '/my_dir/is/here/'),
    ('/my_dir/is/here', '/my_dir/is/here'),
])
def test_get_newest_log_date(monkeypatch, path, expected):
    # In this test, we need os.listdir to simulate a non-dated directory for the instance
    # when we get a base path.
    monkeypatch.setattr(format_utils.os, 'listdir',
                        lambda _: ['2018_01_02', '2018_01_03', '2018_01_04'])

    assert format_utils.get_newest_log_date(path) == expected


def test_make_snake_case():
    """Test that we make things into the expected snake case style."""
    assert format_utils.make_snake_case('(hello) there') == 'hello_there'
    assert format_utils.make_snake_case('') == ''
    assert format_utils.make_snake_case('member[1]') == 'member_1'
    assert format_utils.make_snake_case('eee_(efficient-ethernet)') == 'eee_efficient_ethernet'
    assert format_utils.make_snake_case('ethernet1/1') == 'ethernet1_1'
    assert format_utils.make_snake_case('load-interval_#2 ') == 'load_interval_num_2'
    assert format_utils.make_snake_case('auto-mdix') == 'auto_mdix'
    assert format_utils.make_snake_case(' a@b#c[d]e(f)g/h\\i-j ') == 'ab_num_c_de_fg_h_i_j'
