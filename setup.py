"""Setup configuration and dependencies for the Photon library."""

from setuptools import setup

# These console_scripts will go into the deb package for purelogs/penguin/fuse
commands = [
    # Photon scripts
    # 'check_sas_cabling = photon.tools.hardware.check_sas_cabling:main',
    'cisco_mock_cli = photon.tools.connectivity.cisco_mock_cli:main',
    'devinfo = photon.tools.mockery.dev_info:main',
    'evac_checks = photon.tools.space.evac_checks:main',
    'new_get_iom_reboot_times = photon.tools.hardware.get_iom_reboot_times:main',
    'mce_check = photon.tools.health_checks.mce_checks:main',
    'mr_cisco = photon.tools.connectivity.mr_cisco:main',
    'perf_stats = photon.tools.performance.perf_stats:main',
    'shelf_evac_checks = photon.tools.space.evac_checks:main',
]


# Modules in these packages will go into the deb package for purelogs/penguin/fuse
packages = [
    'photon',
    'photon.backend',
    'photon.backend.cisco',
    'photon.backend.pure',
    'photon.backend.pure.cli',
    'photon.backend.pure.configuration',
    'photon.backend.pure.insights',
    'photon.backend.pure.iris',
    'photon.backend.pure.logs',
    'photon.backend.pure.middleware',
    'photon.backend.pure.mr_tunable',
    'photon.backend.pure.pure1',
    'photon.backend.pure.warehouse',
    'photon.backend.vmware',
    'photon.backend.vmware.configuration',
    'photon.backend.vmware.logs',
    'photon.benchmarks',
    'photon.lib',
    'photon.report',
    'photon.report.configuration',
    'photon.tools',
    'photon.tools.aws',
    'photon.tools.bash',
    'photon.tools.cloudassist',
    'photon.tools.connectivity',
    'photon.tools.hardware',
    'photon.tools.health_checks',
    'photon.tools.host_analysis',
    'photon.tools.mockery',
    'photon.tools.performance',
    'photon.tools.remote_assist',
    'photon.tools.replication',
    'photon.tools.space',
    'photon.tools.standalone',
]

# Additional configuration and data files installed with the package
package_data = {
    'photon': ['settings.ini'],
    'photon.backend.pure.configuration': ['field_index.ini'],
    'photon.backend.pure.pure1': ['pure1_fields.json'],
    'photon.report.configuration': ['metric_index.ini'],
}

requirements = [
    'configparser==3.5.0',
    'future==0.16.0',
    'jira==1.0.10',
    'mock==2.0.0',
    'packaging==16.8',
    'pandas==0.23.3',
    'plotly==2.5.1',
    'psutil==5.4.3',
    'psycopg2-binary',
    'python-dateutil==2.6.1',
    'pytz==2018.4',
    'requests[security]==2.18.4',
    'scipy==1.1.0',
    'SQLAlchemy==1.2.7',
    'tabulate==0.8.2',
    'texttable==1.2.1',
    'ujson==1.35',
]

setup(name              = 'photon',
      version           = '1.2.0',
      description       = 'this is photon',
      packages          = packages,
      package_data      = package_data,
      entry_points      = { 'console_scripts': commands },
      install_requires  = requirements
      )
