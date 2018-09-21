"""Common utility functions related to doing math."""

from __future__ import division

import logging
import numpy

try:
    # Intentional override of build-in for Python2/3 compatibility
    # pylint: disable=redefined-builtin
    from itertools import izip as zip
except ImportError:
    pass

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import List
    from typing import Union
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


def rmse(actual, predicted):
    # type: (List[int], List[int]) -> float
    """Calculate the Root Mean Squared Error for a given prediction.

    Arguments:
        actual (list/set/tuple): One or more int/float.
        predicted (list/set/tuple): One or more int/float.  Must be the same length as actual.

    Returns:
        A list of the difference between actual values and predicted values.
    """
    # Calculate the variance/error of each item in actual versus each item in predicted
    error = [(i[0] - i[1]) ** 2 for i in zip(actual, predicted)]
    # Provide the deviation of the average error
    return numpy.sqrt(numpy.mean(error))


def safe_divide(numerator, denominator, precision=2):
    # type: (int, int, int) -> float
    """Safely divide two numbers.

    Arguments:
        numerator (int/float): The value to be divided.
        denominator (int/float): The value doing the dividing.
        precision (int): The decimal precision to round up to.

    Returns:
        result (float): The division result or 0.0.
    """
    if float(denominator) == 0.:
        return 0
    result = float(numerator) / float(denominator)
    return round(result, precision)
