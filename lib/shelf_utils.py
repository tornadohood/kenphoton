"""Utilities for working with Shelf components."""

import logging

from six import itervalues

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import Tuple
except ImportError:
    pass

from photon.lib import drive_utils
from photon.lib import hardware_utils

LOGGER = logging.getLogger(__name__)


def _build_drive_enclosure(enclosure_name, enclosure_handle):
    # type: (str, str) -> Enclosure
    """Build an Enclosure (shelf/chassis) for the given drive instance."""
    if 'SH' in enclosure_name:
        enc_type = Shelf
    elif 'CH' in enclosure_name:
        enc_type = Chassis
    else:
        LOGGER.warning('Unknown enclosure type: {}.  Using base Enclosure type.'.format(enclosure_name))
        enc_type = Enclosure
    return enc_type(enclosure_name, **{'handle': enclosure_handle})


def build_enclosures(drives):
    # type: (Dict[str, Any]) -> Dict[str, Enclosure]
    """Build Enclosures and add Drive instances to them.

    Arguments:
        drives (dict): One or more named drive instances.

    Returns:
        enclosures (dict): One or more Enclosure instances built, based upon the drives.
    """
    enclosures = {}
    for drive in itervalues(drives):
        enclosure_name = drive.location
        enclosure = _build_drive_enclosure(enclosure_name, drive.parent_id)
        if enclosure_name not in enclosures:
            enclosures[enclosure_name] = enclosure

        # Add the drive to the stored enclosure instance.
        enclosures[enclosure_name].add_component(drive)
    return enclosures


class Enclosure(hardware_utils.StorageGroup):
    """The base class for enclosures which house drives.

    Arguments:
        name (str): The bay name of a drive.  i.e. 'SH2'
        kwargs (Keyword Arguments): Additional pass-through arguments.
    """

    def __init__(self, name, **kwargs):
        # type: (str, **Dict[Any]) -> None
        super(Enclosure, self).__init__(name, **kwargs)
        self.kwargs = kwargs
        self._capacity = None
        self.drives = self.components
        LOGGER.debug('Created an Enclosure ({}).'.format(self.name))

    def __str__(self):
        # type: () -> str
        """Return the name and capacity of this enclosure."""
        return 'Enclosure {} ({} drives; {} B).'.format(self.name, len(self.drives), self.capacity)

    @property
    def compatible_components(self):
        # type: () -> Tuple[drive_utils.NVRAM, drive_utils.SSD]
        """A listing of all compatible sub-components that can be added to this group."""
        return drive_utils.NVRAM, drive_utils.SSD


class Chassis(Enclosure):
    """A single chassis containing drives.

    Arguments:
        name (str): The name of the Chassis.  i.e. 'CH2'
        kwargs (Keyword Arguments): Additional pass-through arguments.
    """


class Shelf(Enclosure):
    """A single Shelf containing drives.

    Arguments:
        name (str): The name of the Shelf.  i.e. 'SH2'
        kwargs (Keyword Arguments): Additional pass-through arguments.
    """
