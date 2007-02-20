"""
setup.py - Setup package with the help from Python's DistUtils
"""

from distutils.core import setup
from ConfigParser import ConfigParser
import sys,os,time

# change release in spec file along with this version string
setup(
	name = 'sos',
	version = '1.3',
	description = 'System Support Tools',
	long_description = """Sos is a set of tools that gathers information about system
	hardware and configuration. The information can then be used for
	diagnostic purposes and debugging. Sos is commonly used to help
	support technicians and developers.""",
	author = 'Steve Conklin, et al.',
	author_email = 'sconklin@redhat.com',
	url = 'http://sos.108.redhat.com/',
	packages = ['sos', 'sos.plugins'],
	scripts = [],
	package_dir = {'': 'lib',},
	# data_files is broken for building dists, works for installs
	data_files = [('/usr/sbin', ['sosreport']), ('/usr/share/man/man1', ['sosreport.1']) ]
)
