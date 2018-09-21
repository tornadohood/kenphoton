"""Contains parser definitions on how to extract data from the esxconf file."""

import logging

from photon.lib import parser_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)    # type: logging.Logger


class EsxconfFormData(parser_utils.FormData):
    """Forms used by the EsxconfParser."""

    ats_offload = parser_utils.SimpleTextForm(
        # /adv/VMFS3/HardwareAcceleratedLocking = "0"
        text_to_match='HardwareAcceleratedLocking',
    )
    disk_max_io_size = parser_utils.SimpleTextForm(
        # /adv/Disk/DiskMaxIOSize = "4096"
        text_to_match='DiskMaxIOSize',
    )
    wsame_offload = parser_utils.SimpleTextForm(
        # /adv/DataMover/HardwareAcceleratedInit = "0"
        text_to_match='HardwareAcceleratedInit',
    )
    xcopy_offload = parser_utils.SimpleTextForm(
        # /adv/DataMover/HardwareAcceleratedMove = "0"
        text_to_match='HardwareAcceleratedMove',
    )
    xcopy_offload_size = parser_utils.SimpleTextForm(
        # /adv/DataMover/MaxHWTransferSize = "16384"
        text_to_match='MaxHWTransferSize',
    )


class EsxconfData(parser_utils.LogData):
    """Container for esxconf data base on parser_utils.LogData."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        esxconf_forms = EsxconfFormData()
        super(EsxconfData, self).__init__({form: esxconf_forms[form] for form in needed_forms})
        LOGGER.debug('EsxconfData initialized with needed_forms: {}'.format(needed_forms))


class EsxconfParser(parser_utils.ParallelLogParser):
    """Defines all esxconf data parsing functions."""
    forms = EsxconfFormData()
    fields = {
        'ats_offload': EsxconfData(['ats_offload']),
        'disk_max_io_size': EsxconfData(['disk_max_io_size']),
        'wsame_offload': EsxconfData(['wsame_offload']),
        'xcopy_offload': EsxconfData(['xcopy_offload']),
        'xcopy_offload_size': EsxconfData(['xcopy_offload_size'])
    }

    def _pull_from_line(self, form_name):
        # type: (str) -> List[Any]
        """Get value tuple from lines."""
        values = []
        results = self.get_form_lines(form_name)
        for line in results:
            if not line or isinstance(line, float):
                # Skip empty and nan lines.
                continue
            # Example line: /adv/DataMover/MaxHWTransferSize = "16384"
            # Remove new line characters and leading whitespace.
            line = line.strip()
            values.append(line.split('=')[-1].strip(' "'))
        return values

    def get_ats_offload(self):
        """Get form lines for ats_offload."""
        return self._pull_from_line('ats_offload')

    def get_disk_max_io_size(self):
        """Get form lines for disk_max_io_size."""
        return self._pull_from_line('disk_max_io_size')

    def get_wsame_offload(self):
        """Get form lines for wsame_offload."""
        return self._pull_from_line('wsame_offload')

    def get_xcopy_offload(self):
        """Get form lines for xcopy_offload."""
        return self._pull_from_line('xcopy_offload')

    def get_xcopy_offload_size(self):
        """Get form lines for xcopy_offload_size."""
        return self._pull_from_line('xcopy_offload_size')
