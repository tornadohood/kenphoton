"""Common Objects and Helpers for working with Hardware."""

import collections
import logging

from six import iteritems

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Type
except ImportError:
    pass

from photon.lib import custom_errors
from photon.lib import file_utils
from photon.lib import format_utils

LOGGER = logging.getLogger(__name__)


def get_parent_name(parent, purehw_info):
    # type: (str, Dict[str, Any]) -> str
    """Get the enclosure/parent human name of a device from 'purehw list'.

    Arguments:
        parent (str): The enclosure ID aka 'parent' name.
            Commands like 'purehw list' list this as 'parent'.
        purehw_info (dict): Parsed output of 'purehw list' (see parse_purehw_list).

    Returns:
        enclosure_name (str): The human name of the enclosure/parent.
    """
    enclosure_info = [encl for encl in purehw_info.values() if encl['Handle'] == parent]
    if not enclosure_info:
        error_msg = 'Unable to determine parent name, no match found in "purehw list" for "{}".'.format(parent)
        LOGGER.exception('InsufficientDataError: {}'.format(error_msg))
        raise custom_errors.InsufficientDataError(error_msg)
    enclosure_name = enclosure_info[0]['Name']
    return enclosure_name


def parse_finddrive(finddrive_lines):
    # type: (List[str]) -> Dict[str, Any]
    """Parse lines (into a dictionary) from a single finddrive output.

    Arguments:
        finddrive_lines (list/set/tuple): The output of 'finddrive.py'.

    Returns:
        drive_dict (dict): Per-drive information.
    """

    drive_dict = collections.defaultdict(list)
    header = ['Drive', 'Nodes', 'Product', 'Rev', 'SN', 'Expander', 'Enclosure', 'Slot', 'Subslot', 'SAT', 'SAT_Rev']
    # Finddrive contains multiple sub-sections.  Split them up:
    sections = file_utils.iter_line_intervals(finddrive_lines, start_string=r'\s+Drive\s+Nodes\s+Product',
                                              end_string=r'^\n', regex=True, inclusive=False)
    for section in sections:
        for line in section:
            chunks = line.split()
            if not chunks or len(chunks) in (1, 8, 11):
                # Exclude empty rows and headers.
                continue
            if len(chunks) == 9:
                # This doesn't have the final 3 columns: Subslot, SAT, and SAT_Revision
                # Example:
                # /dev/sg0  sda  INTEL SSDSCKGW180A4  DC31  CVDA6176004J180H  NA  FA-x70  40186.4
                # Add placeholders for the 3 missing columns.
                chunks.extend(['-'] * 3)
            elif len(chunks) == 10:
                # This is missing the final 3 but has two nodes:
                # Example:
                # /dev/sg1  sdb sdgk ...
                temp = chunks[:1]
                temp.append(' '.join([chunks[1], chunks[2]]))
                temp.extend(chunks[3:])
                chunks = temp
                chunks.extend(['-'] * 3)
            elif len(chunks) == 13:
                # This has multiple nodes:
                # Example:
                # /dev/sg1  sdb sdgk TOSHIBA THNSNJ512GCSU...
                temp = chunks[:1]
                # ['sdb', 'sdgk'] -> 'sdb sdgk'
                temp.append(' '.join([chunks[1], chunks[2]]))
                temp.extend(chunks[3:])
                chunks = temp

            # Merge the chunks of "Product" into a single chunk.
            # ['INTEL', 'SSDCKGW180A4'] -> 'INTEL SSDSCKGW180A4'
            product = ' '.join([chunks[2], chunks[3]])
            # Create a temporary list in order to merge it all together.
            # ['/dev/sg0',  'sda']
            merge = chunks[:2]
            merge.append(product)
            # Everything else (after product)
            merge.extend(chunks[4:])

            # If for whatever reason we don't have the right amount of columns, raise a ValueError for to this line.
            if len(merge) != 11:
                error_msg = 'Unable to parse a line of finddrive output.\n{}'.format(line)
                LOGGER.exception('ValueError: {}'.format(error_msg))
                raise ValueError(error_msg)

            # Add each chunk to the dictionary based upon location:
            for index, key in enumerate(header):
                value = merge[index]
                drive_dict[key].append(value)

    return dict(drive_dict)


def parse_hardware_check(hardware_check_lines):
    # type: (List[str]) -> Dict[str, Any]
    """Process lines from hardware_check.py into a dictionary."""
    parsed = collections.defaultdict(list)
    # Example: ==== CPU ====
    start_string = r'==== .*? ====\n'
    end_string = r'\n'
    gen = file_utils.iter_line_intervals(hardware_check_lines, start_string, end_string, inclusive=True, regex=True)
    for interval in gen:
        header = None
        # First line is the header:
        for line in interval:
            if not header:
                header = line.replace('====', '').strip()
            elif line.strip():
                # Example: No IB adapters found.
                parsed[header].append(line)
    return dict(parsed)


def parse_purehw_list(purehw_lines):
    # type: (List[str]) -> Dict[str, Any]
    """Parse lines (into a dictionary) from a single purehw_list output.

    Arguments:
        purehw_lines (list/set/tuple): The output of 'purehw list'.

    Returns:
        hardware_dict (dict): Per-device information.
    """
    # Skip the headers.
    skip_lines = ('-' * 72, 'Name')
    header = ['Name', 'Status', 'Identify', 'Slot', 'Index', 'Speed', 'Temperature',
              'Voltage', 'Type', 'Handle', 'Parent']
    hardware_dict = collections.defaultdict(dict)
    for line in purehw_lines:
        if line.strip().startswith(skip_lines):
            continue
        sline = [piece.strip() for piece in line.split('  ') if piece.strip()]
        if not sline:
            continue
        device_name = sline[0]
        for index, name in enumerate(header):
            value = sline[index]
            hardware_dict[device_name][name] = value
    return dict(hardware_dict)


class HardwareComponent(object):
    """The base class of all hardware components."""

    def __init__(self, name, serial_number=None, **kwargs):
        # type: (str, Optional[str], **Dict[Any]) -> None
        self.available = True
        self.name = name
        self.serial_number = serial_number
        for key, value in iteritems(kwargs):
            if hasattr(self, key):
                error_msg = '{} already has a {} attribute.'.format(self.__class__.__name__, key)
                LOGGER.exception('ValueError: {}'.format(error_msg))
                raise ValueError(error_msg)
            setattr(self, key, value)
        LOGGER.debug('Created a hardware component ({}).'.format(self.name))

    def __str__(self):
        # type: () -> str
        return '{} ({})'.format(self.name, self.serial_number)


class HardwareGroup(HardwareComponent):
    """A Grouping of hardware components."""

    def __init__(self, name, **kwargs):
        # type: (str, **Dict[Any]) -> None
        super(HardwareGroup, self).__init__(name, **kwargs)
        self.available = True
        self.components = {}
        self._compatible_components = None
        LOGGER.debug('Created a hardware group ({}).'.format(self.name))

    def __repr__(self):
        # type: () -> str
        # <class 'photon.lib.shelf_utils.Shelf'>: ['SH0.BAY1 (107374182400.0 B)']
        return '{}: {}'.format(self.__class__, str([str(component) for component in self.components]))

    def add_component(self, component):
        # type: (Any) -> None
        """Add a supported component to this hardware group."""
        if not isinstance(component, self.compatible_components):
            error_msg = '"{}" is not compatible with "{}".'.format(self.name, component.name)
            LOGGER.error('HardwareGroupError: {}'.format(error_msg))
            raise custom_errors.HardwareCompatibilityError(error_msg)
        LOGGER.debug('Added component "{}" to the hardware group "{}".'.format(component.name, self.name))
        # If a component name is already added, don't add it again.
        name = component.full_name if hasattr(component, 'full_name') else component.name
        if name not in [existing for existing in self.components]:
            self.components[name] = component
        else:
            error_msg = 'Component "{}" already exists.  Not adding it again.'.format(name)
            LOGGER.exception('HardwareGroupError: {}'.format(error_msg))
            raise custom_errors.HardwareGroupError(error_msg)

    def add_components(self, components):
        # type: (List[Any]) -> None
        """Add multiple supported components to the hardware group."""
        for component in components:
            self.add_component(component)

    @property
    def compatible_components(self):
        # type: () -> None
        """A listing of all compatible sub-components that can be added to this group.
        This should return a tuple of types or a single class type.
            * Example: (Port, Sensor)
        """
        raise NotImplementedError

    def has_component(self, component_name):
        # type: (str) -> bool
        """Validate if the component is within this group or one of its sub-components."""
        is_present = False
        component_names = []
        # Drive components will have a location attribute which is part of its unique name:  e.g. 'SH0.BAY11'.
        for comp in self.components.values():
            if hasattr(comp, 'location'):
                component_names.append('.'.join([comp.location, comp.name]))
            else:
                component_names.append(comp.name)
        if component_name.upper().strip() in component_names:
            is_present = True
        else:
            for component in self.components.values():
                if hasattr(component, 'has_component'):
                    if component.has_component(component_name):
                        is_present = True
                        break
        return is_present


class HBA(HardwareGroup):
    """A Host Bus Adapter."""

    def __init__(self, name, **kwargs):
        # type: (str, **Dict[Any]) -> None
        super(HBA, self).__init__(name, **kwargs)
        self.ports = self.components

    @property
    def compatible_components(self):
        # type: () -> Type[Port]
        """A listing of all compatible sub-components that can be added to this group.
        This should return a tuple of types or a single class type.
            * Example: (Port, Sensor)
        """
        return Port


class IOM(HardwareGroup):
    """An IOM with one or more ports."""

    def __init__(self, name, **kwargs):
        # type: (str, **Dict[Any]) -> None
        super(IOM, self).__init__(name, **kwargs)
        self.ports = self.components

    @property
    def compatible_components(self):
        # type: () -> Type[Port]
        """A listing of all compatible sub-components that can be added to this group.
        This should return a tuple of types or a single class type.
            * Example: (Port, Sensor)
        """
        return Port


class IPMI(HardwareGroup):
    """An IPMI device with one or more sensors."""

    def __init__(self, name, **kwargs):
        # type: (str, **Dict[Any]) -> None
        super(IPMI, self).__init__(name, **kwargs)
        self.sensors = self.components

    @property
    def compatible_components(self):
        # type: () -> Type[Sensor]
        """A listing of all compatible sub-components that can be added to this group.
        This should return a tuple of types or a single class type.
            * Example: (Port, Sensor)
        """
        return Sensor


class NIC(HardwareGroup):
    """A Network Interface Card with one or more ports."""

    def __init__(self, name, **kwargs):
        # type: (str, **Dict[Any]) -> None
        super(NIC, self).__init__(name, **kwargs)
        self.ports = self.components

    @property
    def compatible_components(self):
        # type: () -> Type[Port]
        """A listing of all compatible sub-components that can be added to this group.
        This should return a tuple of types or a single class type.
            * Example: (Port, Sensor)
        """
        return Port


class Port(HardwareComponent):
    """The base class for all ports."""

    def __init__(self, name, connected=False, link_speed=None, **kwargs):
        # type: (str, bool, Optional[int], **Dict[Any]) -> None
        super(Port, self).__init__(name, **kwargs)
        self.connected = connected
        self.link_speed = 0 if not connected or not link_speed else format_utils.to_raw(link_speed, 'bits')


class Sensor(HardwareComponent):
    """The base class for all sensors."""

    def __init__(self, name, status=None, **kwargs):
        # type: (str, Optional[str], **Dict[Any]) -> None
        super(Sensor, self).__init__(name, **kwargs)
        self.status = status


class StorageGroup(HardwareGroup):
    """A Grouping of hardware components which store data."""

    def __init__(self, name, **kwargs):
        # type: (str, **Dict[Any]) -> None
        super(StorageGroup, self).__init__(name, **kwargs)
        LOGGER.debug('Created a storage group ({}).'.format(self.name))

    @property
    def capacity(self):
        # type: () -> int
        """Calculate the capacity of all the available sub-components."""
        cap = 0
        for component in self.components.values():
            if not component.available:
                continue
            # TODO: Add support for WSSD and sub-slots here.
            comp_cap = component.capacity
            cap += comp_cap
        return int(cap)

    @property
    def compatible_components(self):
        # type: () -> None
        """A listing of all compatible sub-components that can be added to this group.
        This should return a tuple of types or a single class type.
            * Example: (Port, Sensor)
        """
        raise NotImplementedError

    def component_count(self):
        # type: () -> int
        """Get a total count of the number of components and sub-components within this StorageGroup."""
        return sum([_count_sub_components(comp) for comp in self.components])

    def component_type(self):
        # type: () -> str
        """Evaluate components to determine if they are all the same type or 'mixed'."""
        comp_types = list(set([comp.__class__.__name__ for comp in self.components.values()]))
        if len(comp_types) > 1:
            comp_type = 'mixed'
        elif len(comp_types) == 1:
            comp_type = comp_types[0]
        else:
            comp_type = 'unknown'
        return comp_type

    def evac_single_drive(self, drive_name):
        # type: (str) -> None
        """Evacuate a single drive.

        Arguments:
            drive_name (str): A single drive to evacuate.  i.e. 'SH0.BAY1'
        """
        LOGGER.debug('Evacuating drive: "{}".'.format(drive_name))
        retained_drives = {}
        for component_name, device in self.components.items():
            if drive_name != component_name:
                retained_drives[component_name] = device
            elif hasattr(device, 'components'):
                device.evac_single_drive(drive_name)
        # self.drives is defined within the super class (HardwareGroup).
        # pylint: disable=attribute-defined-outside-init
        self.drives = self.components = retained_drives

    def evac_multiple_drives(self, drive_names):
        # type: (List[str]) -> None
        """Evacuate multiple drives.

        Arguments:
            drive_names (list/set/tuple): One or more drive names to evacuate from this grouping.
        """
        for drive_name in drive_names:
            self.evac_single_drive(drive_name)


def _count_sub_components(component):
    # type: (Any) -> int
    """Get a count of components and sub-components (including the current component)."""
    components = 0
    if hasattr(component, 'components'):
        for sub_component in component.components.values():
            components += _count_sub_components(sub_component)
    else:
        components += 1
    return components
