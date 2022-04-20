#!/usr/bin/env python

from distutils.core import setup
from distutils.command.build import build
from distutils.command.install_data import install_data
from distutils.dep_util import newer
from distutils.log import error

import glob
import os
import re
import subprocess
import sys

from sos import __version__ as VERSION

PO_DIR = 'po'
MO_DIR = os.path.join('build', 'mo')

class BuildData(build):
  def run(self):
    build.run(self)
    for po in glob.glob(os.path.join(PO_DIR, '*.po')):
      lang = os.path.basename(po[:-3])
      mo = os.path.join(MO_DIR, lang, 'sos.mo')

      directory = os.path.dirname(mo)
      if not os.path.exists(directory):
        os.makedirs(directory)

      if newer(po, mo):
        try:
          rc = subprocess.call(['msgfmt', '-o', mo, po])
          if rc != 0:
            raise Warning("msgfmt returned %d" % (rc,))
        except Exception as e:
          error("Failed gettext.")
          sys.exit(1)

class InstallData(install_data):
  def run(self):
    self.data_files.extend(self._find_mo_files())
    install_data.run(self)

  def _find_mo_files(self):
    data_files = []
    for mo in glob.glob(os.path.join(MO_DIR, '*', 'sos.mo')):
      lang = os.path.basename(os.path.dirname(mo))
      dest = os.path.join('share', 'locale', lang, 'LC_MESSAGES')
      data_files.append((dest, [mo]))
    return data_files

  # Workaround https://bugs.python.org/issue644744
  def copy_file (self, filename, dirname):
    (out, _) = install_data.copy_file(self, filename, dirname)
    # match for man pages
    if re.search(r'/man/man\d/.+\.\d$', out):
      return (out+".gz", _)
    return (out, _)

cmdclass = {'build': BuildData, 'install_data': InstallData}
command_options = {}
try:
    from sphinx.setup_command import BuildDoc
    cmdclass['build_sphinx'] = BuildDoc
    command_options={
        'build_sphinx': {
            'project': ('setup.py', 'sos'),
            'version': ('setup.py', VERSION),
            'source_dir': ('setup.py', 'docs')
        }
    }
except Exception:
    print("Unable to build sphinx docs - module not present. Install sphinx "
          "to enable documentation generation")

setup(
    name='sos',
    version=VERSION,
    description=("""A set of tools to gather troubleshooting"""
                 """ information from a system."""),
    author='Bryn M. Reeves',
    author_email='bmr@redhat.com',
    maintainer='Jake Hunsaker',
    maintainer_email='jhunsake@redhat.com',
    url='https://github.com/sosreport/sos',
    license="GPLv2+",
    scripts=['bin/sos', 'bin/sosreport', 'bin/sos-collector'],
    data_files=[
        ('share/man/man1', ['man/en/sosreport.1', 'man/en/sos-report.1',
                            'man/en/sos.1', 'man/en/sos-collect.1',
                            'man/en/sos-collector.1', 'man/en/sos-clean.1',
                            'man/en/sos-mask.1', 'man/en/sos-help.1']),
        ('share/man/man5', ['man/en/sos.conf.5']),
        ('share/licenses/sos', ['LICENSE']),
        ('share/doc/sos', ['AUTHORS', 'README.md']),
        ('config', ['sos.conf'])
    ],
    packages=[
        'sos', 'sos.presets', 'sos.presets.redhat', 'sos.policies',
        'sos.policies.distros', 'sos.policies.runtimes',
        'sos.policies.package_managers', 'sos.policies.init_systems',
        'sos.report', 'sos.report.plugins', 'sos.collector',
        'sos.collector.clusters', 'sos.collector.transports', 'sos.cleaner',
        'sos.cleaner.mappings', 'sos.cleaner.parsers', 'sos.cleaner.archives',
        'sos.help'
    ],
    cmdclass=cmdclass,
    command_options=command_options,
    requires=['pexpect', 'python_magic', 'pyyaml']
    )


# vim: set et ts=4 sw=4 :
