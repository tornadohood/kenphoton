"""Helper library for handling version comparisons."""


from packaging import version

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import List
except ImportError:
    pass


def compare_versions(current_version, fixed_in_version):
    # type: (str, str) -> bool
    """Determine if the current version is greater than or equal to a fixed in version.

    Note: This supports version naming which uses letters instead of numbers.  e.g. '4.10.bravo'

    Arguments:
        current_version (str): The current version to check against.  i.e. '4.8.10'
        fixed_in_version (str): The version where the issue is addressed.  i.e. '4.10.7'

    Returns:
        Bool: Whether the version is greater than or equal to the fixed in version.
    """
    cur_split = current_version.split('.')
    fixed_split = fixed_in_version.split('.')
    # For situations where we have text in the release; just check if we are greater than the major and minor.
    # Otherwise rely upon the normal comparisons.
    # 4.10.bravo > 4.9.10
    if ''.join([cur_split[0], cur_split[1]]).isdigit() and ''.join([fixed_split[0], fixed_split[1]]).isdigit():
        if int(cur_split[0]) >= int(fixed_split[0]) and int(cur_split[1]) > int(fixed_split[1]):
            return True
    return version.parse(current_version) >= version.parse(fixed_in_version)


def compare_multiple_versions(current_version, fixed_in_versions):
    # type: (str, List[str]) -> bool
    """Determine if the current version is greater than or equal to any of the fixed in versions.

    Note: This supports version naming which uses letters instead of numbers.  e.g. '4.10.bravo'

    Arguments:
        current_version (str): The current version to check against.  i.e. '4.8.10'
        fixed_in_versions (list/set/tuple): The version where the issue is addressed.  i.e. ['4.10.7']

    Returns:
        Bool: Whether the version is greater than or equal to the fixed in version(s).
    """
    if not isinstance(fixed_in_versions, (list, set, tuple)):
        raise TypeError('Argument "fixed_in_versions" must be a list, set, or tuple.')
    # If any of the fixed in versions have the same major.minor then just compare that version:
    for fixed_in in fixed_in_versions:
        # Remove revision/private names and only include major.minor:
        fix_major_minor = fixed_in.rsplit('.', 1)[0]
        cur_major_minor = current_version.rsplit('.', 1)[0]
        if fix_major_minor == cur_major_minor:
            return compare_versions(current_version, fixed_in)
    return any(compare_versions(current_version, fixed_in) for fixed_in in fixed_in_versions)
