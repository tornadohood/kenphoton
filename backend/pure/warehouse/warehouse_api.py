"""Contains the Warehouse Connection API for pulling values from the Data Warehouse Database."""

import logging

from photon.backend.pure import SQLDatabaseDataSource
from photon.lib import config_utils

LOGGER = logging.getLogger(__name__)
FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]


# pylint: disable=abstract-method
# This is not yet implemented:
# TODO: PT-1002/PT-1315 - Database connectivity.
class WarehouseConnection(SQLDatabaseDataSource):
    """Placeholder."""
    pass
