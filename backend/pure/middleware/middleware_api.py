"""Contains the Middleware Connection API for pulling values from Middleware."""

import logging

from photon.backend.pure import SQLDatabaseDataSource
from photon.lib import config_utils

LOGGER = logging.getLogger(__name__)
FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]


# pylint: disable=abstract-method
# This is not yet implemented:
# TODO: PT-828 - Middleware Integration.
class MiddlewareConnection(SQLDatabaseDataSource):
    """Placeholder."""
    pass
