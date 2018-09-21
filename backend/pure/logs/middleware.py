"""Contains parser definitions on how to extract data from the middleware.log."""

import logging

from photon.lib import parser_utils

LOGGER = logging.getLogger(__name__)


class MiddlewareFormData(parser_utils.FormData):
    """Forms used by the MiddlewareParser."""
    # Example
    # thing = parser_utils.SimpleTextForm(
    #     text_to_match='stuff',
    #     regexes={'default': r'(?P<timestamp>{}).*''},
    # )


class MiddlewareData(parser_utils.LogData):
    """Container for middleware data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        """Create an object to track needed forms."""
        middleware_forms = MiddlewareFormData()
        super(MiddlewareData, self).__init__({form: middleware_forms[form] for form in needed_forms})
        LOGGER.debug('MiddlewareData initialized with needed_forms: {}'.format(needed_forms))


class MiddlewareParser(parser_utils.ParallelLogParser):
    """Defines all middleware data parsing functions."""
    forms = MiddlewareFormData()
    fields = {
        # Each form will need itself at least, but might require additional fields.
        # 'thing': MiddlewareData(['thing']),
    }

    # Additional function definitions:
    # Example
    # def get_thing(self):
    #    return self.get_form_lines('thing')
