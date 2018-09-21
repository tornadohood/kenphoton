"""Contains parser definitions on how to extract data from the remote_kern.log."""

import logging

from photon.lib import parser_utils

LOGGER = logging.getLogger(__name__)


class RemoteKernFormData(parser_utils.FormData):
    """Forms used by the RemoteKernParser."""
    # Example
    # thing = parser_utils.SimpleTextForm(
    #     text_to_match='stuff',
    #     regexes={'default': r'(?P<timestamp>{}).*''},
    # )


class RemoteKernData(parser_utils.LogData):
    """Container for remote kern data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        """Create an object to track needed forms."""
        remote_kern_forms = RemoteKernFormData()
        super(RemoteKernData, self).__init__({form: remote_kern_forms[form] for form in needed_forms})
        LOGGER.debug('RemoteKernData initialized with needed_forms: {}'.format(needed_forms))


class RemoteKernParser(parser_utils.ParallelLogParser):
    """Defines all remote kern data parsing functions."""
    forms = RemoteKernFormData()
    fields = {
        # Each form will need itself at least, but might require additional fields.
        # 'thing': RemoteKernData(['thing']),
    }

    # Additional function definitions:
    # Example
    # def get_thing(self):
    #    return self.get_form_lines('thing')
