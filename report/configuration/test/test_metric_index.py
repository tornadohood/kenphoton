"""Validate the contents of the metric_index.ini file."""

import pytest

from photon.lib import config_utils
from photon.lib import format_utils
from photon.report import metric_actions

FIELD_INDEX = config_utils.get_field_index()
METRIC_INDEX = config_utils.get_metric_index()
METRIC_TYPES = {'Metric': [], 'FieldMetric': [], 'TextMetric': [], 'EventMetric': [], 'LatencyMetric': [],
                'PercentageMetric': ['numerator', 'denominator'], 'ScaledUnitsMetric': ['scale']}
OPERATIONS = ('avg', 'event', 'value_counts', 'sum', 'std', 'last', 'min', 'max')


@pytest.mark.parametrize('section, options', METRIC_INDEX.items())
def test_metrics(section, options):
    # type: (str, dict) -> None
    """Ensure that each 'metric' has valid settings."""
    if section == '__defaults__':
        pass
    assert options, 'Section "{}" has no options.'.format(section)
    for option, value in options.items():
        if value is None or value == '':
            continue
        if option == 'metric_type':
            msg = 'Unknown metric type "{}" was given.'
            metric_type = value
            assert metric_type in METRIC_TYPES, msg.format(metric_type)
            # Ensure that each required option has a value (based upon metric_type).
            needed_options = METRIC_TYPES[metric_type]
            msg = '{} is missing required options.'.format(section)
            assert all([opt in options for opt in needed_options]), msg
            assert all([options[opt] for opt in needed_options]), msg
        elif option in ('numerator', 'denominator', 'field'):
            field = value
            msg = 'Metric "{}" is requesting an unknown field/metric "{}".'.format(section, field)
            assert field in FIELD_INDEX or field in METRIC_INDEX, msg
            # Ensure that each of these fields is in the required_fields or required_metrics.
            msg = '{} is missing required field "{}".'.format(section, field)
            required = options.get('required_fields', []) + options.get('required_metrics', [])
            assert field in required, msg
        elif option in ('nested_fields', 'required_fields'):
            if isinstance(value, str):
                value = [value]
            for field in value:
                msg = 'Metric "{}" has an unknown required_field "{}".'.format(section, field)
                assert field in FIELD_INDEX, msg
        elif option == 'required_metrics':
            if isinstance(value, str):
                value = [value]
            for metric in value:
                msg = 'Metric "{}" has an unknown required_metric "{}".'.format(section, metric)
                assert metric in METRIC_INDEX, msg
        elif option == 'operation':
            operation = value
            if operation:
                msg = 'Unknown operation "{}" was requested.'.format(operation)
                assert operation in OPERATIONS, msg
        elif option == 'scale':
            scale = value
            if scale:
                msg = 'Unknown scale "{}" was requested.'.format(scale)
                assert scale in format_utils.UNIT_SCALES, msg
        elif option == 'action':
            action = value  # type: str
            if action:
                assert hasattr(metric_actions, action), 'Metric action "{}" does not exist.'.format(action)
        elif option == 'fill':
            fill = value
            msg = 'Unknown argument for fill: "{}"; expected True or False.'.format(fill)
            assert isinstance(fill, bool), msg
        elif value in ('True', 'False'):
            # Detect if a setting needs a type hint.  i.e. 'False' without 'type: bool'
            msg = 'Section "{}" needs a boolean type hint for {}.'.format(section, option)
            assert value not in ('True', 'False'), msg
        elif isinstance(value, str) and ',' in value:
            # Detect if a setting needs a type hint.  i.e. 'item, item2'
            msg = 'Section "{}" needs a list type hint for {}.'.format(section, option)
            assert ',' not in value, msg
