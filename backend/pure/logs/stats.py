"""Contains parser definitions on how to extract data from the volume_stats logs."""

import collections
import logging

from six import iteritems

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

# TODO: Make a universal field/parser for all of these so we don't go over the form lines multiple times.


class StatsFormData(parser_utils.FormData):
    """Forms used by the StatsParser."""
    # pylint: disable=line-too-long
    # Name                                        Time                     B/s (read)  B/s (write)  op/s (read)  op/s (write)  us/op (read)  SAN us/op (read)  us/op (write)  SAN us/op (write)
    # 255-VMFS-Logging                            2018-01-16 23:19:54 CST  21.30K      14.98K       20.00        9.00          215           2                 227            154
    # 11-Mail-Odd                                 2018-01-16 23:19:54 CST  19.18M      2.11M        112.00       186.00        975           106               207            182
    all_data = parser_utils.IntervalForm(
        text_to_match=None,
        start_text='Name ',
        end_text='(total)'
    )


class StatsLogData(parser_utils.LogData):
    """Manage information about each piece of data from the logs."""

    def __init__(self, needed_forms):
        # type: (List[str]) -> None
        """Create an object to track needed forms."""
        stats_forms = StatsFormData()
        super(StatsLogData, self).__init__({form: stats_forms[form] for form in needed_forms})


class StatsParser(parser_utils.ParallelLogParser):
    """Defines all stats data parsing functions."""
    forms = StatsFormData()
    fields = {
        'perf_stats': StatsLogData(['all_data']),
        # Total Stats:
        'read_bandwidth': StatsLogData(['all_data']),
        'read_iops': StatsLogData(['all_data']),
        'read_latency': StatsLogData(['all_data']),
        'read_san_latency': StatsLogData(['all_data']),
        'write_bandwidth': StatsLogData(['all_data']),
        'write_iops': StatsLogData(['all_data']),
        'write_latency': StatsLogData(['all_data']),
        'write_san_latency': StatsLogData(['all_data']),
        # Per Host Stats:
        'host_name': StatsLogData(['all_data']),
        'host_perf_stats': StatsLogData(['all_data']),
        'host_read_bandwidth': StatsLogData(['all_data']),
        'host_write_bandwidth': StatsLogData(['all_data']),
        'host_read_iops': StatsLogData(['all_data']),
        'host_write_iops': StatsLogData(['all_data']),
        'host_read_latency': StatsLogData(['all_data']),
        'host_write_latency': StatsLogData(['all_data']),
        'host_read_san_latency': StatsLogData(['all_data']),
        'host_write_san_latency': StatsLogData(['all_data']),
        # Per Volume Stats:
        'volume_name': StatsLogData(['all_data']),
        'volume_perf_stats': StatsLogData(['all_data']),
        'volume_read_bandwidth': StatsLogData(['all_data']),
        'volume_write_bandwidth': StatsLogData(['all_data']),
        'volume_read_iops': StatsLogData(['all_data']),
        'volume_write_iops': StatsLogData(['all_data']),
        'volume_read_latency': StatsLogData(['all_data']),
        'volume_write_latency': StatsLogData(['all_data']),
        'volume_read_san_latency': StatsLogData(['all_data']),
        'volume_write_san_latency': StatsLogData(['all_data']),
    }
    _all_perf_data = None

    @property
    def all_perf_data(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch all statistics for all volumes."""
        if self._all_perf_data:
            return self._all_perf_data
        all_stats = []
        no_san_header = ('Name', 'Time', 'B/s (read)', 'B/s (write)', 'op/s (read)', 'op/s (write)', 'us/op (read)',
                         'us/op (write)')
        san_header = ('Name', 'Time', 'B/s (read)', 'B/s (write)', 'op/s (read)', 'op/s (write)', 'us/op (read)',
                      'SAN us/op (read)', 'us/op (write)', 'SAN us/op (write)')
        for lines in self.get_form_lines('all_data'):
            if len(lines) == 2:
                # PT-2276 - This is an array which has no volumes... just the header line and '(total)'.
                # We can assume that the (total) values are all 0, as there are no volumes to read/write.
                split_line = split_stats_line(lines[1])
                timestamp = time_utils.Timestamp(split_line[1][:-4])
                stats = {
                    '(total)': {'read_bw': 0, 'write_bw': 0, 'read_iops': 0, 'write_iops': 0, 'read_ms': 0,
                                'write_ms': 0, 'read_san_ms': 0, 'write_san_ms': 0}
                }
                all_stats.append((timestamp, stats))
                continue
            header = tuple(split_stats_line(lines[0]))
            timestamp = None
            stats = {
                # Adding a placeholder so that we can aggregate all of the values here.
                '(total)': collections.defaultdict(int)
            }
            # Skip the header line (first line).
            for line in lines[1:]:
                if '(total)' in line:
                    # PURE-123058 - Purity 5.0/5.1 the '(total)' row is always 0.
                    # We skip this and manually create a total below.
                    continue
                split_line = split_stats_line(line)
                if not split_line:
                    continue
                elif not timestamp:
                    # TODO: PT-1875 - Add support for Timezone.
                    # Exclude the Timezone until this is supported.
                    # Example: '2018-06-13 12:19:07 PDT'
                    timestamp = time_utils.Timestamp(split_line[1][:-4])
                name = split_line[0]
                stats[name] = {
                    'read_bw': _to_raw(split_line[2], 'binary_bytes'),
                    'write_bw': _to_raw(split_line[3], 'binary_bytes'),
                    'read_iops': _to_raw(split_line[4], 'iops'),
                    'write_iops': _to_raw(split_line[5], 'iops'),
                }
                # In some Purity versions there are no SAN latency columns:
                if header == no_san_header:
                    stats[name]['read_ms'] = _ms_latency(split_line[6])
                    stats[name]['write_ms'] = _ms_latency(split_line[7])
                    # Add a placeholder:
                    stats[name]['read_san_ms'] = None
                    stats[name]['write_san_ms'] = None
                elif header == san_header:
                    stats[name]['read_ms'] = _ms_latency(split_line[6])
                    stats[name]['read_san_ms'] = _ms_latency(split_line[7])
                    stats[name]['write_ms'] = _ms_latency(split_line[8])
                    stats[name]['write_san_ms'] = _ms_latency(split_line[9])
                else:
                    msg = 'Unrecognized header columns in stats file.\n{}'.format(header)
                    LOGGER.error(msg)
                    raise ValueError(msg)

                # Manually add values to the (total):
                for stat_name, value in iteritems(stats[name]):
                    # For SAN Latency, we may have None.
                    if value is None:
                        stats['(total)'][stat_name] = None
                    else:
                        stats['(total)'][stat_name] += value

            # Convert sub defaultdict to a dict for compatibility:
            stats['(total)'] = dict(stats['(total)'])

            # Append the stats per-timestamp.
            all_stats.append((timestamp, stats))
        self._all_perf_data = all_stats
        return self._all_perf_data

    def fetch_total_metric(self, metric):
        # type: (str) -> List[Tuple[Any, Any]]
        """Get per-timestamp of the requested metric for (total)."""
        total = []
        for timestamp, stats in self.all_perf_data:
            total_stats = stats['(total)']
            total.append((timestamp, total_stats.get(metric, 0)))
        return total

    def fetch_individual_metric(self, metric):
        # type: (str) -> List[Tuple[Any, Any]]
        """Get per-timestamp of the requested metric for all volumes."""
        metrics = []
        # These are placeholders for totals or when there are no volumes.
        # We don't care about totals in this context, just the individual components.
        for timestamp, stats in self.all_perf_data:
            if metric in ('host_name', 'volume_name'):
                filtered_stats = {name: name for name in stats if name != '(total)'}
            else:
                # For each volume/host get the value of each statistic, if there is not a value associated with it
                # then add a placeholder.  This is true for SAN latency, which may or may not have a value in some
                # Purity versions.
                filtered_stats = {name: stats[name].get(metric, 0) for name in stats if name != '(total)'}
            metrics.append((timestamp, filtered_stats))
        return metrics

    def get_perf_stats(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get per-timestamp of all of the metrics for (total)."""
        total = []
        for timestamp, stats in self.all_perf_data:
            total_stats = stats['(total)']
            total.append((timestamp, total_stats))
        return total

    def get_read_bandwidth(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total read bandwidth for each timestamp."""
        return self.fetch_total_metric('read_bw')

    def get_write_bandwidth(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total write bandwidth for each timestamp."""
        return self.fetch_total_metric('write_bw')

    def get_read_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total read iops for each timestamp."""
        return self.fetch_total_metric('read_iops')

    def get_write_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total write iops for each timestamp."""
        return self.fetch_total_metric('write_iops')

    def get_read_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total read latency for each timestamp."""
        return self.fetch_total_metric('read_ms')

    def get_read_san_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total read SAN latency for each timestamp."""
        return self.fetch_total_metric('read_san_ms')

    def get_write_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total write latency for each timestamp."""
        return self.fetch_total_metric('write_ms')

    def get_write_san_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get total write SAN latency for each timestamp."""
        return self.fetch_total_metric('write_san_ms')

    # Per Host Stats:
    def get_host_name(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host names for each timestamp."""
        return self.fetch_individual_metric('host_name')

    def get_host_perf_stats(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get per-timestamp of all of the metrics for all hosts."""
        return self.all_perf_data

    def get_host_read_bandwidth(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host read bandwidth for each timestamp."""
        return self.fetch_individual_metric('read_bw')

    def get_host_write_bandwidth(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host write bandwidth for each timestamp."""
        return self.fetch_individual_metric('write_bw')

    def get_host_read_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host read iops for each timestamp."""
        return self.fetch_individual_metric('read_iops')

    def get_host_write_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host write iops for each timestamp."""
        return self.fetch_individual_metric('write_iops')

    def get_host_read_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host read latency for each timestamp."""
        return self.fetch_individual_metric('read_ms')

    def get_host_read_san_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host read SAN latency for each timestamp."""
        return self.fetch_individual_metric('read_san_ms')

    def get_host_write_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host write latency for each timestamp."""
        return self.fetch_individual_metric('write_ms')

    def get_host_write_san_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get host write SAN latency for each timestamp."""
        return self.fetch_individual_metric('write_san_ms')

    # Per Volume Stats:
    def get_volume_name(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume names for each timestamp."""
        return self.fetch_individual_metric('volume_name')

    def get_volume_perf_stats(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get per-timestamp of all of the metrics for all volumes."""
        return self.all_perf_data

    def get_volume_read_bandwidth(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume read bandwidth for each timestamp."""
        return self.fetch_individual_metric('read_bw')

    def get_volume_write_bandwidth(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume write bandwidth for each timestamp."""
        return self.fetch_individual_metric('write_bw')

    def get_volume_read_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume read iops for each timestamp."""
        return self.fetch_individual_metric('read_iops')

    def get_volume_write_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume write iops for each timestamp."""
        return self.fetch_individual_metric('write_iops')

    def get_volume_read_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume read latency for each timestamp."""
        return self.fetch_individual_metric('read_ms')

    def get_volume_read_san_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume read SAN latency for each timestamp."""
        return self.fetch_individual_metric('read_san_ms')

    def get_volume_write_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume write latency for each timestamp."""
        return self.fetch_individual_metric('write_ms')

    def get_volume_write_san_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get volume write SAN latency for each timestamp."""
        return self.fetch_individual_metric('write_san_ms')


def _ms_latency(value):
    # type: (str) -> int
    """Convert a latency value to milliseconds."""
    return round(time_utils.Timedelta.from_microseconds(value).milliseconds, 2)


def _to_raw(raw_value, scale):
    # type: (str, str) -> int
    """Add expected unit helpers before converting to raw."""
    if 'byte' in scale and 'B' not in raw_value:
        # The bytes scales expect 'B' to be present.
        if scale == 'binary_bytes' and not raw_value[-1].isdigit():
            raw_value += 'i'
        raw_value += 'B'
    elif scale == 'iops':
        raw_value = raw_value.lower()
    return format_utils.to_raw(raw_value, scale)


def split_stats_line(line):
    # type: (str) -> List[str]
    """Split up a line of vol/volume_stats content."""
    return [item.strip() for item in line.split('  ') if item.strip()]
