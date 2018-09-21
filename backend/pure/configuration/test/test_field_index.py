"""Validate the contents of the field_index.ini file."""

import os

try:
    from ConfigParser import ConfigParser
except ImportError:
    # This is all lowercase in Python3
    from configparser import ConfigParser

DATA_SOURCES = ('insights', 'iris', 'logs', 'middleware', 'mr_tunable', 'pure1', 'warehouse')
PATH = os.path.dirname(__file__)


def test_fields():
    # type: () -> None
    """Ensure that each 'field' has everything it needs."""
    parser = ConfigParser()
    # Remove '/test' from the path and add field_index.ini
    parser.read(os.path.join(os.path.dirname(PATH), 'field_index.ini'))
    # Assert that we have sections
    assert parser.sections(), 'No sections found.'
    for section in parser.sections():
        if section == '__defaults__':
            continue
        # Assert that each section has options specified
        options = parser.options(section)
        assert options, 'Section "{}" has no options.'.format(section)
        for option in options:
            # Assert that the option is defined in the OPTIONS
            msg = 'Section "{}" has an unknown Option "{}".'.format(section, option)
            assert option in DATA_SOURCES, msg
            # Assert that each option has one or more values
            msg = 'Section "{}", Option "{}" has no arguments.'.format(section, option)
            assert parser.get(section, option).split(',') != [''], msg
