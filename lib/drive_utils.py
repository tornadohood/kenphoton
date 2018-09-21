"""Utilities for working with Drive components."""

import logging
import re

from photon.lib import format_utils
from photon.lib import hardware_utils
from photon.lib import report_utils
from photon.lib import validation_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Type
    from typing import Union
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


def _make_subslot_peer_name(drive_name):
    # type: (str) -> str
    """Make the peer subslot name based upon the current drive name."""
    if drive_name[-1] == '1':
        subslot = '0'  # type: str
    else:
        subslot = '1'
    # Remove the old subslot: 'SH0.BAY11.SUBSLOT' -> 'SH0.BAY11.SUBSLOT'; then add the new subslot: 'SH0.BAY11.SUBSLOT'
    return drive_name[:-1] + subslot


def _parse_dev_info(handle, dev_info_data):
    # type: (str, List[Dict[str, Any]]) -> Dict[str, Any]
    """Parse dev_info contents and return the drive info which matches the requested drive."""
    parsed = {}
    for dev_info in dev_info_data:
        # Match puredb_list_drives.handle to dev_info.name:
        if dev_info['name'] == handle:
            parsed['dm'] = dev_info['dm']
            parsed['write_group'] = dev_info['grp']
            parsed['parent_id'] = dev_info['encl']
            parsed['device_id'] = dev_info['dev']
            parsed['apartment_id'] = dev_info['apt']
            parsed['wwn'] = dev_info['wwn']
            break

    if not parsed:
        error_msg = '"{}" was not found in dev_info.  Was this device recently added/removed?'.format(handle)
        LOGGER.error(error_msg)
        # Removed the exception here, because this is a common issue which we should report, but not raise.
        # This can happen when a drive is in a 'failed' or 'unknown' state.
    return parsed


def _sort_helper(full_name):
    # type: (str) -> Tuple[int, int]
    """Return the drive bay number and subslot number as a tuple.

    Example of input:
    CH0.BAY11.SUBSLOT; this would return (11, 1).
    These drive should already be part of the same enclosure; so we discard encl number in the sort.
    """
    spl_name = full_name.split('.')  # type: List[str]
    # BAY0 -> 0, SUBSLOT1 -> 1
    if len(spl_name) == 3:
        result = (int(spl_name[1][3:]), int(spl_name[2][7:]))
    else:
        # Put a placeholder of 0 for the subslot.
        result = (int(spl_name[1][3:]), 0)
    return result


def build_drive_map(drives):
    # type: (Dict[str, Drive]) -> str
    """Build a visual mapping of drives within the group.

    Arguments:
        drives (dict): One or more named Drive instances.

    Returns:
        report (str): A TextTable formatted string of drives and values related to each drive.
    """
    lines = [
        ['Name', 'Status', 'Capacity', 'Model', 'Serial Number']
    ]  # type: List[List[Union[int, str]]]

    for full_name in sorted(drives, key=_sort_helper):
        drive = drives[full_name]  # type: Drive

        capacity = format_utils.auto_scale(drive.capacity, 'binary_bytes')  # type: Union[int, str]
        if not drive.available:
            capacity = '-'
            drive.model = '-'
            drive.serial_number = '-'
        elif drive.degraded:
            capacity = '-'
        drive.model = drive.model or '-'
        drive.serial_number = drive.serial_number or '-'
        lines.append([drive.full_name, drive.status, capacity, drive.model, drive.serial_number])
    report = report_utils.draw_basic_table(lines, header=False, alignment='center', vertical_sep=False)  # type: str
    return report


def build_drives(drive_info, skip_nvram=True):
    # type: (pandas.DataFrame, bool) -> Dict[str, Drive]
    """Build drives based upon dev_info and puredb_list_drives.

    Arguments:
        drive_info (pandas.DataFrame): Drive information from dev_info and puredb_list_drives.
        skip_nvram (bool): Include NVRAM in the output drives.
            * NVRAM is skipped by default, as we generally don't use NVRAM when determining space and other estimations.

    Returns:
        drives (dict): One or more Drive objects built from this information.
    """
    completed_drives = {}

    if drive_info.puredb_list_drives.dropna().empty or drive_info.dev_info.dropna().empty:
        msg = 'Cannot build drives, missing required drive information.'
        LOGGER.error(msg)
        raise ValueError(msg)

    for drive in drive_info.puredb_list_drives[0]:

        # Determine drive-type or skip it.
        if drive['type'] == 'NVRAM':
            if skip_nvram:
                continue
            drive_type = NVRAM
        elif drive['handle'].upper().startswith('WSSD'):
            # Example: 'WSSD7425_00BG008TB08_qp_PFMUN17245A88'
            drive_type = WSSD
        else:
            # If it is not prefixed with WSSD and is not an NVRAM, the drive['type'] tell us that it is an SSD.
            # If there is another option besides SSD/WSSD, we will need to account for it here.
            drive_type = SSD

        parsed = {}
        # Change names to human readable:
        # SH1.DRV3 -> SH1.BAY3
        drive_name = drive['name'].replace('DRV', 'BAY')

        # Determine subslot, if applicable:
        subslot = drive['subslot']
        if drive['type'] != 'NVRAM':
            full_name = '{}.SUBSLOT{}'.format(drive_name, subslot)  # SH0.BAY1 -> SH0
        else:
            full_name = drive_name

        # If we have already parsed/built this drive, skip it.
        if full_name in completed_drives:
            continue

        # Determine enclosure:
        enclosure_name = drive_name.split('.', 1)[0]  # SH0.BAY1 -> SH0
        parsed['location'] = enclosure_name

        # Various other metrics:
        parsed['status'] = drive['status']
        parsed['capacity'] = int(drive['capacity'])
        parsed['subslot'] = subslot
        parsed['last_evac_completed'] = drive['last_evac_completed']
        parsed['last_failure'] = drive['last_failure']
        parsed['handle'] = drive['handle']

        # Parse the handle for additional information:
        if drive['handle'] == '(unknown)':
            # If a drive is in a 'failed' state, these will report '(unknown)'.
            brand = model = serial = 'unknown'
        else:
            spl_handle = drive['handle'].split('_')
            # The handle can have 2, 3, 4, etc. individual components.
            if len(spl_handle) == 2:
                # NVRAM0101_PNVFS1536003D
                model, serial = spl_handle
                brand = '-'
            elif len(spl_handle) == 4:
                # WSSD7423_00BG002TB08_qp_PFMUN17043B23
                brand, model, _, serial = drive['handle'].split('_')
            else:
                # TOSHIBA_THNSNH512GCST_93IZZ06UTD4Y
                brand, model, serial = drive['handle'].split('_')
        parsed['brand'] = brand
        parsed['model'] = model
        parsed['serial_number'] = serial

        # Parse dev_info to get logical group information:
        dev_info = _parse_dev_info(parsed['handle'], drive_info.dev_info[0])
        if not dev_info:
            LOGGER.warning('Skipping an unknown drive.')
            continue
        parsed.update(dev_info)

        # Build the final Drive Instance:
        drive_obj = drive_type(bay=drive_name.split('.', 1)[-1], **parsed)
        completed_drives[drive_obj.full_name] = drive_obj

    if not completed_drives:
        error_msg = 'Failed to build any drives.'
        LOGGER.exception('ValueError: {}'.format(error_msg))
        raise ValueError(error_msg)
    return completed_drives


def sort_drives(drive_tuple):
    # type: (Tuple[str, Union[SSD, WSSD]]) -> Tuple[int, int]
    """Helper to sort drives by enclosure and then drive bay."""
    # drive_tuple: (drive_name, drive_instance)
    drive = drive_tuple[1]
    # SH0, 1 -> (0, 1)
    return int(re.sub(r'CH|SH', '', drive.location)), drive.bay


class Drive(hardware_utils.HardwareComponent):
    """A single Drive."""

    def __init__(self,
                 bay,               # type: str
                 location,          # type: str
                 subslot=None,      # type: str
                 capacity=None,     # type: Optional[Union[int, str]]
                 **kwargs           # type: Any
                ):                  # type: (...) -> None
        """
        Arguments:
            bay (str): The bay name of a drive.  i.e. 'BAY10'
            location (str): The device housing this drive.  i.e. 'CH0' or 'SH2'
            subslot (str): The location of this drive.  i.e. '1'
            capacity (int): The raw (bytes) capacity of this device.
        """
        bay = validation_utils.drive(bay).upper()
        self.bay = int(bay.replace('BAY', '').replace('NVR', ''))
        super(Drive, self).__init__(bay, **kwargs)
        self.capacity = format_utils.to_raw(capacity) if capacity else 0  # type: int
        self.location = location.upper()  # type: str
        self.subslot = str(subslot) if subslot is not None else ''  # type: str
        # Format the drive name: SH0.BAY10.SUBSLOT0
        self._full_name = None  # type: Optional[str]
        status = kwargs.get('status', 'unknown').strip().lower()
        self.status = format_utils.make_title(status)
        self.available = status == 'healthy'
        self.degraded = status == 'degraded'
        LOGGER.debug('Created a Drive ({}).'.format(self.name))

    def __str__(self):
        # type: () -> str
        """Return the full name and capacity of this drive.  i.e. 'SH0.BAY10.0 (123410101)'."""
        return '{} ({} B)'.format(self.full_name, self.capacity)

    @property
    def full_name(self):
        # type: () -> str
        """Generate the full name of the drive based upon the current location/name/sub_slot info."""
        drive_name = '.'.join([self.location, self.name]) if self.location else self.name  # type: str
        if self.subslot:
            drive_name = '.'.join([drive_name, 'SUBSLOT{}'.format(self.subslot)])
        return drive_name


class BootDrive(Drive):
    """A single Boot Drive Device."""

    def __init__(self,
                 bay,               # type: str
                 location,          # type: str
                 subslot=None,      # type: str
                 capacity=None,     # type: str
                 **kwargs           # type: str
                ):                 # type: (...) -> None
        """
        Arguments:
            bay (str): The name of a drive.  i.e. 'BAY10'
            location (str): The device housing this drive.  i.e. 'CT0'
            subslot (str): The location of this drive.  i.e. '1'
            capacity (int): The raw (bytes) capacity of this device.
        """
        # Validate the Controller name.
        validation_utils.ct_name(location)
        super(BootDrive, self).__init__(bay, location, subslot, capacity, **kwargs)
        LOGGER.debug('Created a Boot Drive ({}).'.format(self.name))


class NVRAM(Drive):
    """A single NVRAM Device."""

    def __init__(self,
                 bay,               # type: str
                 location,          # type: str
                 subslot=None,      # type: str
                 capacity=None,     # type: str
                 **kwargs           # type: str
                ):                 # type: (...) -> None
        """
        Arguments:
            bay (str): The name of a drive.  i.e. 'BAY10'
            location (str): The device housing this drive.  i.e. 'CT0'
            subslot (str): The location of this drive.  i.e. '1'
            capacity (int): The raw (bytes) capacity of this device.
        """
        super(NVRAM, self).__init__(bay, location, subslot, capacity, **kwargs)
        LOGGER.debug('Created an NVRAM ({}).'.format(self.name))


class SSD(Drive):
    """A single SSD."""

    def __init__(self,
                 bay,               # type: str
                 location,          # type: str
                 subslot=None,      # type: str
                 capacity=None,     # type: str
                 **kwargs           # type: str
                ):                 # type: (...) -> None
        """
        Arguments:
            bay (str): The name of a drive.  i.e. 'BAY10'
            location (str): The device housing this drive.  i.e. 'CT0'
            subslot (str): The location of this drive.  i.e. '1'
            capacity (int): The raw (bytes) capacity of this device.
        """
        super(SSD, self).__init__(bay, location, subslot, capacity, **kwargs)
        self.apt_id = kwargs.get('apt_id')  # type: Optional[str]
        LOGGER.debug('Created an SSD ({}).'.format(self.name))


class WSSD(SSD):
    """A single WSSD."""

    def __init__(self,
                 bay,               # type: str
                 location,          # type: str
                 subslot=None,      # type: str
                 capacity=None,     # type: str
                 **kwargs           # type: str
                ):                 # type: (...) -> None
        """
        Arguments:
            bay (str): The name of a drive.  i.e. 'BAY10'
            location (str): The device housing this drive.  i.e. 'CT0'
            subslot (str): The location of this drive.  i.e. '1'
            capacity (int): The raw (bytes) capacity of this device.
        """
        super(WSSD, self).__init__(bay, location, subslot, capacity, **kwargs)
        LOGGER.debug('Created a WSSD ({}).'.format(self.name))
