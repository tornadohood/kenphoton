"""Contains parser definitions on how to extract data from the bcon.log."""

import logging

from photon.lib import parser_utils
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)

TIMESTAMP = r'\w{3}\s+\d{1,2}\s\d{2}:\d{2}:\d{2}'


class BconFormData(parser_utils.FormData):
    """Forms used by the BconParser."""
    kernel_panic = parser_utils.IntervalForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='Kernel panic',
        start_text='Kernel panic',
        end_text='------------[ cut here ]------------',
    )
    watchdog_timeout = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        # TODO: PT-2103 find example
        text_to_match='watchdog: Watchdog will fire in',  # PURE-72780
    )


class BconData(parser_utils.LogData):
    """Container for bcon data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        """Create an object to track needed forms."""
        bcon_forms = BconFormData()
        super(BconData, self).__init__({form: bcon_forms[form] for form in needed_forms})
        LOGGER.debug('BconData initialized with needed_forms: {}'.format(needed_forms))


class BconParser(parser_utils.ParallelLogParser):
    """Defines all bcon data parsing functions."""
    forms = BconFormData()
    fields = {
        # Each form will need itself at least, but might require additional fields.
        'kernel_panic': BconData(['kernel_panic']),
        'watchdog_timeout': BconData(['watchdog_timeout']),
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

    def get_kernel_panic(self):
        return self._pull_from_line('kernel_panic')

    def get_watchdog_timeout(self):
        return self._pull_from_line('watchdog_timeout')
