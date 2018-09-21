#!/usr/bin/env make -f

# Use git describe to determine the version number
PURE_SUPPORT_VERSION=$(shell git describe --match 'pure_support-*' 2>/dev/null | cut -f 2- -d "-" )
ifeq (${PURE_SUPPORT_VERSION},)
PURE_SUPPORT_VERSION=99.9.9
endif

UPGRADE_CHECKS_VERSION=$(shell git describe --match 'upgrade_checks-*' 2>/dev/null | cut -f 2- -d "-")
ifeq (${UPGRADE_CHECKS_VERSION},)
UPGRADE_CHECKS_VERSION=99.9.9
endif

HOSTNAME=$(shell hostname)
USERNAME=$(shell whoami)
BUILDNOTE="Built by ${USERNAME}@${HOSTNAME}"

clean:
	@rm -rf `find . -name "__pycache__" -o -name "*.pyc"`
	@rm -rf build .coverage* dist *.egg-info

realclean: clean
	@rm -rf `find . -wholename "*/test/artifacts"`

dtest_docker_image:
	@./build_image.sh runtests_env

dtest: dtest_docker_image
	@./docker_run.sh runtests_env

dtest_packages_docker_image:
	@cd dockerize/ && ./build_image.sh pkgtest_env

dtest_packages: dtest_packages_docker_image
	@cd dockerize/ && ./docker_run.sh pkgtest_env

test_local_packages:
	@cd test_packages/ && ./test_local_packages.sh

test_packages:
	@cd test_packages/ && ./test_packages.sh


dpackages_docker_image:
	@cd dockerize/ && ./build_image.sh packaging_env

dpackages: dpackages_docker_image
	@cd dockerize/ && ./docker_run.sh packaging_env

packages: clean pure_support_internal_package pure_support_package predictive_scans_package rollout_package

pure_support_internal_package: pure_support_internal_source
	@tar  -C dist -xf dist/pure_support_internal-${PURE_SUPPORT_VERSION}.tar.gz
	@rm -f pure_support_internal_debian/changelog
	@dch --create --newversion ${PURE_SUPPORT_VERSION} --package pure-support-internal --distribution unstable --urgency low --changelog pure_support_internal_debian/changelog ${BUILDNOTE}
	@cp -Rp pure_support_internal_debian dist/pure_support_internal-${PURE_SUPPORT_VERSION}/debian
	@cd dist/pure_support_internal-${PURE_SUPPORT_VERSION} && TARGET_VERSION=${PURE_SUPPORT_VERSION} dpkg-buildpackage -b -uc
	@rm -rf dist/pure_support_internal-*/
	@echo ${PURE_SUPPORT_VERSION} > dist/VERSION

pure_support_internal_source:
	@TARGET_VERSION=${PURE_SUPPORT_VERSION} python2.7 pure_support_internal_setup.py sdist

pure_support_package: pure_support_source
	@tar  -C dist -xf dist/pure_support-${PURE_SUPPORT_VERSION}.tar.gz
	@rm -f pure_support_debian/changelog
	@dch --create --newversion ${PURE_SUPPORT_VERSION} --package pure-support --distribution unstable --urgency low --changelog pure_support_debian/changelog ${BUILDNOTE}
	@cp -Rp pure_support_debian dist/pure_support-${PURE_SUPPORT_VERSION}/debian
	@cd dist/pure_support-${PURE_SUPPORT_VERSION} && TARGET_VERSION=${PURE_SUPPORT_VERSION} dpkg-buildpackage -b -uc
	@rm -rf dist/pure_support-*/
	@echo ${PURE_SUPPORT_VERSION} > dist/VERSION

pure_support_source:
	@TARGET_VERSION=${PURE_SUPPORT_VERSION} python2.7 pure_support_setup.py sdist

upgrade_checks_package: upgrade_checks_source upgrade_checks_wheel
	@tar -C dist -xf dist/upgrade_checks-${UPGRADE_CHECKS_VERSION}.tar.gz
	@rm -f upgrade_checks_debian/changelog
	@dch --create --newversion ${UPGRADE_CHECKS_VERSION} --package upgrade-checks --distribution unstable --urgency low --changelog upgrade_checks_debian/changelog ${BUILDNOTE}
	@cp -Rp upgrade_checks_debian dist/upgrade_checks-${UPGRADE_CHECKS_VERSION}/debian
	@cd dist/upgrade_checks-${UPGRADE_CHECKS_VERSION} && TARGET_VERSION=${UPGRADE_CHECKS_VERSION} dpkg-buildpackage -b -uc
	@rm -rf dist/upgrade_checks-*/
	@echo ${UPGRADE_CHECKS_VERSION} > dist/VERSION

upgrade_checks_source:
	@TARGET_VERSION=${UPGRADE_CHECKS_VERSION} python2.7 upgrade_checks_setup.py sdist

upgrade_checks_wheel:
	@TARGET_VERSION=${UPGRADE_CHECKS_VERSION} python2.7 upgrade_checks_setup.py bdist_wheel

predictive_scans_package: predictive_scans_source
	@tar -C dist -xf dist/predictive_scans-${PURE_SUPPORT_VERSION}.tar.gz
	@rm -f predictive_scans_debian/changelog
	@dch --create --newversion ${PURE_SUPPORT_VERSION} --package predictive-scans --distribution unstable --urgency low --changelog predictive_scans_debian/changelog ${BUILDNOTE}
	@cp -Rp predictive_scans_debian dist/predictive_scans-${PURE_SUPPORT_VERSION}/debian
	@cd dist/predictive_scans-${PURE_SUPPORT_VERSION} && TARGET_VERSION=${PURE_SUPPORT_VERSION} dpkg-buildpackage -b -uc
	@rm -rf dist/predictive_scans-*/
	@echo ${PURE_SUPPORT_VERSION} > dist/VERSION

predictive_scans_source:
	@TARGET_VERSION=${PURE_SUPPORT_VERSION} python2.7 predictive_scans_setup.py sdist

rollout_package: rollout_source
	@tar -C dist -xf dist/rollout-${PURE_SUPPORT_VERSION}.tar.gz
	@rm -f rollout_debian/changelog
	@dch --create --newversion ${PURE_SUPPORT_VERSION} --package rollout --distribution unstable --urgency low --changelog rollout_debian/changelog ${BUILDNOTE}
	@cp -Rp rollout_debian dist/rollout-${PURE_SUPPORT_VERSION}/debian
	@cd dist/rollout-${PURE_SUPPORT_VERSION} && TARGET_VERSION=${PURE_SUPPORT_VERSION} dpkg-buildpackage -b -uc
	@rm -rf dist/rollout-*/
	@echo ${PURE_SUPPORT_VERSION} > dist/VERSION

rollout_source:
	@TARGET_VERSION=${PURE_SUPPORT_VERSION} python2.7 rollout_setup.py sdist

