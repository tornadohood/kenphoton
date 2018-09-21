"""Common utilities related to the printing of output."""

import logging
import sys

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Optional
except ImportError:
    pass

from photon.lib import env_utils

LOGGER = logging.getLogger(__name__)


def status_update(update=None, output_pipe=sys.stderr):
    # type: (Optional[str], Any) -> None
    """Print a status bar at the bottom of the screen.

    Args:
        update: (str) that will be printed to the output_pipe.
            NOTE: If update is None (Default), a blank line will be printed to clear the screen.
        output_pipe: (pipe) destination pipe that update will be use.
            NOTE: pipe object must have "write" and "flush" methods.
    """
    if not hasattr(output_pipe, 'write') or not hasattr(output_pipe, 'flush'):
        msg = 'Output_pipe object is missing "write" and/or "flush" methods.'
        LOGGER.error(msg)
        raise TypeError(msg)
    tty_wid = env_utils.get_tty_wid()
    # Write a blank line to prevent overlap with any previous update text.
    output_pipe.write('\r' + ' ' * tty_wid + '\r')
    if not update:
        return
    # Avoid word-wrap by truncating long update text strings to the tty_wid.
    update = ''.join(update[:tty_wid])
    # Print the new update and return to the beginning of the line.
    # The extra space at the beginning prevents the curser from covering cover the first letter
    output_pipe.write('\r {}\r'.format(update))
    # NOTE: This never printed a newline character, the next output will begin on the same line.
    output_pipe.flush()
