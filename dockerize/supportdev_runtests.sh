#!/bin/bash

# Run pylint and pytest on all tools in the Photon infrastructure for Pure Support and Escalations tools.

# TODO: Add flake8, mypy, and possibly isort to our testing infrastructure.

retval=0

# Find our .py files in our Photon folders.
files=$(find ../ -name '*.py')

# Run pylint tests
echo
echo "============================= Starting pylint testing on Photon Infrastructure =============================="
echo

python2 -m pylint --rcfile=../.pylintrc -E ${files} || retval=$((retval || $?))

pl_end="============================= Finished pylint testing on Photon Infrastructure =============================="
echo

if [ ${retval} -eq 0 ]
then
    echo "No pylint errors found."
    echo
    echo ${pl_end}
    echo
else
    # If pylint fails we don't want to continue to pytests, so we cancel the job and inform users.
    echo "ERROR: Pylint returned a non-zero exit status. Not performing Unit Tests and cancelling job."
    echo
    echo ${pl_end}
    exit ${retval}
fi


# If pylint succeeds then we can start running pytest for all the unit tests.
echo
echo "============================= Starting pytest testing on Photon Infrastructure =============================="
echo

# In order to ensure pytest doesn't get confused, pull out only the 'test_*.py' files.
pytest_files=$(for filename in ${files}; do echo ${filename} | grep test_.*py$; done)

### pytest-benchmark ###
# TODO: Remove the baseline (001 file) for each stable release.
# PT-2240: Benchmark breaking the build?
# benchmark_args="--benchmark-autosave --benchmark-compare=0001 --benchmark-storage='file://../benchmarks'"
# Fail Criteria is set to: +-25% on min/max runtime and 1.5 std deviations from the mean.
# bench_fail="--benchmark-compare-fail=stddev:150% --benchmark-compare-fail=min:25% --benchmark-compare-fail=max:25%"

### pytest-cov (code test coverage) ###
coverage_args="--cov ${pytest_files}"

# Full pytest command:
# python2 -m pytest  ${pytest_files} ${coverage_args} ${benchmark_args} ${bench_fail} || retval=$((retval || $?))
python2 -m pytest  ${pytest_files} ${coverage_args} || retval=$((retval || $?))

echo "=========================== Finished pytest testing on Photon Infrastructure =============================="
echo

exit ${retval}
