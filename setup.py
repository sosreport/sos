#!/usr/bin/python
"""
setup.py - Setup package with the help from Python's DistUtils
"""

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    from setuptools import setup, find_packages

import glob
import os

data_files = [ ('/etc', [ 'sos.conf']), 
    ('/usr/sbin', ['sosreport', 'extras/sysreport/sysreport.legacy']), 
    ('/usr/bin', ['extras/rh-upload']),
    ('/usr/share/sos/',['gpgkeys/rhsupport.pub']),
    ('/usr/share/sysreport', ['extras/sysreport/text.xsl', 'extras/sysreport/functions', 'extras/sysreport/sysreport-fdisk']), 
    ('/usr/share/man/man1', ['sosreport.1.gz']),
    ]

lang_files = glob.glob('po/*/sos.mo')
for i18n in lang_files:
    topdir, basedir, fname = i18n.split('/')
    data_files.append(('/usr/share/locale/%s/LC_MESSAGES' % (basedir,) , [i18n]))

test_sub_dirs = []
def test_files_add(dir='test',test_dir='/usr/share/sos'):
    """ test file dir addition """
    test_sub_dirs.append(dir)
    for root, dirs, fname in os.walk(dir):
        if '.svn' in dirs:
            dirs.remove('.svn')
        for name in dirs:
            test_sub_dirs.append(os.path.join(dir,name))
    for dr in test_sub_dirs:
        files = os.listdir(dr)
        for f in files:
            if os.path.isfile(os.path.join(dr,f)):
                data_files.append((os.path.join(test_dir,dr),[os.path.join(dr,f)]))


test_files_add()

test_requirements = ['nose >= 0.10']

setup(
    name = 'sos',
    version = '1.9',
    author = 'Adam Stokes',
    author_email = 'ajs@redhat.com',
    url = 'http://fedorahosted.org/sos',
    description = 'SOS - son of sysreport',
    packages = find_packages(exclude=['test*']),
    include_package_data = True,
    data_files = data_files,
    test_suite = "test",
    tests_require = test_requirements,
    extras_require = {
        'docs' : ['sphinx >= 0.5'],
    },
)

