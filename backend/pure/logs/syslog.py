"""Contains parser definitions on how to extract data from the syslog."""

import collections
import logging

from photon.lib import parser_utils
from photon.lib import format_utils
from photon.lib import time_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)
HEX = r'0x\w+'
PCI = r'\d{4}:\d{2}:\d{2}'
TIMESTAMP = r'\w{3}\s+\d{1,2}\s\d{2}:\d{2}:\d{2}'
WWN = r'\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}'
SID = r'\w{2}:\w{2}:\w{2}'
SESS = r'\w{16}'
CMD = r'\w{16}'
IPADDR = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'

# We always hate the logging format, but it's faster.  We also know we have too few public methods,
# and we don't want to change that.
# pylint: disable=logging-format-interpolation, too-few-public-methods, line-too-long


class SyslogFormData(parser_utils.FormData):
    """ Forms used by the SyslogParser."""

    abort_cmd_found = parser_utils.SimpleTextForm(
        text_to_match='ABORT_TASK:',
        regexes={'default': r'(?P<timestamp>{timestamp}).*ABORT_TASK: (?P<desc>[\w\s]+).*sess (?P<session>\w+) cmd (?P<cmd>\w+) tag (?P<tag>0x\w+) tas (?P<tas>\w+) tr_state (?P<transport_state>0x\w+) t_state (?P<t_state>\w+) flags (?P<flags>\w+) f_state (?P<fabric_state>\w+) cdb (?P<cdb>0x\w+) pr_key (?P<pr_key>0x\w+) psop (?P<psop>\w+) lun (?P<lun>\d+) lba (?P<lba>0x\w+) length (?P<length>0x\w+)'.format(timestamp=TIMESTAMP)},
    )
    ce_events = parser_utils.SimpleTextForm(
        # From /m arrays.
        # Jan 24 19:35:33 fradcb4psp005-ct1 kernel: [39302.631375,14] EDAC MC1: 2 CE memory read error on CPU_SrcID#0_Ha#0_Chan#1_DIMM#1--DIMM_B1 (channel:1 slot:1 page:0x7e45cf9 offset:0xf80 grain:32 syndrome:0x0 -  OVERFLOW area:DRAM err_code:0001:0091 socket:0 ha:0 channel_mask:2 rank:7)
        text_to_match='CE memory',
        regexes={'default': r'(?P<timestamp>{timestamp}).*EDAC\sMC[01]:\s(?P<ce_mem_count>\d+)\sCE\smemory'.format(timestamp=TIMESTAMP)}
    )
    els_notify = parser_utils.SimpleTextForm(
        # Jan  4 16:20:01 fr1-m20-01-admin-ct0 kernel: [4758570.613361,09] qla2xxx 0000:82:00.0: ELS imm notify 0x03: (nport valid 0) loop_id 0x0002 s_id 01:08:00 wwn 10:00:00:00:c9:f3:a7:da exch 0x11a1e0 ox_id 0x1c
        text_to_match='ELS imm notify',
        regexes={'default': r'(?P<timestamp>{timestamp}).*\w+-(?P<ctrl>ct\d)\s.*(?P<pci_addr>{pci}).*ELS imm notify (?P<els>0x\w+):\s\(nport valid\s(?P<nport_valid>\d).*loop_id (?P<loop_id>0x\w+) s_id\s(?P<s_id>{sid})\swwn (?P<wwn>{wwn}) exch (?P<exch>0x\w+) ox_id (?P<ox_id>0x\w+)'.format(timestamp=TIMESTAMP, pci=PCI, sid=SID, wwn=WWN)},
    )
    expander = parser_utils.SimpleTextForm(
        # This catches lines related to foed being killed for whatever reason, resulting in a failover
        # TODO: PT-2103 find example
        text_to_match='expander',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    fc_firmware_dump = parser_utils.SimpleTextForm(
        # Feb 28 23:34:49 KDCPURE08-ct0 kernel: [1488234.264510,4f] qla2xxx [0000:03:00.3]-d015:30: Firmware dump saved to temp buffer (30/ffffc94160397000)
        text_to_match='Firmware dump saved',
        regexes={'default': r'(?P<timestamp>{}).*\[(?P<pci_addr>{}).(?P<port>\d+)\].*Firmware dump saved.*\((?P<tmp_buffer>.*)\)'.format(TIMESTAMP, PCI)},
    )
    fc_loop_up = parser_utils.SimpleTextForm(
        # Oct  4 18:36:56 DRC-PUREARRAY01-ct1 kernel: [10270075.730343,0f] qla2xxx [0000:06:00.1]-580a:11: LOOP UP detected (8 Gbps).
        text_to_match='LOOP UP detected',
        regexes={'default': r'(?P<timestamp>{timestamp}).*\w+-(?P<ctrl>ct\d)\s.*qla2xxx.*(?P<pci_addr>{pci}).*LOOP UP detected.*\((?P<speed>\w+\s*Gbps)\).*'.format(timestamp=TIMESTAMP, pci=PCI)},
    )
    fc_port_down = parser_utils.SimpleTextForm(
        # Jan  4 16:15:22 fr1-m20-01-admin-ct0 kernel: [4758291.501322,09] qla2xxx [0000:82:00.1]-500b:10: LINK DOWN detected for local port 52:4a:93:72:42:36:4a:01 (2 7 0 0).
        text_to_match='LINK DOWN',
        regexes={'default': r'(?P<timestamp>{}).*\w+-(?P<ctrl>ct\d)\s.*\[(?P<pci_addr>{pci}).*LINK DOWN.*local port (?P<wwn>{wwn})'.format(TIMESTAMP, pci=PCI, wwn=WWN)},
    )
    fc_port_gone = parser_utils.SimpleTextForm(
        # Jan  4 16:17:23 fr1-m20-01-admin-ct0 kernel: [4758412.161147,03] qla2xxx 0000:82:00.0: port gone, logging out/killing session: 10:00:00:00:c9:f3:a7:da state 0x1 flags 0x3 fc4_type 0x0 scan_state 1
        text_to_match='port gone',
        regexes={'default': r'(?P<timestamp>{}).*\w+-(?P<ctrl>ct\d)\s.*(?P<pci_addr>{pci}).*port gone, logging out.*: (?P<wwn>{wwn}) state (?P<port_state>{hex}) flags (?P<flags>{hex}) fc4_type (?P<fc4_type>{hex}) scan_state (?P<scan_state>\w+)'.format(TIMESTAMP, wwn=WWN, hex=HEX, pci=PCI)},
    )
    fc_port_updates = parser_utils.SimpleTextForm(
        # Nov 14 01:00:18 AP4P4PFA2-ct1 kernel: [   83.658603,17] qla2xxx [0000:03:00.1]-0000:10: PORT UPDATE loop_id:0x0000 state 0x4/PLOGI complete reason 0x600/PRLI received
        text_to_match='PORT UPDATE',
        regexes={'default': r'(?P<timestamp>{}).*\[(?P<pci_addr>{pci}).(?P<port>\d+)\].*PORT UPDATE.*state (?P<port_state>{hex})/(?P<action>\w+).*reason (?P<reason_code>{hex})/(?P<reason>.*)'.format(TIMESTAMP, hex=HEX, pci=PCI)},
    )
    fc_qlt_free = parser_utils.SimpleTextForm(
        # Jan 19 22:57:36 SLC-X70-ct1 kernel: [2627392.293400,14] qla2xxx 0000:03:00.3: qlt_free_session_done: se_sess ffff889b01eca240 / sess ffff88fe6c6ba240 from port 21:00:00:24:ff:59:bd:de loop_id 0x0e s_id 01:02:00 logout 1 keep 0 els_logo 0
        text_to_match='qlt_free_session_done: se_sess',
        regexes={'default': r'(?P<timestamp>{timestamp}).*\w+-(?P<ctrl>ct\d)\s.*(?P<pci_addr>{pci})\.(?P<port>\d+):.*qlt_free_session_done: se_sess\s*(?P<se_sess>{se_sess})\s*/\s*sess\s*(?P<sess>{sess})\s.*(?P<wwn>{wwn})\s*loop_id\s*(?P<loop_id>0x\w+).*s_id\s*(?P<s_id>{sid}).*'.format(timestamp=TIMESTAMP, sid=SID, wwn=WWN, se_sess=SESS, sess=SESS, pci=PCI)},
    )
    fc_rscn_changes = parser_utils.SimpleTextForm(
        # Nov 14 01:59:17 AP4P4PFA2-ct1 kernel: [ 3620.331528,2f] qla2xxx [0000:82:00.1]-5013:12: RSCN database changed -- s_id: 99:08:08
        text_to_match='RSCN database changed',
        regexes={'default': r'(?P<timestamp>{}).*\[(?P<pci_addr>{pci}).(?P<port>\d+)\].*RSCN database changed.*: (?P<source_id>.*)'.format(TIMESTAMP, pci=PCI)},
    )
    fc_session_added = parser_utils.SimpleTextForm(
        # Jul 15 14:03:31 slc-coz-ct0 kernel: [6666483.983369,0f] qla2xxx 0000:05:00.0: qla_target(0): (local) se_sess ffff88269395cf00 / sess ffff883fc55cc240 for wwn 21:00:00:24:ff:50:a8:a1 (loop_id 1, s_id 3:d:0, confirmed completion not supported) added
        text_to_match='confirmed completion not supported',
        regexes={'default': r'(?P<timestamp>{timestamp}).*\w+-(?P<ctrl>ct\d)\s.*(?P<pci_addr>{pci}).*sess (?P<sess>{sess}).*(?P<wwn>{wwn}).*s_id (?P<s_id>\w+:\w+:\w+).*added'.format(timestamp=TIMESTAMP, sess=SESS, wwn=WWN, pci=PCI)},
    )
    gather_hw_logs = parser_utils.IntervalForm(
        text_to_match='gather_hw_logs:',
        start_text=r'gather_hw_logs: process.*is starting',
        end_text=r'gather_hw_logs: process.*has completed',
        as_regex=True,
    )
    killing_foed = parser_utils.SimpleTextForm(
    # TODO: PT-2103 find example
        # This catches lines related to foed being killed for whatever reason, resulting in a failover
        text_to_match='killing foed',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    linux_version = parser_utils.SimpleTextForm(
    # TODO: PT-2103 find example
        # This catches reboots of the kernel where Linux has restarted
        text_to_match='Linux version',
    )
    mce_events = parser_utils.SimpleTextForm(
        # Found in FA-300/FA-400/FA//m controllers.
        # Dec  2 15:46:29 S01PURE1-ct0 kernel: [13897063.755982,00] sbridge: HANDLING MCE MEMORY ERROR
        text_to_match='HANDLING MCE MEMORY ERROR',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    npiv_disabled = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='tcm_qla2xxx_undepend_tpg: Received Disabled for NPIV port',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    npiv_enabled = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='tcm_qla2xxx_depend_tpg: Received Enable for NPIV port',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    offline_memory = parser_utils.SimpleTextForm(
        # May  1 11:40:20 gb61-24-ct0 kernel: [131160.076797,01] soft offline page 0xfb7206, total offline memory in page(4KB): 7
        text_to_match='total offline memory in page',
        regexes={'default': r'(?P<timestamp>{timestamp}).*total offline memory in page\((?P<size>\d+\wB)\)\:\s+(?P<count>\d+)'.format(timestamp=TIMESTAMP)}
    )
    portal_change = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='ps_change_portal_state',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    pureadm_change = parser_utils.SimpleTextForm(
        # TODO: PT-2103 find example
        # This catches failovers from manual purity administration
        text_to_match=':pureadm \(stop\|start\|restart\)',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    pureboot_reboot = parser_utils.SimpleTextForm(
        # This catches expected reboots from manual reboots.
        # TODO: PT-2103 find example
        text_to_match=':\(\|pureboot \)reboot',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    puredb_run_giveback = parser_utils.SimpleTextForm(
        # This catches expected reboots from a manual failover
        # TODO: PT-2103 find example
        text_to_match=':puredb run giveback',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    pureinstall = parser_utils.SimpleTextForm(
        # This catches expected reboots from pureinstalls
        # TODO: PT-2103 find example
        text_to_match=':pureinstall',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    puresetup = parser_utils.SimpleTextForm(
        # This catches reboots where we've replaced a controller
        # TODO: PT-2103 find example
        text_to_match=':puresetup',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    session_map = parser_utils.SimpleTextForm(
        # Jan 17 14:29:25 PURECON-ct1 kernel: [   90.063754,0f] qla2xxx 0000:03:00.1: set_sess_by_s_id: se_sess ffff88180f1e0580 / sess ffff88300eef9980 46:00:01 initiatorname: 20:00:00:25:b5:20:00:7f (have slot 0)
        text_to_match='initiatorname',
        regexes={'default': r'(?P<timestamp>{timestamp}).*\w+-(?P<ctrl>ct\d)\s.*(?P<pci_addr>{pci})\.(?P<port>\d+):\s+set_sess_by_s_id: se_sess\s+(?P<se_sess>{se_sess}) / sess\s(?P<sess>{sess})\s(?P<s_id>{sid}).*initiatorname:\s+(?P<wwn>{wwn}).*'.format(timestamp=TIMESTAMP, pci=PCI, se_sess=SESS, sess=SESS, sid=SID, wwn=WWN)},
    )
    upgrade = parser_utils.SimpleTextForm(
        # This catches upgrade lines.
        # TODO: PT-2103 find example
        text_to_match='UPGRADE',
        regexes={'default': r'(?P<timestamp>{timestamp})(?P<line>.*)'}
    )
    req_fail = parser_utils.SimpleTextForm(
        # This catches request failure lines.
        # TODO: PT-2103 find example
        text_to_match='REQ_FAIL',
    )


class SyslogData(parser_utils.LogData):
    """ Container for syslog data based on parser_utils.LogData."""
    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        syslog_forms = SyslogFormData()
        super(SyslogData, self).__init__({form: syslog_forms[form] for form in needed_forms})
        LOGGER.debug('SyslogData initialized with needed_forms: {}'.format(needed_forms))


class SyslogParser(parser_utils.ParallelLogParser):
    """Defines all syslog data parsing functions."""
    forms = SyslogFormData()
    fields = {
        # Each form will need itself at least, but might require additional fields.
        'abort_cmd_found': SyslogData(['abort_cmd_found']),
        'ce_events': SyslogData(['ce_events']),
        'els_notify': SyslogData(['els_notify']),
        'expander': SyslogData(['expander']),
        'fc_firmware_dump': SyslogData(['fc_firmware_dump']),
        'fc_loop_up': SyslogData(['fc_loop_up']),
        'fc_port_down': SyslogData(['fc_port_down']),
        'fc_port_gone': SyslogData(['fc_port_gone']),
        'fc_port_updates': SyslogData(['fc_port_updates']),
        'fc_rscn_changes': SyslogData(['fc_rscn_changes']),
        'fc_session_added': SyslogData(['fc_session_added']),
        'fc_qlt_free': SyslogData(['fc_qlt_free']),
        'gather_hw_logs': SyslogData(['gather_hw_logs']),
        'killing_foed': SyslogData(['killing_foed']),
        'linux_version': SyslogData(['linux_version']),
        'mce_counts': SyslogData(['mce_events']),
        'mce_events': SyslogData(['mce_events']),
        'npiv_disabled': SyslogData(['npiv_disabled']),
        'npiv_enabled': SyslogData(['npiv_enabled']),
        'offline_memory': SyslogData(['offline_memory']),
        'portal_change': SyslogData(['portal_change']),
        'pureadm_change': SyslogData(['pureadm_change']),
        'pureboot_reboot': SyslogData(['pureboot_reboot']),
        'puredb_run_giveback': SyslogData(['puredb_run_giveback']),
        'pureinstall': SyslogData(['pureinstall']),
        'puresetup': SyslogData(['puresetup']),
        'session_map': SyslogData(['session_map']),
        'upgrade': SyslogData(['upgrade']),
        'req_fail': SyslogData(['req_fail']),
    }

    def _pull_from_interval(self, form_name):
        # type: (str) -> List[Tuple[Any, Any]]
        """Get timestamp tuple from interval form."""
        timestamped_results = []
        results = self.get_form_lines(form_name)
        for result in results:
            timestamp = time_utils.get_timestamp_from_line(result[0])
            timestamped_results.append((timestamp, result))
        return timestamped_results

    def _pull_from_line(self, form_name):
        # type: (str) -> List[Tuple[Any, Any]]
        """Get timestamp tuple from lines."""
        timestamped_results = []
        results = self.get_form_lines(form_name)
        for line in results:
            timestamp = time_utils.get_timestamp_from_line(line)
            timestamped_results.append((timestamp, line))
        return timestamped_results

    def get_abort_cmd_found(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for abort_cmd_found."""
        return self.pull_from_regex('abort_cmd_found')

    def get_ce_events(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for ce_events."""
        return self.pull_from_regex('ce_events')

    def get_els_notify(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for els_notify."""
        return self.pull_from_regex('els_notify')

    def get_expander(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for expander."""
        return self._pull_from_line('expander')

    def get_fc_firmware_dump(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_firmware_dump."""
        return self.pull_from_regex('fc_firmware_dump')

    def get_fc_loop_up(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_loop_up."""
        return self.pull_from_regex('fc_loop_up')

    def get_fc_port_down(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_port_down."""
        return self.pull_from_regex('fc_port_down')

    def get_fc_port_gone(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_port_gone."""
        return self.pull_from_regex('fc_port_gone')

    def get_fc_port_updates(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_port_updates."""
        return self.pull_from_regex('fc_port_updates')

    def get_fc_rscn_changes(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_rscn_changes."""
        return self.pull_from_regex('fc_rscn_changes')

    def get_fc_session_added(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_session_added."""
        return self.pull_from_regex('fc_session_added')

    def get_fc_qlt_free(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for fc_qlt_free."""
        return self.pull_from_regex('fc_qlt_free')

    def get_gather_hw_logs(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for gather_hw_logs."""
        return self._pull_from_interval('gather_hw_logs')

    def get_killing_foed(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for killing_foed."""
        return self._pull_from_line('killing_foed')

    def get_linux_version(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for linux_versoin."""
        return self._pull_from_line('linux_version')

    def get_mce_counts(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get a count of form lines for mce_events."""
        # Syslog cannot guarantee granularity beyond seconds, so aggregate all events within the same second.
        events = collections.defaultdict(int)
        for timestamp, _ in self._pull_from_line('mce_events'):
            events[timestamp] += 1
        for timestamp, ce_event in self.pull_from_regex('ce_events'):
            events[timestamp] += int(ce_event['ce_mem_count'])
        return sorted(events.items())

    def get_mce_events(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for mce_events."""
        return self._pull_from_line('mce_events')

    def get_npiv_enabled(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for npiv_enabled."""
        return self.pull_from_regex('npiv_enabled')

    def get_npiv_disabled(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for npiv_disabled."""
        return self._pull_from_line('npiv_disabled')

    def get_offline_memory(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the total amount of memory that is offline (bytes)."""
        offline_memory = []
        for timestamp, offline_dict in self.pull_from_regex('offline_memory'):
            size = format_utils.to_raw(offline_dict['size'])
            total = size * int(offline_dict['count'])
            offline_memory.append((timestamp, total))
        return offline_memory

    def get_portal_change(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for portal_change."""
        return self._pull_from_line('portal_change')

    def get_pureadm_change(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for pureadm_change."""
        return self._pull_from_line('pureadm_change')

    def get_pureboot_reboot(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for pureboot_reboot."""
        return self._pull_from_line('pureboot_reboot')

    def get_puredb_run_giveback(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for puredb_run_giveback."""
        return self._pull_from_line('puredb_run_giveback')

    def get_pureinstall(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for pureinstall."""
        return self._pull_from_line('pureinstall')

    def get_puresetup(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for puresetup."""
        return self._pull_from_line('puresetup')

    def get_session_map(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for session_map."""
        return self.pull_from_regex('session_map')

    def get_upgrade(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for upgrade."""
        return self._pull_from_line('upgrade')

    def get_req_fail(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for upgrade."""
        return self._pull_from_line('req_fail')
