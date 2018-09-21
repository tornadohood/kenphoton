"""Contains common utility functions related to CloudAssist."""

import ast
import logging
import os
import re
import shlex
import subprocess
import sys

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
except ImportError:
    pass

from photon.lib import custom_errors

LOGGER = logging.getLogger(__name__)


def _get_full_phonebook():
    # type: (...) -> List[str]
    """Get the full phonebook from Iris."""
    phonebook = run_ssh_cmd('/opt/iris/bin/exec_phonebook.py array list').splitlines()  # type: List[str]
    LOGGER.debug('Got {} entries from the Phonebook.'.format(len(phonebook)))
    return phonebook


# Intentional use of eval for a workaround if ast.literal_eval breaks.
# pylint: disable=eval-used
def get_ca_diagnostics(array_id):
    # type: (str) -> Dict[str, Any]
    """Collect the ca diagnostics from CloudAssist.

    This currently relies on SSH to irisdev to run '/opt/iris/bin/iris_diagnostics.py'
    """
    LOGGER.info('Getting Diagnostics from CloudAssist.')
    query_command = '/opt/iris/bin/iris_diagnostics.py query {} {}'  # type: str
    ca_diagnostics = {}  # type: Dict[str, Any]
    for ct_num, ctlr in enumerate(('ct0', 'ct1')):
        LOGGER.info('Getting CA diagnostics data for "{}".'.format(ctlr))
        ctlr_query_command = query_command.format(array_id, ct_num)  # type: str
        LOGGER.debug('Issuing query: {}.'.format(ctlr_query_command))
        diagnostics_str = run_ssh_cmd(ctlr_query_command).strip()  # type: str
        if not diagnostics_str:
            continue
        try:
            ca_diagnostics[ctlr] = ast.literal_eval(diagnostics_str)
        except (SyntaxError, ValueError):  # Caused by an empty string: ''
            entry = dict(eval(diagnostics_str))  # type: Dict[str, Any]
            if not isinstance(entry, dict):
                raise ValueError('CA diagnostics data was malformed.')
            ca_diagnostics[ctlr] = entry
        LOGGER.debug('Got a response from CA.')
    return ca_diagnostics


def get_phonebook(array_id=None, phonebook=None):
    # type: (str, List[Any]) -> List[str]
    """Get all entries from the CA phonebook.

    Arguments:
        array_id (str): A single array-id.
        phonebook (list): The phonebook from Iris.
            If not given, it will be requested from Iris.

    Returns:
        entries (list): One or more matches for the given array_id/fqdn.

    This currently relies on SSH to irisdev to run "/opt/iris/bin/exec_phonebook.py"
    """
    LOGGER.info('Getting Phonebook Data from CloudAssist.')
    entries = []  # type: List[str]
    if not phonebook:
        phonebook = _get_full_phonebook()
    for line in phonebook:
        if hasattr(line, 'decode'):
            line = line.decode()
        try:
            entry = ast.literal_eval(line)
        except (SyntaxError, ValueError):  # Caused by an empty string
            # If a long type is present it will break eval:
            # i.e. 10000000000000000000L
            # So replace it with a summarized version
            line = re.sub(r'\s\d+L,', ' 1e19,', line)
            entry = eval(line)
            if not isinstance(entry, dict):
                raise
        if array_id and array_id.lower() != entry['array_id'].lower():
            continue
        entries.append(entry)
    return entries


def run_ssh_cmd(cmd, user='ca', server='irisdev.dev.purestorage.com'):
    # type: (str, str, str) -> str
    """Run a command safely through an SSH connection."""
    LOGGER.debug('Running command "{}" on remote server "{}".'.format(cmd, server))
    remote_server = '{}@{}'.format(user, server)  # type: str
    base_cmd = ['ssh', remote_server, '-o', 'ConnectTimeout=10', 'BatchMode=yes']  # type: List[str]
    remote_cmd = base_cmd + shlex.split(cmd)  # type: List[str]
    LOGGER.debug('Issuing remote command to {}: {}'.format(server, remote_cmd))
    try:
        with open(os.devnull, 'w') as stderr_pipe:
            output = subprocess.check_output(remote_cmd, stderr=stderr_pipe)  # type: str
    except subprocess.CalledProcessError as error:
        box = '=' * (len(' '.join(error.cmd)) + 16)  # type: str
        message = """

        {box}

        Error occurred attempting to ssh server: {server}
        Failed Command: {cmd}
        Return Code: {code}

        """.format(box=box, server=remote_server, cmd=error.cmd, code=error.returncode)  # type: str
        LOGGER.error(message)
        sys.stderr.write(message)
        error_message = 'Error occurred in SSH connection to {}'.format(remote_server)  # type: str
        LOGGER.error(error_message)
        raise custom_errors.SSHError(error_message)
    LOGGER.debug('Response from {}: "{}".'.format(server, output))
    return output
