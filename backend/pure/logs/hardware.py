"""Contains parser definitions on how to extract data from the hardware log ."""

import ast
import collections
import logging
import re

from six import iteritems

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import DefaultDict
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

from photon.lib import parser_utils
from photon.lib import format_utils
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)
# pylint: disable=too-few-public-methods, too-many-public-methods, invalid-name, line-too-long

# TODO: Simplify/Merge logic for things which regex within raw_hw_logs.
# TODO: Implement other things in hardware log that we don't need right now.
# expander_edfbinfo, expander_serdesinfo_rx, expander_serdesinfo_tx, luigi_dbg, finddrive_json, sel_raw


class HardwareFormData(parser_utils.FormData):
    """Forms used by the HardwareParser."""

    bmc_info = parser_utils.TarfileForm(
        # Get all BMC log lines.
        text_to_match=None,
        sub_file_pattern='*_bmc',
        include_filename=True
    )
    cpu_interrupts = parser_utils.TarfileForm(
        # Get all CPU Interrupts log lines.
        text_to_match=None,
        sub_file_pattern='*_interrupts',
        include_filename=True
    )
    cpu_throttle = parser_utils.TarfileForm(
        # Get all CPU Throttle log lines.
        text_to_match=None,
        sub_file_pattern='*_cputhrottle',
        include_filename=True
    )
    ddump = parser_utils.TarfileForm(
        # Get all ddump log lines.
        text_to_match=None,
        sub_file_pattern='*_ddump',
        include_filename=True
    )
    df = parser_utils.TarfileForm(
        # Get all df log lines.
        text_to_match=None,
        sub_file_pattern='*_df',
        include_filename=True
    )
    dmi = parser_utils.TarfileForm(
        # Get all DMI log lines.
        text_to_match=None,
        sub_file_pattern='*_dmi',
        include_filename=True
    )
    drive_smart = parser_utils.TarfileForm(
        # Get all SMART log lines.
        text_to_match=None,
        sub_file_pattern='*_smart',
        include_filename=True
    )
    expander_counters = parser_utils.TarfileForm(
        # Get all expander counters log lines.
        text_to_match=None,
        sub_file_pattern='*_counters',
        include_filename=True
    )
    expander_show_logs = parser_utils.TarfileForm(
        # Get all expander show logs log lines.
        text_to_match=None,
        sub_file_pattern='*_showlogs',
        include_filename=True
    )
    expander_show_trace = parser_utils.TarfileForm(
        # Get all expander show trace log lines.
        text_to_match=None,
        sub_file_pattern='*_showtrace',
        include_filename=True
    )
    finddrive_all = parser_utils.TarfileForm(
        # Get all find drive log lines.
        text_to_match=None,
        sub_file_pattern='*_finddrive',
        include_filename=True
    )
    fru = parser_utils.TarfileForm(
        # Get all FRU log lines.
        text_to_match=None,
        sub_file_pattern='*_fru',
        include_filename=True
    )
    raw_hw_logs = parser_utils.TarfileForm(
        # Get all hw_logs lines.
        text_to_match=None,
        sub_file_pattern='hw_log_*',
    )
    hardware_check = parser_utils.TarfileForm(
        # Get all hwcheck log lines.
        text_to_match=None,
        sub_file_pattern='*_hwcheck',
        include_filename=True
    )
    ipmi_sensors = parser_utils.TarfileForm(
        # Get all sensor log lines.
        text_to_match=None,
        sub_file_pattern='*_sensor',
        include_filename=True
    )
    ls_pci = parser_utils.TarfileForm(
        # Get all list PCI log lines.
        text_to_match=None,
        sub_file_pattern='*_lspci',
        include_filename=True
    )
    ls_scsi = parser_utils.TarfileForm(
        # Get all list SCSI log lines.
        text_to_match=None,
        sub_file_pattern='*_lsscsi',
        include_filename=True
    )
    ls_usb = parser_utils.TarfileForm(
        # Get all list USB log lines.
        text_to_match=None,
        sub_file_pattern='*_lsusb',
        include_filename=True
    )
    mce = parser_utils.TarfileForm(
        # Get all MCE log lines.
        text_to_match=None,
        sub_file_pattern='*_mce',
        include_filename=True
    )
    meminfo = parser_utils.TarfileForm(
        # Get all meminfo log lines.
        text_to_match=None,
        sub_file_pattern='*_meminfo',
        include_filename=True
    )
    pci_train = parser_utils.TarfileForm(
        # Get all PCI Train log lines.
        text_to_match=None,
        sub_file_pattern='*_pcitrain',
        include_filename=True
    )
    purechassis = parser_utils.TarfileForm(
        # Get all Pure Chassis log lines.
        text_to_match=None,
        sub_file_pattern='*_purechassis',
        include_filename=True
    )
    purehw_list = parser_utils.TarfileForm(
        # Get all Pure Hardware log lines.
        text_to_match=None,
        sub_file_pattern='*_purehw',
        include_filename=True
    )
    sas_view = parser_utils.TarfileForm(
        # Get all sas log lines.
        text_to_match=None,
        sub_file_pattern='*_sas',
        include_filename=True
    )
    sel = parser_utils.TarfileForm(
        # Get all SEL log lines.
        text_to_match=None,
        sub_file_pattern='*_sel',
        include_filename=True
    )
    storage_view = parser_utils.TarfileForm(
        # Get all storage log lines.
        text_to_match=None,
        sub_file_pattern='*_storage',
        include_filename=True
    )


class HardwareLogData(parser_utils.LogData):
    """Manage forms for raw information to retrieve from hardware logs."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        hardware_forms = HardwareFormData()
        super(HardwareLogData, self).__init__({form: hardware_forms[form] for form in needed_forms})


class HardwareParser(parser_utils.ParallelLogParser):
    """Defines all hardware data parsing functions."""
    forms = HardwareFormData()
    fields = {
        'bmc_info': HardwareLogData(['bmc_info']),
        'controller_info': HardwareLogData(['raw_hw_logs']),
        'controller_mode': HardwareLogData(['raw_hw_logs']),
        'controller_model': HardwareLogData(['raw_hw_logs']),
        'controller_status': HardwareLogData(['raw_hw_logs']),
        'controller_version': HardwareLogData(['raw_hw_logs']),
        'cpu_interrupts': HardwareLogData(['cpu_interrupts']),
        'cpu_throttle': HardwareLogData(['cpu_throttle']),
        'ddump': HardwareLogData(['ddump']),
        'df': HardwareLogData(['df']),
        'dmi': HardwareLogData(['dmi']),
        'domain_name': HardwareLogData(['raw_hw_logs']),
        'drive_smart': HardwareLogData(['drive_smart']),
        'expander_counters': HardwareLogData(['expander_counters']),
        'expander_show_logs': HardwareLogData(['expander_show_logs']),
        'expander_show_trace': HardwareLogData(['expander_show_trace']),
        'finddrive_all': HardwareLogData(['finddrive_all']),
        'fru': HardwareLogData(['fru']),
        'hardware_check': HardwareLogData(['hardware_check']),
        'ipmi_sensors': HardwareLogData(['ipmi_sensors']),
        'ls_pci': HardwareLogData(['ls_pci']),
        'ls_scsi': HardwareLogData(['ls_scsi']),
        'ls_usb': HardwareLogData(['ls_usb']),
        'mce': HardwareLogData(['mce']),
        'meminfo': HardwareLogData(['meminfo']),
        'pci_train': HardwareLogData(['pci_train']),
        'purechassis': HardwareLogData(['purechassis']),
        'purehw_list': HardwareLogData(['purehw_list']),
        'purity_version': HardwareLogData(['raw_hw_logs']),
        'raw_hw_logs': HardwareLogData(['raw_hw_logs']),
        'sas_view': HardwareLogData(['sas_view', 'storage_view']),
        'sel': HardwareLogData(['sel']),
        'sel_critical_events': HardwareLogData(['sel']),
        'uptime': HardwareLogData(['raw_hw_logs']),
    }

    def _pull_lines(self, form_name):
        # type: (str) -> List[Tuple[Any, Any]]
        """Pull lines from a form."""
        raw_lines = self.get_form_lines(form_name)
        # Assumption: The first line of each yielded file will be the filename.
        # All sub-filenames include a datetime like: '20180115_060554'.
        file_sections = collections.defaultdict(list) # type: DefaultDict[str, List[str]]
        time_reg = re.compile(r'var\/log\/hw\_log\_directory\/.*?\_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})\_(?P<timestamp>\d{6})\_')
        # var/log/hw_log_directory/LUIGI2_ICU0999627L3JPK_20180115_060554_luigi_dbg_c
        timestamp = None
        for line in raw_lines:
            if 'var/log/hw_log_directory' in line:
                match = time_reg.search(line)
                if not match:
                    continue
                time_dict = match.groupdict()
                date = '/'.join([time_dict['month'], time_dict['day'], time_dict['year']])
                time = format_utils.split_str(time_dict['timestamp'], ':', 2)
                timestamp = time_utils.Timestamp('{} {}'.format(date, time))
            elif timestamp:
                file_sections[timestamp].append(line)
            else:
                continue
        # Convert the default dicts to a simple flat list of tuples.
        timestamped_sections = []
        for time, lines in iteritems(file_sections):
            timestamped_sections.append((time, lines))
        return timestamped_sections

    def get_bmc_info(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get BMC information."""
        # mc_info::Device ID                 : 32
        # mc_info::Device Revision           : 1
        # mc_info::Firmware Revision         : 0.06
        # mc_info::IPMI Version              : 2.0
        # mc_info::Manufacturer ID           : 0
        # mc_info::Manufacturer Name         : Unknown
        # mc_info::Product ID                : 1 (0x0001)
        # mc_info::Product Name              : Unknown (0x1)
        # mc_info::Device Available          : yes
        # mc_info::Provides Device SDRs      : no
        # mc_info::Additional Device Support :
        # mc_info::    Sensor Device
        # mc_info::    SDR Repository Device
        # mc_info::    SEL Device
        # mc_info::    FRU Inventory Device
        # mc_info::    IPMB Event Receiver
        # mc_info::    Bridge
        # mc_info::    Chassis Device
        # mc_info::Aux Firmware Rev Info     :
        # mc_info::    0x0a
        # mc_info::    0x55
        # mc_info::    0x00
        # mc_info::    0x10
        # mc_info::
        bmc_parsed_contents = []
        bmc_lines = self._pull_lines('bmc_info')
        for timestamp, lines in bmc_lines:
            contents = collections.defaultdict(list) # type: DefaultDict[str, List[str]]
            section_header = None
            for line in lines:
                sline = [part.strip() for part in line.split(':') if part.strip()]
                if len(sline) <= 1:
                    # ['mc_info']
                    # Reset the section header, we're no longer in a section.
                    section_header = None
                elif len(sline) == 2:
                    value = sline[1].strip()
                    if value in ('Additional Device Support', 'Aux Firmware Rev Info'):
                        section_header = value
                        continue
                    if section_header:
                        # We are in a sub-section, so this must be a value.
                        # ['mc_info', '0x0a']
                        contents[section_header].append(sline[1])
                    else:
                        # ['mc_info', 'Aux Firmware Rev Info]
                        section_header = sline[1]
                else:
                    # ['mc_info', 'Device ID', '32']
                    contents[sline[1]] = sline[2]
            bmc_parsed_contents.append((timestamp, dict(contents)))
        return bmc_parsed_contents

    def get_controller_info(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw list of controller states."""
        hw_log_lines = self.get_raw_hw_logs()
        controller_infos = []
        # Example Line:
        # Controller State: [{'status': 'ready', 'name': 'CT0', 'version': '4.10.5', 'mode': 'secondary',
        # 'model': 'FA-m70r2', 'local': False}, {'status': 'ready', 'name': 'CT1', 'version': '4.10.5',
        # 'mode': 'primary', 'model': 'FA-m70r2', 'local': True}]
        for timestamp, lines in hw_log_lines:
            for line in lines:
                if 'Controller State:' in line:
                    values = line.split(': ', 1)[1]
                    state = ast.literal_eval(values) # type: List[Dict[str, Any]]
                    if not isinstance(state, list):
                        error_msg = 'Got an unexpected value for controller state: "{}".'.format(state)
                        LOGGER.exception('ValueError: {}'.format(error_msg))
                        raise ValueError(error_msg)
                    ct_info = collections.defaultdict(dict) # type: DefaultDict[str, Dict[str, Any]]
                    for controller in state:
                        ct_info[controller['name']].update(controller)
                    controller_infos.append((timestamp, dict(ct_info)))
        return controller_infos

    def get_controller_mode(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the each controller's Primary/Secondary mode."""
        ct_mode = []
        ct_states = self.get_controller_info()
        for timestamp, state_dict in ct_states:
            ct_modes = {}
            for controller, controller_info in iteritems(state_dict):
                ct_modes[controller] = controller_info.get('mode')
            ct_mode.append((timestamp, ct_modes))
        return ct_mode

    def get_controller_model(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the each controller's hardware model."""
        ct_mode = []
        ct_states = self.get_controller_info()
        for timestamp, state_dict in ct_states:
            ct_modes = {}
            for controller, controller_info in iteritems(state_dict):
                ct_modes[controller] = controller_info.get('model')
            ct_mode.append((timestamp, ct_modes))
        return ct_mode

    def get_controller_status(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the each controller's I/O readiness status."""
        ct_mode = []
        ct_states = self.get_controller_info()
        for timestamp, state_dict in ct_states:
            ct_modes = {}
            for controller, controller_info in iteritems(state_dict):
                ct_modes[controller] = controller_info.get('status')
            ct_mode.append((timestamp, ct_modes))
        return ct_mode

    def get_controller_version(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the Purity Version for each controller."""
        purity_version = []
        ct_states = self.get_controller_info()
        for timestamp, state_dict in ct_states:
            ct_purity = {}
            for controller, controller_info in iteritems(state_dict):
                ct_purity[controller] = controller_info.get('version')
            purity_version.append((timestamp, ct_purity))
        return purity_version

    def get_cpu_interrupts(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw CPU Interrupts lines."""
        return self._pull_lines('cpu_interrupts')

    def get_cpu_throttle(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw CPU Throttle lines."""
        return self._pull_lines('cpu_throttle')

    def get_ddump(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw DDump lines."""
        # DDump has a bunch of carriage returns
        # that make it impossible to print normal lines, etc.
        # We're going to get rid of them!
        parsed_groups = []
        for timestamp, lines in self._pull_lines('ddump'):
            fixed_lines = []
            for line in lines:
                fixed_lines.append(line.rstrip())
            parsed_groups.append((timestamp, fixed_lines))
        return parsed_groups

    def get_df(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw 'df' lines."""
        return self._pull_lines('df')

    def get_dmi(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw DMI lines."""
        return self._pull_lines('dmi')

    def get_domain_name(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the Array's Domain name."""
        #       Network Domain Name: paylocity.com
        domain_name_results = []
        raw_lines = self.get_raw_hw_logs()
        for timestamp, lines in raw_lines:
            for line in lines:
                if 'Network Domain Name:' in line:
                    domain_name = line.split(':')[1].strip()
                    domain_name_results.append((timestamp, domain_name))
        return domain_name_results

    def get_drive_smart(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Drive SMART lines."""
        return self._pull_lines('drive_smart')

    def get_expander_counters(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Expander Counters lines."""
        return self._pull_lines('expander_counters')

    def get_expander_show_logs(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Expander Show Logs lines."""
        return self._pull_lines('expander_show_logs')

    def get_expander_show_trace(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw DDump lines."""
        return self._pull_lines('expander_show_trace')

    def get_finddrive_all(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Find Drive lines."""
        return self._pull_lines('finddrive_all')

    def get_fru(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw FRU lines."""
        return self._pull_lines('fru')

    def get_hardware_check(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Hardware Check lines."""
        return self._pull_lines('hardware_check')

    def get_ipmi_sensors(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the IPMI Sensors lines."""
        return self._pull_lines('ipmi_sensors')

    def get_ls_pci(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw List PCI lines."""
        return self._pull_lines('ls_pci')

    def get_ls_scsi(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw List SCSI lines."""
        return self._pull_lines('ls_scsi')

    def get_ls_usb(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw List USB lines."""
        return self._pull_lines('ls_usb')

    def get_mce(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw MCE lines."""
        return self._pull_lines('mce')

    def get_meminfo(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Memory Info lines."""
        return self._pull_lines('meminfo')

    def get_pci_train(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw PCI Train lines."""
        return self._pull_lines('pci_train')

    def get_purechassis(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Pure Chassis lines."""
        return self._pull_lines('purechassis')

    def get_purity_version(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the Array's Purity version."""
        #      Purity version: 4.10.5
        version_results = []
        raw_lines = self.get_raw_hw_logs()
        for timestamp, lines in raw_lines:
            for line in lines:
                if 'Purity version:' in line:
                    p_version = line.split(':', 1)[1].strip()
                    version_results.append((timestamp, p_version))
        return version_results

    def get_purehw_list(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw Pure Hardware lines."""
        return self._pull_lines('purehw_list')

    def get_raw_hw_logs(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw hw_logs lines."""
        return self._pull_lines('raw_hw_logs')

    def get_sas_view(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw SAS lines."""
        # PT-1999: The name of 'sas_view' was changed in purity 5.1+.
        # When asking for 'sas_view' it is expected to get either 'sas_view' or 'storage_view'.
        return self._pull_lines('sas_view') or self._pull_lines('storage_view')

    def get_sel(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the raw SEL lines."""
        return self._pull_lines('sel')

    def get_sel_critical_events(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get critical parsed SEL lines."""
        #  'sel_elist::   1 | 05/05/2017 | 22:04:21 | Event Logging Disabled SEL | Log area reset/cleared | Asserted\n',
        #  'sel_elist::\n']
        critical_events = ('Correctable ECC',
                           'Uncorrectable ECC',
                           'CPU_CATERR',
                           'Transition to')
        parsed_sel = []
        raw_sel = self._pull_lines('sel')
        for timestamp, sel in raw_sel:
            for line in sel:
                if 'sel_elist' not in line:
                    continue
                cleaned = line.replace('sel_elist::', '').strip()
                if not cleaned:
                    # '\n' will become '' after the strip().
                    continue
                if any(keyword in cleaned for keyword in critical_events):
                    parsed_sel.append((timestamp, cleaned))
        return parsed_sel

    def get_uptime(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the Array's Linux Uptime."""
        #      System Uptime:  117 days, 15:42:35.260000
        uptime_results = []
        raw_lines = self.get_raw_hw_logs()
        for timestamp, lines in raw_lines:
            for line in lines:
                if 'System Uptime:' in line:
                    uptime = line.split(':', 1)[1].strip()
                    uptime_results.append((timestamp, uptime))
        return uptime_results
