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

setup(name='sos',
      version=VERSION,
      description=("""A set of tools to gather troubleshooting"""
                   """ information from a system."""),
      author='Bryn M. Reeves',
      author_email='bmr@redhat.com',
      url='https://github.com/sosreport/sos',
      license="GPLv2+",
      scripts=['sosreport'],
      data_files=[
        ('share/man/man1', ['man/en/sosreport.1']),
        ('share/man/man5', ['man/en/sos.conf.5']),
        ],
      packages=['sos', 'sos.plugins', 'sos.policies'],
      cmdclass={'build': BuildData, 'install_data': InstallData},
      requires=['six', 'futures'],
     )


# vim: set et ts=4 sw=4 :
