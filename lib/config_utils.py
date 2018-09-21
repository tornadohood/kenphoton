"""Common utility functions related to parsing configuration files."""

import logging
import os

from collections import defaultdict
try:
    from ConfigParser import RawConfigParser
except ImportError:
    # This is all lowercase in Python3
    from configparser import RawConfigParser
# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Type
    from typing import Union
    CONFIG_TYPES = Union[int, float, str, bool, list]
except ImportError:
    pass

HOME = os.path.expanduser('~')
LOGGER = logging.getLogger(__name__)


def _apply_types(items, static_types=None):
    # type: (Tuple[str, str], Optional[Dict[str, str]]) -> Dict[str, CONFIG_TYPES]
    """Apply the type based upon the type hint given in the INI configuration line."""
    static_types = static_types or {}
    section = {}
    type_actions = {
        # Convert string name to the actual type.
        # For some types there is a custom action to take.
        'str': str,
        'float': float,
        'int': int,
        'bool': lambda val: True if val == 'True' else False,
        'list': lambda val: [item.strip() for item in val.split(',') if item.strip()]
    }
    for key, value in items:
        if 'type:' in value:
            raw_value, new_type = value.split('type:')
            new_type = type_actions.get(new_type.strip(), str)
        elif key in static_types:
            # Apply static settings which may have been given from a __defaults__ section.
            new_type = type_actions.get(static_types[key], str)
            raw_value = value
        else:
            # Default to str if we have no static or given type hints.
            new_type = str
            raw_value = value
        section[key] = new_type(raw_value.strip())
    return section


def get_config(ini_file):
    # type: (str) -> Dict[str, Any]
    """Read an INI file and convert the contents to a dictionary.

    Arguments:
        ini_file (str): The full path to an *.ini/*.cfg file.

    Returns:
        config (dict): Sections and sub-sections of the INI file as dict keys and values.
    """
    # Raise an IOError because parser.read does not do this
    if not os.path.exists(ini_file):
        error_msg = '"{}" does not exist.'.format(ini_file)
        raise IOError(error_msg)
    parser = RawConfigParser()  # type: Type[RawConfigParser]
    parser.read(ini_file)
    config = defaultdict(dict)  # type: defaultdict
    # If there is a __defaults__ section, apply defaults to all other sections
    if '__defaults__' in parser.sections():
        defaults = _apply_types(parser.items('__defaults__'))
        # Implicitly apply the type to all of the options, this can be overridden by each section explicitly.
        static_types = {key: type(value).__name__ for key, value in defaults.items()}
    else:
        defaults = {}
        static_types = {}
    for section in parser.sections():
        if section == '__defaults__':
            continue
        # Apply the global defaults to each section.
        # It is much easier to just apply all of the defaults and override them,
        # than to only apply defaults where we don't have a value.
        config[section].update(defaults)
        # PT-2294 - Use the type hint to apply a type, or leave it as a string.
        config[section].update(_apply_types(parser.items(section), static_types))
    return dict(config)


def get_index(path):
    # type: (str) -> Dict[str, Any]
    """Get the full path to the respective index.ini files."""
    # From the path of the config_utils.py (__file__), go back one dir and then join to path.
    # We need to use relative paths since we don't know where photon will live.
    index_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)  # type: str
    information_index = get_config(index_file)  # type: Dict[str, Any]
    return information_index


def get_field_index():
    # type: () -> Dict[str, Any]
    """Get the field_index.ini file contents for pure based tools."""
    path = 'backend/pure/configuration/field_index.ini'  # type: str
    return get_index(path)


def get_metric_index():
    # type: () -> Dict[str, Any]
    """Get the metric_index.ini file contents for all ReportAPI metrics."""
    path = 'report/configuration/metric_index.ini'  # type: str
    return get_index(path)


def get_settings():
    # type: () -> Dict[str, Any]
    """Get the settings.ini file contents.
    Override defaults with user-defined settings in "~/.photon/settings.ini".
    """
    settings_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.ini')  # type: str
    settings = get_config(settings_file)  # type: Dict[str, Any]
    override_file = os.path.join(HOME, '.photon', 'settings.ini')  # type: str
    if os.path.exists(override_file):
        override_settings = get_config(override_file)  # type: Dict[str, Any]
        # Overwrite any of the default settings with the override file contents.
        LOGGER.warning('Overriding photon defaults with the contents of "~/.photon/settings.ini".')
        settings.update(override_settings)
    return settings


def get_table_index():
    # type: () -> Dict[str, Any]
    """Get the table_index.ini file contents for all ReportAPI metrics."""
    path = 'report/configuration/table_index.ini'  # type: str
    return get_index(path)


def get_vmware_index():
    # type: () -> Dict[str, Any]
    """Get the vmware_index.ini file contents for vmware based tools."""
    path = 'backend/vmware/configuration/vmware_index.ini'  # type: str
    return get_index(path)
