#!/usr/bin/env python

"""FlashArray Space Statistics Reports."""

from photon import api
from photon.lib import debug_utils
from photon.lib import interactive_utils
from photon.report import report_api

KB = 'https://support.purestorage.com/Internal_Tools/Support_Tools/Penguin_Fuse_Support_Tools/Fuse_Tool%3A_space_stats'


@debug_utils.debug
def main():
    """Parse user arguments, generate the Space Report, and print it."""
    parser = interactive_utils.photon_argparse(__doc__, kb_article=KB)
    parser.add_argument('--used', action='store_true', help='Display "Used Space" categories.')
    parser.add_argument('--unreported', action='store_true', help='Display "Unreported Space" categories.')
    args = parser.parse_args()
    kwargs = vars(args)
    kwargs['granularity'] = args.granularity or '1 hour'
    array = api.FlashArray(**kwargs)
    report = report_api.Report(array)

    # Generic Report:
    report.add_template('array_space_summary', table_type=args.table_type)

    # Used Space (GUI)
    if args.used:
        report.add_template('array_used_space', table_type=args.table_type)

    # Unreported Space
    if args.unreported:
        report.add_template('array_unreported_space', table_type=args.table_type, grid=True)
        report.add_template('array_unreported_space_continued', table_type=args.table_type, grid=True)

    # Additional tables to build:
    # TODO: PT-2185 - Replication metrics.
    # TODO: PT-2186 - Reduction/Dedup metrics.
    # total_reduction, thin_provisioning, data_reduction, puredb_dedup_version
    # core.log: compression_ratio, if we want to estimate dedup ratio.
    # TODO: PT-2188 - Per-Volume / Pgroup / HostGroup / Pod, etc. used space.
    report.render_tables(jira=args.jira)


if __name__ == '__main__':
    main()
