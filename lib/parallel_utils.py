"""Utilities for running tasks in parallel."""

from __future__ import unicode_literals

import logging
import multiprocessing
import multiprocessing.pool
import os
import signal
import sys
import threading
import traceback

# Intentional override of build-in for Python2/3 compatibility
# pylint: disable=redefined-builtin
from builtins import range
try:
    # Intentional override of build-in for Python2/3 compatibility
    # pylint: disable=redefined-builtin
    from itertools import izip as zip
except ImportError:
    pass

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Callable
    from typing import Dict
    from typing import List
    from typing import Optional
except ImportError:
    pass

from photon.lib import config_utils
from photon.lib import env_utils


LOGGER = logging.getLogger(__name__)
SETTINGS = config_utils.get_settings()


def _set_nice_value(nice_value):
    # type: (Optional[int]) -> int
    """Determine if a nice value is valid, else set it based upon location."""
    if nice_value and nice_value not in range(0, 19):
        msg = 'Nice value must be between 0 and 19.'
        raise ValueError(msg)
    distro = env_utils.get_distro('/etc/lsb-release')
    return nice_value or 1 if distro != 'purity' else 19


def get_parallelism():
    # type: () -> int
    """Determine the number of processes to use."""
    cpus = int(multiprocessing.cpu_count() - SETTINGS['cpu']['reserved_cpus'])
    LOGGER.debug('Parallelism cpu count: {}'.format(cpus))
    busy = int((os.getloadavg()[0] * SETTINGS['cpu']['scale_factor']))
    LOGGER.debug('Business: {}'.format(busy))
    parallelism = int(max(SETTINGS['cpu']['min_children'], cpus - busy))
    LOGGER.debug('Using Thread/CPU count: {}.'.format(parallelism))
    return parallelism


# pylint: disable=abstract-method
class NicePool(multiprocessing.pool.Pool):
    """Makes a multiprocessing pool that will use a NICE value and limit child processes."""

    def __init__(self, processes=None, nice_value=None, max_tasks_per_child=None):
        # type: (Optional[int], Optional[int], Optional[int]) -> None
        """Create a resource conscious process pool.

        Arguments:
            processes (int): Maximum number of sub-processes to run.
                The default is between 4 and (total CPU cores - 2) - busy cores
            nice_value (int): A NICE priority value between 0 and 19.
            max_tasks_per_child (int): How many tasks each child process can run before retiring.
        """
        self.nice_value = _set_nice_value(nice_value)
        # CAVEAT: Don't allow processes count above or below configurable limits.
        # If we pass None, that will evaluate to false.  If we int() to 0
        # that will also evaluate to false.  If processes is not None, then
        # we will int it, and if it's reduced to 0 it will still evaluate
        # as false - so we should always call get_parallelism for cases where
        # we get an invalid process number.
        if processes is not None:
            # If we have some value for processes, we want to convert it to an int and
            # then we'll make sure it's within our min/max.  These are configurable via
            # settings.ini in case we need to increase these for some reason.
            processes = int(processes)
        processes = processes or get_parallelism()
        min_cpu_count = SETTINGS['cpu']['min_process_count']
        max_cpu_count = SETTINGS['cpu']['max_process_count']
        # Fail fast and where we expect - If it's not greater than zero, raise an assertion
        if processes < min_cpu_count:
            LOGGER.error('Invalid process count given to NicePool: {}. Setting minimum to {}.'.format(processes, min_cpu_count))
            processes = min_cpu_count
        elif processes > max_cpu_count:
            LOGGER.error('Invalid process count given to NicePool: {}. Setting maximum to {}.'.format(processes, max_cpu_count))
            processes = max_cpu_count
        max_tasks = max_tasks_per_child or SETTINGS['cpu']['max_tasks_per_child']
        LOGGER.debug('Initializing with {} processes and {} max_tasks'.format(processes, max_tasks))
        super(NicePool, self).__init__(processes, initializer=self.initialize, maxtasksperchild=max_tasks)

    def initialize(self):
        # type: () -> None
        """Set the nice level of the child processes."""
        os.nice(self.nice_value)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def __enter__(self):
        # type: () -> NicePool
        """Return this instance as the entry point."""
        return self

    def __exit__(self, exc_type, exc_value, trace):
        # type: (Any, Any, Any) -> None
        """Close the pool when exiting."""
        self.close()


class ProcessPool(object):
    """Creates a multiprocessing.pool of processes (default == CPU count)."""

    def __init__(self, processes=None, nice_value=None, max_tasks_per_child=None):
        # type: (Optional[int], Optional[int], Optional[int]) -> None
        """Create a pool of 'processes' number of threads."""
        self.results = []  # type: List[Any]
        LOGGER.debug('Initializing NicePool({}, {}, {})'.format(processes, nice_value, max_tasks_per_child))
        self.pool = NicePool(processes, nice_value, max_tasks_per_child)
        self.condition = threading.Condition()

    def parallelize(self, functs, funct_args):
        # type: (List[Callable], List[Any]) -> None
        """Run the tasks in parallel.
        The method will be called asynchronously. Use get_result() generator to get the results.
        """
        self.results = []
        for func, args in zip(functs, funct_args):
            result = self.pool.apply_async(func, args=args, callback=self._completed)
            self.results.append(result)
        self.pool.close()

    def _completed(self, _):
        # type: (Any) -> None
        """Notify anyone sleeping on the condition.

        This should never be called directly. This is invoked when a funct call completes.
        Note: this method runs in the called process, but in a different thread
        """
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()
        # Note, since _completed() is called before result is marked as ready, the sleeping thread
        # could wake up before the results are ready and go back to sleep!
        # (see below for temporary fix)

    def get_results(self, ordered=False):
        # type: (bool) -> Any
        """Create a generator that can be iterated over to get results.

        Note: The generator can go async (wait for a thread to complete) before returning results
        """
        self.condition.acquire()
        while True:
            if not self.results:
                LOGGER.debug('No results left.')
                self.condition.release()
                self.pool.join()
                break

            # If the caller wants ordered results, always wait for the first result
            if ordered and not self.results[0].ready():
                self.condition.wait(1)

            if not any(x.ready() for x in self.results):
                # Note that it is possible that we wake up before the results are ready (See note
                # in _completed() above). Temporary fix is to wake up every second and check
                self.condition.wait(1)

            for result in self.results[:]:
                if result.ready():
                    self.results.remove(result)
                    self.condition.release()
                    try:
                        ret = result.get()
                    # Intentional catch-all to send the child's traceback to logging
                    except Exception:
                        exc_type, exc_value, exc_tb = sys.exc_info()
                        stacktrace = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
                        LOGGER.exception(stacktrace)
                        # Raise the original exception and to stop processing
                        raise
                    LOGGER.debug('Getting next result.')
                    msg = 'Result is a {} and uses: {} bytes of memory.'
                    LOGGER.debug(msg.format(type(ret), sys.getsizeof(ret)))
                    yield ret
                    self.condition.acquire()
                elif ordered:
                    # The result from the first subprocess isn't ready. loop through and wait for it
                    break

    def close(self):
        # type: () -> None
        """Close the pool."""
        self.pool.close()
        LOGGER.debug('Closed the pool')

    def __enter__(self):
        # type: () -> ProcessPool
        """Return this instance as the entry point."""
        return self

    def __exit__(self, exc_type, exc_value, trace):
        # type: (Any, Any, Any) -> None
        """Close the pool when exiting."""
        self.close()
