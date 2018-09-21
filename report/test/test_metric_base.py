"""Unit tests for the metric_base and all of the Metric types."""

import pytest

from photon.lib import config_utils
from photon.report import metric_base

METRIC_INDEX = config_utils.get_metric_index()


@pytest.mark.parametrize('metric_name', METRIC_INDEX.keys())
def test_build_metric(metric_name):
    """Test building all metrics which are listed in the metric_index.ini."""
    assert metric_base.build_metric(metric_name), 'Failed to build metric "{}".'.format(metric_name)


@pytest.mark.parametrize('metric_name', ('fake_metric', 'bad_metric', 'do_you_even_metric_bro'))
def test_fake_metric(metric_name):
    """Test building metrics which don't exist."""
    with pytest.raises(ValueError, msg='Metric "{}" should have failed.'.format(metric_name)):
        metric_base.build_metric(metric_name)
