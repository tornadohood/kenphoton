"""Utilities and helpers to run health checks."""

from __future__ import print_function

import logging

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Type
except ImportError:
    pass

from photon.lib import print_utils
from photon.lib import report_utils
from photon.lib import version_utils

LOGGER = logging.getLogger(__name__)


class Check(object):
    """A single check to run."""

    def __init__(self, jira=None):
        # type: (str) -> None
        """
        Arguments:
            jira (str): A JIRA number to apply to the check,  e.g. 'PURE-12345'.
        """
        self.name = self.__class__.__name__  # type: str
        self.passed = False  # type: bool
        self.details = []  # type: List[str]
        self.jira = jira  # type: Optional[str]

    def run_test(self, array_api):  # type: (Any) -> None
        """Not Yet Implemented."""
        raise NotImplementedError


# TODO: PT-2336 - Simplify VersionCheck logic
class VersionCheck(Check):
    """A simple test which just compares Purity versions."""

    def __init__(self,
                 fixed_in_versions,                 # type: List[str]
                 jira=None,                         # type: Optional[str]
                 fail_message=None,                 # type: Optional[str]
                 pass_message=None,                 # type: Optional[str]
                 minimum_affected_version=None      # type: Optional[str]
                ):                                  # type: (...) -> None
        """
        Arguments:
            fixed_in_versions (list): One or more versions where the issue is fixed.
            jira (str): A JIRA number to apply to apply for more information, e.g. 'PURE-12345'.
            fail_message (str): A custom message to show when failure.
            pass_message (str): A custom message to show when passing.
            minimum_affected_version (str): A version which indicates minimum version where the issue is applicable.
        """
        super(VersionCheck, self).__init__(jira=jira)
        self.minimum_affected_version = minimum_affected_version  # type: str
        self.fixed_in_versions = fixed_in_versions  # type: List[str]
        self.fail_message = fail_message or 'Not fixed in this version.'  # type: str
        self.pass_message = pass_message or 'Fixed in the current Purity version.'  # type: str

    def run_test(self, array_api):
        # type: (Any) -> None
        """Get the latest Purity version and compare it against the fixed_in_versions.

        Arguments:
            array_api (photon.api.FlashArray): A Photon API or sub-class.
                # See photon.api for more information on the base-class.
        """
        # Reset details from previous test runs.
        self.details = []
        # TODO: PT-1957 - Use a simpler way of getting the latest value from both controllers.
        versions = array_api.get_fields(['purity_version'])
        try:
            ct0_version = versions[versions['controller'] == 'CT0'].purity_version.dropna().tail(1).tolist()[-1]
            ct1_version = versions[versions['controller'] == 'CT1'].purity_version.dropna().tail(1).tolist()[-1]
        # We can get a KeyError or an IndexError depending upon where the information is missing.
        # A KeyError if we don't have a 'purity_version' column, and an IndexError if the column has no values.
        except (KeyError, IndexError):
            self.details.append('Missing Purity version information for one or both controllers.')
            self.passed = False
            return
        if ct0_version != ct1_version:
            self.details.append('Purity versions do not match!')
            self.passed = False
        else:
            # The versions match, so just use CT0.
            purity_version = ct0_version
            on_affected_version = True
            if self.minimum_affected_version:
                on_affected_version = version_utils.compare_versions(purity_version, self.minimum_affected_version)
            if on_affected_version:
                fixed = version_utils.compare_multiple_versions(purity_version, self.fixed_in_versions)  # type: bool
                if fixed:
                    self.details.append(self.pass_message)
                    self.passed = True
                else:
                    self.details.append(self.fail_message)
                    self.passed = False
            else:
                self.details.append(self.pass_message)
                self.passed = True


class Exam(object):
    """A collection of checks to perform."""

    def __init__(self, checks):
        # type: (Dict[str, Type[Check]]) -> None
        """
        Arguments:
            checks (dict): Named Check objects that will be run by the exam.
                Example: {'Space Health': SpaceHealth(jira='PURE-102034'), ...}
        """
        self.name = self.__class__.__name__  # type: str
        self.checks = checks  # type: Dict[str, Type[Check]]
        self._passed = None  # type: Optional[bool]

    @property
    def passed(self):
        # type: (...) -> bool
        """Determine if all tests have passed."""
        if self._passed is not None:
            return self._passed
        self._passed = all([check.passed for check in self.checks.values()])
        return self._passed

    def run_tests(self, array_api=None):
        # type: (Any) -> None
        """Run all known checks with the given array_api.

        Arguments:
            array_api (FlashArray): A connection to the FlashArray API.
        """
        check_len = len(self.checks)
        for index, test in enumerate(sorted(self.checks.values(), key=lambda check: check.name)):
            print_utils.status_update('Running test "{}": {} of {}.'.format(test.name, index, check_len))
            test.run_test(array_api)

    def print_exam_results(self, title='Health Check Results'):
        # type: (str) -> None
        """Print out all check results in a tabular format."""
        lines = [['Known Issue', 'JIRA', 'Passed', 'Details']]
        for check, inst in sorted(self.checks.items()):
            line = [check, inst.jira or '-', str(inst.passed), '\n'.join(inst.details) or '-']
            lines.append(line)
        print('\n{}:'.format(title))
        print(report_utils.draw_basic_table(lines))
