"""Base Metric forms.

Wiki Page: https://wiki.purestorage.com/display/SDT/Photon%3A+Report+API+Overview
"""

import logging
import numpy

from photon.lib import config_utils
from photon.lib import format_utils
from photon.lib import pandas_utils
from photon.lib import math_utils
from photon.lib import time_utils
from photon.report import metric_actions

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass


LOGGER = logging.getLogger(__name__)
METRIC_INDEX = config_utils.get_metric_index()


class Metric(object):
    """Base class for required metric fields."""
    # Attributes are dynamically applied via the _apply_defaults() method.  Pylint gets confused...
    # pylint: disable=no-member, access-member-before-definition

    def __init__(self,
                 field,                     # type: str
                 nice_name=None,            # type: Optional[str]
                 required_fields=None,      # type: Optional[List[str]]
                 required_metrics=None,     # type: Optional[List[str]]
                 defaults=None,             # type: Optional[Dict[str, Any]]
                 **kwargs                   # type: **Dict[str, Any]
                 ):                         # type: (...) -> None
        """Setup for creating a Metric.

        Arguments:
            field (str): The name of the field being created.
                NOTE: For single field Metrics, the required_fields arg is not needed. Refer to the
                field_index.ini for valid field names.
            nice_name (str): Human readable name. (eg. 'SSD Mapped')
                NOTE: If not set, the field name will be used (eg. 'ssd_mapped' -> 'SSD Mapped').
            required_fields (List[str]): The fields needed to create the Metric.
                NOTE: Used to tell the FlashArray object what fields to pull. Only be used when more
                than one field is needed from the FlashArray. (See the 'field' arg)
            required_metrics (List[str]): The metrics needed to create this Metric.
            operation (str): The operation to perform in order to generate the Metric.
                'avg' - Values like ssd_mapped. These should be forward or back filled via averages (mean).
                'event'  - A unique timeline event. These should not be forward or back filled.
                'last' - Just get the most recent applicable value.  This can be back filled and forward filled.
                'std' - The Standard Deviation of a value.
                'sum' - An value which needs to be aggregated/totaled.
                'value_counts' - An event which simply needs to be counted.
            defaults (dict): Used to apply against the default attributes from kwargs.

        Optional Keyword Arguments:
            base_unit (str): The base unit of latency (raw unit).
            controller (str): Which controllers to use: 'CT0' or 'CT1'.  Otherwise, this uses both.
            fill (bool): The metric should be forward/back filled.
            nested_fields (list): One or more fields which need to be unpacked.
            placeholder (str/int/float): A placeholder to use when we have no/missing data.
            required_metrics (list): One or more metrics which are needed in order to build this metric.
            sub_tables (list): Which keys to create sub-tables for.  i.e. which hosts or volumes.
        """
        self._apply_defaults()
        self.field = field
        self.nice_name = nice_name or format_utils.make_title(field)
        self.required_fields = required_fields or []
        self.required_fields.append(field)
        # If we do not have the field itself in required_fields, add it.
        self.required_metrics = required_metrics or []
        # Some metrics require other metrics to work, make sure we have all of their required fields/metrics too.
        self._get_required_fields()
        # Ensured these are unique.
        self.required_fields = list(set(self.required_fields))
        self.required_metrics = list(set(self.required_metrics))

        if defaults:
            # Apply Metric specific defaults to attributes.
            for key, value in defaults.items():
                setattr(self, key, value)
        # Apply all of the kwargs to override defaults.
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Update the nice_name if this metric is just for one controller.
        if self.controller:
            # Prefix the nice_name with the controller name.
            # e.g. 'CT0 SSD mapped'
            self.nice_name = ' '.join([self.controller, self.nice_name])

    def __str__(self):
        # type: () -> str
        # Example: 'ScaledUnitsMetric: SSD Capacity'
        return '{}: {}'.format(self.__class__.__name__, self.nice_name)

    def _apply_defaults(self):
        # type: () -> None
        """If we don't have an attribute set, then set one with the default setting."""
        # CAVEAT: We need these defaults here and not in the INI.  Otherwise we override class specific defaults.
        defaults = {
            'alignment': 'auto',
            'base_unit': 'milliseconds',
            'controller': None,
            'denominator': None,
            'display_unit': None,
            'dtype': None,
            'fill': True,
            'nested_fields': [],
            'numerator': None,
            'operation': 'last',
            'placeholder': '-',
            'precision': 2,
            'scale': None,
            'sub_tables': [],
        }
        for attr, value in defaults.items():
            if not hasattr(self, attr):
                setattr(self, attr, value)

    def _get_required_fields(self):
        # type: () -> None
        """Get needed fields from required_metrics."""
        for needed_metric in self.required_metrics:
            self.required_fields.extend(build_metric(needed_metric).required_fields)

    def _fill(self, frame, frequency):
        # type: (Any, str) -> Any
        """Fill missing and infer values for metrics for a consistent output."""
        if self.fill:
            frame = frame.ffill().bfill()
        resampler = pandas_utils.resample_frame(frame, frequency)
        if self.operation == 'avg':
            self.operation = 'mean'
        if not hasattr(resampler, self.operation):
            error_msg = 'The resampling operation "{}" is not defined.'.format(self.operation)
            LOGGER.error(error_msg)
            raise ValueError(error_msg)
        # PT-2128 - If we have all None/nan for a required numerical field, then we will fail to do any aggregation.
        frame = getattr(resampler, self.operation)()
        frame['Timestamp'] = frame.index
        frame.reset_index(drop=True, inplace=True)
        return frame

    def process(self, frame, frequency):
        # type: (Any, str) -> Any
        """Return original DataFrame as it already the requested field as a column.

        Arguments:
            frame (pandas.DataFrame): The dataset required to process this metric.
            frequency (str): The frequency to apply when resampling the dataset.

        Returns:
            frame (pandas.DataFrame): The same frame, but with only the new Metric.nice_name column.
        """
        if self.controller:
            # Only get rows where the 'controller' value is equal to the requested controller.
            frame = frame[frame['controller'] == self.controller]

        # Fill in missing values via the given operation method.
        if self.operation != 'event':
            frame = self._fill(frame, frequency)

        if hasattr(self, '_action') and not frame.empty:
            frame[self.nice_name] = frame.apply(getattr(self, '_action'), axis=1)
        else:
            frame[self.nice_name] = frame[self.field]

        # Enforce dtype if applicable:
        if self.dtype:
            frame[self.nice_name] = frame[self.nice_name].astype(self.dtype)

        # Add a placeholder for controller as this may have been removed during resampling.
        frame['controller'] = self.controller

        # Only return columns related to the newly created metric.
        return frame[['Timestamp', 'controller', self.nice_name]]


class EventMetric(Metric):
    """Base Metric for single Text fields which are unique and must all be kept."""

    def __init__(self, field, **kwargs):
        # type: (str, **Dict[str, Any]) -> None
        """Setup for creating an EventMetric.

        Arguments:
            field (str): A field from the field_index.
        """
        defaults = {
            'alignment': 'left',
            'fill': False,
            'operation': 'event',
        }
        super(EventMetric, self).__init__(field, defaults=defaults, **kwargs)


class LatencyMetric(Metric):
    """Base Metric for latency metrics which uses time_utils.Timedelta."""

    def __init__(self,
                 field,                         # type: str
                 base_unit='milliseconds',      # type: str
                 display_unit=None,             # type: Optional[str]
                 precision=2,                   # type: int
                 **kwargs                       # type: **Dict[str, Any]
                ):                              # type: (...) -> None
        """Setup for creating a LatencyMetric.

        Arguments:
            field (str): A field from the field_index.
            base_unit (str): The unit the raw data is in.
            display_unit (str): A unit to statically set to (otherwise it auto-scales).
            precision (int): How many values after the decimal point to preserve.
        """
        defaults = {
            'alignment': 'right',
            'fill': True,
            'operation': 'mean',
            'placeholder': '0.00 ms'
        }
        # Changing the name so that we do not overwrite the columns with raw data.
        super(LatencyMetric, self).__init__(field, defaults=defaults, **kwargs)
        self.base_unit = base_unit
        self.display_unit = display_unit
        self.precision = precision

    def _action(self, row):
        # type: (Any) -> str
        """Action to perform on each row in the column."""
        raw_value = row[self.field]
        if numpy.isnan(float(raw_value)):
            scaled = '-'
        else:
            scaled = time_utils.scale_latency(value=raw_value, base_unit=self.base_unit,
                                              display_unit=self.display_unit, precision=self.precision)
        return scaled


class PercentageMetric(Metric):
    """Base Metric for single field metrics using format_utils.percentage()."""

    def __init__(self,
                 field,                     # type: str
                 numerator,                 # type: str
                 denominator,               # type: str
                 **kwargs                   # type: **Dict[str, Any]
                ):                          # type: (...) -> None
        """Setup for creating a PercentageMetric.

        Arguments:
            field (str): A field from the field_index.
            numerator (str): The column name to be divided.
            denominator (str): The column name doing the dividing.
        """
        defaults = {
            'alignment': 'right',
            'fill': True,
            'operation': 'mean',
            'placeholder': '0.00%',
        }
        super(PercentageMetric, self).__init__(field, defaults=defaults, **kwargs)
        self.numerator = numerator
        self.denominator = denominator

    def _action(self, row):
        # type: (Any) -> str
        """Action to perform on each row in the column."""
        return format_utils.percentage(math_utils.safe_divide(row[self.numerator], row[self.denominator]))


class ScaledUnitsMetric(Metric):
    """Base Metric for single field metrics using format_utils.auto_scale()."""

    def __init__(self,
                 field,                     # type: str
                 scale,                     # type: str
                 **kwargs                   # type: **Dict[str, Any]
                ):                          # type: (...) -> None
        """Setup for creating a ScaledUnitsMetric.

        Arguments:
            field (str): A field from the field_index.
            scale (str): Refer to format_utils.UNIT_SCALES.keys() for available scales.
        """
        defaults = {
            'alignment': 'right',
            'fill': True,
            'operation': 'mean',
            'placeholder': '0.00 B',
        }
        super(ScaledUnitsMetric, self).__init__(field, defaults=defaults, **kwargs)
        if scale not in format_utils.UNIT_SCALES:
            msg = 'Scale "{}" does not exist.  Options include "{}".'.format(scale, ', '.join(format_utils.UNIT_SCALES))
            LOGGER.error(msg)
            raise ValueError(msg)
        self.scale = scale

    def _action(self, row):
        # type: (Any) -> str
        """Action to perform on each row in the column."""
        return format_utils.auto_scale(row[self.field], self.scale)


class TextMetric(Metric):
    """Base Metric for single Text fields that are part of the series."""

    def __init__(self, field, **kwargs):
        # type: (str, **Dict[str, Any]) -> None
        """Setup for creating a TextMetric.

        Arguments:
            field (str): A field from the field_index.
        """
        defaults = {
            'alignment': 'left',
            'fill': True,
            'operation': 'last'
        }
        super(TextMetric, self).__init__(field, defaults=defaults, **kwargs)


def build_metric(metric_name, **metric_kwargs):
    # type: (str, **Dict[str, Any]) -> Metric
    """Helper to validate and then build a metric based upon its name.

    Arguments:
        metric_name (str): The name of a single metric to build.
            Note: The available metrics are listed in the metric_index.ini file.

    Returns:
        metric (Metric): A Metric instance based upon the name and parameters given.
    """
    metric_config, action, metric_cls = _build_metric_config(metric_name, **metric_kwargs)
    metric = metric_cls(**metric_config)
    if action:
        # If we have a custom action, apply it to the metric instance.
        setattr(metric, '_action', getattr(metric_actions, action))
    return metric


def _build_metric_config(metric_name, **kwargs):
    # type: (str, **Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str], Metric]
    """Generate the metric's configuration based upon name and any override keyword arguments."""
    metric_types = {key: value for key, value in globals().items() if 'Metric' in key}
    # Validate that the requested metric exists.
    if metric_name not in METRIC_INDEX:
        msg = 'Metric "{}" does not exist.'.format(metric_name)
        LOGGER.error(msg)
        raise ValueError(msg)

    # Fetch the configuration for this metric.
    metric_config = METRIC_INDEX[metric_name]
    metric_config.update(kwargs)

    # Validate that the requested metric_type exists.
    metric_type = metric_config.get('metric_type', 'Metric')
    if not metric_type or metric_type not in metric_types:
        msg = 'Unknown metric type "{}" was requested.'.format(metric_type)
        raise TypeError(msg)
    metric_cls = metric_types[metric_type]

    # Clean up the metric_config.
    # Exclude 'metric_type' and 'action' as these are used to pick the metric class and action to use.
    action = metric_config.get('action')
    ignore = ('metric_type', 'action')
    metric_config = {key: value for key, value in metric_config.items() if value != '' and key not in ignore}

    # Use the metric_name as the field name, if an explicit field is not set.
    metric_config['field'] = metric_config.get('field', metric_name)

    # Nice name is dynamically generated from the field name, if it is not explicitly given.
    metric_config['nice_name'] = metric_config.get('nice_name', format_utils.make_title(metric_config['field']))
    return metric_config, action, metric_cls
