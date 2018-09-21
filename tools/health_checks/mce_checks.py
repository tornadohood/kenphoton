#!/usr/bin/env python
"""Memory Exception Checks."""

from photon import api
from photon.lib import debug_utils
from photon.lib import interactive_utils
from photon.report import report_api


@debug_utils.debug
def main():
    """Parse user arguments, generate the MCE Report, and print it."""
    controllers = ('CT0', 'CT1')
    parser = interactive_utils.photon_argparse(__doc__)
    args = parser.parse_args()

    array = api.FlashArray(**args)
    report = report_api.Report(array)

    # TODO: PT-2292 - Make this dynamic, this static list is bad mkay?
    total_mces = array.get_fields(['controller_serial', 'mce_counts', 'offline_memory', 'sel_critical_events'])
    ct0_total = int(total_mces[total_mces['controller'] == 'CT0'].mce_counts.sum())
    ct1_total = int(total_mces[total_mces['controller'] == 'CT1'].mce_counts.sum())

    # Build the Tables (MCE, Overall counts, Offline Memory, and SEL events):
    mce_table = report.add_table(args.table_type, title='MCE Events Over Time', grid=True)
    mce_table.add_metric('controller_serial', controller='CT0')
    mce_table.add_metric('mce_counts', controller='CT0')
    mce_table.add_metric('controller_serial', controller='CT1')
    mce_table.add_metric('mce_counts', controller='CT1')

    # Overall MCE Totals:
    report.add_text_area(text=str(ct0_total), title='CT0 Total MCE Events')
    report.add_text_area(text=str(ct1_total), title='CT1 Total MCE Events')

    # Offline Memory
    offline_table = report.add_table(args.table_type, title='Dynamically Offline Memory', grid=True)
    for controller in controllers:
        offline_table.add_metric('offline_memory', controller=controller)
        # SEL Events
        sel_table = report.add_table(args.table_type, title='{} Memory Related SEL Events'.format(controller), grid=True)
        sel_table.add_metric('sel_critical_events', controller=controller)
    report.render_tables(jira=args.jira)


if __name__ == '__main__':
    main()
