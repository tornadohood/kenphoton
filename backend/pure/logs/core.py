"""Contains parser definitions on how to extract data from the core log."""

import collections
import re

from six import iteritems

try:
    # pylint: disable=unused-import
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

from photon.lib import parser_utils
from photon.lib import file_utils
from photon.lib import flutter_utils
from photon.lib import format_utils
from photon.lib import time_utils

TIMESTAMP = r'(?P<timestamp>\w{3}\s+\d{1,2}\s+(?:\d{2}:?){3}\.\d+).*?'
# pylint: disable=too-few-public-methods, too-many-public-methods, invalid-name, line-too-long


class CoreFormData(parser_utils.FormData):
    """Forms used by the CoreParser."""

    # flutters
    postman_tcp_info_rcv_space_probe = parser_utils.FlutterForm('svc::postman_tcp_info_rcv_space_probe')
    # Other core lines
    a_crumb = parser_utils.SimpleTextForm(
        # This line captures A crumb events
        # TODO: PT-2103 find example
        text_to_match=' A  ',
    )
    au_map_mainarea = parser_utils.SimpleTextForm(
        text_to_match='segmap.au_mapper_boot au map mainarea avg free',
        # Dec  8 23:38:29.350 7F65EF5FD700 I     segmap.au_mapper_boot au map mainarea avg free = 29845+293 (garbage=9838) / 60986 on 140/140 healthy devs
        regexes={'default': r'{timestamp}.*?(?P<free>\d+)\+(?P<inflight>\d+)\s+\(garbage=(?P<garbage>\d+)\)\s+/\s+(?P<au_cnt>\d+)\s+on\s+(?P<healthy_devs>\d+)/(?P<total_devs>\d+)'.format(timestamp=TIMESTAMP)}
    )
    devices_without_references = parser_utils.SimpleTextForm(
        text_to_match='Reporting 0',
        # Mar 12 06:25:03.345 000000001741 I      segmap.device_reference Reporting 0 persistent + 0 inflight reserved-area refs for device (15518390543196150589, 34277887545602668)
        regexes={'default': r'{timestamp}.*?Reporting 0.*-area refs for device\s\((?P<dev_id>\d+, \d+)\)'.format(timestamp=TIMESTAMP)},
    )
    foed_entering = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='foed Entering',
    )
    is_online = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='is now online',
    )
    k_crumb = parser_utils.SimpleTextForm(
        # This log line catches K crumb lines
        # TODO: PT-2103 find example
        text_to_match=' K  ',
    )
    log_header_tenant = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='segmap.tenant Log Header Tenant',
    )
    out_of_memory = parser_utils.SimpleTextForm(
        # Out of memory indicator
        # TODO: PT-2103 find example
        text_to_match='out_of_memory_die() called,'
    )
    ps_init_env = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='ps_init_env(osenv)'
    )
    pyramid = parser_utils.SimpleTextForm(
        text_to_match='vol.space_report Pyramid space',
        # Apr 29 23:41:13.440 000000002306 I      vol.space_report Pyramid space: curr levels/bytes/scaled bytes = 5/1506442604544/605736288256, parent levels/bytes = 15/1737290960896
        regexes={'default': r'{timestamp}.*?=\s+(?P<levels>\d+)/(?P<bytes>\d+)/(?P<scaled_bytes>\d+), parent levels/bytes = (?P<parent_levels>\d+)/(?P<parent_bytes>\d+)'.format(timestamp=TIMESTAMP)},
    )
    shmem = parser_utils.IntervalForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='shmem.res',
        start_text='C      shmem.res ->',
        end_text='C      shmem.res <-    total',
    )
    space_summary_dropped = parser_utils.SimpleTextForm(
        text_to_match='vol.space_summary Dropped',
        # Sep  7 00:16:41.875 7F2E237D1700 I      vol.space_summary Dropped 0.000B in distribution, 1.882KB from triage (169.131MB total triage physical), missed 0 segments (0.000B)
        regexes={'default': r'{timestamp}.*?Dropped (?P<dropped>\d+.\d+.?B)'.format(timestamp=TIMESTAMP)}
    )
    stacktrace_core = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2102 This needs to be a multiline
        # TODO: PT-2103 find example
        text_to_match='STACKTRACE',
    )
    total_physical = parser_utils.SimpleTextForm(
        text_to_match='vol.space_report Total physical space:',
        # Apr 29 23:36:13.437 0000000022F9 I      vol.space_report Total physical space: 53951236324786 (53951236324786 + 0 backlog)
        regexes={'default': r'{timestamp}.*?Total\s+physical\s+space:\s(?P<raw>\d+)\s\(((includes|(?P<volume>\d+)\s\+)\s(?P<backlog>\d+))'.format(timestamp=TIMESTAMP)},
    )
    triage_count = parser_utils.SimpleTextForm(
        # Jul 24 23:18:14.682 000000001058 I      vol.metrics triage_svc triage finished in 8558 ms (segid 6633, valid segios 64, preferred 0, logical 0), seg_data_0, appeal 22123373, benefit 22123373, cost 221920, discrepancy phys 22121493, discrepancy unmap 918, discrepancy logical 0, discrepancy reach 0
        text_to_match='triage_svc triage finished',
        # For the time being we do not require any of the content from this line, just that the line appeared.
        # A regex may be added later if it is determined that having more info is needed.
    )
    volume_space_report = parser_utils.IntervalForm(
        text_to_match='vol.space_report Volume',
        # Jun 28 23:19:22.405 000000001133 I      vol.space_report Volume '29HVFXC_CSV_VMs' - volume_id: 69650, is_volume 1, volume size: 1074815565824, virtual space: 314838297088, dedup space: 0, physical space: 51055252238, log space: 0, shared space: 9557810757
        start_text='vol.space_report Volume \'(',
        end_text='vol.space_report Array fullness (uncooked):',
        regexes={'default': r'Volume \'\(?(?P<volume>\w+)\)?\'.*? (?P<vol_id>\d+),\s+is_volume\s+(?P<is_volume>0|1),.*?: (?P<size>\d+),.*?: (?P<virtual_space>\d+),.*?: (?P<dedup_space>\d+),.*?: (?P<physical_space>\d+),.*?: (?P<log_space>\d+),.*?: (?P<shared_space>\d+)'},
    )


class CoreLogData(parser_utils.LogData):
    """Manage information about a piece Data from the logs."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        core_forms = CoreFormData()
        super(CoreLogData, self).__init__({form: core_forms[form] for form in needed_forms})


class CoreParser(parser_utils.ParallelLogParser):
    """Defines all core data parsing functions."""
    forms = CoreFormData()
    fields = {
        'a_crumb': CoreLogData(['a_crumb']),
        'allocator_performance': CoreLogData(['shmem']),
        'backing_slabs': CoreLogData(['shmem']),
        'backlog': CoreLogData(['total_physical']),
        'context_map_count': CoreLogData(['shmem']),
        'devices_without_references': CoreLogData(['devices_without_references']),
        'foed_entering': CoreLogData(['foed_entering']),
        'free_pool': CoreLogData(['shmem']),
        'is_online': CoreLogData(['is_online']),
        'k_crumb': CoreLogData(['k_crumb']),
        'log_header_tenant': CoreLogData(['log_header_tenant']),
        'malloc_stats': CoreLogData(['shmem']),
        'memory_contexts': CoreLogData(['shmem']),
        'memory_users': CoreLogData(['shmem']),
        'out_of_memory': CoreLogData(['out_of_memory']),
        'postman_tcp_info_rcv_space_probe': CoreLogData(['postman_tcp_info_rcv_space_probe']),
        'ps_init_env': CoreLogData(['ps_init_env']),
        'reported_pyramid': CoreLogData(['pyramid']),
        'reclaimable_space': CoreLogData(['au_map_mainarea']),
        'rsize': CoreLogData(['shmem']),
        'space_summary_dropped': CoreLogData(['space_summary_dropped']),
        'stacktrace_core': CoreLogData(['stacktrace_core']),
        'total_memory': CoreLogData(['shmem']),
        'triage_count': CoreLogData(['triage_count']),
        'untracked_memory': CoreLogData(['shmem']),
        'volume_space_report': CoreLogData(['volume_space_report']),
        'vsize': CoreLogData(['shmem']),
        'vsize_cap': CoreLogData(['shmem']),
    }

    def _pull_from_line(self, form_name):
        # type: (str) -> List[Tuple[Any, Any]]
        """Get timestamp tuple from lines."""
        timestamped_results = []
        results = self.get_form_lines(form_name)
        for line in results:
            timestamp = time_utils.get_timestamp_from_line(line)
            timestamped_results.append((timestamp, line))
        return timestamped_results

    # pylint: disable=too-many-arguments
    def _parse_sub_interval(self,
                            interval,       # type: List[str]
                            start,          # type: str
                            end,            # type: str
                            regex,          # type: Any
                            as_regex        # type: bool
                           ):               # type: (...) -> Tuple[Any, Any]
        """Create a sub-interval based upon start/end and then parse only those lines via regex."""
        # There should only ever be 1 sub-interval per interval for each section.
        sub_interval = list(file_utils.iter_line_intervals(interval, start, end, regex=as_regex))[0]
        return _parse_interval(sub_interval, regex)

    def _get_shmem_sub_section(self, start, end, pattern, as_regex=False):
        # type: (str, str, str, bool) -> List[Any]
        """Process a sub-section of the shmem.res output."""
        matches = []
        regex = re.compile(TIMESTAMP + pattern)
        for interval in self.get_form_lines('shmem'):
            if not interval:
                continue
            if start and end:
                timestamp, parsed = self._parse_sub_interval(interval, start, end, regex, as_regex)
            else:
                timestamp, parsed = _parse_interval(interval, regex)
            matches.append((timestamp, parsed))
        return matches

    def get_a_crumb(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for a_crumb."""
        return self._pull_from_line('a_crumb')

    def get_allocator_performance(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get Memory allocator performance statistics (Allocator performance stats)."""
        # Apr 17 23:18:28.587 0000000015A7 I          shmem.res 	Allocator performance stats
        # Apr 17 23:18:28.587 0000000015A7 C          shmem.res ->	maps	unmaps	size	object()
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	44809	44813	32768	unknown/backing slab[temporal]->inherent
        # Apr 17 23:18:28.587 0000000015A7 C          shmem.res <-	maps	unmaps	size	object
        regexp = r'shmem.res\s+(?P<maps>\d+)\s+(?P<unmaps>\d+)\s+(?P<object>.*)'
        return self._get_shmem_sub_section('Allocator performance stats', 'C          shmem.res <-', regexp)

    def get_backing_slabs(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get Memory Heap/Backing Slab information (Backing slabs info)."""
        # Apr 17 23:17:57.042 0000000010FE C          shmem.res ->\tBacking slabs info()
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	Objects				numa0		numa1
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	allocated malloc objects	3908		2232
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	allocated other objects		2209201		18446744073707299733
        # ...
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	179087	152201	(all)	[62 objects elided]
        # Apr 17 23:17:57.042 0000000010FE C          shmem.res <-\tBacking slabs info
        regexp = r'shmem.res\s+(?P<object>.*?)\s+(?P<numa0>\d+)\s+(?P<numa1>\d+)'
        return self._get_shmem_sub_section('Backing slabs info()', 'Backing slabs info', regexp)

    def get_backlog(self):
        # type: () -> List[Tuple[Any, float]]
        """Get the total space backlog."""
        space_backlog = []
        for timestamp, backlog in self.pull_from_regex('total_physical', keys=['backlog']):
            try:
                backlog_value = float(backlog.get('backlog'))
            except ValueError:
                backlog_value = None
            space_backlog.append((timestamp, backlog_value))
        return space_backlog

    def get_context_map_count(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the total memory mapping count."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	5973			total map_count
        regexp = r'shmem.res\s+(?P<total_map_count>\d+)\s+total map_count'
        return self._get_shmem_sub_section(None, None, regexp)

    def get_devices_without_references(self):
        # type: () -> List[Tuple[Any, str]]
        """Get all device IDs and timestamps where we are reporting 0 area references."""
        # This is typically an indication of hardware failure or PURE-81137 (fixed in 4.8.8).
        return self.pull_from_regex('devices_without_references')

    def get_flutter(self, flut_name, as_flutter=True):
        # type: (str, bool) -> flutter_utils.Flutter
        """Get the flutters given by flut_name."""
        flut_nice_name = flut_name.split('::')[1]
        flut_form = parser_utils.FlutterForm(flut_name)
        setattr(self.forms, flut_nice_name, flut_form)
        self.fields[flut_nice_name] = parser_utils.LogData({flut_nice_name: flut_form})
        temp_flutters = self.get_form_lines(flut_nice_name)
        if as_flutter:
            flutters = flutter_utils.Flutter(temp_flutters)
        else:
            flutters = temp_flutters
        return flutters

    def get_foed_entering(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for foed_entering."""
        return self._pull_from_line('foed_entering')

    def get_free_pool(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the amount of memory free (unmapped/allocated) in the pool."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	0.000B			total free pool
        regexp = r'shmem.res\s+(?P<free_pool>\d+\.\d+\w?B)\s+total free pool'
        return self._get_shmem_sub_section(None, None, regexp)

    def get_is_online(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for is_online."""
        return self._pull_from_line('is_online')

    def get_k_crumb(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for k_crumb."""
        return self._pull_from_line('k_crumb')

    def get_log_header_tenant(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for log_header_tenant."""
        return self._pull_from_line('log_header_tenant')

    def get_malloc_stats(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get Malloc Arena statistics (Malloc stats)."""
        # Apr 17 23:17:57.042 0000000010FE C          shmem.res ->\tMalloc stats()
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	Arena	system bytes	in use bytes	free bytes
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	0	752877568	609335168	136.892MB
        # ...
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	total	12876513280	8640952368	3.944GB
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	Max mmap regions = 785
        # Apr 17 23:18:28.587 0000000015A7 I              shmem.res 	Max mmap bytes   = 8852078592
        regexp = r'shmem.res\s+(?P<arena>\d+|total)\s+(?P<system_bytes>\d+)\s+(?P<in_use_bytes>\d+)\s+(?P<free_bytes>\d+\.\d+\w?B)'
        return self._get_shmem_sub_section('Malloc stats()', 'Malloc stats', regexp)

    def get_memory_contexts(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get memory contexts (groups)."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	context unknown	4.136GB
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	[709 elided contexts]	290.667MB
        regexp = r'shmem.res\s+context (?P<context>\w+)\s+(?P<size>\d+\.\d+\w?B)'
        return self._get_shmem_sub_section(None, None, regexp)

    def get_memory_users(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get individual memory objects/users, their allocation sizes/counts and total usage."""
        # Apr 17 23:18:28.532 0000000015A7 C      shmem.res ->	total	size	count	object()
        # Apr 17 23:18:28.584 0000000015A7 I          shmem.res 	22.317MB			elided
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	230686720	2097152	110	no_context/thread stacks
        regexp = r'shmem.res\s+(?P<total>\d+)\s+(?P<size>\d+)\s+(?P<count>\d+)\s+(?P<object>.*)'
        return self._get_shmem_sub_section('C      shmem.res ->',
                                           r'(Allocator performance stats|C      shmem.res <-    total)', regexp,
                                           as_regex=True)

    def get_out_of_memory(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for out_of_memory."""
        return self._pull_from_line('out_of_memory')

    def get_postman_tcp_info_rcv_space_probe(self, as_flutter=True):
        # type: (bool) -> List[Tuple[Any, flutter_utils.Flutter]]
        """Get the 'postman_tcp_info_rcv_space_probe' flutter."""
        temp_flutters = self.get_form_lines('postman_tcp_info_rcv_space_probe')
        flutters = flutter_utils.Flutter(temp_flutters) if as_flutter else temp_flutters
        return flutters

    def get_ps_init_env(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for ps_init_env."""
        return self._pull_from_line('ps_init_env')

    def get_reported_pyramid(self):
        # type: () -> List[Tuple[Any, float]]
        """Get the reported_pyramid space."""
        pyramid_space = []
        needed_values = ['bytes', 'scaled_bytes', 'parent_bytes']
        raid_size = 7. / 9.
        for timestamp, values in self.pull_from_regex('pyramid', keys=needed_values):
            pyramid_bytes = values.get('bytes')
            scaled_bytes = values.get('scaled_bytes')
            parent_bytes = values.get('parent_bytes')
            if all([pyramid_bytes, scaled_bytes, parent_bytes]):
                combined = float(pyramid_bytes) - float(scaled_bytes) + float(parent_bytes)
                pyramid = combined / raid_size
            else:
                pyramid = None
            pyramid_space.append((timestamp, pyramid))
        return pyramid_space

    def get_reclaimable_space(self):
        # type: () -> List[Tuple[Any, float]]
        """Get reclaimable space."""
        reclaimable_space = []
        needed_values = ['garbage', 'healthy_devs']
        au_size = ((2 ** 20) * 8.)
        for timestamp, values in self.pull_from_regex('au_map_mainarea', keys=needed_values):
            garbage_aus_value = values.get('garbage')
            healthy_devs_value = values.get('healthy_devs')
            if all([garbage_aus_value, healthy_devs_value]):
                reclaimable = float(garbage_aus_value) * au_size * float(healthy_devs_value)
            else:
                reclaimable = None
            reclaimable_space.append((timestamp, reclaimable))
        return reclaimable_space

    def get_rsize(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the estimated real memory usage (rsize)."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	15.520GB			total rsize
        regexp = r'shmem.res\s+(?P<rsize>\d+\.\d+\w?B)\s+total rsize'
        return self._get_shmem_sub_section(None, None, regexp)

    def get_space_summary_dropped(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for space_summary_dropped space."""
        dropped = []
        for timestamp, value_dict in self.pull_from_regex('space_summary_dropped'):
            dropped.append((timestamp, format_utils.to_raw(value_dict['dropped'], 'binary_bytes')))
        return dropped

    def get_stacktrace_core(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get form lines for stacktrace."""
        return self._pull_from_line('stacktrace_core')

    def get_total_memory(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total memory usage (Purity Heap)."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	20.392GB			total
        regexp = r'shmem.res\s+(?P<total>\d+\.\d+\w?B)\s+total\Z'
        return self._get_shmem_sub_section(None, None, regexp)

    def get_triage_count(self):
        # type: () -> List[Tuple[Any, int]]
        """Get the number of times triage completed within the log."""
        events = collections.defaultdict(int)
        for timestamp, _ in self._pull_from_line('triage_count'):
            # It is possible to have more than one event per timestamp.
            events[timestamp] += 1
        return sorted(events.items())

    def get_untracked_memory(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get memory which is untracked (within the pool's mmap range, but unusable)."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	412.639MB			total untracked memory
        regexp = r'shmem.res\s+(?P<untracked_memory>\d+\.\d+\w?B)\s+total untracked memory'
        return self._get_shmem_sub_section(None, None, regexp)

    def get_volume_space_report(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get per-volume space metrics."""
        return self.regex_in_intervals('volume_space_report')

    def get_vsize(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total memory usage (total vsize)."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	392.226GB			total vsize
        regexp = r'shmem.res\s+(?P<vsize>\d+\.\d+\w?B)\s+total vsize'
        return self._get_shmem_sub_section(None, None, regexp)

    def get_vsize_cap(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get the Virtual Memory Capacity limit."""
        # Apr 17 23:18:28.586 0000000015A7 I          shmem.res 	433.785GB			vsize cap (177.783GB regular cap + 256.001GB virtual memory only allocations)
        regexp = r'shmem.res\s+(?P<limit>\d+\.\d+\w?B)\s+vsize cap \((?P<real>\d+\.\d+\w?B).*?\+ (?P<virtual>\d+\.\d+\w?B)'
        return self._get_shmem_sub_section(None, None, regexp)


def _parse_interval(interval, regex):
    # type: (List[str], Any) -> Tuple[Any, Dict[str, List[Any]]]
    """Parse lines within the interval with the given regex."""
    combined = collections.defaultdict(list)
    timestamp = time_utils.Timestamp(re.search(TIMESTAMP, interval[0]).group('timestamp'))
    for line in interval:
        found = regex.match(line)
        if not found:
            continue
        results = found.groupdict()
        for key, value in iteritems(results):
            if key == 'timestamp':
                continue
            if value.isdigit():
                value = int(value)
            elif value.endswith('B'):
                value = format_utils.to_raw(value)
            combined[key].append(value)
    return timestamp, dict(combined)
