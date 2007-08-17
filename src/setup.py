"""
setup.py - Setup package with the help from Python's DistUtils
"""

from distutils.core import setup

setup(
	name = 'sos',
	packages = ['sos', 'sos.plugins'],
	scripts = [],
	package_dir = {'': 'lib',},
	data_files = [ ('/usr/sbin', ['sosreport', 'extras/sysreport/sysreport.legacy']), ('/usr/bin', ['extras/rh-upload-core']), ('/usr/share/sysreport', ['extras/sysreport/text.xsl', 'extras/sysreport/functions', 'extras/sysreport/sysreport-fdisk']), ('/usr/share/man/man1', ['sosreport.1']), ('/usr/share/locale/en', []), ('/usr/share/locale/it', []), ('/usr/share/locale/en/LC_MESSAGES', ['locale/en/LC_MESSAGES/sos.mo']), ('/usr/share/locale/it/LC_MESSAGES', ['locale/it/LC_MESSAGES/sos.mo']), ('/usr/share/locale/fr/LC_MESSAGES', ['locale/fr/LC_MESSAGES/sos.mo']), ('/usr/share/locale/ar/LC_MESSAGES', ['locale/ar/LC_MESSAGES/sos.mo'])
	]
)
