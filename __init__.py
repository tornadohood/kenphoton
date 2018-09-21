""" Base init for photon library. """

from photon.lib import logging_utils

# Configure the logger if it doesn't exist.
if not logging_utils.get_loggers().get(__name__):
    logging_utils.configure_logger(__name__)
# If we have any placeholder loggers like in PT-1547, configure them.
logging_utils.configure_photon_placeholder()
