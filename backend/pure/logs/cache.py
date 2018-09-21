"""Contains parser definitions on how to extract data from the cache.log."""

import logging

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Type
except ImportError:
    pass

from photon.lib import parser_utils
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)


class CacheFormData(parser_utils.FormData):
    """Forms used by the CacheParser."""
    # Example
    # thing = parser_utils.SimpleTextForm(
    #     text_to_match='stuff',
    #     regexes={'default': r'(?P<timestamp>{}).*''},
    # )
    cache_uptime = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='uptime',
        regexes={'default': r'(?P<timestamp>\w{3}\s+\d{1,2}\s\d{2}:\d{2}:\d{2}(.\d+)?).+Purity (?P<purity_version>\d+\.\d+\.\d+(\.\w+)?).+uptime (?P<days>\d+)d:(?P<hours>\d+)h:(?P<minutes>\d+)m:(?P<seconds>\d+)s'}
    )
    stacktrace_cache = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='STACKTRACE',
    )


class CacheData(parser_utils.LogData):
    """Container for cache data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        # type: (List[str]) -> None
        """Create an object to track needed forms."""
        cache_forms = CacheFormData()
        super(CacheData, self).__init__({form: cache_forms[form] for form in needed_forms})
        LOGGER.debug('CacheData initialized with needed_forms: {}'.format(needed_forms))


class CacheParser(parser_utils.ParallelLogParser):
    """Defines all cache data parsing functions."""
    forms = CacheFormData()
    fields = {
        # Each form will need itself at least, but might require additional fields.
        'cache_uptime': CacheData(['cache_uptime']),
        'stacktrace_cache': CacheData(['stacktrace_cache']),
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

    def get_cache_uptime(self):
        # type: () -> Any
        return self.pull_from_regex('cache_uptime')

    def get_stacktrace_cache(self):
        # type: () -> List[Tuple[Any, Any]]
        """Get generic stack trace lines."""
        return self._pull_from_line('stacktrace_cache')
