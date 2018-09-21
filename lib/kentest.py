"""Contains common util functions that abstract the concept of "the array".
See: https://wiki.purestorage.com/display/SDT/ArrayIdent+Object
"""

import logging
import os
import re

from photon.lib import custom_errors
from photon.lib import file_utils
from photon.lib import env_utils
from photon.lib import validation_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

# pylint: disable=logging-format-interpolation
LOGGER = logging.getLogger(__name__)


def convert_fqdn_to_logdir(fqdn):
    # type: (str) -> str
    """Convert an FQDN to the named logs directory.

    Arguments:
        fqdn (str): valid FQDN to parse into directory on fuse

    Returns:
        log_dir (str): validated log directory built from valid FQDN
    """
    validation_utils.fqdn(fqdn, ValueError)
    LOGGER.debug('Converting FQDN "{}" to a FUSE log path.'.format(fqdn))
    array, domain = get_array_and_domain_from_fqdn(fqdn)  # type: str, str
    base_log_dir = os.path.join('/logs', domain, '{}-ct0'.format(array))  # type: str
    return base_log_dir


def convert_logdir_to_fqdn(log_dir):
    # type: (str) -> str
    """Convert a log directory to an FQDN.

    Arguments:
        log_dir (str): A log path for a FlashArray on FUSE.

    Returns:
        A fully qualified domain name for an Array.  i.e. 'array.domain.com'
    """
    validation_utils.fuse_base_path(log_dir, ValueError)
    # Example: /logs/domain.com/array-ct0
    path_reg = re.compile(r'.*/(?P<domain>.*?)/(?P<array_name>.*?)-ct\d/?')  # type: Any
    match = path_reg.search(log_dir)  # type: Any
    if not match:
        error_msg = 'Unable to generate an FQDN from the log directory: "{}".'.format(log_dir)  # type: str
        LOGGER.exception('LogParserError: {}'.format(error_msg))
        raise custom_errors.LogParserError(error_msg)
    array_domain = '.'.join([match.group('array_name'), match.group('domain')])  # type: str
    return array_domain


def get_array_and_domain_from_fqdn(fqdn):
    # type: (str) -> Tuple[str, str]
    """Return array and domain from fqdn.

    Arguments:
        fqdn (str): FQDN to pull array and domain from

    Returns:
        array (str): array name (analogous to hostname)
        domain (str): domain name
    """
    validation_utils.fqdn(fqdn, ValueError)
    array, domain = fqdn.split('.', 1)  # type: str, str
    LOGGER.debug('array: {}, domain: {}'.format(array, domain))
    array = re.sub('-ct[01]$', '', array)
    LOGGER.debug('array updated to {}'.format(array))
    return array, domain


def get_peer_path(path):
    # type: (str) -> str
    """Generate the peer's path based upon the current controller's log path.

    Arguments:
        path (str): The current controller's path.

    Returns:
        peer_path (str): The peer controller's path.
    """
    match = re.match(r'/.*-(?P<ct>ct[01])/?', path)  # type: Any
    if not match:
        error_msg = 'Unable to locate a controller number from path: "{}".'.format(path)  # type: str
        LOGGER.exception('ValueError: {}'.format(error_msg))
        raise ValueError(error_msg)
    if match.group('ct') == 'ct0':
        peer_path = re.sub(r'-(?P<ct>ct0)', '-ct1', path)  # type: str
    else:
        peer_path = re.sub(r'-(?P<ct>ct1)', '-ct0', path)
    return peer_path


class ArrayIdent(object):
    """The identity container of a Pure FlashArray."""

    def __init__(self, fqdn=None, log_path=None, files=None):
        # type: (Optional[str], Optional[str], Optional[str]) -> None
        """
        Arguments:
            fqdn (str): The Fully Qualified Domain Name of a FlashArray.
            log_path (str): A log path to a FlashArray's log files.
            files (list); One or more log files to use to identify an FlashArray.
        """
        self.fqdn = validation_utils.fqdn(fqdn, ValueError) if fqdn else None  # type: Optional[str]
        self._log_path = log_path  # type: Optional[str]
        self.on_box = env_utils.is_onbox()  # type: bool
        self.group_logs_by_type = {}  # type: Dict[str, str]
        self.files = file_utils.group_logs_by_type(files) if files else {}  # type: Optional[Dict[str, List[str]]]
        LOGGER.info('Using Array Identity: "{}"'.format(self.fqdn or self.log_path or
                                                        ('files' if self.files else os.getcwd())))

    @property
    def log_path(self):
        # type: (...) -> str
        """Get the log path from the FQDN or from the current directory."""
        if self._log_path:
            return self._log_path
        if self.fqdn:
            log_path = convert_fqdn_to_logdir(self.fqdn)  # type: str
        elif self.on_box:
            log_path = '/var/log'
        else:
            log_path = os.getcwd()
        self._log_path = log_path
        return self._log_path

    @property
    def ct_paths(self):
        # type: (...) -> Dict[str, str]
        """Get the log paths of each controller based upon self.log_path."""
        if self.group_logs_by_type:
            return self.group_logs_by_type
        log_paths = {}  # type: Dict[str, str]
        if '-ct0' in self.log_path:
            log_paths['CT0'] = self.log_path
            log_paths['CT1'] = get_peer_path(self.log_path)
        elif '-ct1' in self.log_path:
            log_paths['CT1'] = self.log_path
            log_paths['CT0'] = get_peer_path(self.log_path)
        else:
            LOGGER.warning('Unable to identify a specific controller path.  Setting both to the current path.')
            log_paths['CT0'] = log_paths['CT1'] = self.log_path
        self.group_logs_by_type = log_paths
        return self.group_logs_by_type
