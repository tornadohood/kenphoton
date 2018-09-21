#!/usr/bin/env python
"""Array Performance statistics."""

from photon import api
from photon.lib import debug_utils
from photon.lib import interactive_utils
from photon.report import report_api

KB = 'https://support.purestorage.com/Internal_Tools/Support_Tools/Penguin_Fuse_Support_Tools/Fuse_Tool%3A_perf_stats'


@debug_utils.debug
def main():
    """Parse user arguments, generate the Performance Report, and print it."""
    parser = interactive_utils.photon_argparse(__doc__, kb_article=KB)
    args = parser.parse_args()
    # TODO: Verbose output?
    kwargs = vars(args)
    # 30 seconds is the finest granularity available currently; use this by default.
    kwargs['granularity'] = args.granularity or '30s'
    array = api.FlashArray(**kwargs)
    report = report_api.Report(array)
    report.add_template('array_performance_summary', table_type=args.table_type)
    report.render_tables(jira=args.jira)


if __name__ == '__main__':
    main()
