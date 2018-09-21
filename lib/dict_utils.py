"""Common utility functions related to mutating or creating modified copies."""

from __future__ import unicode_literals

import copy
import functools
import itertools
import operator

# Python 2/3 compatibility change, intentionally overwriting range
# pylint: disable=redefined-builtin
from builtins import range
from collections import defaultdict
from six import iteritems

from photon.lib import format_utils


class DictTree(dict):
    """A Dictionary with keys containing dictionaries.

    Contains utilities to:
        - Map the keys for all the branch paths.
        - Get values multiple layers deep.
        - Set values multiple layers deep.
    """

    def __init__(self, *args, **kwargs):
        dict.__doc__.replace('dict(', 'DictTree(').replace('dictionary', 'DictTree')
        super(DictTree, self).__init__(*args, **kwargs)

    @property
    def branches(self):
        """Map the structure of this DictTree."""
        bob = tuple(sorted([tuple(branch_keys) for branch_keys in self._map_branches_helper()]))
        return bob

    def _map_branches_helper(self, branch=None, branches=None, branch_keys=None):
        """Helper method to recursively build branch_keys to find all branches."""
        if branch is None:
            branch = self
        branches = branches or []
        branch_keys = branch_keys or []
        if isinstance(branch, dict) and branch != {}:
            for key, section in iteritems(branch):
                branches = self._map_branches_helper(section, branches, branch_keys + [key])
        else:
            if branch_keys:
                branches.append(branch_keys)
        return branches

    def filter_branches(self, max_depth=None, min_depth=1):
        """Find all branches of the required depths."""
        if not isinstance(min_depth, int):
            raise ValueError('min_depth must be an int')
        if max_depth is not None and not isinstance(max_depth, int):
            raise ValueError('max_depth must be an int')
        if min_depth < 1:
            raise ValueError('min_depth must be greater than 0')
        if max_depth and max_depth < 1:
            raise ValueError('max_depth must be greater than 0')
        branches = [tuple(keys[:max_depth]) for keys in self.branches if len(keys) >= min_depth]
        return tuple(sorted(set(branches)))

    def get_branch_value(self, branch_keys, suppress_keyerror=False, default_value=None):
        """Get the value of the branch from this DictTree.

        args:
        branch_keys (Sequence): Keys for each layer of the DictTree Branch
        suppress_keyerror (bool): suppress KeyError exceptions while looking up value
        default_value (...): Value to return if KeyError occurs and is suppressed
        """
        try:
            value = functools.reduce(operator.getitem, branch_keys, self)
        except KeyError:
            if suppress_keyerror is False:
                raise
            value = default_value
        return value

    def set_branch_value(self, branch_keys, value):
        """Set a value that is multiple layers deep."""
        if not isinstance(branch_keys, (list, tuple)):
            raise TypeError('branch_keys: Expected list or tuple, not {}'.format(type(branch_keys)))
        temp_dict = self
        for key in branch_keys[:-1]:
            temp_dict[key] = temp_dict.get(key, {})
            temp_dict = temp_dict[key]
        temp_dict[branch_keys[-1]] = value

    def expand_tree(self, branches, default_value):
        """Expand this tree to have all provided branch in branches.

        If a branch doesn't already exist, it will be given a copy of the default value.
        """
        current_branches = set(self.branches)
        new_branches = (current_branches | set(branches)) - current_branches
        for branch_keys in new_branches:
            self.set_branch_value(branch_keys, copy.deepcopy(default_value))

    def equalize_tree(self, default_value, max_depth=None, min_depth=1):
        """Make all layers of branches have all the keys of that layer from across all branches."""
        branches = self.filter_branches(max_depth=max_depth, min_depth=min_depth)
        max_branch_len = max([len(branch_keys) for branch_keys in branches])
        layer_keys = []
        for layer in range(0, max_branch_len):
            layer_keys.append(set([branch[layer] for branch in branches if len(branch) > layer]))
        new_tree = tuple(itertools.product(*layer_keys))
        self.expand_tree(new_tree, default_value)

    def update_tree(self, new_dict):
        """Update the values of this tree from another dict.

        Similar to ".update" for a dictionary, but recursively.
        """
        new_dict = DictTree(new_dict)
        for branch_keys in new_dict.branches:
            self.set_branch_value(branch_keys, new_dict.get_branch_value(branch_keys))


class ValueOrderDict(object):
    """ defaultdict(list) that tracks order globally across the dict.

    Will function as a normal defaultdict(list) unless you use one of
    the properties to pull out the values in relation to the index.

    """
    def __init__(self):
        self.ordered = False
        self._data = defaultdict(list)
        self._next_index = 0

    def __getitem__(self, key):
        return [val[0] for val in self._data[key]]

    def append_value_to_key(self, key, value):
        """ Append <value> to dict[key] and track it's index. """
        self._data[key].append((value, self._next_index))
        self._next_index += 1

    @property
    def tuples(self):
        """ Return a raw tuples list in the normal order the dict decides to iterate keys. """
        full_list = []
        for key, tup in iteritems(self._data):
            for val, order in tup:
                full_list.append((val, order, key))
        return full_list

    @property
    def ordered_tuples(self):
        """ Returns the tuples ordered by value."""
        return sorted(self.tuples, key=operator.itemgetter(0, 1))

    @property
    def ordered_values(self):
        """ Returns just the values in order, not tuples. """
        return [val[0] for val in self.ordered_tuples]

    @property
    def indexed_order_values(self):
        """ Returns the values in the order they were inserted into the dict. """
        return [val[0] for val in sorted(self.tuples, key=operator.itemgetter(1))]

    @property
    def index_total(self):
        """ Return the current total index count. """
        return self._next_index


def merge_number_dicts(dict_one, dict_two):
    """Merge two multilevel dictionaries with ending values that are numbers."""
    merged_dict = DictTree()
    dict_one = DictTree(dict_one)
    dict_two = DictTree(dict_two)
    merged_dict.update(dict_one)
    for branch_keys in dict_two.branches:
        merged_dict_value = merged_dict.get_branch_value(branch_keys, True, 0)
        dict_two_value = dict_two.get_branch_value(branch_keys)
        merged_dict.set_branch_value(branch_keys, merged_dict_value + dict_two_value)
    return merged_dict


def make_dict_keys_titles(orig_dict):
    """Create a new dictionary with keys renamed to be title formatted."""
    orig_type = type(orig_dict)
    return orig_type({format_utils.make_title(key): orig_dict[key] for key in orig_dict})
