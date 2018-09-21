"""Contains common utility functions related to JIRA."""

from photon.lib import custom_errors

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import List
except ImportError:
    pass


def wrap_in_jira(lines, title=None, format_type='noformat'):
    # type: (List[str], str, str) -> List[str]
    """Wrap one or more lines of text in JIRA formatting.

    Arguments:
        lines (list/set/tuple): Strings to include in the JIRA formatting.
        title (str): The title to include in the JIRA wrapping.
        format_type (str): The JIRA tag to apply.
            # Choices: noformat, code, quote, color, panel.

    Returns:
        lines_list (list): The same lines with a JIRA header and footer.
    """
    jira_formats = (
        'code',
        'color',
        'noformat',
        'panel',
        'quote'
    )
    if not lines:
        raise custom_errors.FormatError('One or more lines is required.')
    # Split on ':' because of color usage.  Example 'color:red'
    elif format_type.split(':')[0] not in jira_formats:
        raise custom_errors.FormatError('Unknown jira format: "{}" requested.'.format(format_type))
    if 'color' in format_type:
        header = '{{ {} }}'.format(format_type)
        footer = '{{ {} }}'.format(format_type.split(':')[0])
    else:
        header = '{{ {}:title={} }}'.format(format_type, title)
        footer = '{{ {} }}'.format(format_type)
        if not title:
            header = footer
    lines_list = list(lines)
    lines_list.insert(0, header)
    lines_list.append(footer)
    return lines_list
