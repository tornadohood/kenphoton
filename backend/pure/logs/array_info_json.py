"""Contains parser definitions on how to extract data from the array_info_json.log."""

import logging
import ujson

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

from photon.lib import parser_utils
from photon.lib import time_utils

LOGGER = logging.getLogger(__name__)


class ArrayInfoFormData(parser_utils.FormData):
    """Forms used by the ArrayInfoParser."""
    array_info = parser_utils.IntervalForm(
        text_to_match=None,
        start_text=r'^{$',
        end_text=r'^}$',
        as_regex=True
    )


class ArrayInfoData(parser_utils.LogData):
    """Container for array_info data based on parser_utils.LogData."""

    def __init__(self, needed_forms):
        # type: (List[Any]) -> None
        """Create an object to track needed forms."""
        array_info_forms = ArrayInfoFormData()
        super(ArrayInfoData, self).__init__({form: array_info_forms[form] for form in needed_forms})
        LOGGER.debug('ArrayInfoData initialized with needed_forms: {}'.format(needed_forms))


class ArrayInfoParser(parser_utils.ParallelLogParser):
    """Defines all array_info data parsing functions."""
    forms = ArrayInfoFormData()
    fields = {
        'array_id': ArrayInfoData(['array_info']),
        'array_info': ArrayInfoData(['array_info']),
        'array_name': ArrayInfoData(['array_info']),
        'chassis_serial': ArrayInfoData(['array_info']),
        'controller_name': ArrayInfoData(['array_info']),
        'controller_serial': ArrayInfoData(['array_info']),
        'domain_name': ArrayInfoData(['array_info']),
        'purity_version': ArrayInfoData(['array_info']),
        }

    def _pull_from_array_info(self, key):
        # type: (str) -> List[Tuple[Any, Any]]
        """Pull the key from each timestamp from array_info."""
        results = []
        for timestamp, json_blob in self.get_field('array_info'):
            results.append((timestamp, json_blob.get(key)))
        return sorted(results)

    def get_array_id(self):
        # type: () -> List[Tuple[Any, str]]
        """Get the Array ID."""
        array_id = []
        # ArrayID is composed of: 'net_id-fc_id-iscsi_id'.
        fc_ids = self._pull_from_array_info('fc_array_id')
        iscsi_ids = self._pull_from_array_info('iscsi_array_id')
        net_ids = self._pull_from_array_info('net_array_id')
        for index, fc_data in enumerate(fc_ids):
            timestamp = fc_data[0]
            fc_id = fc_data[1]
            net_id = net_ids[index][1]
            iscsi_id = iscsi_ids[index][1]
            aid = '-'.join([str(net_id), str(fc_id), str(iscsi_id)])
            array_id.append((timestamp, aid))
        return array_id

    def get_array_info(self):
        # type: () -> List[Tuple[Any, Any]]
        """Fetch the raw JSON data from the array_info file(s)."""
        array_info = []
        for lines in self.get_form_lines('array_info'):
            text_blob = ' '.join([line.strip() for line in lines])
            json_blob = ujson.loads(text_blob, precise_float=True)
            # 2018_02_05-00_20_53_555000 -> 2018_02_05 00:20:53.555000
            raw_ts = json_blob['current_datetime']
            date, time = raw_ts.split('-')
            formatted_ts = ' '.join([date, time.replace('_', ':', 2).replace('_', '.', 1)])
            timestamp = time_utils.Timestamp(formatted_ts)
            array_info.append((timestamp, json_blob))
        return array_info

    def get_array_name(self):
        # type: () -> List[Tuple[Any, str]]
        """Get the Array Name."""
        array_names = []
        hostnames = self._pull_from_array_info('hostname')
        # DR-Pure3-ct0.paylocity.com
        for timestamp, hostname in hostnames:
            array_name_ct = hostname.split('.', 1)[0]
            array_name = array_name_ct.rsplit('-', 1)[0]
            array_names.append((timestamp, array_name))
        return array_names

    def get_chassis_serial(self):
        # type: () -> List[Tuple[Any, str]]
        """Get the chassis serial number."""
        return self._pull_from_array_info('chassis_sn')

    def get_controller_name(self):
        # type: () -> List[Tuple[Any, str]]
        """Get the controller name."""
        controller_name = []
        controller_number = self._pull_from_array_info('controller')
        for timestamp, ct_num in controller_number:
            controller_name.append((timestamp, 'CT{}'.format(ct_num)))
        return controller_name

    def get_controller_serial(self):
        # type: () -> List[Tuple[Any, str]]
        """Get the controller serial number."""
        return self._pull_from_array_info('controller_sn')

    def get_domain_name(self):
        # type: () -> List[Tuple[Any, str]]
        """Get the Domain name."""
        domain_names = []
        hostnames = self._pull_from_array_info('hostname')
        # DR-Pure3-ct0.paylocity.com
        for timestamp, hostname in hostnames:
            domain_name = hostname.split('.', 1)[1]
            domain_names.append((timestamp, domain_name))
        return domain_names

    def get_purity_version(self):
        # type: () -> List[Tuple[Any, str]]
        """Get the Purity version.."""
        purity_versions = []
        version_blobs = self._pull_from_array_info('purity_version')
        #   "purity_version" : {
        #       "crypto_lib_version" : "1.2",
        #       "driver_version" : "237842469",
        #       "operating_environment" : "purity",
        #       "product_version" : "4.10.5",
        #       "version" : "201707222306+e8b53a9-410d"
        #   }
        for timestamp, blob in version_blobs:
            purity_version = blob.get('product_version')
            purity_versions.append((timestamp, purity_version))
        return purity_versions
