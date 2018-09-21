"""Contains common utility functions related to building Reports."""

from __future__ import print_function
from __future__ import unicode_literals

import logging
import texttable

from collections import OrderedDict
from six import string_types

# pylint: disable=unused-import
try:
    from typing import List
    from typing import Optional
except ImportError:
    pass

from photon.lib import custom_errors

LOGGER = logging.getLogger(__name__)


def draw_basic_table(table_lines, alignment=None, header=True, vertical_sep=True):
    # type: (List[str], Optional[str], bool, bool) -> List[str]
    """Draw a basic text table.

    Arguments:
        table_lines (list/set/tuple): One or more strings to include within the table.
            # The First line is assumed to be a header if 'header' is True.
        alignment (list/set/tuple): Alignment to apply to the table lines.
            # Each column can have a distinct alignment, or a string may be given to apply to all.
            # Options: left, right, center (or l, r, c).
        header (bool): The first line in table_lines is a header.
        vertical_sep (bool): Vertically separate each row.

    Returns:
        table (list/set/tuple): The drawn/rendered table structure; a list of strings.
    """
    if not table_lines:
        raise custom_errors.FormatError('One or more lines is required.')
    table = texttable.Texttable(max_width=0)
    if not vertical_sep:
        table.set_deco(texttable.Texttable.BORDER | texttable.Texttable.HEADER | texttable.Texttable.VLINES)
    if alignment:
        if isinstance(alignment, string_types):
            alignment = [alignment]
        if len(alignment) == 1:
            alignment *= len(table_lines[0])
        table.set_cols_align(alignment)
    table.add_rows(table_lines, header=header)
    return table.draw()


def wrap_in_box(lines, box_char='=', description=None):
    # type: (List[str], str, Optional[str]) -> List[str]
    """Wrap report lines in a dynamically sized box.

    Arguments:
        lines (list/set/tuple): Strings to include in the box.
        box_char (str): The character to use for drawing the table lines.
        description (str): A description to include in the header of the table.

    Returns:
        box_lines (list): The drawn/rendered box lines.
    """
    if not lines:
        raise custom_errors.FormatError('One or more lines is required.')
    if description:
        lines.insert(0, description)
    line_lens = [len(line.rstrip()) for line in lines]
    box_line = box_char * max(line_lens)
    box_lines = [box_line]
    box_lines.extend(lines)
    box_lines.append(box_line)
    return box_lines


def get_table_info(list_of_lists):
    # type: (List[List[Any]]) -> OrderedDict[int, int]
    """Create table_info for making separators.
    Arguments:
        list_of_lists (list): Any list of lists that can be stringified.

    Returns:
        table_info (OrderedDict): Index and max column length for each item
                                  in my list of lists - i.e. list[:][0] has a
                                  max length of 5 characters for all lists.
    """
    table_info = OrderedDict()
    for list_item in list_of_lists:
        for index, col in enumerate(list_item):
            max_len = table_info.get(index, 0)
            # Make sure whatever it is, we try to stringify it
            # for length testing.  Formats below will take care
            # of making it a string in the end.
            str_col = str(col)
            if len(str_col) > max_len:
                table_info[index] = len(str_col)
    return table_info


def create_separator(table_info, header=False):
    # type: (OrderedDict[int, int]) -> str
    """Create header and normal separators for list of lists.
    Arguments:
        table_info (OrderedDict): Index and max column length for each item
                                  in my list of lists - i.e. list[:][0] has a
                                  max length of 5 characters for all lists.
        header (bool): Whether or not the separator should be a header separatator
    Returns:
        header_sep (string): vertical separators using = for header, - for normal
        """
    sep_char = "=" if header else "-"
    separator = []
    for index, column_width in table_info.items():
        column_width = table_info.get(index)
        # For each item, add a +==== or +----
        # | Hello |  <= Width of 5, add 2 for spaces
        # +=======   <= We only add up to the next delimiter because
        #               the next column item will add the trailing +.
        separator.append('+' + sep_char * (column_width + 2))
    # Add a trailing + to our separators to close out the last space.
    # | Hello |
    # +=======+  <= Adds this extra + at the end that wasn't taken care of yet.
    separator.append('+')
    return separator


def create_table(list_of_lists, alignment=None, header=True, vertical_sep=False):
    # type: (List[list[Any]]) -> List[str]
    """Print a table based on a list of lists.
    Arguments:
        list_of_lists (list): Each item in this list is a row and should be a list
                              of values for columns
        header (bool): If true, first line will be treated as a header.
        vertical_sep (bool): If true, vertical separators will be added between rows.

    Returns:
        table_lines (list): Strings for each line in the table.
    """
    table_lines = []
    first_row = []

    # Go through and get our widths from the list of lists
    table_info = get_table_info(list_of_lists)

    # Create separators based on the widths we got.
    header_sep = create_separator(table_info, header=True)
    normal_sep = create_separator(table_info)

    # Create our first row special since it might be a header - this is done
    # whether or not we have a header, because it *might* be a header, and we have
    # to do this first if it is.
    # If it is, we'll need it before the rest of the list.  If it is not a header
    # we won't wrap it up pretty, we'll just wrap the top like a normal line with
    # or without a vertical separator, depending on your selection.
    for index, col_value in enumerate(list_of_lists[0]):
        column_width = table_info.get(index)
        formt_str = '| {{!s:{}}} '.format(column_width)
        first_row.append(formt_str.format(str(col_value)))
    first_row.append('|')

    # If it's a header, wrap it up, otherwise give it raw.
    if header:
        # +======+====+====+=======+======+
        # | Here | Is | my | first | line |
        # +======+====+====+=======+======+
        table_lines.append(''.join(header_sep))
        table_lines.append(''.join(first_row))
        table_lines.append(''.join(header_sep))
    elif vertical_sep:
        # +------+----+----+-------+------+
        # | Here | Is | my | first | line |
        # +------+----+----+-------+------+
        table_lines.append(''.join(normal_sep))
        table_lines.append(''.join(first_row))
        table_lines.append(''.join(normal_sep))
    else:
        # +------+----+----+-------+------+
        # | Here | Is | my | first | line |
        table_lines.append(''.join(normal_sep))
        table_lines.append(''.join(first_row))

    # Go through the rest and add them.
    for line in list_of_lists[1:]:
        row = []
        for index, col_value in enumerate(line):
            column_width = table_info.get(index)
            formt_str = '| {{!s:{}}} '.format(column_width)
            row.append(formt_str.format(str(col_value)))
        row.append('|')
        table_lines.append(''.join(row))
        # If we want vertical separators, add them after every row.
        if vertical_sep:
            table_lines.append(''.join(normal_sep))

    # If we aren't vertically separating, we won't have appended a separator
    # row, so add it if not vertical_sepa
    if not vertical_sep:
        table_lines.append(''.join(normal_sep))

    return table_lines


def build_table_and_print(list_of_lists, alignment=None, header=True, vertical_sep=False):
    # type: (List[list[Any]]) -> None
    """Print's a table from a list of lists. """
    table = create_table(list_of_lists, header=header, vertical_sep=vertical_sep)
    for line in table:
        print(line)
