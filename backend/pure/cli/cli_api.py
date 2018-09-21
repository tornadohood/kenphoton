"""Contains the Purity CLI API for pulling values from the CLI."""

import logging

from photon.backend.pure import DataSource
from photon.lib import config_utils

LOGGER = logging.getLogger(__name__)
FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]


# pylint: disable=abstract-method
# This is not yet implemented:
class CLI(DataSource):
    """Placeholder."""
    pass
