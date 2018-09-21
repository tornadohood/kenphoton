#!/usr/bin/env python
"""Device Info - Mockery of the dev_info output in platform.log."""

from __future__ import print_function

import logging

from six import iteritems

from photon import api
from photon.lib import apartment_utils
from photon.lib import debug_utils
from photon.lib import drive_utils
from photon.lib import print_utils
from photon.lib import shelf_utils
from photon.lib import interactive_utils

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Union
except ImportError:
    pass


LOGGER = logging.getLogger(__name__)
# TODO: PT-2190 - A-Z testing with various argparse combinations.


class DevInfo(api.FlashArray):
    """A wrapper to add functionality needed for dev_info."""

    # All of these args are needed.
    # pylint: disable=too-many-arguments
    def __init__(self, fqdn=None, log_path=None, start=None, end=None, files=None):
        # type: (Optional[str], Optional[str], Optional[str], Optional[str], Optional[List[str]]) -> None
        """
        Arguments:
            fqdn (str): A Fully Qualified Domain Name for the array.  i.e. "array_name.domain.com"
            log_path (str): A path to find log files for this array.
            start (str/datetime/pandas.Timestamp): The start of the time frame to request.
            end (str/datetime/pandas.Timestamp): The end of the time frame to request.
                * The end must be AFTER the start.
            files (list): One or more log files (full paths).
        """
        kwargs = dict(fqdn=fqdn, log_path=log_path, start=start, end=end, files=files, from_latest='1h')
        super(DevInfo, self).__init__(**kwargs)
        self._device_map = {}  # type: Dict[str, Any]

    @property
    def device_map(self):
        # type: () -> Dict[str, Any]
        """Build a mapping of all enclosures, groups, etc. to drives.
        This relies upon the output of puredrive_list, purehw_list, and dev_info.
        """
        if self._device_map:
            return self._device_map

        print_utils.status_update('Mapping drive/group/enclosure relationships.')
        fields = ['dev_info', 'puredb_list_drives']
        drive_info = self.get_latest_values(fields)

        # Build all Drive instances.
        drives = drive_utils.build_drives(drive_info, skip_nvram=False)

        if not drives:
            error_msg = 'No drives found on the array.'
            LOGGER.exception('ValueError: {}'.format(error_msg))
            raise ValueError(error_msg)

        # Build enclosures and add drives to them.
        enclosures = shelf_utils.build_enclosures(drives)

        # Build write groups and add drives to them.
        write_groups = apartment_utils.build_write_groups(drives)

        # Build apartments and add write groups to them.
        apartments = apartment_utils.build_apartments(drives, write_groups)

        # Build data packs and add write groups to them.
        data_packs = apartment_utils.build_data_packs(drives, write_groups)

        self._device_map = {
            'apartments': apartments,
            'data_packs': data_packs,
            'drives': drives,
            'enclosures': enclosures,
            'write_groups': write_groups,
        }

        if not any([apartments, data_packs, enclosures, write_groups]):
            error_msg = 'No devices found on the array.'
            LOGGER.exception('ValueError: {}'.format(error_msg))
            raise ValueError(error_msg)

        print_utils.status_update()
        return self._device_map

    def print_report(self):
        # type: () -> None
        """Print out the dev_info report."""
        for apt_name, apartment in iteritems(self.device_map['apartments']):
            print('Apartment <{}>, {} device(s)'.format(apt_name, apartment.component_count()))
            # Sort WriteGroups by type, i.e. NVRAM before SSD.
            wgrps = sorted(iteritems(apartment.components), key=lambda wgrp: wgrp[1].component_type())
            for wgroup_name, wgroup in wgrps:
                print('\tWrite group <{}>, {} device(s), type {}'.format(wgroup_name,
                                                                         wgroup.component_count(),
                                                                         wgroup.component_type()))

                for dev_name, device in sorted(iteritems(wgroup.components), key=drive_utils.sort_drives):
                    print('\t\tDevice {name}\t\t\t{handle}\t\t\t{dev_id}'.format(name=dev_name,
                                                                                 handle=device.handle,
                                                                                 dev_id=device.device_id))


@debug_utils.debug
def main():
    # type: () -> None
    """Parse user arguments, fix dev_info issues, and then print results."""
    parser = interactive_utils.photon_argparse(description=__doc__)
    args = parser.parse_args()
    array = DevInfo(fqdn=args.fqdn, log_path=args.log_path, start=args.start, end=args.end, files=args.files)
    array.print_report()


if __name__ == '__main__':
    main()
