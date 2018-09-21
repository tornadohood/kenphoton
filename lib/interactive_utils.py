"""Contains common utility functions related to interacting with the user."""

from __future__ import print_function

import argparse
import logging
import six
import sys

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
except ImportError:
    pass

from photon.lib import config_utils
from photon.lib import time_utils
from photon.lib import validation_utils

LOGGER = logging.getLogger(__name__)
SETTINGS = config_utils.get_settings()


class ChangeRequired(argparse.Action):
    """Store true and make "to_modify" required args.

    This defaults to True when evaluated - i.e.
    if args.change_required_arg:

    The if statement above would evaluate to True if the flag was present,
    and false if the flag is not present.

    Example:
        parser = photon_argparse()
        parser.add_argument('--required-arg', action='store_true', required=True)
        parser.add_argument('--dont-require', action=ChangeRequired, to_modify=['required_arg'], target_value=False)
        parser.parse_args(['--dont-require'])
    """

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        """Init for ChangeRequired class.

        Arguments:
            to_modify (list): destination names of the args to modify required flags for.
            target_value (bool): Value to set the arg.required attribute to.
        """
        kwargs['const'] = True
        kwargs['nargs'] = 0
        kwargs['default'] = False
        self.changes = kwargs.pop('changes', {})
        super(ChangeRequired, self).__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # type: (argparse.ArgumentParser, argparse.Namespace, Any, Any) -> None
        """Perform these when this action is called."""
        self._modify_required(parser)
        setattr(namespace, self.dest, self.const)

    def _modify_required(self, parser):
        # type: (argparse.ArgumentParser) -> None
        """Modify any actions to the required value requested."""
        # argparse doesn't currently have a "modify actions conditionally" that's
        # public, so we get to use the protected method.
        # pylint: disable=protected-access
        destinations = [action.dest for action in parser._actions]
        for dest, required in six.iteritems(self.changes):
            if dest not in destinations:
                message = "Could not find a valid destination for '{}'.  Please check that it is a valid argparse flag for this parser.".format(dest)
                raise argparse.ArgumentError(self, message)
            if required not in (True, False):
                message = "Only True or False changes are permitted for the required attribute, but received {} for destination {}".format(required, dest)
                raise argparse.ArgumentError(self, message)

        for action in parser._actions:
            if action.dest in self.changes:
                # Set it to the value for that action if it's in our changes.
                action.required = self.changes[action.dest]


class PhotonNamespace(argparse.Namespace):
    """An iterable/unpackable namespace object."""

    def __init__(self, **kwargs):
        super(PhotonNamespace, self).__init__(**kwargs)

    def __iter__(self):
        return six.iteritems(self.__dict__)

    def keys(self):
        return list(self.__dict__.keys())

    def __getitem__(self, key):
        return self.__dict__.get(key)


class PhotonArgumentParser(argparse.ArgumentParser):
    """An argparser with utility attributes and methods added."""

    def __init__(self, *args, **kwargs):
        super(PhotonArgumentParser, self).__init__(*args, **kwargs)

    def parse_known_args(self, args=None, namespace=None):
        if args is None:
            # args default to the system args
            args = sys.argv[1:]
        else:
            # make sure that args are mutable
            args = list(args)

        # default Namespace built from parser defaults
        if namespace is None:
            # We're using our nifty iterable/unpackable namespace instead.
            namespace = PhotonNamespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not argparse.SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not argparse.SUPPRESS:
                        setattr(namespace, action.dest, action.default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            namespace, args = self._parse_known_args(args, namespace)
            if hasattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR):
                args.extend(getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR))
                delattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR)
            return namespace, args
        except argparse.ArgumentError:
            err = sys.exc_info()[1]
            self.error(str(err))


def photon_argparse(description=None, kb_article=None, **kwargs):
    # type: (Optional[str], Optional[str], **Dict[Any, Any]) -> argparse.ArgumentParser
    """Build the generic argparse and subparsers for Photon tools.

    Arguments:
        description (str): A description of the program.
        kb_article (str): A KB article to include at the bottom of argparse.
        kwargs (dict): Keyword arguments.

    Return:
        parser (argparse.ArgumentParser): The argparse parser with the default arguments applied.
    """
    epi = """
Timestamp Examples (any timestamp from logs should work):
    'MM/DD/YYYY HH:MM:SS'
    '06/28/2025 10:37:11'

Timedelta Examples:
    Seconds: '1s' or '1 second' or '10 seconds'
    Minutes: '2m' or '1 minute' or '30 minutes'
    Hours: '3h' or '1 hour' or '24 hours'
    Days: '1d' or '1 day' or '3 days'

If you experience any issues with this tool or have suggestions on how to improve it,
please let us know in #support-dev via slack or support-dev@purestorage.com via email.
    """
    if kb_article:
        epi = 'KB Article: {}\n'.format(kb_article) + epi
    parser = PhotonArgumentParser(description=description, epilog=epi,
                                  formatter_class=argparse.RawTextHelpFormatter, **kwargs)
    ####################
    # Generic Arguments:
    ####################
    parser.add_argument('-f', '--files', help='One or more files to use.', nargs='+', type=validation_utils.filename)
    parser.add_argument('-j', '--jira', action='store_false', help='Do not include JIRA formatting.')
    parser.add_argument('-p', '--no_puffin', action='store_true', help=argparse.SUPPRESS)

    # Hidden Arguments:
    parser.add_argument('-d', '--debug', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('-P', '--profile', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('-v', '--verbose', action='store_true', help=argparse.SUPPRESS)

    # Time Range Arguments:
    parser.add_argument('-g', '--granularity', type=time_utils.Timedelta,
                        help='How granular the results should be.  See: "Timedelta Examples" below.')
    parser.add_argument('-e', '--end-date-time', dest='end', type=time_utils.Timestamp,
                        help='End time of data collection.  See: "Timestamp Examples" below.', nargs='?')
    parser.add_argument('-s', '--start-date-time', dest='start', type=time_utils.Timestamp,
                        help='Start time of data collection.  See: "Timestamp Examples" below.', nargs='?')
    parser.add_argument('-l', '--from_latest', type=time_utils.Timedelta, nargs='?',
                        default=SETTINGS['parsers']['time_range'],
                        help='A range of time from the present.  See: "Timedelta Examples" below.')

    ##################
    # Mutex Arguments:
    ##################
    # Array Identity Arguments:
    array_ident = parser.add_mutually_exclusive_group()
    # TODO: PT-1152 - Add Support for Array ID and Serial Number.
    # array_ident.add_argument('--aid', type=validation_utils.aid, help='An Array ID.', dest='aid')
    array_ident.add_argument('--fqdn', type=validation_utils.fqdn, help='An Array FQDN. i.e. array.domain.com',
                             dest='fqdn')
    array_ident.add_argument('--log_path', type=validation_utils.fuse_log_path, help='A path to array logs.',
                             dest='log_path')

    # Output Format:
    out_format = parser.add_mutually_exclusive_group()
    out_format.add_argument('--csv', action='store_const', const='csv', help='Output in CSV format.', dest='table_type')
    out_format.add_argument('--html', action='store_const', const='html', help='Output in HTML format.', dest='table_type')
    out_format.add_argument('--json', action='store_const', const='json', help='Output in JSON format.', dest='table_type')

    ##################
    # Sub-Parsers:
    ##################

    # subparsers = parser.add_subparsers()

    # JIRA Subparser:
    # TODO: Add support for direct JIRA updates
    # jira_subparser = subparsers.add_parser('jira', help='Interactions with JIRA.')
    # jira_subparser.add_argument('-n', '--no_format', help='Don\'t include JIRA formatting.',
    #                            action='store_true')
    # jira_subparser.add_argument('-j', '--jira', help='JIRAs to update with this output.',
    #                            type=_jira, nargs='+')
    return parser
