#
# A simple setup script for creating a Windows service.
#
# Installing the service is done with the option --install <Name> and
# uninstalling the service is done with the option --uninstall <Name>. The
# value for <Name> is intended to differentiate between different invocations
# of the same service code -- for example for accessing different databases or
# using different configuration files.
#

import sys
import shutil
from cx_Freeze import setup, Executable
import os
import platform

version_file = os.path.join(os.path.dirname(__file__),
                            '..',
                            'VERSION')
version = open(version_file, 'r').readline().strip()

if not version[-1].isdigit():
    x = version.rsplit('.', 1)
    version = x[0]

sys.argv += ['-p', 'xml']

includefiles = [('var/log/ncpa_listener.log', 'var/log/ncpa_listener.log'),
                ('var/log/ncpa_passive.log', 'var/log/ncpa_passive.log'),
                ('listener/templates', 'listener/templates'),
                ('listener/static', 'listener/static'),
                'etc',
                'plugins',
                'passive']

includes = ['xml.dom.minidom']

includefiles += [('build_resources/LicenseAgreement.txt', 'build_resources/LicenseAgreement.txt'),
                 ('build_resources/nsis_listener_options.ini', 'build_resources/nsis_listener_options.ini'),
                 ('build_resources/nsis_passive_options.ini', 'build_resources/nsis_passive_options.ini'),
                 ('build_resources/nsis_passive_checks.ini', 'build_resources/nsis_passive_checks.ini'),
                 ('build_resources/ncpa.ico', 'build_resources/ncpa.ico'),
                 ('build_resources/nagios_installer.bmp', 'build_resources/nagios_installer.bmp'),
                 ('build_resources/nagios_installer_logo.bmp', 'build_resources/nagios_installer_logo.bmp')]

buildOptions = dict(includes=includes + ["ncpa_windows"],
                    include_files=includefiles)

listener = Executable("ncpa_windows_listener.py", 
                      base = "Win32Service",
                      targetName = "ncpa_listener.exe",
                      icon = "build_resources/ncpa.ico")

passive = Executable("ncpa_windows_passive.py",
                     base = "Win32Service",
                     targetName = "ncpa_passive.exe",
                     icon = "build_resources/ncpa.ico")

setup(name = "NCPA",
      version = version,
      description = "Nagios Cross-Platform Agent",
      executables = [listener, passive],
      options = dict(build_exe = buildOptions),
)

if platform.architecture()[0].lower() == '32bit':
    os.rename(os.path.join('build', 'exe.win32-3.5'), os.path.join('build', 'NCPA'))
elif platform.architecture()[0].lower() == '64bit':
    os.rename(os.path.join('build', 'exe.win-amd64-3.5'), os.path.join('build', 'NCPA'))
else:
    print("unhandled architecture")
    sys.exit(1)

shutil.copy(u'build_resources/ncpa.nsi', u'build/')
