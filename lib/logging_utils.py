""" Logging utilities for consistent logging across photon. """

from __future__ import unicode_literals

import getpass
import logging
import logging.handlers
import os

from six import iteritems

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
except ImportError:
    pass

from photon.lib import config_utils
from photon.lib import env_utils


SETTINGS = config_utils.get_settings()
DEFAULT_LOG_DIR = os.getcwd()
DEFAULT_LOG_NAME = 'pure_tools.log'
DEFAULT_LOCATION = os.path.join(DEFAULT_LOG_DIR, DEFAULT_LOG_NAME)
USER = getpass.getuser()

# Log Formatting:
DATE_FORMAT = '%b %d, %Y %H:%M:%S%z'
LOG_FORMAT = '%(levelname)-8s: %(asctime)s - %(module)s.%(funcName)s -  %(message)s'
DEBUG_FORMAT = '%(levelname)-8s: %(asctime)s - %(process)d.%(module)s.%(funcName)s - %(message)s'
INFO_FORMAT = '%(levelname)-8s: %(asctime)s - %(module)s.%(funcName)s -  %(message)s'
MS_FORMAT = '%s.%03d'  # Milliseconds formatting.

# Non-default formats based on log level.  Use default if not found.
# -8 after (levelname) ensures consistent spacing for the rest of the log line.
FORMATS = {logging.INFO: INFO_FORMAT,
           logging.DEBUG: DEBUG_FORMAT}

LOCATIONS = {
    'Ubuntu': os.path.join('/support/pure_tools', '{}-pure_tools.log'.format(USER)),
    'Purity': '/var/log/purity/pure_tools.log',
    'other': os.path.join(os.path.expanduser('~'), 'pure_tools.log')
}


def configure_logger(name,                                                                  # type: str
                     level=getattr(logging, SETTINGS['logging']['log_level'].upper()),      # type: str
                     lsb_location='/etc/lsb-release',                                       # type: str
                     backup_count=SETTINGS['logging']['log_retention_count'],               # type: int
                     add_stream=SETTINGS['logging']['add_stream']                           # type: bool
                    ):                                                                      # type: (...) -> Any
    """Instantiate the logger with photon logging config.

    Arguments:
        name  (str): logger name - will affect ancestry inheritance.
        level (int): logging level for the logger to operate at.
        lsb_location (str): Where to locate the LSB Release file.
        backup_count (int): How many log files to retain before overwriting.
        add_stream (bool): Include a stream handler in the logger.

    Returns:
        logger (logging.Logger): reference to configured Logger object
    """
    # Get locations and formats or use default.
    distro = env_utils.get_distro(lsb_location)
    log_path = get_log_path(distro)

    # Get and configure logger.
    logger = logging.getLogger(name)
    has_file_handler = False
    has_stream_handler = False
    # TODO: Need to configure handler separate so we can test it before we put it on purity.
    # TODO: handler configure needs to rotate if on fuse, not rotate on box

    if logger.handlers:
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.TimedRotatingFileHandler):
                has_file_handler = True
            if isinstance(handler, logging.StreamHandler):
                has_stream_handler = True
    # Add a stream handler if it's configured.
    if add_stream and not has_stream_handler:
        add_stream_handler(logger)
    if not has_file_handler:
        add_file_handler(logger, log_path, backup_count, when='D')
    # set logger level.
    logger.setLevel(level)
    return logger


def add_file_handler(logger, log_path, backup_count, when='D'):
    # type: (Any, str, int, str) -> None
    """ Add a TimedRotatingFileHandler to a logger. """
    log_handler = logging.handlers.TimedRotatingFileHandler(log_path, when=when,
                                                            backupCount=backup_count)
    log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    log_formatter.default_msec_format = MS_FORMAT
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)


def is_placeholder(logger_name):
    # type: (str) -> bool
    """ Check if our logger exists and is a placeholder and return bool."""
    logger = get_photon_loggers().get(logger_name)
    return isinstance(logger, logging.PlaceHolder)


def configure_photon_placeholder():
    # type: () -> None
    """ Configure any placeholders as full loggers."""
    loggers = get_photon_loggers()
    base_logger = sorted(loggers.keys())[0]
    configure_logger(base_logger)


def add_stream_handler(logger):
    # type: (Any) -> None
    """ Add a stream handler to a logger. """
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)


def get_loggers():
    # type: () -> Any
    """Return all loggers as a dict with name as key, logger as value.

    Returns:
        loggerDict (dict): logger name key with logger value.
    """
    return logging.Logger.manager.loggerDict


def get_photon_loggers():
    # type: () -> Dict[str, Any]
    """Return photon loggers as a dict with name as key, logger as value.

    Returns:
        photon_loggers (dict): logger name key with logger value.
    """
    photon_loggers = {}
    # Mimicking the format of get_loggers output.
    for name, logger in iteritems(get_loggers()):
        # Only return loggers with photon in name.
        if 'photon' in name:
            photon_loggers[name] = logger
    return photon_loggers


def get_log_path(distro, locations=None):
    # type: (str, Optional[List[str]]) -> str
    """ Get the location for logging that's valid and exists.

    Arguments:
        distro (str): lsb-release
        locations (dict): dict to override the default locations.

    Returns:
        log_path (str): location where log files will be generated
    """
    locations = locations or LOCATIONS
    expected_location = locations.get(distro, LOCATIONS['other'])
    if distro == 'Ubuntu' and not os.path.exists(expected_location):
        # If the path doesn't exist and we're Ubuntu, we're not on Fuse, so default to other.
        log_path = LOCATIONS['other']
    elif os.path.exists(expected_location):
        log_path = expected_location
    else:
        log_path = LOCATIONS['other']
    return log_path
