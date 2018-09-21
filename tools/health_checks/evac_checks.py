#!/usr/bin/env python

"""Health checks to perform prior to doing an "evac" of one or more devices.

There are several known issues and caveats to be aware of.
Here are a few of the more common ones:

Controllers:
- FA-300 and FA-400 do not natively support Evacuation.
- //X controller evacuation is not supported until 4.10.6.

Data Packs:
- 6G shelves do not Support Data Packs.
- Therefore 12G and/or Chassis shelf is required.

Purity:
- 4.7.3 is required for Shelf evacuation.
- 4.10.6 is required for Data Pack evacuation.
"""

from __future__ import print_function

import logging
import pandas
import ujson

from photon.lib import debug_utils
from photon.lib import format_utils
from photon.lib import interactive_utils
from photon.lib import print_utils
from photon.lib import report_utils
from photon.lib import validation_utils
from photon.tools.health_checks import evac_health_checks

LOGGER = logging.getLogger(__name__)

# TODO: PT-2190 - A-Z testing with various argparse combinations.
# TODO: PT-2036 - Replace this with the Report API.


# pylint: disable=too-many-locals
def _print_reports(evac_api, table_type, details, skip_checks):
    """Print the output report.  This will be replaced by the Report API."""

    # Generate Reports:
    # This order is important, as estimations impacts the status of drives printed in drive_details.
    array_summary = evac_api.build_array_summary()

    if not skip_checks:
        # Check for known issues and caveats:
        exam = evac_health_checks.EvacHealthChecks()
        exam.run_tests(evac_api)
    print_utils.status_update()

    # Estimate space based upon compatible devices being evacuated:
    if evac_api.devices_to_evac:
        estimations = evac_api.estimate_evac_space()
    else:
        estimations = {}

    # Generate the drive details / enclosure mappings:
    drive_details = evac_api.build_drive_details() if details else None

    if table_type == 'json':
        report = {
            'array': array_summary,
            'drive_details': drive_details,
            'estimations': estimations,
        }
        if not skip_checks:
            report['known_issues'] = {check.name: check.passed for check in exam.checks.values()}
        print(ujson.dumps(report))
    elif table_type == 'csv':
        print(pandas.DataFrame(array_summary).to_csv())
        print(pandas.DataFrame(estimations).to_csv())
        # TODO: Add Exam Checks.
        # TODO: Add drive_details.
    else:
        # Array Summary:
        lines = [['Array Name', 'Purity Version', 'Controller Model', 'GUI % Used', 'Usable Capacity', 'Raw % Used',
                  'Raw Capacity', 'System Space']]
        line = [array_summary['array_name'], array_summary['purity_version'], array_summary['model'],
                array_summary['used_pct'], array_summary['usable_capacity'], array_summary['raw_pct'],
                array_summary['raw_capacity'], array_summary['system_space']]
        lines.append(line)
        print('\nArray Summary:')
        print(report_utils.draw_basic_table(lines))

        # Known Issues:
        if not skip_checks:
            exam.print_exam_results()

        # Space Estimations:
        lines = [['Evacuated Device', 'Device Type', 'Device Capacity', 'GUI % Used', 'Usable Capacity', 'Raw % Used',
                  'Raw Capacity', 'System Space', 'Safe', 'Reduce By']]

        if estimations:
            # Sort by usable capacity (in reverse).
            for device in sorted(estimations.keys(), key=lambda dev: estimations[dev]['device_capacity']):
                dev_data = estimations[device]
                # Format results for readability:
                device_type = dev_data['device_type']
                dev_cap = format_utils.auto_scale(dev_data['device_capacity'], 'binary_bytes')
                gui_pct = format_utils.percentage(dev_data['gui_pct'])
                raw_pct = format_utils.percentage(dev_data['raw_pct'])
                raw_capacity = format_utils.auto_scale(dev_data['raw_capacity'], 'binary_bytes')
                system_space = format_utils.auto_scale(dev_data['system_space'], 'binary_bytes')
                usable_capacity = format_utils.auto_scale(dev_data['usable_capacity'], 'binary_bytes')
                reduce_by = format_utils.auto_scale(dev_data['reduce_by'], 'binary_bytes')
                line = [device, device_type, dev_cap, gui_pct, usable_capacity, raw_pct,
                        raw_capacity, system_space, dev_data['safe'], reduce_by]
                lines.append(line)
            print('\nSpace Estimations After Evacuation:')
            print(report_utils.draw_basic_table(lines))
        else:
            print('\nNo devices to evacuate.')

        # Drive Details:
        if drive_details:
            for device in sorted(drive_details):
                print('\nDrive map for {}:'.format(device))
                print(drive_details[device])


@debug_utils.debug
def main():
    """Main Function:

    1) Parse user arguments
    2) Connect to the EvacHealthChecksAPI
    3) Print all applicable reports
    """
    kb_link = """
    https://support.purestorage.com/Internal_Tools/Support_Tools/Penguin_Fuse_Support_Tools/Fuse_Tool%3A_new_evac_checks
    """
    parser = interactive_utils.photon_argparse(kb_article=kb_link, description=__doc__)
    parser.add_argument('--drive', help='One or more drives to evacuate.', action='append',
                        type=validation_utils.drive, default=[])
    parser.add_argument('--pack', help='One or more drive packs to evacuate.', action='append',
                        type=validation_utils.drive, default=[])
    parser.add_argument('--shelf', help='One or more shelves to evacuate.', action='append',
                        type=validation_utils.chassis_name, default=[])
    parser.add_argument('--details', help='Show the drive details table(s).', action='store_true')
    parser.add_argument('--skip_checks', help='Skip known issue checks.', action='store_true')
    args = parser.parse_args()
    LOGGER.debug('Arguments given for evac_checks: {}'.format(args))

    # Override the defaults for latest of 24h as we only need the most recent hour.
    args.from_latest = '1h'
    to_evac = {'enclosures': args.shelf, 'data_packs': args.pack, 'drives': args.drive}
    # Wrap the Photon FlashArray API:
    evac_api = evac_health_checks.EvacHealthChecksAPI(to_evac=to_evac, **args)

    # Send results to the Report API:
    _print_reports(evac_api, args.table_type, args.details, args.skip_checks)


if __name__ == '__main__':
    main()
