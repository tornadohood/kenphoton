"""Wrapper for cisco parsers that converts to report API friendly formats."""

import logging
import pandas

from photon.backend.cisco import tech_support_show
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)


# TODO: PT-2311 - Make this friendly for report API, i.e. consistent return types across parsers for the few
# types that the report API supports.
class CiscoSwitch(object):
    """Main cisco switch object for parsing multiple logfiles."""

    def __init__(self, logfiles):
        """Instantiate SupportShowParsers for each logfile and get values from them."""
        self.parsers = []
        # TODO: PT-2295 - add logic for is_available and different log types.
        forms = tech_support_show.SupportShowParserFormData()
        for logfile in logfiles:
            LOGGER.debug('appending parser for {}'.format(logfile))
            self.parsers.append(tech_support_show.SupportShowParser(logfile))

    def get_fields(self, fields):
        """Get requested fields and return a dataframe with results.
        Arguments:
            fields (list): Strings representing the field requested.
        Returns:
            all_results_df (pandas.DataFrame): Report API friendly dataframe with requested field information.
        """
        dfs = []
        for support_show_parser in self.parsers:
            dfs.append(get_fields_dataframe(support_show_parser, fields))
        all_results_df = pandas.concat(dfs)
        all_results_df.sort_index(inplace=True)
        return all_results_df


def get_fields_dataframe(parser, fields):
    """Create a dataframe result from the parser fields requested.
    Arguments:
        parser (tech_support_show.SupportShowParser): Instantiated parser instance.
        fields (list): Fields that are requested for the dataframe result.
    Returns
        dataframe (pandas.DataFrame): Results of the requested fields in a datafarme.
    """
    timestamp, vals_dict = parser.get_fields(fields)
    vals_dict['Timestamp'] = timestamp
    dataframe = pandas.DataFrame([vals_dict])
    dataframe['Timestamp'] = time_utils.Timestamp(dataframe['Timestamp'])
    dataframe.set_index('Timestamp', inplace=True)
    return dataframe
