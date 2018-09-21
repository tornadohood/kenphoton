"""Utilities for debugging and profiling."""

from __future__ import division
from __future__ import print_function

import errno
import logging
import os
import pdb
import signal
import sys
import time
import textwrap
import traceback

try:
    import tracemalloc
except ImportError:
    tracemalloc = None
from functools import wraps
from cProfile import Profile
try:
    from psutil import Process
except ImportError:
    Process = None

import pickle
import six

from photon.lib import config_utils
from photon.lib import custom_errors

HOME = os.path.expanduser('~')
LOGGER = logging.getLogger(__name__)
# If you are using debug_utils, then set logging to DEBUG.
LOGGER.setLevel(logging.DEBUG)
SETTINGS = config_utils.get_settings()


# pylint: disable=too-few-public-methods
class MallocTraceManager(object):
    """Context Manager for tracemalloc functionality.

    This will start the malloc tracing,and stop the tracer once the function is done."""

    def __init__(self, nframes=1):
        self.nframes = nframes
        self.tracer = tracemalloc

    def __enter__(self):
        self.tracer.start(self.nframes)
        return self.tracer

    def __exit__(self, *args):
        self.tracer.stop()


def cprofile_me(funct):
    """Decorator to cProfile a function.

    Example of usage:
    @cprofile_me
    def my_function():

    This will create a cprofile file named after the module, function called.
    These will be stored in the user's home directory under the .local folder.
    i.e. file_utils_parallel_grep.cprofile
    The cprofile files can be visualized via snakeviz: https://jiffyclub.github.io/snakeviz/
    """
    @wraps(funct)
    def function_cprofile(*args, **kwargs):
        """cProfile a function."""
        name = '{}.{}.cprofile'.format(funct.__module__, funct.__name__)
        profiler = Profile()
        result = profiler.runcall(funct, *args, **kwargs)
        profiler.dump_stats(os.path.join(HOME, name))
        return result
    return function_cprofile


def debug(funct):
    """Decorator to apply the debug action found in settings.ini or a local override."""
    @wraps(funct)
    def function_debugger(*args, **kwargs):
        """Helper to debug a function run."""
        try:
            result = funct(*args, **kwargs)
            return result
        # Intentional catch-all:
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.exception(error)
            if SETTINGS['debug']['on_exception'] == 'pdb':
                _, _, stacktrace = sys.exc_info()
                traceback.print_exc()
                pdb.post_mortem(stacktrace)
            elif SETTINGS['debug']['on_exception'] == 'raise':
                raise
            elif SETTINGS['debug']['on_exception'] == 'quiet':
                msg = """

                An error occurred:
                Error Message: {}
                Please create a PT Jira and/or ping in the slack channel #support-dev for guidance.

                """.format(error)
                print(textwrap.dedent(msg))
    return function_debugger


def profile_malloc(top=25, group_by='lineno'):
    """Decorator to dump the malloc allocations used by Python.

    Arguments:
        top (int): How many of the top users to display.
        group_by (str): Either 'filename', 'lineno', or 'traceback.
            See: https://docs.python.org/3/library/tracemalloc.html

    Example of usage:
    @profile_malloc
    def my_function():

    Example of the output dump file:
    python_malloc.dump
    """

    def helper_decorator(funct):
        """Apply the top/group_by arguments."""

        @wraps(funct)
        def python_malloc(*args, **kwargs):
            """Log how much memory is being used by Python."""
            if not tracemalloc:
                return funct(*args, **kwargs)
            with MallocTraceManager() as tracer:
                result = funct(*args, **kwargs)
                usage = tracer.take_snapshot()
                top_users = [str(user) for user in usage.statistics(group_by)[:top]]
                msg = 'Top Memory Users:\n{}'.format('\n\t'.join(top_users))
                LOGGER.debug(msg)
            return result
        return python_malloc
    return helper_decorator


def profile_memory(funct):
    """Decorator to profile the memory usage of a function.

    Example of usage:
    @profile_memory
    def my_function():

    Example of debug log content:
    "Python memory usage during photon.lib.test.test_debug_utils_simple_funct: 35.09 MB"
    """
    @wraps(funct)
    def function_memory(*args, **kwargs):
        """Log how much memory the function is using."""
        if not Process:
            return funct(*args, **kwargs)
        proc = Process(os.getpid())
        name = '{}_{}'.format(funct.__module__, funct.__name__)
        msg = 'Python memory usage during {}: {:.2f} MB'
        LOGGER.debug(msg.format(name, proc.memory_info().rss / 1048576.))
        result = funct(*args, **kwargs)
        LOGGER.debug('Estimated size of results: {} bytes'.format(sys.getsizeof(result)))
        return result
    return function_memory


def profile_runtime(funct):
    """Decorator to time the runtime of a function.

    Example of usage:
    @profile_runtime
    def my_function():

    Example of debug log content:
    "Runtime of file_utils.parallel_grep: 10.22 ms."
    """
    @wraps(funct)
    def function_timer(*args, **kwargs):
        """Time how long the function takes to run."""
        start = time.time()
        result = funct(*args, **kwargs)
        end = time.time()
        runtime = (end - start) * 1000
        name = '{}.{}'.format(funct.__module__, funct.__name__)
        LOGGER.debug('Runtime of {}: {:.2f} milliseconds.'.format(name, runtime))
        return result
    return function_timer


def timeout(seconds=60, msg=os.strerror(errno.ETIME)):
    """Decorator to raise a custom_errors.TimeoutError if a function takes too long to run.

    Arguments:
        seconds (int): A timeout value in seconds.
        msg (str): An error message to include in the custom_errors.TimeoutError; if raised.

    Example of usage:
    @timeout(seconds=30, msg='This function took longer than 30 seconds to run.)
    def my_function():
    """
    def helper_decorator(funct):
        """Apply the seconds/msg arguments."""

        def _handle_timeout(signum, frame):
            """Raise a custom_errors.TimeoutError with given message."""
            LOGGER.exception('custom_errors.TimeoutError signo({}): {}\n{}'.format(signum, frame, msg))
            # Python2 complains about this, but it does exist in Python3
            # pylint: disable=undefined-variable
            raise custom_errors.TimeoutError(msg)

        @wraps(funct)
        def timeout_wrapper(*args, **kwargs):
            """Handle signals for custom_errors.TimeoutError while running the function."""
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = funct(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return timeout_wrapper
    return helper_decorator


def profile_all(funct):
    """Decorator to do all profiling for a function.

    Example of usage:
    @profile_all
    def my_function():
    """
    @profile_malloc()
    @cprofile_me
    @profile_memory
    @profile_runtime
    @wraps(funct)
    def function_profiler(*args, **kwargs):
        """Run the function with profiling."""
        return funct(*args, **kwargs)
    return function_profiler


def save_var(variable, varname=None):
    """Save a pickled variable."""
    # Troll through our globals key/vals to find the name of our variable
    # if we weren't given one to name it.
    if not varname:
        # Have to wrap the globals() in a dict otherwise they'll mutate
        # while we check and throw an error we don't want.
        for key, value in six.iteritems(dict(globals())):
            if (value == variable) and not key.startswith('_'):
                varname = key
    # If we still can't find it, raise an error.  Because a man needs a name.
    if not varname:
        LOGGER.error('Could not find the variable in locals().')
        raise ValueError('Could not find the variable in locals().')
    varpath = '{}.{}.pklvar'.format(os.path.expanduser('~/'), varname)
    # Pickle that shiznit bruh.
    with open(varpath, 'wb') as var_file:
        pickle.dump(variable, var_file)
    LOGGER.info('Saved variable as \'%s\'', varname)


def load_var(varname):
    """Load a pickled variable."""
    varpath = '{}.{}.pklvar'.format(os.path.expanduser('~/'), varname)
    with open(varpath, 'rb') as var_file:
        variable = pickle.load(var_file)
    return variable


def clean_var(varname):
    """Remove a pickled variable."""
    varpath = '{}.{}.pklvar'.format(os.path.expanduser('~/'), varname)
    try:
        os.remove(varpath)
    except OSError:
        LOGGER.error('Tried to remove pklvar %s, but it was not found.', varname)
    LOGGER.info('Removed pklvar {}'.format(varname))
