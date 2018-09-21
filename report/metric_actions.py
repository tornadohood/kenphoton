"""Unit tests for metric_actions."""

from photon.lib import format_utils


def calculate_raw_unaccounted(row):
    # type: (Any) -> Any
    """Helper to calculate raw Unaccounted Space."""
    return format_utils.zero(row['unreported_space'] - row['reclaimable_space'] - row['reported_pyramid'])


def scale_unaccounted_space(row):
    # type: (Any) -> Any
    """Helper to convert raw Unaccounted space to human readable."""
    return format_utils.auto_scale(row['Unaccounted Raw'], 'binary_bytes')


def format_unreported_ratio(row):
    # type: (Any) -> Any
    """Helper to format a value as a ratio."""
    return '{:.2f}:1'.format(row['unreported_ratio'])
