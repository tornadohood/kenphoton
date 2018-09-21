"""Common utility functions related to interacting with the environment."""

import fcntl
import logging
import os
import struct
import termios

# pylint: disable=unused-import
try:
    from typing import Any
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


def get_distro(lsb_file):
    # type: (str) -> str
    """Determine if on array by checking to see if array specific directories exist.

    Arguments:
        lsb_file (str): Location of the lsb-release file

    Returns:
        distro (str): Purity/Ubuntu depending on content of /etc/lsb-release.
    """
    # Using the Linux Standard Base release file to determine if we're on array or on fuse.
    # Example of file content.
    # os76@SLC-405-2-ct0:~$ cat /etc/lsb-release
    # DISTRIB_ID=Purity
    # DISTRIB_RELEASE=4.7.6
    # DISTRIB_DESCRIPTION="Purity Operating Environment 4.7.6"
    # DISTRIB_CODENAME="Star Sapphire"
    location = 'other'
    if os.path.exists(lsb_file):
        with open(lsb_file, 'rt') as release:
            for line in release.readlines():
                if 'purity' in line.lower():
                    location = 'Purity'
                elif 'ubuntu' in line.lower():
                    location = 'Ubuntu'
    # An explicit return False to show our exit point more clearly.
    return location


def get_tty_wid():
    # type: (...) -> int
    """Determine the width of the current terminal."""
    try:
        _, tty_wid = struct.unpack('hh', fcntl.ioctl(2, termios.TIOCGWINSZ, '1234'))  # type: Any, int
    # Leaving the broad exception, because PowerShell.
    # pylint: disable=broad-except
    except Exception as err:
        # We catch all Exceptions to be safe, ignore it and use the default terminal width.
        LOGGER.debug(err)
        tty_wid = 80
    # Workaround: Powershell's scroll bar may displace a character and cause word-wrap.
    # We simply remove 2 from the tty_wid to be safe.
    tty_wid -= 2
    return tty_wid


def is_fuse():
    # type: (...) -> bool
    """Determine if the current environment is FUSE."""
    # The FUSE environment has /fuse or /fuse2 folders as well as /support.
    return (os.path.exists('/fuse') or os.path.exists('/fuse2')) and os.path.exists('/support')


def is_onbox():
    # type: (...) -> bool
    """Check if the script is being run onbox."""
    return bool(os.path.exists('/opt/Purity') and os.path.exists('/cache/nursery/nursery'))
