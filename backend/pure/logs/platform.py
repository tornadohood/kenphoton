"""Contains parser definitions on how to extract data from platform.log."""

import collections
import logging

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
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)
TIME_REG = r'(?P<timestamp>\w+\s+\d{1,2}\s+(\d{2}:?){3}\.\d{3})'


# Example log lines may be very long.
# pylint: disable=line-too-long
class PlatformFormData(parser_utils.FormData):
    """Forms used by the PlatformParser."""
    dev_info = parser_utils.SimpleTextForm(
        # Feb  6 00:08:59.205 00000000308A I      DEVINFO: (11951019079781516624, 12986023337942797145) (13419475094725538408, 8251457055466146758)(10572254556938388712, 14492479880651491927) /dev/ps-MkfoarAukpX:JK4MYFdUUTo-144 SAMSUNG_MZ7LM1T9_S2TVNX0J509810 0x5002538C406154B7 EB-2425-E12EBD SHT1019220G0YYC 19 2 SSD
        text_to_match='DEVINFO:',
        regexes={'default': r'{timestamp}.*?DEVINFO:\s+\((?P<apt>\d+, \d+)\)\s+\((?P<grp>\d+, \d+)\)\s+\((?P<dev>\d+, \d+)\)\s+(?P<dm>\S+)\s+(?P<name>\S+)\s+0x(?P<wwn>\S+)\s+(?P<encl>\S+)\s+(?P<slot>\d+)\s+(?P<subslot>\d+)\s+(?P<type>\w+)'.format(timestamp=TIME_REG)}
    )
    devices_claimed = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='Devices claimed',
        regexes={'default': r'storage.failover .*Devices claimed', }
    )
    disable_vport = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='disable_vport',
        regexes={'default': r'lio_helper.py disable_vport.*took', }
    )
    disabling_local_borrowed = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='disabling_local_borrowed',
        regexes={'default': r'ha::sanity_impl_state::checking -> ha::sanity_impl_state::disabling_local_borrowed', }
    )
    enabling_local_borrowed = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='enabling_local_borrowed',
        regexes={'default': r'ha::sanity_impl_state::checking -> ha::sanity_impl_state::enabling_local_borrowed', }
    )
    enabling_peer_owned = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='enabling_peer_owned',
        regexes={'default': r'ha::sanity_impl_state::checking -> ha::sanity_impl_state::enabling_peer_owned', }
    )
    enable_vport = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='enable_vport',
        regexes={'default': r'lio_helper.py enable_vport.*took', }
    )
    failovers = parser_utils.SimpleTextForm(
        # May 13 03:03:23.385 7F9342EBF700 B     storage.failover [platform_framework] Takeover -> Giveback
        text_to_match='storage.failover',
        regexes={'default': r'{timestamp}.*?storage.failover.*?\]\s+(?P<action>\w+) \-\> (?P<reason>\w+)'.format(timestamp=TIME_REG)}
    )
    foed_health_change = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='foed change in health',
        regexes={'default': r'storage.failover .*foed change in health', }
    )
    foed_health_diagnosis = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='new foed health diagnosis',
        regexes={'default': r'storage.failover .*new foed health diagnosis', }
    )
    forms_quorum = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='forms quroum',
        regexes={'default': r'landlord .*forms quorum', }
    )
    giveback = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='Giveback',
        regexes={'default': r'storage.failover .*Giveback', }
    )
    in_quorum = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='in quorum',
        regexes={'default': r'landlord.util .*in quorum', }
    )
    landlord_logging = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='landlord.logging',
        regexes={'default': r'landlord.logging', }
    )
    lost_quorum = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='lost quorum',
        regexes={'default': r'landlord .*lost quorum', }
    )
    no_pulse = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='returning no_pulse',
        regexes={'default': r'storage.failover .*primary_req: returning no_pulse', }
    )
    platform_framework = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='platform_framework',
        regexes={'default': r'storage.failover .*\[platform_framework\]', }
    )
    primary = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='Primary',
        regexes={'default': r'storage.failover .*Primary', }
    )
    purity_info = parser_utils.SimpleTextForm(
        # Feb  5 23:21:36.212 000000002A0A I      osenv.jobs Purity 4.10.5 201707222306+e8b53a9-410d (release) uptime 139d:14h:32m:18s
        text_to_match='osenv.jobs Purity',
        regexes={'default': r'{timestamp}.*?osenv.jobs Purity (?P<version>(\S+\.?)+).*?uptime\s(?P<uptime>.*)'.format(timestamp=TIME_REG)}
    )
    quorum = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='ha.enum.',
        regexes={'default': r'ha.enum.*quorum', }
    )
    rebooting_peer = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='Rebooting peer due to status',
        regexes={'default': r'ha.sanity Rebooting peer due to status', }
    )
    run_time = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='primary_req run time',
        regexes={'default': r'storage.failover .*primary_req run time.*total', }
    )
    secondary = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='Secondary',
        regexes={'default': r'storage.failover .*Secondary', }
    )
    slow_primary = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='primary_req slow',
        regexes={'default': r'storage.failover .*primary_req slow', }
    )
    stacktrace_platform = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='STACKTRACE',
        regexes={'default': r'STACKTRACE', }
    )
    platform_stall = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='STALL',
        regexes={'default': r'STALL', }
    )
    stopped_primary = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='primary_req stopped',
        regexes={'default': r'storage.failover .*primary_req stopped', }
    )
    unhealthy_primary = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='primary_req stopped',
        regexes={'default': r'storage.failover .*primary_req unhealthy', }
    )
    weak_pulse = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='primary_req: returning weak_pulse',
        regexes={'default': r'storage.failover .*primary_req: returning weak_pulse', }
    )


class PlatformData(parser_utils.LogData):
    """Container for platform data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        platform_forms = PlatformFormData()
        super(PlatformData, self).__init__({form: platform_forms[form] for form in needed_forms})
        LOGGER.debug('PlatformData initialized with needed_forms: {}'.format(needed_forms))


class PlatformParser(parser_utils.ParallelLogParser):
    """Defines all platform data parsing functions."""
    forms = PlatformFormData()
    fields = {
        'dev_info': PlatformData(['dev_info']),
        'devices_claimed': PlatformData(['devices_claimed']),
        'disable_vport': PlatformData(['disable_vport']),
        'disabling_local_borrowed': PlatformData(['disabling_local_borrowed']),
        'enable_vport': PlatformData(['enable_vport']),
        'enabling_local_borrowed': PlatformData(['enabling_local_borrowed']),
        'enabling_peer_owned': PlatformData(['enabling_peer_owned']),
        'failovers': PlatformData(['failovers']),
        'foed_health_change': PlatformData(['foed_health_change']),
        'foed_health_diagnosis': PlatformData(['foed_health_diagnosis']),
        'forms_quorum': PlatformData(['forms_quorum']),
        'giveback': PlatformData(['giveback']),
        'in_quorum': PlatformData(['in_quorum']),
        'landlord_logging': PlatformData(['landlord_logging']),
        'lost_quorum': PlatformData(['lost_quorum']),
        'no_pulse': PlatformData(['no_pulse']),
        'platform_framework': PlatformData(['platform_framework']),
        'primary': PlatformData(['primary']),
        'purity_uptime': PlatformData(['purity_info']),
        'purity_version': PlatformData(['purity_info']),
        'quorum': PlatformData(['quorum']),
        'rebooting_peer': PlatformData(['rebooting_peer']),
        'run_time': PlatformData(['run_time']),
        'secondary': PlatformData(['secondary']),
        'slow_primary': PlatformData(['slow_primary']),
        'stacktrace_platform': PlatformData(['stacktrace_platform']),
        'platform_stall': PlatformData(['platform_stall']),
        'stopped_primary': PlatformData(['stopped_primary']),
        'unhealthy_primary': PlatformData(['unhealthy_primary']),
        'weak_pulse': PlatformData(['weak_pulse']),
    }

    def _pull_from_line(self, form_name):
        # type: (str) -> List[Tuple[Any, Any]]
        """Get timestamp tuple from lines."""
        timestamped_results = []
        results = self.get_form_lines(form_name)
        for line in results:
            if not line or isinstance(line, float):
                # Skip empty and nan values.
                continue
            timestamp = time_utils.get_timestamp_from_line(line)
            timestamped_results.append((timestamp, line))
        return timestamped_results

    def get_dev_info(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get device information.  Manually merge device lines based upon timestamp."""
        # TODO: Test case which have slightly different timestamps
        # TODO: Test case where there's more than one dev_info dump per file.
        matches = self.pull_from_regex('dev_info')
        merged = []
        temp = collections.defaultdict(list)
        for timestamp, match in matches:
            # Reduce the resolution of the timestamp, so we can match lines which took longer than 1 ms to log.
            timestamp = timestamp.replace(second=0, microsecond=0)
            temp[timestamp].append(match)
        for timestamp, matches in temp.items():
            merged.append((timestamp, matches))
        return merged

    def get_devices_claimed(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for devices_claimed."""
        return self._pull_from_line('devices_claimed')

    def get_disable_vport(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for disable_vport."""
        return self._pull_from_line('disable_vport')

    def get_disabling_local_borrowed(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for disabling_local_borrowed."""
        return self._pull_from_line('disabling_local_borrowed')

    def get_enable_vport(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for enable_vport."""
        return self._pull_from_line('enable_vport')

    def get_enabling_local_borrowed(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for enabling_local_borrowed."""
        return self._pull_from_line('enabling_local_borrowed')

    def get_enabling_peer_owned(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for enabling_peer_owned."""
        return self._pull_from_line('enabling_peer_owned')

    def get_failovers(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get all failover events."""
        return self.pull_from_regex('failovers')

    def get_foed_health_change(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for foed_health_change."""
        return self._pull_from_line('foed_health_change')

    def get_foed_health_diagnosis(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for foed_health_diagnosis."""
        return self._pull_from_line('foed_health_diagnosis')

    def get_forms_quorum(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for forms_quorum."""
        return self._pull_from_line('forms_quorum')

    def get_giveback(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for giveback."""
        return self._pull_from_line('giveback')

    def get_in_quorum(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for in_quorum."""
        return self._pull_from_line('in_quorum')

    def get_landlord_logging(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for landlord_logging."""
        return self._pull_from_line('landlord_logging')

    def get_lost_quorum(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for lost_quorum."""
        return self._pull_from_line('lost_quorum')

    def get_no_pulse(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for no_pulse."""
        return self._pull_from_line('no_pulse')

    def get_platform_framework(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for platform_framework."""
        return self._pull_from_line('platform_framework')

    def get_primary(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for primary."""
        return self._pull_from_line('primary')

    def get_purity_uptime(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the 'uptime' of Purity on this controller."""
        fixed = []
        raw = self.pull_from_regex('purity_info', ['uptime'])
        for timestamp, value in raw:
            if value is None:
                fixed.append((timestamp, value))
            else:
                fixed.append((timestamp, value['uptime']))
        return fixed

    def get_purity_version(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the version of Purity."""
        fixed = []
        raw = self.pull_from_regex('purity_info', ['version'])
        for timestamp, value in raw:
            if value is None:
                fixed.append((timestamp, value))
            else:
                fixed.append((timestamp, value['version']))
        return fixed

    def get_quorum(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for quorum."""
        return self._pull_from_line('quorum')

    def get_rebooting_peer(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for rebooting_peer."""
        return self._pull_from_line('rebooting_peer')

    def get_run_time(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for run_time."""
        return self._pull_from_line('run_time')

    def get_secondary(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for secondary."""
        return self._pull_from_line('secondary')

    def get_slow_primary(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for slow_primary."""
        return self._pull_from_line('slow_primary')

    def get_stacktrace_platform(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for stacktrace."""
        return self._pull_from_line('stacktrace_platform')

    def get_platform_stall(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for stall."""
        return self._pull_from_line('platform_stall')

    def get_stopped_primary(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for stopped_primary."""
        return self._pull_from_line('stopped_primary')

    def get_unhealthy_primary(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for unhealthy_primary."""
        return self._pull_from_line('unhealthy_primary')

    def get_weak_pulse(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for weak_pulse."""
        return self._pull_from_line('weak_pulse')
