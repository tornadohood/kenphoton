"""Unit tests for lib/parallel_utils."""

from __future__ import unicode_literals

import unittest

from photon.lib import parallel_utils


class TestNicePool(unittest.TestCase):
    """Unit tests for NicePool."""

    def test_static_process_count(self):
        """Ensure that setting a static processes number on init works as expected."""
        with parallel_utils.NicePool(8) as pool:
            # pylint: disable=protected-access
            self.assertEqual(pool._processes, 8)
            pool.close()

    def test_dynamic_process_count(self):
        """Ensure that dynamic scaling works as expected."""
        # TODO: Not sure how to do this in a consistent manner
        # Jenkins will have different cores and busyness than local/vm/etc.
        pass


    def test_zero_process_count(self):
        """Ensure that bad process counts don't explodinate us."""
        with parallel_utils.NicePool(0) as pool:
            assert pool._processes >= 1
            pool.close()

    def test_negative_process_count(self):
        """Ensure that bad process counts don't explodinate us."""
        with parallel_utils.NicePool(-1.25) as pool:
            assert pool._processes >= 1
            pool.close()

    def test_fractional_process_count(self):
        """Ensure that bad process counts don't explodinate us."""
        with parallel_utils.NicePool(0.25) as pool:
            assert pool._processes >= 1
            pool.close()

    def test_excessive_process_count(self):
        """Ensure that bad process counts don't explodinate us."""
        with parallel_utils.NicePool(33) as pool:
            self.assertEqual(pool._processes, 32)
            pool.close()


class TestProcessPool(unittest.TestCase):
    """Unit tests for ProcessPool."""

    def test_parallelize(self):
        """Ensure that tasks are able to be run in parallel."""
        tasks = [my_funct, my_funct]
        args = [(1, 2), (2, 4)]
        with parallel_utils.ProcessPool(2) as pool:
            pool.parallelize(tasks, args)
            results = [val for val in pool.get_results()]
        # Use a set, because the order may vary.
        self.assertEqual(set(results), {3, 6})

    def test_parallelize_ordered(self):
        """Test get results with order enforced."""
        tasks = [my_funct, my_funct]
        args = [(1, 2), (2, 4)]
        with parallel_utils.ProcessPool(2) as pool:
            pool.parallelize(tasks, args)
            results = [val for val in pool.get_results(True)]
        self.assertEqual(results, [3, 6])

    def test_child_traceback(self):
        """Test a child process having a traceback."""
        tasks = [my_funct, my_funct]
        args = [(1, 2), ('2', 4)]
        with parallel_utils.ProcessPool(2) as pool:
            pool.parallelize(tasks, args)
            with self.assertRaises(TypeError):
                # This should raise a TypeError because str + int == badness.
                for val in pool.get_results():
                    str(val)  # Do something with val...


def my_funct(first, second):
    """Dummy test helper."""
    return first + second
