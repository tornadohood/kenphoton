"""Pandas helpers.

                 `odNMNh:.-::::-`
                 dMMMMMMMy:-----:/::...`
                 mMMMMMMM/          -oNNs
                 -NNNNNm+             `sM-
                 +s`...                 +/
                -N                       s
                sm                       s`
                oN.```           `-+     o
                oMmdmdh+-`   .:oymMM`  .+-
               /NMMMMMMMMd+.`dMMMMMM` .h:
              +MMMMMMMMMMMMNy/+shddy  o.
             +ddmmNMMMMMMMMMMNh:` `  :h
           ` .````.-/oydNMMMMMMMmo--:+-
          --           `.+dMMMMMMMMm:
         -/               `/dMMMMMMMN-
        ./                  `omMMMMMMy
       `+                   `:sNMMMMMs:`
       +.                  oNMMMMMMMMMMmo
       y`                 yMMMMMMMMMMMMMM+
       +y`               :MMMMMMMMMMMMMMMo
        omo-             oMMMMMMMMMMMMMMN.
         -yNNho/-`       +MMMMMMMMMMMMMy.
-/osyhdmmNNNMMMMMMNmmddmmNMMMMMMMMMMMMNNNmmdhyso/-
"""

import logging
import warnings

import pandas

from pandas.tseries.frequencies import to_offset

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Set
except ImportError:
    pass

# TODO: PT-2058 - Fix the pandas warnings here.
warnings.simplefilter(action='ignore')

LOGGER = logging.getLogger(__name__)  # type: logging.Logger
# This zero's out the frequency of the data_frame.
FREQ_REPLACE = {
    'D': {'hour': 0, 'minute': 0, 'second': 0, 'microsecond': 0},  # D == Days
    'H': {'minute': 0, 'second': 0, 'microsecond': 0},  # H == Hours
    'T': {'second': 0, 'microsecond': 0},  # T == Minutes
    'S': {'microsecond': 0},  # S == Seconds
}  # type: Dict[str, Dict[str, int]]


def get_latest_values(frame, fields, both_controllers=False):
    # type: (pandas.DataFrame, List[str], bool) -> pandas.DataFrame
    """Get the value of the requested fields.

    Arguments:
        frame (pandas.DataFrame): A frame containing the requested fields.
        fields (list): One or more fields to request.
        both_controllers (bool): Get the latest from both controllers.

    Returns:
        last_row (pandas.DataFrame): A frame with a single row containing each field.
    """
    # Add placeholders for missing fields, so we return None instead of crashing.
    for field in fields:
        if field not in frame:
            LOGGER.warning('Requested field "{}" was not in the DataFrame.'.format(field))
            frame[field] = None
    if both_controllers:
        ct_results = []
        for controller in ('CT0', 'CT1'):
            ct_frame = frame[frame['controller'] == controller]
            if ct_frame.empty:
                LOGGER.warning('Controller "{}" had no values for fields "{}".'.format(controller, fields))
                # Make a placeholder DataFrame:
                placeholder = {'Timestamp': None, 'controller': [controller]}
                for field in fields:
                    placeholder[field] = None
                ct_results.append(pandas.DataFrame(placeholder))
            else:
                # Fill forward so we will have a value in the last row for each field.
                ct_frame.ffill(inplace=True)
                ct_results.append(ct_frame.tail(1))
        latest_values = pandas.concat(ct_results).reset_index(drop=True)
        # Only return the requested fields as Timestamp is no longer relevant.
        # We still need controller, as that was specifically requested here.
        latest_values = latest_values[['controller'] + fields]
    else:
        frame.ffill(inplace=True)
        latest_values = frame.tail(1)  # type: pandas.DataFrame
        latest_values.reset_index(drop=True, inplace=True)
        # Only return the requested fields as Timestamp and controller are no longer relevant.
        latest_values = latest_values[fields]
    return latest_values


def get_latest_value(frame, field, both_controllers=False):
    # type: (pandas.DataFrame, str, bool) -> Any
    """Get the value of the requested fields.

    Arguments:
        frame (pandas.DataFrame): A frame containing the requested fields.
        field (str): A single field to request.
        both_controllers (bool): Get the latest from both controllers.

    Returns:
        latest_value: The latest value for the requested field.
    """
    result = get_latest_values(frame, [field], both_controllers)
    if both_controllers:
        # Create a dictionary of per controller values -> {'CT0': 'value', 'CT1': 'value'}.
        latest_value = {}
        for controller in ('CT0', 'CT1'):
            # Get a sub-frame for each controller and get the latest value.
            latest_value[controller] = result[result['controller'] == controller][field].tolist()[-1]
    else:
        if result[field].empty:
            latest_value = None
        else:
            latest_value = result[field][0]
    return latest_value


def merge_on_timestamp(frames, ts_column='Timestamp'):
    # type: (List[pandas.DataFrame], str) -> pandas.DataFrame
    """Merge multiple DataFrames on a given column.

    Arguments:
        frames (list): One or more pandas.DataFrame objects.
        ts_column (str): The name of the timestamp column to use.

    Returns:
        merged (pandas.DataFrame): A single merged DataFrame.
    """
    # TODO: PT-2372 - Detect and test composite indexes.
    # Set a common Timestamped Index:
    for frame in frames:
        frame.set_index(ts_column, drop=True, inplace=True)
    merged = pandas.concat(frames, axis=1)
    # Set the Timestamp index back to a column and reset the index.
    merged.reset_index(inplace=True)
    return merged


def resample_frame(frame, frequency):
    # type: (pandas.DataFrame, Any) -> pandas.DataFrame
    """Re-sample a pandas DataFrame at the given frequency."""
    freq = to_offset(frequency).name  # type: str
    # Pick the frequency at which to work with the Timestamp.
    freq_choice = FREQ_REPLACE.get(freq, FREQ_REPLACE['H'])
    # Have to adjust the Timestamp to reflect the requested frequency to avoid odd values.
    frame['Timestamp'] = frame['Timestamp'].apply(lambda t: t.replace(**freq_choice))
    # Re-sample with the frequency in the array_api. Setting Timestamp column as the index.
    table_rs = frame.resample(to_offset(frequency), on='Timestamp')  # type: Any
    return table_rs


def sort_by_index_and_columns(frame, columns):
    # type: (pandas.DataFrame, List[str]) -> Any
    """Sort a pandas.DataFrame by the given columns and and then by the index."""
    # We have an inconsistent index at this point, sort by index number and then by the given column(s):
    if frame.empty:
        return frame
    for col in columns:
        if col not in frame:
            error_msg = 'Column "{}" is not in the frame.'.format(col)
            LOGGER.error(error_msg)
            raise KeyError(error_msg)
    # Create a placeholder for the index just for sorting purposes:
    columns.append('temp_index')
    frame['temp_index'] = frame.index

    # Sort the values by the requested columns + the temp columns (index).
    frame.sort_values(columns, inplace=True)

    # Clean-up: Reset the index now that it's sorted, and drop the temporary column.
    frame.reset_index(drop=True, inplace=True)
    frame.drop('temp_index', axis=1, inplace=True)
    return frame
