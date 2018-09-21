"""Unit tests and validation for the table_index.ini configuration file."""

import pytest

from photon.lib import config_utils

METRIC_INDEX = config_utils.get_metric_index()
TABLE_INDEX = config_utils.get_table_index()


@pytest.mark.parametrize('section, options', TABLE_INDEX.items())
def test_templates(section, options):
    # type: (str, dict) -> None
    """Ensure that each table 'template' has valid settings."""
    if section == '__defaults__':
        pass
    assert options, 'Section "{}" has no options.'.format(section)
    for option, value in options.items():
        if value is None or value == '':
            continue
        if option == 'columns':
            for metric in value:
                if metric == '|':
                    continue
                assert metric in METRIC_INDEX, 'Section "{}" had an unknown metric "{}".'.format(section, metric)
        elif value in ('True', 'False'):
            # Detect if a setting needs a type hint.  i.e. 'False'
            msg = 'Section "{}" needs a boolean type hint for {}.'.format(section, option)
            assert value not in ('True', 'False'), msg
        elif isinstance(value, str) and ',' in value:
            # Detect if a setting needs a type hint.  i.e. 'item, item2'
            msg = 'Section "{}" needs a list type hint for {}.'.format(section, option)
            assert ',' not in value, msg
