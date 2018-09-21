"""Base classes and overall helpers for parsers."""
# pylint: disable=unused-import

import collections
import logging

from six import iteritems
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Union
except ImportError:
    pass

from photon.lib import config_utils
from photon.lib import validation_utils

FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]
LOGGER = logging.getLogger(__name__)  # type: logging.Logger


class DataSource(object):
    """The base class for all DataSources."""

    def __init__(self, ident, timeframe, controllers=('CT0', 'CT1')):
        # type: (Any, Any, Tuple[str, str]) -> None
        """
        Arguments:
            ident (array_utils.ArrayIdent): An identity for the array.
            timeframe (time_utils.Timeframe): A time range for information to gather.
            controllers (tuple): One or multiple controllers to use.
        """
        self.controllers = controllers
        self.ident = ident  # type: Any
        self.timeframe = timeframe  # type: Any

    # pylint: disable=unused-argument
    @staticmethod
    def is_available(ident, fields, timeframe):
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
            mapping (dict): A mapping of categories (e.g. 'logs') and data_sources (e.g. 'syslog') and related fields.
                * Example of mapping:
                * {'logs': 'frequentdiagnostics.log': {'ssd_mapped, ...}}}
        """
        mapping = collections.OrderedDict()  # type: collections.OrderedDict
        validate_fields(fields)
        for field in fields:
            # e.g. 'ssd_mapped'
            if field not in FIELD_INDEX:
                msg = 'Field "{}" is not defined in the Information Index.'.format(field)  # type: str
                LOGGER.exception('ValueError: {}'.format(msg))
                raise ValueError(msg)
            field_index = FIELD_INDEX[field]  # type: Dict[str, str]
            for category, data_sources in iteritems(field_index):
                if category not in mapping:
                    # e.g. 'logs'
                    mapping[category] = collections.defaultdict(set)
                for data_source in data_sources:
                    # e.g. 'frequentdiagnostics.log'
                    mapping[category][data_source].add(field)
        return dict(mapping)


class SQLDatabaseDataSource(DataSource):
    """The base class for database connection parsers."""

    # pylint: disable=too-many-arguments
    # All of the arguments are required.
    def __init__(self,
                 ident,             # type: Any
                 timeframe,         # type: Any
                 hostname,          # type: str
                 username,          # type: str
                 password,          # type: str
                 schema             # type: str
                ):                  # type: (...) -> None
        """
        Arguments:
            ident (array_utils.ArrayIdent): An identity for the array.
            timeframe (time_utils.Timeframe): A time range for information to gather.
            hostname (str): The hostname/IP Address used for connecting to the database.
            username (str): The username to use for connecting to the database.
            password (str): The password to use for connecting to the database.
            schema (str): The schema to use within the database connection.
        """
        super(SQLDatabaseDataSource, self).__init__(ident=ident, timeframe=timeframe)
        self.hostname = hostname            # type: str
        self.username = username            # type: str
        self.password = password            # type: str
        self.schema = schema                # type: str
        self._connection = None             # type: Optional[object]

    # pylint: disable=unused-argument
    @staticmethod
    def is_available(ident, fields, timeframe):
        # type: (Any, Optional[List[str]], Optional[Any]) -> bool
        """Confirm if this data source is online and usable."""
        return False

    def get_fields(self, fields):
        # type: (List[str]) -> None
        """Placeholder for required method."""
        raise NotImplementedError('DatabaseDataSource objects require a get_fields method.')

    def get_source_order(self, fields):
        # type: (List[str]) -> None
        """Get the order of sub-sources to use; based upon the timeframe's granularity and requested fields."""
        raise NotImplementedError('DatabaseDataSource objects require a get_source_order method.')


def validate_fields(fields):
    # type: (List[str]) -> None
    """Validate all fields."""
    for field in fields:
        validation_utils.field(field, ValueError)
