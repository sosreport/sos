"""
setup.py - Setup package with the help from Python's DistUtils
"""

from distutils.core import setup
import glob


data_files = [ ('/etc', [ 'sos.conf']), 
    ('/usr/sbin', ['sosreport', 'extras/sysreport/sysreport.legacy']), 
    ('/usr/bin', ['extras/rh-upload']),
    ('/usr/share/sos/',['gpgkeys/rhsupport.pub']),
    ('/usr/share/sysreport', ['extras/sysreport/text.xsl', 'extras/sysreport/functions', 'extras/sysreport/sysreport-fdisk']), 
    ('/usr/share/man/man1', ['sosreport.1.gz']),
    ]

test_dir = '/usr/share/sos/tests'
test_files = glob.glob('tests/*')
data_files.append((test_dir,[file for file in test_files]))

lang_files = glob.glob('po/*/sos.mo')
for i18n in lang_files:
    topdir, basedir, fname = i18n.split('/')
    data_files.append(('/usr/share/locale/%s/LC_MESSAGES' % (basedir,) ,[i18n]))

setup(
    name = 'sos',
    version = '1.8',
    author = 'Adam Stokes',
    author_email = 'ajs@redhat.com',
    url = 'http://fedorahosted.org/sos',
    description = 'SOS - son of sysreport',
    packages = ['sos', 'sos.plugins'],
    scripts = [],
    package_dir = {'': 'lib',},
    data_files = data_files,
)
