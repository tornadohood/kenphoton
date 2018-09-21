"""Health Checks to run prior to doing an evacuation."""

import logging
import re

from six import itervalues

from photon import api
from photon.lib import apartment_utils
from photon.lib import check_utils
from photon.lib import debug_utils
from photon.lib import drive_utils
from photon.lib import format_utils
from photon.lib import interactive_utils
from photon.lib import math_utils
from photon.lib import print_utils
from photon.lib import sasview_utils
from photon.lib import shelf_utils
from photon.lib import time_utils
from photon.lib import version_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple
    from typing import Union
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

# Intentionally renaming the run_test argument to evac_api for clarity.
# pylint: disable=arguments-differ


# TODO: PT-1675 - Create a more general check in hardware_utils for this.
def _check_for_wssd(component):
    # type: (Union[shelf_utils.Enclosure, apartment_utils.WriteGroup]) -> bool
    """Check if the component or any sub-component is a WSSD."""
    wssd_found = False
    if isinstance(component, drive_utils.WSSD):
        wssd_found = True
    elif hasattr(component, 'components'):
        for sub_comp in itervalues(component.components):
            wssd_found = _check_for_wssd(sub_comp)
            if wssd_found is True:
                break
    return wssd_found


def _fix_leading_zero(device_name):
    """Remove leading zeros from a device name."""
    # e.g. SH07 -> SH7
    # e.g. SH1.BAY05 -> SH1.BAY5
    # e.g. SH01.BAY07.SUBSLOT01 -> SH1.BAY7.SUBSLOT1
    return re.sub(r'0(?P<num>\d+)', r'\g<num>', device_name)


def _in_apartment(evac_api, active_events):
    # type: (Any, Set[Tuple[Any, Any]]) -> Set[str]
    """Determine if each drive in unique events is in an active apartment."""
    affected_drives = set()
    # For each affected device, determine if it is within an active Apartment:
    apartments = itervalues(evac_api.device_map['apartments'])
    for apartment in apartments:
        for _, dev_id in active_events:
            drive_name = apartment_utils.in_apartment(dev_id, apartment)
            if drive_name:
                affected_drives.add(drive_name)
    return affected_drives


def _list_all_drives(apartment):
    # type: (apartment_utils.Apartment) -> List[drive_utils.Drive]
    """List all of the drive objects within an apartment."""
    all_drives = []  # type: List[drive_utils.Drive]
    wgroups = itervalues(apartment.components)
    for wgroup in wgroups:
        drives = itervalues(wgroup.drives)
        all_drives.extend(drives)
    return all_drives


def estimate_capacity(device_capacity, usable_capacity, ssd_capacity):
    """Estimate the amount of usable and raw capacity after evacuating the given device.

    Arguments:
        device_capacity (float/int): The capacity of a single device.
        usable_capacity (float/int): The usable capacity of the FlashArray. (aka GUI space)
        ssd_capacity (float/int): The SSD capacity of the FlashArray.  (aka raw space)
        # Note: All values represent raw Bytes.

    Returns:
        usable_capacity (float): The usable (GUI) capacity of the FlashArray.
        ssd_capacity (float); The SSD (raw) capacity of the FlashArray.
    """
    usable_ratio = math_utils.safe_divide(usable_capacity, ssd_capacity) or 0.622
    ssd_capacity -= device_capacity
    usable_capacity = ssd_capacity * usable_ratio
    return format_utils.zero(usable_capacity), format_utils.zero(ssd_capacity)


def estimate_system_space(unreported_space, ssd_capacity):
    """Estimate how much System space will be visible in the GUI post-evacuation of the given device.

    Arguments:
        unreported_space (float/int): The amount of Unreported Space on the FlashArray (raw bytes).
        ssd_capacity (float/int): The SSD Capcity (raw) of the FlashArray (raw bytes).

    Returns:
        estimated_system (float): The estimated visible System space given the estimated Unreported space.
    """
    estimated_system = 0
    if unreported_space > 0:
        # https://wiki.purestorage.com/display/psw/Deprecated+-+Diagnosing+Space+:+High+System,+Unreported+and+Garbage
        # hidden_budget = (0.9 * raw capacity) - (0.8 * 0.778 * raw capacity) = 0.2776 * raw_capacity
        hidden_budget = 0.2776 * ssd_capacity
        estimated_system = unreported_space - hidden_budget
    return format_utils.zero(estimated_system)


class EvacHealthChecksAPI(api.FlashArray):
    """A Wrapper to extend the features of the FlashArray API."""

    # pylint: disable=too-many-arguments
    # All of these arguments are required.
    def __init__(self, to_evac=None, **kwargs):
        """
        Arguments:
            fqdn (str): A Fully Qualified Domain Name for the array.  i.e. "array_name.domain.com"
            log_path (str): A path to find log files for this array.
            start (str/datetime/pandas.Timestamp): The start of the time frame to request.
            end (str/datetime/pandas.Timestamp): The end of the time frame to request.
                * The end must be AFTER the start.
            files (list): One or more log files (full paths).
            to_evac (dict): One or more devices to evacuate organized by type.
                Example: {'enclosures': ['SH0', 'CH1'], 'data_packs': ['SH0.BAY1'], 'drives': ['SH1.BAY1']}
        """
        super(EvacHealthChecksAPI, self).__init__(**kwargs)
        self._device_map = None
        self._to_evac = to_evac or {}
        self._devices_to_evac = None
        self._capacity = None
        self.compatible_devices = set()
        self.incompatible_devices = set()
        self.missing_devices = set()

    def _get_evac_drives(self, drive_names):
        """Get individual drive instances to evacuate."""
        to_evac = []
        for full_name in drive_names:
            full_name = _fix_leading_zero(full_name)
            # Example of full_name: 'SH0.BAY10.SUBSLOT0'
            # name_pieces = full_name.split('.')
            # encl = name_pieces[0]
            # Try looking for sub-slots and normal bays.
            drive_names = (full_name, '{}.SUBSLOT0'.format(full_name), '{}.SUBSLOT1'.format(full_name))
            for drive_name in drive_names:
                drive_inst = self.device_map['drives'].get(drive_name)
                # drive_inst = self.device_map['enclosures'][encl].drives.get(drive_name)
                if drive_inst:
                    to_evac.append(drive_inst)
        return to_evac

    def _get_evac_enclosures(self, encl_names):
        """Get individual enclosure instances to evacuate."""
        to_evac = []
        for encl_name in encl_names:
            encl_name = _fix_leading_zero(encl_name)
            # Enclosure Names should be like: 'SH0'.
            inst = self.device_map['enclosures'].get(encl_name)
            if not inst:
                LOGGER.warning('The requested Enclosure {} does not exist.'.format(encl_name))
                continue
            to_evac.append(inst)
        return to_evac

    def _get_evac_packs(self, pack_names):
        """Get individual data pack instances to evacuate."""
        to_evac = []
        for drive_name in pack_names:
            drive_name = _fix_leading_zero(drive_name)
            # We use a drive_name to find DataPacks.  Example: 'SH0.BAY1'.
            LOGGER.debug('Searching for a Data Pack related to: {}'.format(drive_name))
            for data_pack in itervalues(self.device_map['data_packs']):
                if data_pack.has_component(drive_name):
                    # Update the name of the DataPack to match the requested evacuation device.
                    data_pack.name = 'Pack ({})'.format(drive_name)
                    to_evac.append(data_pack)
        return to_evac

    def build_array_summary(self):
        """Build the Array Summary Report.

        Returns:
            array_summary (dict): A quick summary of information concerning the array.
        """
        print_utils.status_update('Gathering Array summary information.')

        # Get the most recent values for the report:
        raw_capacity = self.get_latest_value('ssd_capacity')
        ssd_mapped = self.get_latest_value('ssd_mapped')
        system_space = self.get_latest_value('system_space')
        used_space = self.get_latest_value('physical_space')
        usable_capacity = self.get_latest_value('capacity')

        # Build the summary:
        array_summary = {
            'array_name': self.get_latest_value('array_name'),
            'model': ' | '.join(self.get_latest_value('controller_model')['Model']),
            'purity_version': self.get_latest_value('purity_version'),
            'raw_capacity': format_utils.auto_scale(raw_capacity, 'binary_bytes'),
            'raw_pct': format_utils.percentage(math_utils.safe_divide(ssd_mapped, raw_capacity)),
            'system_space': format_utils.auto_scale(system_space, 'binary_bytes'),
            'usable_capacity': format_utils.auto_scale(usable_capacity, 'binary_bytes'),
            'used_pct': format_utils.percentage(math_utils.safe_divide(used_space, usable_capacity)),
        }
        print_utils.status_update()
        return array_summary

    def build_drive_details(self):
        """Build a simple table of enclosure/group device details.

        Returns:
            enclosure_details (dict): Per-device formatted string tabular results.
        """
        enclosure_details = {}
        for enclosure_name in sorted(self.device_map['enclosures']):
            enclosure_obj = self.device_map['enclosures'][enclosure_name]
            # If we have evac information to apply:
            enclosure_details[enclosure_name] = drive_utils.build_drive_map(enclosure_obj.drives)
        return enclosure_details

    @property
    def capacity(self):
        """Get the current capacity of the array."""
        # TODO: PT-1560 - Calculate usable/raw capacity based upon objects; not log information.
        return sum([apartment.capacity for apartment in self.device_map['apartments'].values()])

    @property
    def device_map(self):
        """Build a mapping of all enclosures, groups, etc. to drives.
        This relies upon the output of puredrive_list, purehw_list, and dev_info.
        """
        if self._device_map:
            return self._device_map

        print_utils.status_update('Mapping drive/group/enclosure relationships.')
        fields = ['dev_info', 'puredb_list_drives']
        drive_info = self.get_latest_values(fields)

        # Build all Drive instances.
        drives = drive_utils.build_drives(drive_info)

        if not drives:
            error_msg = 'No drives found on the array.'
            LOGGER.exception('ValueError: {}'.format(error_msg))
            raise ValueError(error_msg)

        # Build enclosures and add drives to them.
        enclosures = shelf_utils.build_enclosures(drives)

        # Build write groups and add drives to them.
        write_groups = apartment_utils.build_write_groups(drives)

        # Build apartments and add write groups to them.
        apartments = apartment_utils.build_apartments(drives, write_groups)

        # Build data packs and add write groups to them.
        data_packs = apartment_utils.build_data_packs(drives, write_groups)

        self._device_map = {
            'apartments': apartments,
            'data_packs': data_packs,
            'drives': drives,
            'enclosures': enclosures,
            'write_groups': write_groups,
        }

        if not any([apartments, data_packs, enclosures, write_groups]):
            error_msg = 'No devices found on the array.'
            LOGGER.exception('ValueError: {}'.format(error_msg))
            raise ValueError(error_msg)

        print_utils.status_update()
        return self._device_map

    @property
    def devices_to_evac(self):
        """Fetch the instances of the requested devices for evacuation.

        Returns:
            device_instances (dict): One or more device instances ready to evacuate.
        """
        if self._devices_to_evac:
            return self._devices_to_evac

        if not self._to_evac:
            LOGGER.warning('No devices found to evacuate.')

        print_utils.status_update('Evaluating devices for evacuation.')

        # We can evacuate 3 types of devices: Data Packs, Drives, and Enclosures (Shelves/Chassis).
        device_instances = {}
        data_packs = self._to_evac.get('data_packs', [])
        drives = self._to_evac.get('drives', [])
        enclosures = self._to_evac.get('enclosures', [])

        # Data Packs:
        for device in self._get_evac_packs(data_packs):
            device_instances[device.name] = device

        # Drives:
        for device in self._get_evac_drives(drives):
            device_instances[device.full_name] = device

        # Enclosures:
        for device in self._get_evac_enclosures(enclosures):
            device_instances[device.name] = device

        # Check if any of the requested devices to evacuate are not found:
        for device_type, devices in self._to_evac.items():
            for device_name in devices:
                if device_type == 'data_packs':
                    # We re-name these to match the requested enclosure.drive name:
                    # i.e. DataPack0 -> SH0.BAY1 because that's how we identified the DataPack.
                    device_name = 'Pack ({})'.format(device_name)
                elif device_type == 'drives':
                    # We should use the full_name to match the requested drive:
                    # i.e. SH0.BAY1.SUBSLOT0
                    # Try all variations on the drive's name:
                    drive_names = [device_name, '{}.SUBSLOT0'.format(device_name), '{}.SUBSLOT1'.format(device_name)]
                    if not any(name not in device_instances for name in drive_names):
                        self.missing_devices.add(device_name)

                    continue
                if device_name not in device_instances:
                    self.missing_devices.add(device_name)

        self._devices_to_evac = device_instances
        print_utils.status_update()

        return self._devices_to_evac

    def estimate_evac_space(self):
        """Estimate the array fullness/usage after evacuating each device.
        This requires the following fields: capacity, physical_space, ssd_capacity, ssd_mapped, and unreported_space.

        Returns:
            estimations (dict): Per-device estimations on capacity, space utilization, etc.
        """
        estimations = {}
        if not self.devices_to_evac:
            LOGGER.warning('No devices to evacuate.')
            return estimations

        # Get the latest values for the needed fields:
        ssd_capacity = self.get_latest_value('ssd_capacity')
        ssd_mapped = self.get_latest_value('ssd_mapped')
        unreported_space = self.get_latest_value('unreported_space')
        usable_capacity = self.get_latest_value('capacity')
        used_space = self.get_latest_value('physical_space')

        # Calculate estimations post-evacuation.
        print_utils.status_update('Calculating Post Evacuation Space Metrics.')
        # Order by raw capacity: PT-1897
        for device in sorted(self.devices_to_evac.values(), key=lambda dev: dev.capacity):
            if device.name in self.incompatible_devices:
                LOGGER.warning('Skipping device "{}", it is not compatible with evacuation.'.format(device.name))
                continue
            device_capacity = device.capacity
            # TODO: PT-1560 - Calculate usable/raw capacity based upon objects; not log information.
            usable_capacity, ssd_capacity = estimate_capacity(device_capacity, usable_capacity, ssd_capacity)

            # Evacuate the device and all of its sub-components, if applicable.
            self._evac_device(device)

            # Add System space which will show up in the GUI post-evac to used_space.
            system_space = estimate_system_space(unreported_space, ssd_capacity)
            used_space += system_space

            # Determine percentages of raw/usable:
            gui_pct = math_utils.safe_divide(used_space, usable_capacity)
            raw_pct = math_utils.safe_divide(ssd_mapped, ssd_capacity)
            estimations[device.name] = {
                'device_capacity': device_capacity,
                'device_type': device.__class__.__name__,  # e.g. SSD, WriteGroup, etc.
                'gui_pct': gui_pct,
                'raw_pct': raw_pct,
                'raw_capacity': ssd_capacity,
                'system_space': system_space,
                # PT-2355 - Simplify the fail criteria for space utilization.
                # Fail if we exceed 88% SSD mapped or 100% GUI used or usable capacity reaches 0.
                'safe': str((raw_pct <= 0.88 and gui_pct <= 1.0) and usable_capacity > 0.),
                'usable_capacity': usable_capacity,
                # Determine how much we would need to reduce used space in order to be successful:
                'reduce_by': format_utils.zero(used_space - usable_capacity),
            }
        print_utils.status_update()
        return estimations

    def _evac_device(self, device):
        """Evacuate a device from the array."""
        LOGGER.debug('Evacuating device: {}'.format(device.name))
        if hasattr(device, 'components'):
            for component in itervalues(device.components):
                self._evac_device(component)
        device.available = False


class CapacityOverrideTunableCheck(check_utils.Check):
    """Check if PS_STORAGE_CAPACITY_OVERRIDE_GB is set too high."""

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Ensure that this is at or below 5% of the array's capacity.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        capacity = evac_api.get_latest_value('ssd_capacity')
        tunables = evac_api.get_latest_value('tunables')
        tunable_name = 'PS_STORAGE_CAPACITY_OVERRIDE_GB'
        cap_value = tunables.get(tunable_name)
        # If this has a non-numerical value then don't try to calculate percentages:
        if cap_value and not cap_value.strip().isdigit():
            # This should always be an integer value:
            self.details.append('{} has a bad value.  Consult Escalations.'.format(tunable_name))
            self.passed = False
        elif cap_value:
            # https://mrtunable.dev.purestorage.com/show-definition?tunable=PS_STORAGE_CAPACITY_OVERRIDE_GB
            # This definition indicates that it is indeed GB and not GiB...
            override_bytes = format_utils.to_raw('{} GB'.format(cap_value))
            # This should not be >5% of the array capacity:
            if override_bytes / capacity > 0.05:
                self.details.append('{} is set too high.  '
                                    'Open a JIRA to verify if this can be reduced.'.format(tunable_name))
                self.passed = False
            else:
                self.details.append('{} is set at or below 5% of the Array capacity.'.format(tunable_name))
                self.passed = True
        else:
            self.details.append('{} is not set.'.format(tunable_name))
            self.passed = True


class ControllerHardwareCompatibility(check_utils.Check):
    """Confirm that both controllers' hardware is compatible with Evacuation."""

    def __init__(self):
        # type: () -> None
        super(ControllerHardwareCompatibility, self).__init__(jira='PURE-91862')

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Verify that the controller model is compatible."""
        evac_api.incompatible_devices = set()  # Clear this out from previous tests.
        ct_models = evac_api.get_latest_value('controller_model')['Model']
        if len(ct_models) != 2 or ct_models[0] != ct_models[1]:
            self.passed = False
            self.details.append('The controller models are not the same.')
            # No more testing is needed here; the controllers don't match!
            return
        else:
            # The models are the same, just get one of them.
            model = ct_models[0]
        if model.startswith(('FA-x', 'TUNG')):
            purity_version = evac_api.get_latest_value('purity_version')
            if not version_utils.compare_versions(purity_version, '5.1.0'):
                # Must be on 5.1.0+ to do WSSD upgrades on TUNGSTEN.
                found_wssd = False
                for component in itervalues(evac_api.devices_to_evac):
                    if _check_for_wssd(component):
                        self.passed = False
                        self.details.append('Cannot do in-place upgrades on WSSD and TUNGSTEN until Purity 5.1.0+.')
                        found_wssd = True
                        break
                if not found_wssd:
                    self.passed = True
                    self.details.append('No WSSD drives being evacuated.')
            else:
                self.passed = True
                self.details.append('Evacuating WSSD is supported on this version of Purity.')
        elif model.startswith('FA-3'):
            self.details.append('Cannot do evacuations on FA-3XX series arrays.')
            self.passed = False
        elif model.startswith('FA-4'):
            msg = 'Consult with Escalations before proceeding.  FA-4XX series arrays have several restrictions.'
            self.details.append(msg)
            self.passed = False
        elif model.startswith(('FA-m', 'FA-X')):
            self.passed = True
            self.details.append('Controller Hardware is compatible.')
        else:
            self.passed = False
            self.details.append('Controller Hardware "{}" is unknown.'.format(model))


class DenyEvictionTunableCheck(check_utils.Check):
    """Check if PS_DENY_DRIVE_EVICTION is set."""

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Ensure that we don't have any risky tunables set.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        tunables = evac_api.get_latest_value('tunables')
        deny_evict = 'PS_DENY_DRIVE_EVICTION'

        if deny_evict in tunables:
            # This prevents empty drives from evicting if we have to move around drives between shelves / slots / bays.
            if tunables[deny_evict] == '1':
                self.details.append('{} is enabled.  '
                                    'Open a JIRA to verify if this can be unset'.format(deny_evict))
                self.passed = False
            elif tunables[deny_evict] == '0':
                self.details.append('{} is not enabled.'.format(deny_evict))
                self.passed = True
            else:
                self.details.append('{} has a bad value.  Consult Escalations.'.format(deny_evict))
                self.passed = False
        else:
            self.details.append('{} is not set.'.format(deny_evict))
            self.passed = True


class EarlyEvict(check_utils.Check):
    """Check for the presence of PURE-81137."""
    # Re-work this to make it easier to test.

    def __init__(self):
        # type: () -> None
        super(EarlyEvict, self).__init__(jira='PURE-81137')
        self.affected_devices = {
            'CT0': [],
            'CT1': [],
        }  # type: Dict[str, List[drive_utils.Drive]]

    def _get_active_events(self, evac_api):
        # type: (Any) -> Set[Tuple[Any, Any]]
        """Check for events which were not cleared by a failover."""
        active_events = set()
        # TODO: PT-1957 - Need something at the API layer to get the latest from BOTH controllers.
        # Use the Purity uptime to infer when the last failover occurred:
        uptime_values = evac_api.get_fields(['purity_uptime'])
        ct0_df = uptime_values[uptime_values['controller'] == 'CT0'].set_index('Timestamp',
                                                                               drop=True).dropna().tail(1)
        ct1_df = uptime_values[uptime_values['controller'] == 'CT1'].set_index('Timestamp',
                                                                               drop=True).dropna().tail(1)

        ct0_delta = time_utils.Timedelta(ct0_df.purity_uptime[0])
        ct1_delta = time_utils.Timedelta(ct1_df.purity_uptime[0])

        # Timestamp - Uptime = Last failover timestamp
        ct0_purity_reset = ct0_df.index[0] - ct0_delta
        ct1_purity_reset = ct1_df.index[0] - ct1_delta
        # For each affected device, decide if a failover has cleared it:
        for controller, events in self.affected_devices.items():
            if controller == 'CT0':
                last_reset = ct0_purity_reset
            else:
                last_reset = ct1_purity_reset

            for event in events:
                # If the failover happened after the timestamp of the event, remove the affected device(s).
                if last_reset > event[0]:
                    self.affected_devices[controller].remove(event)
                else:
                    active_events.add(event)
        return active_events

    def _get_reporting_0_devices(self, flasharray, apartments):
        # type: (Any, Dict[str, Any]) -> None
        """Get all drive ids for devices in apartments which are reporting 0 references.

        This will request data from core.log which can take a long time, so this only runs if it NEEDS to.

        Arguments:
            flasharray (API): An API connection to use for requesting fields.
            apartments (dict): One or more named Apartment instances.
        """
        # Check for devices reporting 0.
        report_values = flasharray.get_fields(['devices_without_references'])
        reporting_0 = {ctlr: report_values[ctlr].get('devices_without_references') for ctlr in report_values}
        for controller in reporting_0:
            reporting_devs = reporting_0[controller]
            if not reporting_devs:
                continue
            # For each device, check if it's in an Apartment:
            for timestamp, device in reporting_devs:
                for apt_inst in itervalues(apartments):
                    drive_full_name = apartment_utils.in_apartment(device, apt_inst)
                    if drive_full_name:
                        self.affected_devices[controller].append((timestamp, drive_full_name))

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Run the EarlyEvict test and set self.passed to True if it succeeds.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        purity_version = evac_api.get_latest_value('purity_version')
        if version_utils.compare_multiple_versions(purity_version, ('4.7.10', '4.8.8', '4.9.0')):
            self.passed = True
            self.details.append('Fixed in the current Purity version.')
            # The issue is fixed in this version, no need to run further tests.
            return
        else:
            self.details.append('Not fixed in the current Purity version; an upgrade is recommended.')

        # Added affected devices:
        devices_df = evac_api.get_fields(['devices_without_references'])
        for controller in ('CT0', 'CT1'):
            ct_events = devices_df[devices_df['controller'] == controller]
            for devices in ct_events.dropna().devices_without_references.tolist():
                self.affected_devices[controller].extend(devices)

        unique_events = set(self.affected_devices['CT0'] + self.affected_devices['CT1'])
        # If there are devices affected by this issue, check if there are 3 or less.
        # If there are 3 or less, then this is likely a transient hardware failure.
        # If there are more than 3, then check if a failover has cleared the errors.
        # If not, recommend a failover before proceeding.
        if unique_events:
            if len(unique_events) <= 3:
                self.details.append('\nCheck for recent hardware failures or SSD replacements.')
                self.passed = True
                return
        active_events = self._get_active_events(evac_api)
        drive_ids = {drv.device_id: drv.full_name for drv in evac_api.device_map['drives'].values()}
        affected_drives = [drive_ids[drv_id] for _, drv_id in active_events if drv_id in drive_ids]

        # If there are actively affected drives, recommend a failover:
        if affected_drives:
            msg = '{} drives are affected.  A failover is required before proceeding.'
            self.details.append(msg.format(len(affected_drives)))
            self.passed = False
        else:
            msg = 'No devices are currently affected by the issue.'
            self.details.append(msg)
            self.passed = True


class EvacDevicesExist(check_utils.Check):
    """Check if all of the requested devices to evacuate exist within the array."""

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Ensure that each device requested is found and is not redundant.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        # Get the devices to evacuate:
        to_evac = evac_api.devices_to_evac
        # If there's any devices requested that weren't found, list then out in details.
        if evac_api.missing_devices:
            self.details.append('Devices(s) not found: {}.  '.format(', '.join(evac_api.missing_devices)))
            self.passed = False
        elif not to_evac:
            self.details.append('Found no devices to evacuate.')
            self.passed = False
        else:
            self.details.append('All devices were found.')
            self.passed = True


class EvacStallCheck(check_utils.VersionCheck):
    """Check if the array may be impacted by PURE-85207."""

    def __init__(self):
        # type: () -> None
        msg = 'Evacuation may stall due to an issue with segment guard.'
        super(EvacStallCheck, self).__init__(('4.8.9', '4.9.5', '4.10.1'), 'PURE-85207', msg)


class LatencyDuringRebuildCheck(check_utils.VersionCheck):
    """Check for the presence of PURE-95283."""

    def __init__(self):
        # type: () -> None
        msg = 'To prevent latency, enable PS_ALLOW_DIFFERENT_SIZE_STEM and evacuate 1 drive at a time.'
        super(LatencyDuringRebuildCheck, self).__init__(('4.8.11', '4.9.6', '4.10.5', '5.0.0'), 'PURE-95283', msg)


class LongSecureErase(check_utils.Check):
    """Check for the presence of PURE-73789."""

    def __init__(self):
        # type: () -> None
        super(LongSecureErase, self).__init__(jira='PURE-73789')

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Run the LongSecureErase test and set self.passed to True if it succeeds.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        purity_version = evac_api.get_latest_value('purity_version')
        if version_utils.compare_multiple_versions(purity_version, ('4.7.10', '4.8.8', '4.9.0')):
            self.passed = True
            self.details.append('Fixed in the current Purity version.')
        else:
            affected_drives = set()
            for drive in itervalues(evac_api.device_map['drives']):
                # Example of an affected model: SAMSUNG_MZ7LM1T9_S1YKNX0H602232
                if drive.model.startswith('SAMSUNG MZ7LM'):
                    affected_drives.add(drive.full_name)
            if affected_drives:
                self.details.append('Affected Drives: {}'.format(', '.join(sorted(affected_drives))))
                # Explicitly set this to False in case anything else set it to True.
                self.passed = False
            else:
                self.details.append('There are no drives affected by PURE-73789.')
                self.passed = True


class KCrumbWithX(check_utils.Check):
    """Check for the presence of PURE-108757."""

    def __init__(self):
        # type: () -> None
        super(KCrumbWithX, self).__init__(jira='PURE-108757')

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Run the KCrumbWithX test and set self.passed to True if it succeeds.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        purity_version = evac_api.get_latest_value('purity_version')
        if version_utils.compare_versions(purity_version, '4.10.9'):
            self.passed = True
            self.details.append('Fixed in the current Purity version.')
        elif purity_version in ('4.10.6', '4.10.7', '4.10.8'):
            ct_models = evac_api.get_latest_value('controller_model')
            # This should only affect Purity 4.10.6 -> 4.10.8 (fixed in 4.10.9)
            # Example of ct_models:
            # {'Model': ['FA-m70r2', 'FA-m70r2'], 'Name': ['CT0', 'CT1']}
            if any(model.startswith('FA-x') for model in ct_models.get('Model')):
                self.details.append('Evacuations on "//X" controllers are not supported before Purity 4.10.9.')
                self.passed = False
            else:
                self.details.append('Both controllers are compatible with evacuation.')
                self.passed = True
        else:
            self.details.append('Not on an affected Purity version.')
            self.passed = True


class MishomedDrives(check_utils.Check):
    """Check for the presence of Mishomed Drives issues."""

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Ensure that there are no mishomed drives on shelves.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        affected_shelves = set()
        for wgroup in itervalues(evac_api.device_map['write_groups']):
            wgroup_shelves = set([drive.location for drive in wgroup.drives.values()])
            if len(wgroup_shelves) != 1:
                for shelf in wgroup_shelves:
                    affected_shelves.add(shelf)
        if affected_shelves:
            self.details.append('Shelves with mishomed drives: {}'.format(', '.join(sorted(affected_shelves))))
            # Explicitly set this to False in case anything else set it to True.
            self.passed = False
        else:
            self.passed = True
            self.details.append('No shelves with mishomed drives found.')


class ParallelGCFunnels(check_utils.VersionCheck):
    """Check for the presence of PURE-92222."""

    def __init__(self):
        # type: () -> None
        msg = 'PURE-92222 is not fixed in this version.  Strongly recommend an upgrade before the evac.'
        super(ParallelGCFunnels, self).__init__(('4.8.11', '4.9.6', '4.10.4'), 'PURE-92222', msg)


class PurityVersionCompatibility(check_utils.Check):
    """Check if the devices to evacuate are compatible with this version of Purity."""

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Ensure that we are on a version which supports evacuating each requested device."""
        evac_api.incompatible_devices = set()  # Clear this out from previous tests.
        for name, device in evac_api.devices_to_evac.items():

            # DataPack Checks:
            if isinstance(device, apartment_utils.DataPack):
                purity_version = evac_api.get_latest_value('purity_version')
                # If we are evacuating a DataPack, then we must be on Purity 4.10.6+:
                if version_utils.compare_versions(purity_version, '4.10.6'):
                    enclosures = evac_api.device_map['enclosures']
                    incompatible = False
                    for wgroup in itervalues(device.components):
                        for drive in itervalues(wgroup.drives):
                            drive_encl = enclosures[drive.location]
                            # Data Pack evac is only supported on 12G shelves and //m, //x, and //X chassis.
                            # Example of a Mercury handle: MERCURYA_PCHFL174100AA
                            if drive_encl.handle.startswith(('EB-2425-E12EBD', 'M_SERIES', 'TUNG', 'MERCURYA')):
                                continue
                            else:
                                incompatible = True
                                break
                        if incompatible:
                            break
                    if incompatible:
                        evac_api.incompatible_devices.add(name)
                else:
                    evac_api.incompatible_devices.add(name)

            # Shelf/Chassis Checks:
            elif isinstance(device, (shelf_utils.Shelf, shelf_utils.Chassis)):
                purity_version = evac_api.get_latest_value('purity_version')
                # If we are evacuating a shelf, then we must be on 4.7.3+:
                if not version_utils.compare_versions(purity_version, '4.7.3'):
                    evac_api.incompatible_devices.add(name)

            # Drive Checks:
            elif isinstance(device, (drive_utils.SSD, drive_utils.WSSD)):
                if device.available:
                    evac_api.compatible_devices.add(name)
                else:
                    evac_api.incompatible_devices.add(name)
            else:
                evac_api.incompatible_devices.add(name)

        if evac_api.incompatible_devices:
            self.details.append('Incompatible devices: {}.'.format(', '.join(sorted(evac_api.incompatible_devices))))
            self.passed = False
        else:
            self.details.append('No incompatible devices found.')
            self.passed = True


class SASCabling(check_utils.Check):
    """Check for the presence of SAS Cabling issues."""

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Not yet implemented, but we don't want this to crash here."""
        cabling = sasview_utils.SASCabling(evac_api)
        cabling.get_array_topology()
        sas_errors = cabling.parse_errors()
        if sas_errors:
            for ctlr, errors in sas_errors.items():
                self.details.append('{}:'.format(ctlr))
                self.details.append('\n'.join(errors))
            self.passed = False
        else:
            self.details.append('No SAS errors found.')
            self.passed = True


class SegmentGuardFailoverCheck(check_utils.VersionCheck):
    """Check if the array may be impacted by PURE-84251."""

    def __init__(self):
        # type: () -> None
        msg = 'Consult escalations before doing the evac; an unplanned failover may occur.'
        super(SegmentGuardFailoverCheck, self).__init__(('4.8.9', '4.9.5', '4.10.1'), 'PURE-84251', msg)


class ShardRebuildRiskCheck(check_utils.VersionCheck):
    """Check if the array may be impacted by PURE-97183."""

    def __init__(self):
        # type: () -> None
        # TODO: PURE-97183 - When 5.0.e is available, add it to fixed in versions.
        fail_msg = 'Do not perform an evacuation on this Purity version!  Upgrade to 5.1.x.'
        pass_msg = 'Not applicable to this Purity version.'
        super(ShardRebuildRiskCheck, self).__init__(('5.1.0', ), 'PURE-97183', fail_msg, pass_msg,
                                                    minimum_affected_version='5.0.0')


class SlowSANStartupCheck(check_utils.VersionCheck):
    """Check if the array may be impacted by PURE-86636."""

    def __init__(self):
        # type: () -> None
        msg = 'Consult escalations before doing a failover.'
        super(SlowSANStartupCheck, self).__init__(('4.8.9', '4.9.5', '4.10.1'), 'PURE-86636', msg)


class SystemSpaceInflationCheck(check_utils.VersionCheck):
    """Check if the array may be impacted by PURE-81922."""

    def __init__(self):
        # type: () -> None
        msg = 'System Space may inflate during and/or post-evacuation.'
        super(SystemSpaceInflationCheck, self).__init__(('4.8.12', '4.9.e', '4.10.6'), 'PURE-81922', msg)


class WSSDBadCapacityCheck(check_utils.Check):
    """Check for the presence of PURE-116769."""

    def __init__(self):
        # type: () -> None
        super(WSSDBadCapacityCheck, self).__init__(jira='PURE-116769')

    def run_test(self, evac_api):
        # type: (Any) -> None
        """If we are evacuating any WSSD devices, warn that capacity calculations may be wrong in Purity.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        purity_version = evac_api.get_latest_value('purity_version')
        if version_utils.compare_multiple_versions(purity_version, ('4.10.11', '5.1.0', '5.0.7')):
            self.passed = True
            self.details.append('Fixed in the current Purity version.')
        else:
            # Check if we have any WSSD devices and we are evacuating non-WSSD:
            found_wssd = False
            evac_non_wssd = False
            for component in itervalues(evac_api.devices_to_evac):
                if not _check_for_wssd(component):
                    evac_non_wssd = True
                    break
            if evac_non_wssd:
                for component in itervalues(evac_api.device_map['drives']):
                    if _check_for_wssd(component):
                        found_wssd = True
                        break
                if found_wssd:
                    msg = 'Capacity calculations are wrong due to PURE-116769, this can cause evac to stall.'
                    self.details.append(msg)
                    self.details.append('Consult Escalations to tune PS_EVAC_DATA_GC_BATCH_SZ.')
                    self.passed = False
                else:
                    self.details.append('No WSSD devices found in the array.')
                    self.passed = True
            elif not evac_api.devices_to_evac:
                self.passed = True
                self.details.append('No devices are being evacuated.')
            else:
                self.passed = True
                self.details.append('Evacuating WSSD(s), therefore, not affected by the AU calculation bug.')


class WSSDMismatchedSegioCheck(check_utils.Check):
    """Check for the presence of PURE-108757."""

    def __init__(self):
        # type: () -> None
        super(WSSDMismatchedSegioCheck, self).__init__(jira='PURE-108757')

    def run_test(self, evac_api):
        # type: (Any) -> None
        """If we are evacuating any WSSD devices, we may be at risk of a K-crumb issue.

        Arguments:
            evac_api (EvacHealthChecksAPI): An EvacHealthChecks API.
        """
        evac_wssd = False
        # Check if we are evacuating any WSSD devices:
        for component in itervalues(evac_api.devices_to_evac):
            if _check_for_wssd(component):
                evac_wssd = True
                break
        if not evac_wssd:
            self.details.append('No WSSD devices are being evacuated.')
            self.passed = True
        # K-Crumb risk before: 4.10.9, 5.0.5
        else:
            purity_version = evac_api.get_latest_value('purity_version')
            if not version_utils.compare_multiple_versions(purity_version, ('4.10.9', '5.0.5')):
                self.details.append('The array is at risk of K-crumbs.  Consult escalations.')
                self.passed = False
            else:
                self.details.append('Fixed in the current Purity version.')
                self.passed = True


class UnhealthyDrivesCheck(check_utils.Check):
    """Check for any drives which are not in a healthy state."""

    def run_test(self, evac_api):
        # type: (Any) -> None
        """Ensure that there are no drives in an unhealthy state."""
        unhealthy_drives = []
        for drive in itervalues(evac_api.device_map['drives']):
            if drive.status != 'Healthy':
                unhealthy_drives.append(drive.full_name)
        if unhealthy_drives:
            self.details.append('Unhealthy drives found: "{}".'.format(', '.join(unhealthy_drives)))
            self.passed = False
        else:
            self.details.append('No unhealthy drives found.')
            self.passed = True


class EvacHealthChecks(check_utils.Exam):
    """All checks to perform prior to doing an evacuation."""

    def __init__(self):
        # type: () -> None
        super(EvacHealthChecks, self).__init__(checks={
            'Capacity Override Tunable': CapacityOverrideTunableCheck(),
            'Controller Hardware Compatibility': ControllerHardwareCompatibility(),
            'Deny Eviction Tunable': DenyEvictionTunableCheck(),
            'Early Evict': EarlyEvict(),
            'Evac Devices Exist': EvacDevicesExist(),
            'Evacuation Stall': EvacStallCheck(),
            'Latency During Rebuild': LatencyDuringRebuildCheck(),
            'Long Secure Erase': LongSecureErase(),
            'K-Crumb with //X': KCrumbWithX(),
            'Mishomed Drives': MishomedDrives(),
            'Parallel GC Funnels': ParallelGCFunnels(),
            'Purity Version Compatibility': PurityVersionCompatibility(),
            'SAS Cabling': SASCabling(),
            'Segment Guard Failover': SegmentGuardFailoverCheck(),
            'Shard Rebuild Risk': ShardRebuildRiskCheck(),
            'Slow SAN Startup': SlowSANStartupCheck(),
            'System Space Inflation': SystemSpaceInflationCheck(),
            'WSSD Capacity Miscalculation': WSSDBadCapacityCheck(),
            'WSSD Mismatched SegIO': WSSDMismatchedSegioCheck(),
            'Unhealthy Drives': UnhealthyDrivesCheck(),
        })


@debug_utils.debug
def main():
    # type: () -> None
    """Parse user arguments, run all health checks."""
    parser = interactive_utils.photon_argparse(__doc__)
    args = parser.parse_args()
    array = api.FlashArray(fqdn=args.fqdn, log_path=args.log_path, start=args.start, end=args.end, from_latest='1h',
                           files=args.files)
    exam = EvacHealthChecks()
    exam.run_tests(array)
    exam.print_exam_results()


if __name__ == '__main__':
    main()
