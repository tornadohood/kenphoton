"""Contains parser definitions on how to extract data from the frequentdiagnostics log."""

import logging

from collections import defaultdict

try:
    # pylint: disable=redefined-builtin
    from itertools import izip as zip
except ImportError:
    # This only exists in Python 2.
    pass

import six
import ujson

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

from photon.lib import parser_utils
from photon.lib import dict_utils
from photon.lib import format_utils
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)
# pylint: disable=too-few-public-methods, too-many-public-methods, invalid-name, line-too-long


class FDiagFormData(parser_utils.FormData):
    """Forms used by the FDiagnosticsParser."""

    diagnostics = parser_utils.SimpleTextForm(
        text_to_match='] Diagnostics: {',
        regexes={},
    )


class FDiagLogData(parser_utils.LogData):
    """Manage information about a piece Data from the logs."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        fdiag_forms = FDiagFormData()
        super(FDiagLogData, self).__init__({form: fdiag_forms[form] for form in needed_forms})


class FDiagnosticsParser(parser_utils.ParallelLogParser):
    """Defines all fdiag data parsing functions."""
    forms = FDiagFormData()
    _fields = {
        'actual_system_space',
        'array_id',
        'array_name',
        'cap_for_hidden',
        'capacity',
        'controller_num',
        'controller_model',
        'controller_model_local',
        'controller_serial',
        'copyout_error_extents',
        'data_reduction',
        'domain_name',
        'eradicated_vol_phys',
        'fdiags',
        'fdiags_unflattened',
        'is_primary',
        'live_physical_space',
        'local_time',
        'logical_discrepancy',
        'newly_written_space',
        'num_shelves',
        'pgroup_settings',
        'pgroup_snaps',
        'physical_discrepancy',
        'physical_space',
        'pslun_names',
        'purealert_list',
        'pureapp_list',
        'puredb_list_drives',
        'puredb_list_job',
        'puredrive_list',
        'purehw_list',
        'puremessage_list_audit',
        'purepod_list_array',
        'purity_version',
        'reclaimable_space',
        'replbond_info',
        'reported_pyramid',
        'reported_raid',
        'san_targets',
        'sas_port_info',
        'serials',
        'shared_space',
        'snapshot_space',
        'ssd_capacity',
        'ssd_mapped',
        'system_space',
        'thin_provisioning',
        'total_reduction',
        'triage_error',
        'unknown_space',
        'unreachable_extent_phys',
        'unreported_pyramid',
        'unreported_raid',
        'unreported_ratio',
        'unreported_space',
        'vector_space',
        'visible_system_space',
        'volume_space',
    }
    fields = {field: FDiagLogData(['diagnostics']) for field in _fields}

    def _pull_value(self, dict_map):
        # type: (List[str]) -> List[Tuple[time_utils.Timestamp, Any]]
        """Delve into a multi-level fdiags dict to get a particular nested sub-value."""
        fdiag_values = []
        for timestamp, fdiags in self.get_field('fdiags'):
            fdiags_tree = dict_utils.DictTree(fdiags)
            try:
                value = fdiags_tree.get_branch_value(dict_map)
            except KeyError:
                # The key mapping does not exist within this dict_tree.
                value = None
            fdiag_values.append((timestamp, value))
        return sorted(fdiag_values)

    def get_array_id(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for array_id."""
        results = []
        net_ids = self._pull_value(['controller.info', 'net_array_id'])
        fc_ids = self._pull_value(['controller.info', 'fc_array_id'])
        iscsi_ids = self._pull_value(['controller.info', 'iscsi_array_id'])
        # Array ID is composed of: 'net_id-fc_id-iscsi_id'
        for index, value_tuple in enumerate(net_ids):
            timestamp = value_tuple[0]
            if not value_tuple[1]:
                results.append((timestamp, value_tuple[1]))
                continue
            net_id = str(value_tuple[1])
            fc_id = str(fc_ids[index][1])
            iscsi_id = str(iscsi_ids[index][1])
            # Append the tuple: (timestamp, array_id)
            results.append((timestamp, '-'.join([net_id, fc_id, iscsi_id])))
        return results

    def get_array_name(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for array_name."""
        return self._pull_value(['controller.info', 'array_name'])

    def get_actual_system_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, int]]
        """Parse all fdiags for actual_system_space space."""
        return self._pull_value(['puredb.dump.health', 'space.actual_system_space', 'value'])

    def get_cap_for_hidden(self):
        # type: () -> List[Tuple[time_utils.Timestamp, int]]
        """Parse all fdiags for cap_for_hidden space."""
        return self._pull_value(['puredb.dump.health', 'space.cap_for_hidden', 'value'])

    def get_capacity(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for capacity."""
        return self._pull_value(['purearray.list.space', 'capacity'])

    def get_controller_num(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for ct_num."""
        return self._pull_value(['controller.info', 'controller_name'])

    def get_controller_model(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for controller_model to mimic diagnostics.log."""
        # Expected output:
        # {'Model': ['FA-420', 'FA-420'], 'Name': ['CT0', 'CT1']}
        ct_model = []
        for timestamp, ctlr_info in self._pull_value(['purearray.list.controller']):
            model_dict = {
                'Model': [],
                'Name': [],
            }
            for ct_num, ct_info in six.iteritems(ctlr_info):
                model_dict['Model'].append(ct_info['model'])
                model_dict['Name'].append(ct_num)
            ct_model.append((timestamp, model_dict))
        return ct_model

    def get_controller_model_local(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for ct_model from the controller the log came from."""
        model_idents = {
            'beta medium':           'FA-300',
            'HS-1235T-ATX':          'FA-300',
            'gamma_minus medium':    'FA-405',
            '0JP31P':                'FA-420',
            'gamma medium':          'FA-420',
            'gamma_plus medium':     'FA-450',
            'platinum_sas_a small':  'FA-m20',
            'platinum_sas_a medium': 'FA-m50',
            'platinum_sas_a big':    'FA-m70',
            'platinum_sas_b tiny':   'FA-m10r2',
            'platinum_sas_b small':  'FA-m20r2',
            'platinum_sas_b medium': 'FA-m50r2',
            'platinum_sas_b big':    'FA-m70r2',
            'platinum_sas_b huge':   'FA-m70r2',
        }
        ct_model = []
        for timestamp, model in self._pull_value(['controller.info', 'controller_model']):
            if not model:
                ct_model.append((timestamp, model))
                continue
            if isinstance(model, list):
                # The lists are generally formatted like this
                # 'controller_model': ['gamma', 'medium']
                model = ' '.join(model)
            # We need to translate the model type we got from CA to the standard FA-XXX name
            if model in model_idents:
                model = model_idents[model]
            ct_model.append((timestamp, model))
        return ct_model

    def get_controller_serial(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for ct_serial."""
        return self._pull_value(['controller.info', 'controller_sn'])

    def get_copyout_error_extents(self):
        # type: () -> List[Tuple[time_utils.Timestamp, str]]
        """Parse all fdiags for copyout_error_extents space."""
        values = self._pull_value(['puredb.dump.health', 'space.copyout_error_extents', 'value'])
        results = []
        # These are a count so we need a string not an int.
        for timestamp, value in values:
            if value:
                value = str(value)
            results.append((timestamp, value))
        return results

    def get_data_reduction(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for data_reduction."""
        return self._pull_value(['purearray.list.space', 'data_reduction'])

    def get_domain_name(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for domain_name."""
        return self._pull_value(['controller.info', 'sender_domain'])

    def get_eradicated_vol_phys(self):
        # type: () -> List[Tuple[time_utils.Timestamp, int]]
        """Parse all fdiags for eradicated_vol_phys space."""
        return self._pull_value(['puredb.dump.health', 'space.eradicated_vol_phys', 'value'])

    def get_fdiags(self):
        # type: () -> List[Tuple[Any, Dict[str, Any]]]
        """Flatten the frequent diagnostics contents."""
        parsed = []
        for timestamp, fdiags in self.get_fdiags_unflattened():
            # Flatten the contents of the JSON Blob for easier navigation.
            parsed.append((timestamp, _flatten_json_section(fdiags)))
        return parsed

    def get_fdiags_unflattened(self):
        # type: () -> List[Tuple[Any, Dict[str, Any]]]
        """Parse the frequent diagnostics contents."""
        parsed = []
        for diag_line in self.get_form_lines('diagnostics'):
            time_str, contents = diag_line.split(' [monitord:WARNING] Diagnostics: ', 1)
            timestamp = time_utils.Timestamp(time_str)
            json_blob = ujson.loads(contents, precise_float=True)
            parsed.append((timestamp, json_blob))
        return parsed

    def get_is_primary(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for is_primary."""
        return self._pull_value(['controller.info', 'is_primary'])

    def get_live_physical_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for live physical space."""
        return self._pull_value(['puredb.dump.health', 'space.live_physical', 'value'])

    def get_local_time(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for local_time."""
        return self._pull_value(['controller.info', 'local_time'])

    def get_logical_discrepancy(self):
        # type: () -> List[Tuple[time_utils.Timestamp, int]]
        """Parse all fdiags for logical_discrepancy space."""
        return self._pull_value(['puredb.dump.health', 'space.logical_discrepancy', 'value'])

    def get_newly_written_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for live physical space."""
        return self._pull_value(['puredb.dump.health', 'space.space_newly_written', 'value'])

    def get_num_shelves(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for num_shelves."""
        hw_parts = []
        for timestamp, parts in self._pull_value(['purehw.list']):
            if not parts:
                hw_parts.append((timestamp, parts))
                continue
            num_parts = len([part for part in six.itervalues(parts) if part['type'] == 'storage_shelf'])
            hw_parts.append((timestamp, num_parts))
        return hw_parts

    def get_pgroup_settings(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for pgroup_settings."""
        settings = []
        results = self._pull_value(['purepgroup.list.schedule'])
        for timestamp, pgroups in results:
            if not pgroups:
                settings.append((timestamp, pgroups))
                continue
            pgroup_settings = {}
            for pgroup_name, pgroup in six.iteritems(pgroups):
                pgroup_settings[pgroup_name] = pgroup
            settings.append((timestamp, pgroup_settings))
        return settings

    def get_pgroup_snaps(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for pgroup snapshot information."""
        return self._pull_value(['purepgroup.list.snap'])

    def get_physical_discrepancy(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for physical discrepancy space."""
        return self._pull_value(['puredb.dump.health', 'space.physical_discrepancy', 'value'])

    def get_physical_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for physical_space."""
        physical_space = []
        for timestamp, space_info in self._pull_value(['purearray.list.space']):
            if not space_info:
                physical_space.append((timestamp, space_info))
                continue
            volume = format_utils.to_raw(space_info['volumes'], 'binary_bytes')
            shared = format_utils.to_raw(space_info['shared_space'], 'binary_bytes')
            snapshots = format_utils.to_raw(space_info['snapshots'], 'binary_bytes')
            system_space = format_utils.to_raw(space_info['system'], 'binary_bytes')
            physical_space.append((timestamp, int(volume + shared + snapshots + system_space)))
        return physical_space

    def get_pslun_names(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for pslun_names."""
        pslun_names = []
        for timestamp, purevol in self._pull_value(['purevol.list.space']):
            if not purevol:
                pslun_names.append((timestamp, purevol))
                continue
            names = {}
            for volume_name, volume in six.iteritems(purevol):
                if volume_name == '(total)':
                    continue
                if 'id' in volume:
                    pslun = str(volume['id'])
                elif 'id' in volume.get('space', {}):
                    pslun = str(volume['space']['id'])
                else:
                    continue
                names[pslun] = volume_name
            pslun_names.append((timestamp, names))
        return pslun_names

    def get_purealert_list(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for purealert_list."""
        return self._pull_value(['purealert.list'])

    def get_pureapp_list(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for pureapp_list."""
        return self._pull_value(['pureapp.list'])

    def get_puredb_list_drives(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for puredb_list_drives."""
        return self._pull_value(['puredb.list.drives'])

    def get_puredb_list_job(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for puredb_list_job."""
        return self._pull_value(['puredb.list.job'])

    def get_puredrive_list(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for puredrive_list."""
        return self._pull_value(['puredrive.list'])

    def get_purehw_list(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for purehw_list."""
        return self._pull_value(['purehw.list'])

    def get_puremessage_list_audit(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for puremessage_list_audit."""
        return self._pull_value(['puremessage_list_audit'])

    def get_purepod_list_array(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for purepod_list_array."""
        return self._pull_value(['purepod.list.array'])

    def get_purity_version(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for purity_version."""
        return self._pull_value(['controller.info', 'version', 'product_version'])

    def get_reclaimable_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for reclaimable space."""
        return self._pull_value(['puredb.dump.health', 'space.reclaimable', 'value'])

    def get_replbond_info(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for replication speed and interfaces."""
        replbond_info = []
        for timestamp, interfaces in self._pull_value(['purenetwork.list']):
            if not interfaces:
                replbond_info.append((timestamp, interfaces))
                continue
            for iface_name, config in six.iteritems(interfaces):
                if iface_name != 'replbond':
                    continue
                # Depending on Purity version we either have 'status' = enabled or 'enabled' = True
                if not config.get('status') == 'enabled' and not config.get('enabled'):
                    continue
                slave_ifs = config.get('slaves', [])
                if not slave_ifs:
                    break
                slaves = ', '.join(sorted(slave_ifs))
                if config['speed'] == 10**9:
                    speed = '1G'
                elif config['speed'] == 10**10:
                    speed = '10G'
                else:
                    speed = config['speed']
                if not (slaves and speed):
                    slaves = "Replication not enabled"
                    speed = "Replication not enabled"
                replbond_info.append((timestamp, {'Replication Speed': speed, 'Replication Slaves': slaves}))
        return replbond_info

    def get_reported_pyramid(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for reported pyramid space."""
        return self._pull_value(['puredb.dump.health', 'space.reported_pyramid', 'value'])

    def get_reported_raid(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for reported RAID space."""
        return self._pull_value(['puredb.dump.health', 'space.reported_raid', 'value'])

    def get_san_targets(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for san_targets."""
        san_targets = []
        for timestamp, array_ports in self._pull_value(['pureport.list']):
            if not array_ports:
                san_targets.append((timestamp, array_ports))
                continue
            targets = {'iqn': {}, 'wwn': {}}

            for port_name, port in six.iteritems(array_ports):
                iqn = port.get('iqn')
                wwn = port.get('wwn')
                if iqn:
                    targets['iqn'][port_name] = iqn
                elif wwn:
                    # Convert the raw WWN value to a human readable format.
                    readable_wwn = format_utils.split_str(wwn, delim=':', every=2)
                    targets['wwn'][port_name] = readable_wwn
            san_targets.append((timestamp, targets))
        return san_targets

    def get_sas_port_info(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for sas_port_info."""
        sas_port_info = []
        sections = ('index', 'slot', 'speed', 'status')
        for timestamp, purehw in self._pull_value(['purehw.list']):
            if not purehw:
                sas_port_info.append((timestamp, purehw))
                continue
            sas_ports = {'ct0': {}, 'ct1': {}}
            for part_name, part in six.iteritems(purehw):
                full_part_name = part_name.lower()
                if not full_part_name.startswith('ct'):
                    continue
                if part['type'] == 'sas_port':
                    ctlr, part_name = part['name'].lower().split('.', 1)
                    sas_port = {}
                    for info in sections:
                        if info in part:
                            sas_port[info] = part[info]
                    wwn = hex(part.get('wwn')).replace('0x', '').upper()
                    sas_port['wwn'] = ':'.join([x+y for x, y in zip(wwn[::2], wwn[1::2])])
                    sas_ports[ctlr][part_name] = sas_port
            sas_port_info.append((timestamp, sas_ports))
        return sas_port_info

    def get_serials(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for serials."""
        serials = []
        enclosure_types = ['chassis', 'controller', 'storage_shelf']
        for timestamp, purehw in self._pull_value(['purehw.list']):
            if not purehw:
                serials.append((timestamp, purehw))
                continue
            enclosures = [part for part in six.itervalues(purehw) if part['type'] in enclosure_types]
            hw_serials = {}
            for part in enclosures:
                name = part['name'].lower()
                serial = part['handle'].split('_')[-1]
                if name == 'ctx':
                    name = self.get_field('ct_num')
                hw_serials[name] = serial.lower()
            serials.append((timestamp, hw_serials))
        return serials

    def get_shared_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for shared_space."""
        return self._pull_value(['purearray.list.space', 'shared_space'])

    def get_snapshot_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for snapshot_space."""
        return self._pull_value(['purearray.list.space', 'snapshots'])

    def get_ssd_capacity(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for ssd_capacity."""
        ssd_capacity = []
        for timestamp, puredrive in self._pull_value(['puredrive.list']):
            if not puredrive:
                ssd_capacity.append((timestamp, puredrive))
                continue
            healthy_drives = [drv for drv in six.itervalues(puredrive) if drv['status'] == 'healthy']
            # PT-2242: Check status before type.
            # If a drive has a status of 'unused', then it won't have a type key.
            capacity = sum([int(drive['capacity']) for drive in healthy_drives if drive['type'] == 'SSD'])
            ssd_capacity.append((timestamp, int(capacity)))
        return ssd_capacity

    def get_ssd_mapped(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for ssd_mapped."""
        return self._pull_value(['puredb.list.ssd_mapped', 'bytes'])

    def get_system_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for system_space."""
        return self._pull_value(['purearray.list.space', 'system'])

    def get_thin_provisioning(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for thin_provisioning."""
        return self._pull_value(['purearray.list.space', 'thin_provisioning'])

    def get_total_reduction(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for total_reduction."""
        return self._pull_value(['purearray.list.space', 'total_reduction'])

    def get_triage_error(self):
        # type: () -> List[Tuple[time_utils.Timestamp, int]]
        """Parse all fdiags for triage_error space."""
        return self._pull_value(['puredb.dump.health', 'space.triage_error', 'value'])

    def get_unknown_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for unknown space."""
        return self._pull_value(['puredb.dump.health', 'space.space_summary_unknown', 'value'])

    def get_unreachable_extent_phys(self):
        # type: () -> List[Tuple[time_utils.Timestamp, str]]
        """Parse all fdiags for unreachable_extent_phys space."""
        values = self._pull_value(['puredb.dump.health', 'space.unreachable_extent_phys', 'value'])
        results = []
        # These are a count so we need a string not an int.
        for timestamp, value in values:
            if value:
                value = str(value)
            results.append((timestamp, value))
        return results

    def get_unreported_pyramid(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for unreported pyramid space."""
        return self._pull_value(['puredb.dump.health', 'space.unreported_pyramid', 'value'])

    def get_unreported_raid(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for unreported RAID space."""
        return self._pull_value(['puredb.dump.health', 'space.unreported_raid', 'value'])

    def get_unreported_ratio(self):
        # type: () -> List[Tuple[time_utils.Timestamp, float]]
        """Parse all fdiags for unreported_ratio space."""
        return self._pull_value(['puredb.dump.health', 'space.unreported_ratio', 'value'])

    def get_unreported_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for unreported_space."""
        unreported_space = []
        # Diagnosing: High System/Unreported Space wiki.
        # https://wiki.purestorage.com/pages/viewpage.action?pageId=23995245
        # unreported = ssd_mapped - ((volume + shared + snapshots) / 0.778   # 0.778 == 1 - 2/9
        ssd_mapped = self.get_field('ssd_mapped')
        shared_space = self.get_field('shared_space')
        snapshot_space = self.get_field('snapshot_space')
        volume_space = self.get_field('volume_space')
        for index, mapped_tuple in enumerate(ssd_mapped):
            timestamp = mapped_tuple[0]
            if not mapped_tuple[1]:
                unreported_space.append((timestamp, mapped_tuple[1]))
                continue
            mapped = mapped_tuple[1]
            volume = volume_space[index][1]
            shared = shared_space[index][1]
            snapshot = snapshot_space[index][1]
            used = volume + shared + snapshot
            unreported = int(mapped - (used / 0.778))
            if unreported < 0:
                unreported = 0
            unreported_space.append((timestamp, unreported))
        return unreported_space

    def get_visible_system_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, int]]
        """Parse all fdiags for visible_system_space space."""
        return self._pull_value(['puredb.dump.health', 'space.visible_system_space', 'value'])

    def get_volume_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for volume_space."""
        return self._pull_value(['purearray.list.space', 'volumes'])

    def get_vector_space(self):
        # type: () -> List[Tuple[time_utils.Timestamp, Any]]
        """Parse all fdiags for vector space."""
        return self._pull_value(['puredb.dump.health', 'space.vector_space', 'value'])


def _flatten_json_section(json_blob):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """Flatten a section of the JSON blob by using sub-keys."""
    flattened = defaultdict(dict)
    for section, contents in six.iteritems(json_blob):
        # PT-2160: puredb list drives needs own logic otherwise all drives are not found.
        if section == 'puredb.list.drives':
            flattened[section] = contents
            continue
        if isinstance(contents, list):
            if len(contents) == 1:
                flattened[section] = contents[0]
            else:
                temp = {}
                for item in contents:
                    if isinstance(item, dict):
                        if 'name' in item:
                            temp[item['name']] = item
                        else:
                            temp.update(item)
                    else:
                        # We cannot reliably unpack this further.
                        temp = contents
                        break
                flattened[section] = temp
        elif isinstance(contents, dict):
            flattened[section] = _flatten_json_section(contents)
        else:
            flattened[section] = contents
    return dict(flattened)
