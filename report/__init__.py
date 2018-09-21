"""Defaults for the report package."""

import pandas

# Disable the column width limit of 50 characters by setting this effectively to infinity.
# If this is not set, then the column truncates at 50 characters and we cannot see the full output.
pandas.set_option('display.max_colwidth', -1)
