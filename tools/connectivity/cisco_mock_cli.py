#!/usr/bin/python
""" A simple mock CLI

The simple mock CLI will parse a non-compressed cisco log file
and let you view the results."""

from __future__ import print_function

import argparse
import os

from collections import defaultdict

# So we're python2/3 compatible, we'll make sure we're using the input that works.
# pylint: disable=redefined-builtin, invalid-name
try:
    input = raw_input
except NameError:
    pass

try:
    # pylint: disable=unused-import
    from typing import BinaryIO
    from typing import Dict
    from typing import DefaultDict
    from typing import List
    from typing import Optional
except ImportError:
    pass
# TODO: PT-2190 - A-Z testing with various argparse combinations.


def cisco_mock_cli(logfile):
    # type: (str) -> None
    """Open the log file and loop command input until user exits."""
    with open(logfile, 'rt') as raw_log:
        command_dict = get_command_dict(raw_log)
        exit_cmd = False
        name = command_dict.get('show switchname', ['Unknown'])[0]
        while not exit_cmd:
            # Get user input
            user_input = input("\n{}$ ".format(name))
            # Exit on these commands:
            if user_input in ['/q', '/quit']:
                print('Exiting')
                exit_cmd = True
                break
            # If someone didn't read the intro and types one of these, it'll give the big
            # help text we've got...
            if user_input in ['/h', '/help']:
                print("Available Commands:")
                print("{:15}{}".format("/help", "Displays this help screen."))
                print("{:15}{}".format("/quit", "Quits the cisco mock CLI."))
                print("{:15}{}".format("/list_commands", "Lists the available commands parsed from the current log."))
                continue
            # if we type list_commands, either filter, or print them all.
            elif "/list_commands" in user_input.lower():
                search_string = ' '.join(user_input.split()[1:])
                if search_string:
                    filtered_commands = filter_commands(command_dict, search_string)
                    print("\nHere are commands with '{}' in them:\n".format(search_string))
                    for command in sorted(filtered_commands):
                        print(command)
                else:
                    print("\nNo search string provided - showing all commands:\n")
                    for key in sorted(command_dict.keys()):
                        print(key)
                        continue
            # If it's not one of the above, we're trying to get a command.
            else:
                command_results = command_dict.get(user_input)
                # If we don't have any command key for that user input, filter and print out ones
                # that have that in it, or tell them we don't have any commands with that.
                if not command_results:
                    filtered_commands = filter_commands(command_dict, user_input)
                    print('\nERROR: Could not find that command. Type "help" for help.')
                    if filtered_commands:
                        print("\nDid you mean...\n")
                        for command in sorted(filtered_commands):
                            print(command)
                # If we have the command results, print them.
                else:
                    for line in command_results:
                        print(line)


def filter_commands(command_dict, search_string):
    # type: (Dict[str, List[str]], str) -> List[str]
    """Filter command_Dict based on search_string."""
    filtered_commands = set()
    for command in sorted(list(command_dict.keys())):
        if search_string in command:
            filtered_commands.add(command)
    return sorted(filtered_commands)


def get_command_dict(raw_log):
    # type: (BinaryIO) -> Dict[str, List[str]]
    """Get a dict of commands from the logfileself.
    Arguments:
        raw_log (FileObj): Cisco logfile to mock CLI fromself.
    Returns:
        command_dict (dict): Cisco commands for keys with list of command result lines for values.
    """
    command_dict = defaultdict(list) # type: DefaultDict[str, List]
    command = None
    for line in raw_log:
        if "`show" in line:
            # Some lines may have output from a previous line that doesn't have a newline
            # character, so we split on our command start/end backtick, and take the second
            # element - that should be our command.
            command = line.strip().split('`')[1]
            continue
        if command:
            command_dict[command].append(line.rstrip())
    return dict(command_dict)


def check_file(filepath):
    # type: (str) -> bool
    """Check that the filepath exists, and is valid type."""
    # Check that the file exists
    exists = os.path.exists(filepath)
    # Check that the file is a unicode file by decoding the first line.
    raw_log = open(filepath, 'rt')
    line = raw_log.readline()
    readable = isinstance(line, str)
    # Return all() of both conditions.
    return all([exists, readable])


def main():
    # type: () -> None
    """Get filename and run CLI parser."""
    parser = argparse.ArgumentParser(description='Read uncompressed tech-support-show and convert it to a CLI.')
    parser.add_argument('filepath', help='File path of the uncompressed text Cisco log file.')
    args = parser.parse_args()
    message = """
                 +==========================================================================================================+
                 | Welcome to the Cisco mock CLI!  If you're completely unfamiliar with the available commands, please type |
                 | list_commands for a list of all possible commands.  If you'd like to filter commands, type /list_commands|
                 | with the search string immediately after, e.g.:                                                          |
                 |                                                                                                          |
                 | This will show you a list of all commands:                                                               |
                 | list_commands                                                                                            |
                 |                                                                                                          |
                 | This would show you all commands that have the string "show zoneset active" in them:                     |
                 | list_commands show zoneset active                                                                        |
                 |                                                                                                          |
                 | The CLI commands are based on the logfile listed below:                                                  |
                 ===========================================================================================================+
                 LOGFILE = {}
""".format(args.filepath)
    print(message)
    if check_file(args.filepath):
        cisco_mock_cli(args.filepath)
    else:
        print("Please check that the filepath you specified is a valid non-compressed text log file.")


if __name__ == '__main__':
    main()
