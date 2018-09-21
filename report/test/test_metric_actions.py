"""Unit tests for metric_actions."""

import pandas
import pytest

from photon.report import metric_actions


@pytest.mark.parametrize('row, expected', [
    (pandas.Series({'unreported_space': 0, 'reclaimable_space': 1, 'reported_pyramid': 2}), 0),
    (pandas.Series({'unreported_space': 10, 'reclaimable_space': 1, 'reported_pyramid': 2}), 7),
    (pandas.Series({'unreported_space': 0, 'reclaimable_space': 0, 'reported_pyramid': 2}), 0),
])
def test_calculate_raw_unaccounted(row, expected):
    """Unit tests for calculate_raw_unaccounted."""
    result = metric_actions.calculate_raw_unaccounted(row)
    assert result == expected


@pytest.mark.parametrize('row, expected', [
    (pandas.Series({'Unaccounted Raw': 10000}), '9.77 KiB'),
    (pandas.Series({'Unaccounted Raw': 20000}), '19.53 KiB'),
    (pandas.Series({'Unaccounted Raw': 30000}), '29.30 KiB'),
])
def test_scale_unaccounted_space(row, expected):
    """Unit tests for scale_unaccounted_space."""
    result = metric_actions.scale_unaccounted_space(row)
    assert result == expected


@pytest.mark.parametrize('row, expected', [
    (pandas.Series({'unreported_ratio': 0.8}), '0.80:1'),
    (pandas.Series({'unreported_ratio': 20.3523}), '20.35:1'),
    (pandas.Series({'unreported_ratio': 0.12823}), '0.13:1'),
])
def test_format_unreported_ratio(row, expected):
    """Unit tests for format_unreported_ratio."""
    result = metric_actions.format_unreported_ratio(row)
    assert result == expected
