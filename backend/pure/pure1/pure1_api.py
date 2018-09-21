"""Contains the Pure1 Connection API for pulling values from the Pure1 Database."""

# pylint: logging-format-interpolation

import functools
import logging
import multiprocessing
import os
import time

try:
    # pylint: disable=unused-import
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Union
except ImportError:
    pass

import pandas
import requests
import ujson

from sqlalchemy import create_engine

from photon.backend.pure import DataSource
from photon.lib import config_utils
from photon.lib import custom_errors
from photon.lib import time_utils
from photon.lib import parallel_utils

logger = logging.getLogger(__name__)
FIELD_INDEX = config_utils.get_field_index()  # type: Dict[str, Any]
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(CURRENT_PATH, 'pure1_fields.json'), 'rt') as infile:
    KAIROS_FIELDS = ujson.loads(infile.read())


class Pure1Connection(DataSource):
    """Source to query Pure1 backend for available metrics."""
    array_query_body = """
        {{
           "start_absolute": {start},
           "end_absolute": {end},
           "metrics": [
                       {{
                           "tags": {{'array_id': "{array_id}"}},
                           "name": "{metricname}",
                           "aggregators": [
                               {{
                                   "name": "avg",
                                   "sampling": {{
                                       "value": 30,
                                       "unit": "seconds"
                                   }}
                               }}
                           ]
                       }}
                       ]
        }}"""  # type: str
    url = "http://kairos-support.cloud-support.purestorage.com/api/v1/datapoints/query"  # type: str

    def __init__(self, ident, timeframe, controllers=('CT0', 'CT1')):
        # type: (Any, time_utils.Timeframe, Union[Tuple[str], Tuple[str, str]]) -> None
        """
        Arguments:
            ident (array_utils.ArrayIdent): An identity for the array.
            timeframe (time_utils.Timeframe): A time range for information to gather.
            controllers (tuple): One or multiple controllers to use.
        """
        # For Kairos/Pure1, we need the array_id and orgid.  We get these from DataWH because
        # it's quick.
        self.orgid, self.array_id = get_array_meta(fqdn=ident.fqdn)
        self.timeframe = timeframe
        self.granularity = timeframe.granularity
        self.ident = ident
        super(Pure1Connection, self).__init__(ident=ident, timeframe=timeframe, controllers=controllers)

    # TODO: PT-1833 - update other is_available for sources to include fields and
    # timeframe checks if pertinent.
    @staticmethod
    def is_available(ident, fields, timeframe):
        # type: (Any, List[str], time_utils.Timedelta) -> bool
        """If an FQDN exists, we can use Kairos.

        Arguments:
            ident (array_utils.ArrayIdent): Ident of the array which we'll be querying.
            fields (list): Field names that we want to query.
            timeframe (time_utils.Timeframe): Timeframe during which we want data.

        Returns:
            is_available (bool): True or false that we meet all conditions to use Pure1.
        """
        granularity = timeframe.granularity
        # FQDN is required.
        has_fqdn = bool(ident.fqdn)
        # Will be true if any fields are available at that granularity.
        has_fields_at_granularity = any(get_fields_availability(fields, granularity).values())
        # Quick filter for granularity since our lowest is 30s
        has_granularity = bool(granularity >= time_utils.Timedelta('30s'))
        # Try and connect to kairos - if we get a connection error or time out
        # then we'll consider it false.  Timeout is for two seconds.
        try:
            kairos_avail = check_kairos()
        except (requests.ConnectionError, custom_errors.TimeoutError):
            kairos_avail = False
        msg = 'has_fqdn={}, has_fields_at_granularity={}, has_granularity={}, kairos_avail={}'
        logger.debug(msg.format(has_fqdn, has_fields_at_granularity, has_granularity, kairos_avail))
        is_available = all([has_fqdn, has_fields_at_granularity, has_granularity, kairos_avail])
        logger.info('Pure1Connection is available: {}'.format(is_available))
        return is_available

    # pylint: disable=arguments-differ
    def get_fields(self, fields, raw=False):
        # type: (List[str], bool) -> pandas.DataFrame
        """Get the field metrics for the timeframe and return it as a dataframe.
        Arguments:
            fields (list): Field names that we want to retrieve.

        Returns:
            results (pandas.DataFrame): Per field values.
                # Note: The results also include metadata:  source, timestamp.
        """
        metricnames = get_metric_queries(fields, self.granularity, self.orgid, raw=raw) # type: dict
        field_dataframes = []
        logger.info('Getting fields for {} - raw={}'.format(fields, raw))
        for field, metric_dict in metricnames.items():
            translated_field_dataframes = []
            if not metric_dict:
                continue
            for translated_field, metricname in metric_dict.items():
                # Kairos time queries aren't quite as granular as logs - i.e. we don't
                # do millisecond or microsecond.  The timeframe.start/end.value
                # includes millisecond and microsecond since epoch time - so we're
                # removing those by dividing by 100k and truncating to meet the
                # acceptance criteria.
                start = int(self.timeframe.start.value / 10**6)
                end = int(self.timeframe.end.value / 10**6)
                metric_query = self.array_query_body.format(array_id=self.array_id,
                                                            metricname=metricname,
                                                            start=start,
                                                            end=end)
                json_response = requests.post(self.url, data=metric_query).content.decode()
                output = ujson.loads(json_response)
                # Kairos results for multiple queries or single queries are equivalent in
                # performance, but more complicated to parse - due to that, we're going
                # to run one query at a time and keep our lives simple.  This means that
                # we need to pull the first query and the first result from the json - and
                # then pull the values from that. There are always at least one query and
                # one result, so this is presumably safe, and values will be an empty list
                # if there were no results.
                dataframe = pandas.DataFrame(output['queries'][0]['results'][0]['values'],
                                             columns=['Timestamp', translated_field])
                dataframe.set_index('Timestamp', inplace=True)
                dataframe['State'] = 'Seconary' if '_sec_' in translated_field else 'Primary'
                dataframe = dataframe.rename({translated_field: field}, axis='columns')
                dataframe.reset_index(inplace=True)
                # We have to have rate limiting in place -> No more than 300 requests per minute
                time.sleep(0.5)
                translated_field_dataframes.append(dataframe)
            if not translated_field_dataframes:
                logger.info('No results for {}'.format(field))
            else:
                field_dataframes.append(pandas.concat(translated_field_dataframes))
        # We want to merge the dataframes on the timestamp because they all have duplication but we want
        # to consolidate all the columns into a single dataframe.
        result = functools.reduce(lambda first, second: pandas.merge(first, second), field_dataframes)
        result['Timestamp'] = result.Timestamp.apply(lambda x: time_utils.Timestamp(x / 1000))
        logger.debug('Result: {}'.format(result))
        return result

    def get_source_order(self, fields):
        # type: (List[str]) -> Dict[str, List[str]]
        """Get the source order to use."""
        # TODO: PT-1832 - add a source order!
        # Least granular as possible - the rollup is what will change here.  We can
        # always get bigger granularity, but we can't always get smaller.
        # Basically we're going to implement our rollups as our different sources
        # We have array and volume types, and then we also have rollups.
        # We'll return these as a string.
        pass


# TODO: PT-1831 - Convert this to datawh connection source.
def get_array_meta(array_id=None, fqdn=None):
    # type: (Optional[str], Optional[str]) -> Tuple[Any, Any]
    """Get array orgid and array_id from datawh.

    Arguments:
        array_id (str): Array ID that we want to pull data from.
        fqdn (str): FQDN of array that we want to pull data from.

    Returns:
        orgid (int): Organization ID pulled from all_arrays
        array_id (str): array_id that we want to pull data from.
    """
    sql_url = 'postgresql://warehouse_readonly:7GPjRgQfMC,Y6v@warehouse.dev.purestorage.com:5439/datawh'
    sql_engine = create_engine(sql_url)
    # Use array_id first if possible since it's more accurate
    if array_id:
        where_statement = "WHERE array_id = '{}'".format(array_id)
    # If fqdn supplied and not array_id, build the hostname and domain from fqdn
    # and use that to get the orgid
    elif fqdn:
        split_fqdn = fqdn.split('.')
        hostname = split_fqdn[0]
        domain = '.'.join(split_fqdn[1:])
        where_statement = "WHERE domain = '{}'\n AND hostname = '{}'".format(domain, hostname)
    else:
        raise ValueError("Must have either array_id or fqdn.")
    # We should only ever have one result since it's updated daily.
    query = """SELECT organization_id, array_id
               FROM all_arrays
               {}
               LIMIT 1;
               """.format(where_statement)
    logger.debug('Getting orgid with query: {}'.format(query))
    result_frame = pandas.read_sql_query(query, con=sql_engine)
    # Pylint complains that there is no organization ID because it can't infer
    # the results of column names.
    # pylint: disable=no-member
    orgid = result_frame.organization_id[0]
    array_id = result_frame.array_id[0]
    return orgid, array_id


def get_fields_availability(fields, granularity):
    # type: (List[str], time_utils.Timedelta) -> Dict[str, bool]
    """Get availability of requested fields based on granularity.

    Arguments:
        fields (list): Field names that will be checked.
        granularity (time_utils.Timedelta): Granularity that's needed from field.

    Returns:
        field_availability (dict): Field name as key with bool true/false value.
    """
    field_availability = {field: False for field in fields}
    for field in fields:
        field_index_field = FIELD_INDEX.get(field, {})
        has_pure1 = field_index_field.get('pure1')
        if has_pure1:
            translated_fields = FIELD_INDEX[field]['pure1']
        else:
            translated_fields = [field]
        for translated_field in translated_fields:
            translated_availability = get_field_availability(translated_field, granularity)
            field_availability[field] = translated_availability
            logger.info('field_availability for {}:{} is {}'.format(field, translated_field, translated_availability))
    logger.info('Field availability: {}'.format(field_availability))
    return field_availability


def get_field_availability(field, granularity):
    # type: (str, str) -> bool
    """Get availability of an individual field from the pure1 database."""
    logger.debug('Checking pure1 availability for fields {} at granularity {}'.format(field, granularity))
    field_is_avail = False
    td_gran = time_utils.Timedelta(granularity)
    for field_granularity in KAIROS_FIELDS:
        if td_gran < time_utils.Timedelta('{}s'.format(field_granularity)):
            logger.debug('Granularity {} was less than granularity for {}'.format(granularity, field_granularity))
            continue
        for available_field in KAIROS_FIELDS[field_granularity]['type_array']:
            if (field == available_field) or ('bm_{}'.format(field) == available_field):
                logger.debug('Found availability for field in {}'.format(field_granularity))
                field_is_avail = True
                break
    # If we don't find it in any granularity, return False.
    return field_is_avail


def get_metric_queries(fields, granularity, orgid, raw=False):
    # type: (List[str], time_utils.Timedelta, int, bool) -> Dict[str, Optional[str]]
    """Build metric names from fields, granularity and orgid.

    Arguments:
        fields (list): Field names that will be checked.
        granularity (time_utils.Timedelta): Granularity that's needed from field.
        orgid (int): Organization ID pulled from datawh all_arrays table.

    Returns:
        metric_dict (dict): field name for key with string value of metric name.
    """
    nice_names = {'30': 'rollup_PT30S',
                  '180': 'rollup_PT3M',
                  '86400': 'rollup_P1D'}
    metric_dict = {} # type: dict
    for field in fields:
        logger.debug('Getting metric queries for field: {}'.format(field))
        metric_dict[field] = {}
        if raw:
            translated_fields = fields
        else:
            translated_fields = FIELD_INDEX[field]['pure1']
        for translated_field in translated_fields:

            if raw:
                translated_avail = get_field_availability(translated_field, granularity)
                if not translated_avail:
                    continue
            for field_granularity in KAIROS_FIELDS:
                delta_field_granularity = time_utils.Timedelta('{}s'.format(field_granularity))
                if granularity < delta_field_granularity:
                    msg = 'Requested granularity is too small for kairos fields with granularity of {}'
                    logger.debug(msg.format(delta_field_granularity))
                    continue
                for available_field in KAIROS_FIELDS[field_granularity]['type_array']:
                    if translated_field.strip() == available_field.strip():
                        metric_name = 'orgid_{}|type_array|{}|{}'.format(orgid,
                                                                         nice_names.get(field_granularity),
                                                                         translated_field)
                        metric_dict[field][translated_field] = metric_name
                    elif 'bm_{}'.format(translated_field).strip() == available_field.strip():
                        metric_name = 'orgid_{}|type_array|{}|bm_{}'.format(orgid,
                                                                            nice_names.get(field_granularity),
                                                                            translated_field)
                        metric_dict[field][translated_field] = metric_name
    logger.debug('Metric queries: {}'.format(metric_dict))
    return metric_dict


def check_kairos():
    # type: (...) -> bool
    """Check if kairos-support endpoint is available."""
    with parallel_utils.ProcessPool(processes=1) as pool:
        # Health status looks like this if it's good:
        # b'["JVM-Thread-Deadlock: OK","Datastore-Query: OK"]'
        # status_response = requests.get('http://kairos-support/api/v1/health/status').content.decode()
        async_result = pool.pool.apply_async(
            requests.get,
            ['http://kairos-support.cloud-support.purestorage.com/api/v1/health/status'])
        try:
            response = async_result.get(timeout=2)
        except multiprocessing.TimeoutError:
            # If we have a problem, fake a response object so we still have a byte
            # attribute for content.decode()
            response = type('obj', (object,), {'content': b''})
            logger.debug('We timed out attempting to connect to pure1.')
    # If we have 2 OK's, we're good to test for pure1_api stuff.
    # Pylint is going to complain because it might be a "faked" response object.
    # pylint: disable=no-member
    avail = bool(response.content.decode().count('OK') == 2)
    return avail
