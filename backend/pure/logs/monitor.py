"""Contains parser definitions on how to extract data from the monitor.log."""

import ast
import logging
import ujson

from photon.lib import parser_utils

LOGGER = logging.getLogger(__name__)
# Example: 'May 31 18 00:14:09'
TIMESTAMP = r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}\s+(?:\d{2}:?){3}).*?'


class MonitorFormData(parser_utils.FormData):
    """Forms used by the MonitorParser."""
    alerts = parser_utils.SimpleTextForm(
        text_to_match='alert.generated',
        regexes={'default': TIMESTAMP + r'\s+alert.generated\s+(?P<alert>\{.*\})'},
    )
    messages = parser_utils.SimpleTextForm(
        text_to_match='message:',
        regexes={'default': TIMESTAMP + r'\s+message:\s+(?P<message>\{.*\})'},
    )


class MonitorData(parser_utils.LogData):
    """Container for monitor data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        """Create an object to track needed forms."""
        monitor_forms = MonitorFormData()
        super(MonitorData, self).__init__({form: monitor_forms[form] for form in needed_forms})
        LOGGER.debug('MonitorData initialized with needed_forms: {}'.format(needed_forms))


class MonitorParser(parser_utils.ParallelLogParser):
    """Defines all monitor data parsing functions."""
    forms = MonitorFormData()
    fields = {
        'alerts': MonitorData(['alerts']),
        'messages': MonitorData(['messages']),
    }

    def get_alerts(self):
        """Get array alerts."""
        parsed = []
        messages = self.pull_from_regex('alerts')
        for timestamp, message in messages:
            parsed.append((timestamp, ujson.loads(message['alert'], precise_float=True)))
        return parsed

    def get_messages(self):
        """Get array message events."""
        parsed = []
        messages = self.pull_from_regex('messages')
        for timestamp, message in messages:
            parsed.append((timestamp, ast.literal_eval(message['message'])))
        return parsed
