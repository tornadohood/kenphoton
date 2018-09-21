"""Contains parser definitions on how to extract data from the rdmaoopsd.log."""

import logging

from photon.lib import parser_utils
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)


class RdmaoopsdFormData(parser_utils.FormData):
    """Forms used by the RdmaoopsdParser."""
    # Example
    # thing = parser_utils.SimpleTextForm(
    #     text_to_match='stuff',
    #     regexes={'default': r'(?P<timestamp>{}).*''},
    # )
    zero_line = parser_utils.SimpleTextForm(
        # TODO: PT-2094 Find out what this log line actually tells us.
        text_to_match='<0>',
    )


class RdmaoopsdData(parser_utils.LogData):
    """Container for rdmaoopsd data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        """Create an object to track needed forms."""
        rdmaoopsd_forms = RdmaoopsdFormData()
        super(RdmaoopsdData, self).__init__({form: rdmaoopsd_forms[form] for form in needed_forms})
        LOGGER.debug('RdmaoopsdData initialized with needed_forms: {}'.format(needed_forms))


class RdmaoopsdParser(parser_utils.ParallelLogParser):
    """Defines all rdmaoopsd data parsing functions."""
    forms = RdmaoopsdFormData()
    fields = {
        # Each form will need itself at least, but might require additional fields.
        'zero_line': RdmaoopsdData(['zero_line']),
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

    def get_zero_line(self):
        return self._pull_from_line('zero_line')
