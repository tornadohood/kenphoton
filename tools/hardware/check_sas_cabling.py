#!/usr/bin/env python
"""Check for SAS miscabling from sas_view/storage_view output."""

from __future__ import print_function

import textwrap

from photon import api
from photon.lib import debug_utils
from photon.lib import format_utils
from photon.lib import interactive_utils
from photon.lib import sasview_utils
# TODO: PT-2190 - A-Z testing with various argparse combinations.

KB = 'https://support.purestorage.com/Internal_Tools/Support_Tools/Penguin_Fuse_Support_Tools/Fuse_Tool%3A_check_sas_cabling'


@debug_utils.debug
def main():
    # type: () -> None
    """Create a SAS cabling visual within the terminal."""
    parser = interactive_utils.photon_argparse(__doc__, kb_article=KB)
    parser.add_argument('-c', '--color', action='store_true', help='highlight miscabling in red')
    args = parser.parse_args()
    flash_array = api.FlashArray(**vars(args))
    cabling = sasview_utils.SASCabling(flash_array, add_color=args.color)
    cabling.get_array_topology()
    cabling.generate_visual()
    jira_open = '\n{{noformat:title={}}}'
    jira_close = '{noformat}'
    error_table = cabling.get_error_table()
    print(jira_open.format('SAS Cabling Visual'))
    print('\n'.join(cabling.visual))
    print(jira_close)
    if error_table:
        print(jira_open.format('SAS Errors'))
        print('\n'.join(error_table))
        print(jira_close)
        msg = textwrap.dedent("""
            Cabling issues found.  DO NOT try to change the cabling of a production array.
            Doing so may cause a SEV-1.  Please contact support to get help on how to best fix the cabling issues.
        """)
        formatted_text = format_utils.text_fmt(['red', 'bold'], msg)
        print(formatted_text)


if __name__ == '__main__':
    main()
