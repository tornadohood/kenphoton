#!/usr/bin/env python

"""Health Checks to run prior to doing a hardware NDU."""

from photon import api
from photon.lib import check_utils
from photon.lib import debug_utils
from photon.lib import interactive_utils
from photon.lib import version_utils

# pylint: disable=unused-import, arguments-differ
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple
    from typing import Union
except ImportError:
    pass

# TODO: Hardware NDU Checks needed:
# 1) NDU's now supported with WFS on 4.10.7; tunable PS_APPS_AUX_INTERFACE      (DONE)
# 2) Number of shelves > 4: Purity must be upgraded to 4.5.6+
# 3) Minimum version: 4.5.5     (DONE)
# 4) SAS port counts to and from Models (we need to have the same amount of support for more ports).
# 5) SAS Cabling topology
# 6) FC Card transfer, r2 may not support the legacy cards (8 Gbit to 16 Gbit upgrade)
# 7) Non-standard Ethernet port configurations
# 8) Versions affected by failover/giveback bugs
# 9) Recent Alerts
# 10) Non-redundant hosts
# 11) r2 model support 4.7.3+; generalize hardware target supported versions checks...
# Everything else in PT-465, PT-1945, and PT-926

NDU_CT_TYPES = (
    'FA-m20',
    'FA-m50',
    'FA-m70',
    'FA-m10r2',
    'FA-m20r2',
    'FA-m50r2',
    'FA-m70r2',
    'FA-x10r2',
    'FA-x20r2',
    'FA-x50r2',
    'FA-x70r2',
    'FA-x90r2',
    'FA-X70R2',
    'FA-X90R2',
)


class HardwareNDUAPI(api.FlashArray):
    """Helper class for handling Hardware upgrades."""

    def __init__(self, new_hardware=None, **kwargs):
        # type: (Optional[str], **Dict[str, Any]) -> None
        self.new_hardware = new_hardware
        super(HardwareNDUAPI, self).__init__(**kwargs)


# TODO: PT-1945
class MercuryChecks(check_utils.Check):
    """Check for upgrading to the '//X series'."""

    def run_test(self, ndu_api):
        # type: (HardwareNDUAPI) -> None
        """Caveats when upgrading to Mercury controllers."""
        pass


class MinimumNDUVersionCheck(check_utils.VersionCheck):
    """Check if the array is on a supported version of Purity."""

    def __init__(self):
        # type: () -> None
        fail_msg = 'Hardware NDU is not supported until Purity 4.5.5 or later.'
        pass_msg = 'Hardware NDU is supported.'
        super(MinimumNDUVersionCheck, self).__init__(('4.5.5', ), '', fail_msg, pass_msg)


class MixedControllerTypesCheck(check_utils.Check):
    """Check if the array has mixed controller hardware."""

    def run_test(self, ndu_api):
        # type: (HardwareNDUAPI) -> None
        """Check if the controller hardware types don't match up."""
        controller_models = [item for item in ndu_api.get_latest_value('controller_model')['Model']
                             if item.startswith('FA')]
        # Mercury configurations will put the Managed Shelves in here as well, so only include FA controllers.
        # Example:
        # {'Model': ['FA-X70R2', 'FA-X70R2', 'DFSC1', 'DFSC1'], 'Name': ['CT0', 'CT1', 'SH9.SC1', 'SH9.SC0']}
        if len(controller_models) != 2 or controller_models[0] != controller_models[1]:
            self.details.append('Controller models are not the same!')
            self.passed = False
        else:
            self.details.append('Controller models are {}.'.format(' and '.join(controller_models)))
            self.passed = True


class NewHardwareCheck(check_utils.Check):
    """Helper to run a specific check based upon the controller hardware to upgrade to."""

    def run_test(self, ndu_api):
        # type: (HardwareNDUAPI) -> None
        """Run the upgrade check related to the target hardware."""
        if not ndu_api.new_hardware:
            self.details.append('No target hardware specified.')
            self.passed = False
            return
        # Pick the appropriate check based upon the hardware type:
        new_hw = ndu_api.new_hardware
        if new_hw.startswith('FA-m'):
            check_name = 'PlatinumChecks'
        elif new_hw.startswith('FA-x'):
            check_name = 'TungstenChecks'
        elif new_hw.startswith('FA-X'):
            check_name = 'MercuryChecks'
        else:
            check_name = 'unknown'
        check_class = globals().get(check_name)
        if not check_class:
            self.details.append('Failed to locate a check for the new hardware "{}".'.format(new_hw))
            self.passed = False
        else:
            check = check_class()
            check.run_test(ndu_api)
            self.details = check.details
            self.passed = check.passed


# TODO: PT-1945
class PlatinumChecks(check_utils.Check):
    """Check for upgrading to the '//m series'."""

    def run_test(self, ndu_api):
        # type: (HardwareNDUAPI) -> None
        """Caveats when upgrading to Platinum controllers."""
        pass


# TODO: PT-1945
class TungstenChecks(check_utils.Check):
    """Check for upgrading to the '//x series'."""

    def run_test(self, ndu_api):
        # type: (HardwareNDUAPI) -> None
        """Caveats when upgrading to Tungsten controllers."""
        pass


class WFSCompatibilityCheck(check_utils.Check):
    """Check if WFS is being used, then the Virtual File Server Role may need to be changed."""

    def run_test(self, ndu_api):
        # type: (HardwareNDUAPI) -> None
        """Check if WFS is being used."""
        tunables = ndu_api.get_latest_value('tunables')
        if tunables.get('PURITY_APPS_ENABLED') == '1' and 'PS_APPS_AUX_INTERFACE' in tunables:
            controller_models = ndu_api.get_latest_value('controller_model')['Model']
            if controller_models[0].startswith('FA-X'):
                self.details.append('The Virtual File Server Role needs to be moved off the controller being replaced.')
                self.passed = False
            elif version_utils.compare_versions(ndu_api.get_latest_value('purity_version'), '4.10.7'):
                self.details.append('Hardware NDU is supported.')
                self.passed = True
            else:
                self.details.append('Hardware NDU is not supported with WFS until Purity 4.10.7+.')
                self.passed = False
        else:
            self.details.append('WFS is not enabled.')
            self.passed = True


class HardwareNDUChecks(check_utils.Exam):
    """All checks to perform prior to doing a hardware NDU."""

    def __init__(self):
        # type: () -> None
        super(HardwareNDUChecks, self).__init__(checks={
            # TODO: PT-1945 - Enable this once all of the Hardware Checks are implemented:
            # 'New Hardware Checks': NewHardwareCheck(),
            'Minimum NDU Purity Version': MinimumNDUVersionCheck(),
            'Mixed Controller Hardware': MixedControllerTypesCheck(),
            'WFS Compatibility': WFSCompatibilityCheck(),
        })


@debug_utils.debug
def main():
    # type: () -> None
    """Parse user arguments, run all health checks."""
    parser = interactive_utils.photon_argparse(__doc__)
    parser.add_argument('--new_hardware', help='The hardware type to upgrade to.', choices=NDU_CT_TYPES, required=True)
    args = parser.parse_args()
    array = HardwareNDUAPI(**{'fqdn': args.fqdn,
                              'log_path': args.log_path,
                              'start': args.start,
                              'end': args.end,
                              'from_latest': '1h',
                              'files': args.files,
                              'new_hardware': args.new_hardware})
    exam = HardwareNDUChecks()
    exam.run_tests(array)
    exam.print_exam_results()


if __name__ == '__main__':
    main()
