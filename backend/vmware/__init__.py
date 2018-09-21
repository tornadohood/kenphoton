"""Base classes and overall helpers for parsers."""

import collections
import logging

from six import iteritems

# pylint: disable=unused-argument
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Union
except ImportError:
    pass

from photon.lib import config_utils

VMWARE_INDEX = config_utils.get_vmware_index()  # type: Dict[str, Any]
LOGGER = logging.getLogger(__name__)  # type: logging.Logger


class DataSource(object):
    "The base class for all Datasources."

    def __init__(self, ident, timeframe=None):
        # type: (Any, Any) -> None
        """
        Arguments:
            ident: An identity for the ESXi Host.
            timeframe (time_utils.Timeframe): An optional time range for information to gather.
        """
        self.ident = ident  # type: str
        self.timeframe = timeframe  # type: Any

    @staticmethod
    def is_available(ident, fields):
        # type: (Any, Optional[List[str]], Optional[Any]) -> bool
        """Confirm if this data source is online and usable."""
        return False

    def get_fields(self, fields):
        # type: (List[str]) -> Optional[Union[str, Dict[str, Any]]]
        """Placeholder for required method."""
        raise NotImplementedError('DataSource objects require a get_fields method.')

    def get_source_order(self, fields):
        # type: (List[str]) -> None
        """Get the order of sub-sources to use; based upon the timeframe's granularity and requested fields."""
        raise NotImplementedError('DataSource objects require a get_source_order method.')

    @staticmethod
    def map_fields_to_sources(fields):
        # type: (List[str]) -> Dict[str, Any]
        """Map which fields need which data_sources; so we can get all applicable fields from a data_source at once.

        Arguments:
            fields (list/set/tuple): One or more fields to map to data_sources.

        Returns:
            mapping (dict): A mapping of categories (e.g. 'esxlogs') and data_sources (e.g. 'esxconf') and related fields.
                * Example of mapping:
                * {'esxlogs': 'esxconf': {'ats_offload, ...}}}
        """
        mapping = {}  # type: Dict
        for field in fields:
            # e.g. 'ats_offload'
            if field not in VMWARE_INDEX:
                msg = 'Field "{}" is not defined in the Information Index.'.format(field)  # type: str
                LOGGER.exception('ValueError: {}'.format(msg))
                raise ValueError(msg)
            field_index = VMWARE_INDEX[field]  # type: Dict[str, str]
            for category, data_sources in iteritems(field_index):
                if category not in mapping:
                    # e.g. 'esxlogs'
                    mapping[category] = collections.defaultdict(set)
                for data_source in data_sources:
                    # e.g. 'esxconf'
                    mapping[category][data_source].add(field)
        return dict(mapping)
