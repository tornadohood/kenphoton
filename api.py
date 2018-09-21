"""Simple API for accessing the Photon infrastructure.
See: https://wiki.purestorage.com/pages/viewpage.action?pageId=46827128
"""

import logging
import pandas

from photon.backend.pure.cli import cli_api
from photon.backend.pure.logs import logs_api
from photon.backend.pure.insights import insights_api
from photon.backend.pure.iris import iris_api
from photon.backend.pure.middleware import middleware_api
from photon.backend.pure.mr_tunable import mr_tunable_api
from photon.backend.pure.pure1 import pure1_api
from photon.backend.pure.warehouse import warehouse_api

from photon.lib import array_utils
from photon.lib import config_utils
from photon.lib import pandas_utils
from photon.lib import time_utils
from photon.lib import validation_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple
    from typing import Union
    FIELD_TYPES = Union[Dict, List, str, int, float]
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)  # type: logging.Logger
FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]
SETTINGS = config_utils.get_settings()  # type: Dict[str, Any]
SOURCES = {
    'cli':        cli_api.CLI,
    'logs':       logs_api.Logs,
    'insights':   insights_api.InsightsConnection,
    'iris':       iris_api.IrisConnection,
    'middleware': middleware_api.MiddlewareConnection,
    'mr_tunable': mr_tunable_api.MRTunableConnection,
    'pure1':      pure1_api.Pure1Connection,
    'warehouse':  warehouse_api.WarehouseConnection
}  # type: Dict[str, Any]


class FlashArray(object):
    """A single Pure FlashArray from which to request data."""

    # pylint: disable=too-many-arguments
    # All of these arguments are required for this front-end.
    def __init__(self,
                 fqdn=None,         # type: Optional[str]
                 log_path=None,     # type: Optional[str]
                 files=None,        # type: Optional[List[str]]
                 start=None,        # type: Optional[str]
                 end=None,          # type: Optional[str]
                 granularity=None,  # type: Optional[str]
                 from_latest=None,  # type: Optional[str]
                 **kwargs           # type: **Dict[str, Any]
                ):                  # type: (...) -> None
        """The FlashArray will try to use the current path to identify itself if no other information is given.

        Arguments:
            fqdn (str): A Fully Qualified Domain Name for the array.  i.e. "array_name.domain.com"
            log_path (str): A path to find log files for this array.
            files (list): One or more log files (full paths).
            start (str/datetime/pandas.Timestamp): The start of the time frame to request.
            end (str/datetime/pandas.Timestamp): The end of the time frame to request.
                * The end must be AFTER the start.
            granularity (str): How granular the data should be; Time in Pandas.Timedelta friendly format.
                * Example: '1d' meaning one day.
            from_latest (str): A time delta to use from the latest hour.
                * Example: '1h' meaning the most recent hour.
        """
        # TODO: PT-1152 - Add Support for Array ID and Serial Number.
        self.ident = array_utils.ArrayIdent(fqdn=fqdn, log_path=log_path, files=files)
        self.timeframe = time_utils.generate_timeframe(start, end, granularity, from_latest, self.ident)
        self.parsers = {}
        self.kwargs = kwargs
        LOGGER.debug('FlashArray object created.')

    def __str__(self):
        # type: (...) -> str
        return 'Pure FlashArray <{}>.'.format(self.ident.fqdn if hasattr(self, 'ident') else '')

    def get_data_sources(self, fields):
        # type: (List[str]) -> List[Any]
        """Get the available data sources.

        Arguments:
            fields (list): One or more fields to request.

        Returns:
            A sorted list of available sources which have the requested field(s).
        """
        applicable_sources = set()  # type: Set[str]

        # Get data sources which can supply data for our requested field(s):
        for field in fields:
            # Assume that the field has already been validated:
            field_sources = [src for src, sub_src in FIELD_INDEX[field].items() if sub_src]  # type: List[str]
            for field_source in field_sources:
                source_name = field_source.strip().lower()  # type: str
                # PT-2139 - Temporarily disabling Pure1 manually:
                if source_name == 'pure1':
                    continue
                if SOURCES[source_name].is_available(self.ident, fields, self.timeframe):
                    applicable_sources.add(source_name)

        # Order the sources by their respective priority:
        source_priority = SETTINGS['data_sources']['priority']  # type: List[str]
        # pylint: disable=unnecessary-lambda
        return sorted(list(applicable_sources), key=lambda src_name: source_priority.index(src_name))

    def get_fields(self, fields, data_sources=None, controllers=('CT0', 'CT1')):
        # type: (List[str], Optional[List[str]], Union[Tuple[str, str], Tuple[str]]) -> pandas.DataFrame
        """Get one or more fields from this array within the given time frame.

        Arguments:
            fields (str/list/set/tuple): One or more fields to request from the array.
            data_sources (list/set/tuple): Which source of information to use.
                * Available Sources include:
                    1) logs
                    2) insights
                    3) iris
                    4) middleware
                    5) mr_tunable
                    6) pure1
                    7) warehouse
            controllers (tuple): One or both controllers ('CT0' and/or 'CT1').

        Returns:
            results (dict): Per-controller dictionary containing per-field results.
        """
        completed_fields = set()
        all_results = []
        # Validate that all fields are defined in the FIELD_INDEX.
        for field in fields:
            validation_utils.field(field, ValueError)

        data_sources = data_sources or self.get_data_sources(fields)
        for data_source in data_sources:
            # TODO: Get fields which are available within this data_source ONLY.
            applicable_fields = set(fields) - completed_fields
            if not applicable_fields:
                continue
            if data_source not in self.parsers:
                parser = SOURCES[data_source](ident=self.ident, timeframe=self.timeframe, controllers=controllers)
                self.parsers[data_source] = parser
            elif data_source not in SOURCES:
                error_msg = 'Unknown DataSource "{}" requested.'.format(data_source)
                LOGGER.error(error_msg)
                raise ValueError(error_msg)
            LOGGER.info('Requesting {} fields from the "{}" API.'.format(fields, data_source))
            parser_results = self.parsers[data_source].get_fields(applicable_fields)  # type: pandas.DataFrame
            if 'source' not in parser_results:
                parser_results['source'] = data_source
            for field, series in parser_results.iteritems():
                if field in ('Timestamp', 'source', 'controller'):
                    # These are meta fields.
                    continue
                elif series.dropna().empty:
                    # We have no results for this field, so don't count it as completed.
                    continue
                completed_fields.add(field)
                all_results.append(parser_results[['Timestamp', field, 'source', 'controller']])

        if not all_results:
            merged = pandas.DataFrame()
        else:
            # Merge all of the individual frames back together:
            merged = pandas.concat(all_results)

        # Add placeholders for missing values:
        for field in fields:
            if field not in merged:
                merged[field] = None
        if 'controller' not in merged:
            merged['controller'] = None
        if 'Timestamp' not in merged:
            merged['Timestamp'] = None
        LOGGER.info('Done getting {} fields.'.format(len(completed_fields)))
        return pandas_utils.sort_by_index_and_columns(merged, ['Timestamp'])

    def get_latest_values(self, fields, both_controllers=False):
        # type: (List[str]) -> pandas.DataFrame
        """Get the most recent value for the requested fields.

        Arguments:
            fields (list/set/tuple): One or more field names to fetch the latest value of.
            both_controllers (bool): Return a value for each controller, not just the latest value.

        Returns:
            result (Any): The field's latest value from one or both controllers.
        """
        return pandas_utils.get_latest_values(self.get_fields(fields), fields, both_controllers)

    def get_latest_value(self, field, both_controllers=False):
        # type: (str, bool) -> FIELD_TYPES
        """Get the latest value for the requested field; optionally get a value from both controllers.

        Arguments:
            field (str): The name of the field to fetch.  See the field_index.ini for available fields.
            both_controllers (bool): Return a value for each controller, not just the latest value.

        Returns:
            result (Any): The field's latest value from one or both controllers.
        """
        return pandas_utils.get_latest_value(self.get_fields([field]), field, both_controllers)
