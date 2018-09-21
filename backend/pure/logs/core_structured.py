"""Contains parser definitions on how to extract data from the core-structured log."""

import collections
import ujson

from six import iteritems

# pylint: disable=unused-import,line-too-long
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


class CoreStructuredFormData(parser_utils.FormData):
    """Forms used by the CoreParser."""

    per_bdev_stats = parser_utils.SimpleTextForm(
        text_to_match='per_bdev_stats',
    )


class CoreStructuredLogData(parser_utils.LogData):
    """Manage information about a piece Data from the logs."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        core_forms = CoreStructuredFormData()
        super(CoreStructuredLogData, self).__init__({form: core_forms[form] for form in needed_forms})


class CoreStructuredParser(parser_utils.ParallelLogParser):
    """Defines all core data parsing functions."""
    forms = CoreStructuredFormData()
    fields = {
        'per_bdev_stats': CoreStructuredLogData(['per_bdev_stats']),
        'per_bdev_read_latency': CoreStructuredLogData(['per_bdev_stats']),
        'per_bdev_read_bytes': CoreStructuredLogData(['per_bdev_stats']),
        'per_bdev_read_iops': CoreStructuredLogData(['per_bdev_stats']),
        'per_bdev_write_latency': CoreStructuredLogData(['per_bdev_stats']),
        'per_bdev_write_bytes': CoreStructuredLogData(['per_bdev_stats']),
        'per_bdev_write_iops': CoreStructuredLogData(['per_bdev_stats']),
    }

    def get_per_bdev_stats(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch per-timestamp values for 'per_bdev_stats'."""
        lines = self.get_form_lines('per_bdev_stats')
        threshold = time_utils.Timedelta('10 seconds')
        bdev_values = []
        temp = collections.defaultdict(list)  # type: collections.defaultdict
        floor = None
        for line in lines:
            month, day, time, _, _, json_dump = line.split()
            # Slightly reduce resolution of the timestamp so we can match up when logging took longer than 1 ms.
            timestamp = time_utils.Timestamp(' '.join([month, day, time]))
            if not floor:
                floor = timestamp
            elif timestamp - floor >= threshold:
                floor = timestamp
            else:
                timestamp = floor
            temp[timestamp].append(ujson.loads(json_dump, precise_float=True))
        for timestamp, matches in iteritems(temp):
            bdev_values.append((timestamp, matches))
        return bdev_values

    def _get_stat_from_bdev_stats(self, stat):
        # type: (str) -> List[Tuple[Any, Any]]
        """Pull a single stat from each drive per timestamp."""
        all_stats = self.get_field('per_bdev_stats')
        parsed = []
        temp = collections.defaultdict(dict)  # type: collections.defaultdict
        for timestamp, json_dumps in all_stats:
            for json_dump in json_dumps:
                name = json_dump[1]['name'].replace(':', '')
                stats = json_dump[1]['stats']
                temp[timestamp][name] = stats[stat]
        for timestamp, matches in iteritems(temp):
            parsed.append((timestamp, matches))
        return parsed

    def get_per_bdev_read_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch per-timestamp values for 'bdev_read_latency'."""
        return self._get_stat_from_bdev_stats('rd_avg_lat')

    def get_per_bdev_read_bytes(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch per-timestamp values for 'bdev_read_bytes'."""
        return self._get_stat_from_bdev_stats('rd_bytes')

    def get_per_bdev_read_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch per-timestamp values for 'bdev_read_iops'."""
        return self._get_stat_from_bdev_stats('rd_cnt')

    def get_per_bdev_write_latency(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch per-timestamp values for 'bdev_write_latency'."""
        return self._get_stat_from_bdev_stats('wr_avg_lat')

    def get_per_bdev_write_bytes(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch per-timestamp values for 'bdev_write_bytes'."""
        return self._get_stat_from_bdev_stats('wr_bytes')

    def get_per_bdev_write_iops(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch per-timestamp values for 'bdev_write_iops'."""
        return self._get_stat_from_bdev_stats('wr_cnt')
