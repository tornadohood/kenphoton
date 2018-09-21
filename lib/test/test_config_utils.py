"""Unit tests for lib/config_utils."""

import os
import pytest

from photon.lib import config_utils
from photon.lib import test_utils

PATH = os.path.dirname(__file__)


@pytest.mark.parametrize('filename', test_utils.get_files_of_type('Uncategorized/*.ini'))
def test_parse_ini_files(filename):
    """Test parsing INI file types."""
    results = {
        'bad_config.ini': None,
        'empty_config.ini': None,
        'simple_config.ini': {'test-header': {'content': ['item1', 'item2', 'item3'], 'content2': 'item4'}},
    }
    expected = results.get(os.path.basename(filename))
    if expected:
        result = config_utils.get_config(filename)
        assert result == expected


@pytest.mark.parametrize('getter', ('get_field_index', 'get_vmware_index'))
def test_get_field_index(getter):
    """Ensure we return a dict."""
    assert hasattr(config_utils, getter), 'config_utils does not have a "{}" function.'.format(getter)
    index = getattr(config_utils, getter)()
    assert index, '{} returned an empty index.'.format(getter)
    assert isinstance(index, dict), '{} returned an unexpected type: "{}".'.format(getter, type(index))
