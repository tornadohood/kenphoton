"""Unit tests for validation_utils."""

from __future__ import unicode_literals

import os
import unittest

# pylint: disable=redefined-builtin
from builtins import range
from photon.lib import validation_utils


class StrValidatorTestCase(unittest.TestCase):
    """Unit tests for str_validator."""

    def test_raises(self):
        """Test raising a specific error."""
        funct = lambda x: 'a' in x
        with self.assertRaises(IOError):
            validation_utils.str_validator('', funct, IOError, 'Message')

    def test_doesnt_raise(self):
        """Test that we don't raise when given None."""
        funct = lambda x: 'a' in x
        assert '' == validation_utils.str_validator('test', funct, None, 'Message')

    def test_doesnt_raise_returns(self):
        """Test raising a specific error."""
        funct = lambda x: 'test' == x
        assert 'test' == validation_utils.str_validator('test', funct, None, 'Message')


# Individual Validators:
class AIDTestCase(unittest.TestCase):
    """Unit tests for aid."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.aid('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.aid('782859-14778676-1975978063281993217'))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.aid('782859-14778676-1975978', TypeError)


class ChassisNameTestCase(unittest.TestCase):
    """Unit tests for chassis_name."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.chassis_name('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        valid_cts = (
            'ch0',
            'sh10',
            'SH0',
            'cH5'
        )
        for valid_ct in valid_cts:
            self.assertTrue(validation_utils.chassis_name(valid_ct))

    def test_invalid_str(self):
        """Test using an invalid str."""
        invalid_names = (
            'CT0',
            'CH',
            'chassis0',
            'SH0.BAY1',
        )
        for invalid_name in invalid_names:
            with self.assertRaises(TypeError):
                validation_utils.chassis_name(invalid_name, TypeError)


class CTNameTestCase(unittest.TestCase):
    """Unit tests for ct_name."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.ct_name('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        valid_cts = (
            'ct0',
            'CT1',
            'cT0',
            'Ct1'
        )
        for valid_ct in valid_cts:
            self.assertTrue(validation_utils.ct_name(valid_ct))

    def test_invalid_str(self):
        """Test using an invalid str."""
        invalid_cts = (
            'CT2',
            'CT',
            '-ct0',
        )
        for invalid_ct in invalid_cts:
            with self.assertRaises(TypeError):
                validation_utils.ct_name(invalid_ct, TypeError)


class DataSourceTestCase(unittest.TestCase):
    """Unit tests for data_source."""

    def test_valid_data_source(self):
        """Test valid data_sources."""
        valid_sources = ('LOGS', )
        for year in valid_sources:
            self.assertTrue(validation_utils.data_source(str(year)))

    def test_invalid_year(self):
        """Test invalid data_sources."""
        invalid_sources = (
            'fake',
            'fa_logs',
            'CloudAssist',
        )
        for bad_source in invalid_sources:
            with self.assertRaises(ValueError):
                validation_utils.data_source(bad_source, ValueError)


class DateHourTestCase(unittest.TestCase):
    """Unit tests for date_hour."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.date_hour('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.date_hour('2017_10_10-12'))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.date_hour('2017_10_10', TypeError)


class DayTestCase(unittest.TestCase):
    """Unit tests for day."""

    def test_valid_day(self):
        """Test valid days."""
        for day in range(1, 32):
            self.assertTrue(validation_utils.day(str(day)))

    def test_invalid_day(self):
        """Test invalid days."""
        bad_days = (0, 32)
        for bad_day in bad_days:
            with self.assertRaises(ValueError):
                validation_utils.day(str(bad_day), ValueError)


class DirectoryTestCase(unittest.TestCase):
    """Unit tests for directory."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.directory('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.directory(os.path.dirname(__file__)))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.directory('/this/is/a/fake/path', TypeError)


class DriveTestCase(unittest.TestCase):
    """Unit tests for drive."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.drive('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.drive('BAY10'))
        self.assertTrue(validation_utils.drive('SH0.BAY10'))
        self.assertTrue(validation_utils.drive('SH1.NVR0'))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.drive('BAYY12', TypeError)
        with self.assertRaises(TypeError):
            validation_utils.drive('CT0.BAY1', TypeError)


class FieldTestCase(unittest.TestCase):
    """Unit tests for field."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.field('', TypeError)

    def test_valid_str(self):
        """Test using a valid field defined within the FIELD_INDEX."""
        valid_fields = (
            'array_id',
            'array_NAME',
            'CONTROLLER_num'
        )
        for field in valid_fields:
            msg = 'Valid Field "{}" was not found in the FIELD_INDEX.'.format(field)
            self.assertTrue(validation_utils.field(field), msg)

    def test_invalid_str(self):
        """Test using an invalid field."""
        with self.assertRaises(TypeError):
            validation_utils.field('fake_field', TypeError)


class FilenameTestCase(unittest.TestCase):
    """Unit tests for filename."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.filename('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.filename(__file__))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.filename('I_AM_A_FAKE_FILE.xyz', TypeError)


class FQDNTestCase(unittest.TestCase):
    """Unit tests for fqdn."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.fqdn('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.fqdn('array.domain.com'))
        self.assertTrue(validation_utils.fqdn('array-ct0.domain.com'))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.fqdn('invalid.domain', TypeError)


class FuseBasePathTestCase(unittest.TestCase):
    """Unit tests for fuse_base_path."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.fuse_base_path('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        fuse_paths = (
            '/fuse/merged_mirror/purestorage.com/slc-coz-ct0',
            '/logs/paylocity.com/dr-pure3-ct1',
            '/logs/paylocity.com/dr-pure3-ct1',
            '/logs/lab3.service-now.com/sdlabpure103-ct1',
            '/support/ES-123456/domain.me/array-name-ct1/',
            '/support/ES-123456/domain.me/array-name-ct0/',
        )
        for fuse_path in fuse_paths:
            msg = 'Fuse Base Path: "{}" failed validation.'.format(fuse_path)
            self.assertTrue(validation_utils.fuse_base_path(fuse_path), msg=msg)

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.fuse_base_path('/not/a/valid/fuse/path', TypeError)


class FuseLogPathTestCase(unittest.TestCase):
    """Unit tests for fuse_log_path."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.fuse_log_path('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        fuse_paths = (
            '/fuse/merged_mirror/purestorage.com/slc-coz-ct0/2018_01_30',
            '/logs/paylocity.com/dr-pure3-ct1/2017_12_21',
            '/logs/paylocity.com/dr-pure3-ct1/2017_12_21',
            '/logs/lab3.service-now.com/sdlabpure103-ct1/2017_12_21',
            '/support/ES-123456/domain.me/array-name-ct1/2017_12_21/',
            '/support/ES-123456/domain.me/array-name-ct0/2017_12_21/',
        )
        for fuse_path in fuse_paths:
            msg = 'Fuse Path: "{}" failed validation.'.format(fuse_path)
            self.assertTrue(validation_utils.fuse_log_path(fuse_path), msg=msg)

    def test_invalid_str(self):
        """Test using an invalid str."""
        invalid_paths = (
            '/not/a/valid/fuse/path',
            '/logs/lab3.service-now.com/sdlabpure103-ct1/2017_12_21/2017_12_21', # JIRA: PT-2341
        )
        for invalid_path in invalid_paths:
            with self.assertRaises(TypeError):
                validation_utils.fuse_log_path(invalid_path, TypeError)


class HourTestCase(unittest.TestCase):
    """Unit tests for hour."""

    def test_valid_hour(self):
        """Test valid hours."""
        for hour in range(0, 24):
            self.assertTrue(validation_utils.hour(str(hour)))

    def test_invalid_hour(self):
        """Test invalid hours."""
        bad_hours = (24, )
        for bad_hour in bad_hours:
            with self.assertRaises(ValueError):
                validation_utils.hour(str(bad_hour), ValueError)


class HWIDPathTestCase(unittest.TestCase):
    """Unit tests for hw_id."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.hw_id('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        hw_ids = (
            '(11951019079781516624, 12986023337942797145)',
            '11951019079781516624, 12986023337942797145',
        )
        for hw_id_str in hw_ids:
            msg = 'Fuse Path: "{}" failed validation.'.format(hw_id_str)
            self.assertTrue(validation_utils.hw_id(hw_id_str), msg=msg)

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.hw_id('not-a-valid-id', TypeError)


class JIRATestCase(unittest.TestCase):
    """Unit tests for jira."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.jira('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.jira('ES-1234'))
        self.assertTrue(validation_utils.jira('pure-4'))
        self.assertTrue(validation_utils.jira('CLOUD-1234567'))
        self.assertTrue(validation_utils.jira('fail-12340'))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            validation_utils.jira('es123', TypeError)


class LogDateTestCase(unittest.TestCase):
    """Unit tests for log_date."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.log_date('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.log_date('20181127'))
        self.assertTrue(validation_utils.log_date('20101127'))
        self.assertTrue(validation_utils.log_date('20581127'))
        self.assertTrue(validation_utils.log_date('20161201'))

    def test_invalid_str(self):
        """Test using an invalid str."""
        bad_dates = (
            '19691012',  # Bad year
            '20001301',  # Bad month
            '20181232',  # Bad day
            '20171200',  # Also a bad day value.
        )
        for date in bad_dates:
            msg = 'Log Date "{}" should have raised an error.'.format(date)
            with self.assertRaises(ValueError, msg=msg):
                validation_utils.log_date(date, ValueError)


class MetricTestCase(unittest.TestCase):
    """Unit tests for metric."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.metric('', TypeError)

    def test_valid_str(self):
        """Test using a valid metric defined within the METRIC_INDEX."""
        valid_metrics = (
            'array_name',
            'controller_serial'
        )
        for metric in valid_metrics:
            msg = 'Valid Field "{}" was not found in the METRIC_INDEX.'.format(metric)
            self.assertTrue(validation_utils.metric(metric), msg)

    def test_invalid_str(self):
        """Test using an invalid field."""
        with self.assertRaises(TypeError):
            validation_utils.field('fake_field', TypeError)


class MonthTestCase(unittest.TestCase):
    """Unit tests for month."""

    def test_valid_month(self):
        """Test valid month."""
        month_names = ('jun', 'January', 'Mar', 'APR')
        for month in range(1, 13):
            self.assertTrue(validation_utils.month(str(month)))
        for month_name in month_names:
            self.assertTrue(validation_utils.month(str(month_name)))

    def test_invalid_month(self):
        """Test invalid month."""
        bad_month = (24, 'faketember')
        for bad_month in bad_month:
            with self.assertRaises(ValueError):
                validation_utils.month(str(bad_month), ValueError)


class WWNTestCase(unittest.TestCase):
    """Unit tests for wwn."""

    def test_empty_str(self):
        """Test using an empty string."""
        with self.assertRaises(TypeError):
            validation_utils.wwn('', TypeError)

    def test_valid_str(self):
        """Test using a valid str."""
        self.assertTrue(validation_utils.wwn('10:00:00:00:C9:B7:DD:4B'))
        self.assertTrue(validation_utils.wwn('10:00:00:90:FA:92:B7:58'))
        self.assertTrue(validation_utils.wwn('52:4A:93:70:E1:81:34:01'))
        self.assertTrue(validation_utils.wwn('52:4A:93:70:E1:81:34:13'))

    def test_invalid_str(self):
        """Test using an invalid str."""
        with self.assertRaises(TypeError):
            # Simulate a timestamp... this could be a comment mis-match.
            validation_utils.wwn('10:00:12', TypeError)


class YearTestCase(unittest.TestCase):
    """Unit tests for year."""

    def test_valid_year(self):
        """Test valid year."""
        for year in range(1970, 10000):
            self.assertTrue(validation_utils.year(str(year)))

    def test_invalid_year(self):
        """Test invalid year."""
        bad_year = (1969, 1900)
        for bad_year in bad_year:
            with self.assertRaises(ValueError):
                validation_utils.year(str(bad_year), ValueError)


# Input/Output Validation:
class AcceptsTestCase(unittest.TestCase):
    """Unit tests for the accepts decorator."""

    def test_with_positional_args(self):
        """Test using only 'positional args'."""

        @validation_utils.accepts(types={'val1': int, 'val2': int, 'val3': int})
        def my_funct(val1, val2, val3):
            """For testing purposes."""
            return (val1 * val2) - val3

        with self.assertRaises(TypeError):
            my_funct('string', 'string', 'string')

        expected = -1
        result = my_funct(1, 2, 3)
        self.assertEqual(expected, result)

    def test_with_args(self):
        """Test using only 'args'."""

        @validation_utils.accepts(types={'val1': int, 'val2': int, 'val3': int})
        def my_funct(val1, val2, val3):
            """For testing purposes."""
            return (val1 * val2) - val3

        with self.assertRaises(TypeError):
            my_funct(*['string'] * 3)

        expected = -1
        result = my_funct(*[1, 2, 3])
        self.assertEqual(expected, result)

    def test_with_kwargs(self):
        """Test using only 'keyword args'."""

        @validation_utils.accepts(types={'val1': int, 'val2': int, 'val3': int})
        def my_funct(val1, val2, val3):
            """For testing purposes."""
            return (val1 * val2) - val3

        with self.assertRaises(TypeError):
            my_funct(**{'val1': 'string', 'val2': 'string', 'val3': 'string'})

        expected = -1
        result = my_funct(**{'val1': 1, 'val2': 2, 'val3': 3})
        self.assertEqual(expected, result)

    def test_with_all(self):
        """Test using a combination of positional, args, and kwargs."""

        @validation_utils.accepts(types={'val1': int, 'val2': int, 'val3': int})
        def my_funct(val1, val2, val3):
            """for testing purposes."""
            return (val1 * val2) - val3

        with self.assertRaises(TypeError):
            my_funct('1', *['2'], **{'val3': '3'})

        expected = -1
        result = my_funct(1, *[2], **{'val3': 3})
        self.assertEqual(expected, result)

    def test_argument_length_mismatch(self):
        """The declarations of types doesn't match the function input args length."""

        with self.assertRaises(ValueError):
            # We don't ever use my_funct here, because the decoration will raise a ValueError.
            # pylint: disable=unused-variable
            @validation_utils.accepts(types={'val1': int, 'val2': int, 'val3': int})
            def my_funct(val1):
                """For testing purposes."""
                return val1 * 2

    def test_argument_name_mismatch(self):
        """The declarations of types doesn't match the function input args names."""

        with self.assertRaises(ValueError):
            # We don't ever use my_funct here, because the decoration will raise a ValueError.
            # pylint: disable=unused-variable
            @validation_utils.accepts(types={'val0': int, 'val1': int, 'val2': int})
            def my_funct(val1, val2, val3):
                """For testing purposes."""
                return val1 + val2 + val3
