"""Utilities for working with Apartments."""

import logging
import re

from six import itervalues

from photon.lib import drive_utils
from photon.lib import hardware_utils
from photon.lib import validation_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Type
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


def _build_subslot_data_pack(index, drive, drives):
    # type: (int, drive_utils.Drive, Dict[str, drive_utils.Drive]) -> Optional[DataPack]
    """Build a Data Pack for the given drive instance.

    Arguments:
        index (int): The index to include in the DataPack name.
        drive (drive_utils.Drive): A single drive instance.
        drives (dict): All of the known drive instances.

    Return:
        data_pack (DataPack): A single DataPack instance.
    """
    # Get information about the "peer" drive that shares this subslot/bay.
    # Shelves can enumerate subslots as 0,1 or 1,2.
    data_pack = None
    options = ['0', '1', '2']
    options.remove(str(drive.subslot))
    for option in options:
        peer_name = re.sub(r'SUBSLOT\d+', 'SUBSLOT{}'.format(option), drive.full_name)  # type:  str
        dpack_name = 'DataPack{}'.format(index)
        slot_partner = drives.get(peer_name)  # type: Optional[drive_utils.Drive]
        if not slot_partner:
            continue
        peer_wgroup = slot_partner.write_group  # type: str
        if drive.write_group == peer_wgroup:
            # This may be an indication of malformed WriteGroup.
            msg = 'Write Groups must be different for sub-slots in the same bay.  {} may be malformed.'
            LOGGER.warning(msg.format(drive.write_group))
        data_pack = DataPack(dpack_name, [drive.write_group, peer_wgroup])  # type: Optional[DataPack]
        break
    return data_pack


def build_apartments(drives, write_groups):
    # type: (Dict[str, drive_utils.Drive], Dict[str, WriteGroup]) -> Dict[str, WriteGroup]
    """Build Apartment Instances and add WriteGroups to them.

    Arguments:
        drives (dict): One or more named Drive/SSD/NVRAM Instances.
        write_groups (dict): One or more named WriteGroup Instances.

    Returns:
        apartments (dict): One or more named Apartments containing WriteGroups (which contain Drives).
    """
    apartments = {}  # type: Dict[str, Apartment]
    for drive in itervalues(drives):
        apt_id = drive.apartment_id  # type: str
        if apt_id not in apartments:
            apartments[apt_id] = Apartment(apt_id)

    # Add the WriteGroups to their respective Apartment.
    for write_group in itervalues(write_groups):
        apt_id = write_group.apartment_id
        apartments[apt_id].add_component(write_group)
    return apartments


def build_data_packs(drives, write_groups):
    # type: (Dict[str, drive_utils.Drive], Dict[str, WriteGroup]) -> Dict[str, DataPack]
    """Build data packs from all of the known drive instances.

    Arguments:
        drives (dict): All of the current drive_utils.SSD instances.
        write_groups (dict): All of the WriteGroups instances.

    Returns:
        data_packs (dict): All of the DataPacks objects (without WriteGroups).
    """
    data_packs = {}  # type: Dict[str, DataPack]
    for drive in itervalues(drives):
        # Just name the DataPack generically for reference.
        # Increase the data pack index (name) based upon the number of packs currently in data_packs.
        # i.e. "DataPack0"
        index = len(data_packs)  # type: int
        if not drive.subslot:
            # PT-1921 - This is a pack which only spans a single write group:
            pack = DataPack(drive.full_name, write_group_names=[drive.write_group])  # type: Optional[DataPack]
        else:
            pack = _build_subslot_data_pack(index, drive, drives)  # type: Optional[DataPack]
        if not pack:
            continue
        if pack.name not in data_packs:
            data_packs[pack.name] = pack

    # Add WriteGroups to DataPacks:
    for data_pack in itervalues(data_packs):
        for write_group in data_pack.write_group_names:
            data_pack.add_component(write_groups[write_group])
    return data_packs


def build_write_groups(drives):
    # type: (Dict[str, drive_utils.Drive]) -> Dict[str, WriteGroup]
    """Build all WriteGroups based upon Drive instances; add all Drives to WriteGroups.

    Arguments:
        drives (dict): One or more named drive_utils.Drives/SSD/NVRAM Instances.

    Returns:
        write_groups (dict): One or more WriteGroups (with drives added) based upon the group_id of each drive.
    """
    write_groups = {}  # type: Dict[str, WriteGroup]
    for drive in itervalues(drives):
        apt_id = drive.apartment_id  # type: str
        wgroup = drive.write_group  # type: str
        if wgroup not in write_groups:
            write_groups[wgroup] = WriteGroup(wgroup, apartment_id=apt_id)

        # Add the drive to its respective WriteGroup.
        write_groups[wgroup].add_component(drive)
    return write_groups


def in_apartment(device_id, apartment):
    # type: (str, Apartment) -> Optional[str]
    """Return the full name of the drive if the device exists in the apartment.

    Arguments:
        device_id (str):  A device ID like: '3318688885924402965, 13833487721375652852'.
        apartment (Apartment):  An apartment to check.

    Returns:
        full_name (str):  The full name of the drive if it is found in the Apartment.
    """
    # TODO: Replace this with something more generic to check if a device is within a StorageGroup.
    full_name = None  # type: Optional[str]
    for write_group in apartment.components.values():
        for drive in write_group.drives.values():
            if drive.device_id == device_id:
                full_name = drive.full_name
                break
        if full_name:
            break
    return full_name


class Apartment(hardware_utils.StorageGroup):
    """A single Apartment of Write Groups."""

    def __init__(self, apartment_id, **kwargs):
        # type: (str, Any) -> None
        """
        Arguments:
            apartment_id (str): The Apartment ID.
        """
        apartment_id = validation_utils.hw_id(apartment_id)
        super(Apartment, self).__init__(name=apartment_id, **kwargs)
        self._capacity = None  # type: Optional[int]
        self.write_groups = self.components  # type: Dict[str, WriteGroup]
        LOGGER.debug('Created an Apartment ({}).'.format(self.name))

    def __str__(self):
        # type: () -> str
        return 'Apartment {} ({} write groups; {} B)'.format(self.name, len(self.write_groups), self.capacity)

    @property
    def compatible_components(self):
        # type: () -> Type[WriteGroup]
        """A listing of all compatible sub-components that can be added to this group."""
        return WriteGroup


class DataPack(hardware_utils.StorageGroup):
    """A Data pack containing multiple drives."""

    def __init__(self, name, write_group_names, **kwargs):
        # type: (str, List[str], Any) -> None
        """
        Arguments:
            name (str): The name of a drive within the data pack; used to identify this grouping.
            write_group_names (list/set/tuple): One or more WriteGroups associated with this Data Pack.
        """
        super(DataPack, self).__init__(name, **kwargs)
        self.write_group_names = write_group_names  # type: List[str]
        self.write_groups = self.components  # type: Dict[str, WriteGroup]
        LOGGER.debug('Created a Data Pack ({}).'.format(self.name))

    def __str__(self):
        # type: (...) -> str
        return 'DataPack {} ({} B).'.format(self.name, self.capacity)

    @property
    def compatible_components(self):
        # type: (...) -> Type[WriteGroup]
        """A listing of all compatible sub-components that can be added to this group."""
        return WriteGroup


class WriteGroup(hardware_utils.StorageGroup):
    """A Single Write Group of drives."""

    def __init__(self, write_group_id, **kwargs):  # type: (str, Any) -> None
        """
        Arguments:
            write_group_id (str): The Write Group ID.
        """
        write_group_id = validation_utils.hw_id(write_group_id)
        super(WriteGroup, self).__init__(write_group_id, **kwargs)
        self._capacity = None  # type: Optional[int]
        self.drives = self.components  # type: Dict[str, drive_utils.Drive]
        LOGGER.debug('Created a WriteGroup ({}).'.format(self.name))

    def __str__(self):
        # type: (...) -> str
        return 'Write Group "{}" ({} drives; {} B)'.format(self.name, len(self.drives), self.capacity)

    @property
    def compatible_components(self):
        # type: (...) -> Tuple[Type[drive_utils.NVRAM], Type[drive_utils.SSD]]
        """A listing of all compatible sub-components that can be added to this group."""
        return drive_utils.NVRAM, drive_utils.SSD
