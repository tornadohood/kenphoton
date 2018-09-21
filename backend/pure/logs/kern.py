"""Contains parser definitions on how to extract data from the kern.log."""

import logging

from photon.lib import parser_utils

LOGGER = logging.getLogger(__name__)


class KernFormData(parser_utils.FormData):
    """Forms used by the KernParser."""
    # Example
    # thing = parser_utils.SimpleTextForm(
    #     text_to_match='stuff',
    #     regexes={'default': r'(?P<timestamp>{}).*''},
    # )


class KernData(parser_utils.LogData):
    """Container for kern data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        """Create an object to track needed forms."""
        kern_forms = KernFormData()
        super(KernData, self).__init__({form: kern_forms[form] for form in needed_forms})
        LOGGER.debug('KernData initialized with needed_forms: {}'.format(needed_forms))


class KernParser(parser_utils.ParallelLogParser):
    """Defines all kern data parsing functions."""
    forms = KernFormData()
    fields = {
        # Each form will need itself at least, but might require additional fields.
        # 'thing': KernData(['thing']),
    }

    # Additional function definitions:
    # Example
    # def get_thing(self):
    #    return self.get_form_lines('thing')
