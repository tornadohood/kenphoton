"""Unit tests for check_utils."""

import unittest

from photon.lib import check_utils


class DummyExam(check_utils.Exam):
    """Helper class for the sake of testing Exam."""

    def __init__(self):
        super(DummyExam, self).__init__({'Test1': DummyTest('PURE-12345'), 'Test2': DummyTest()})


class DummyTest(check_utils.Check):
    """Helper class for the sake of testing Check."""

    # Intentionally different for the sake of testing.
    # pylint: disable=arguments-differ
    def run_test(self, pass_test=False):
        """Run a test."""
        result = False
        if pass_test:
            result = True
        # This is defined in the sub-class.
        # pylint: disable=attribute-defined-outside-init
        self.passed = result
        return result


class CheckTestCase(unittest.TestCase):
    """Unit tests for Check."""
    check = DummyTest('Dummy Test')

    def test_fail(self):
        """Run a test that should fail."""
        self.check.run_test(False)
        self.assertFalse(self.check.passed)

    def test_pass(self):
        """Run a test that should pass."""
        self.check.run_test(True)
        self.assertTrue(self.check.passed)


class ExamTestCase(unittest.TestCase):
    """Unit tests for Exam."""
    exam = DummyExam()

    def test_fail(self):
        """Run all tests; they should fail."""
        self.exam.run_tests()
        self.assertFalse(self.exam.passed)


if __name__ == '__main__':
    unittest.main()
