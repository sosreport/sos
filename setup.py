#!/usr/bin/python
"""
setup.py - Setup package with the help from Python's DistUtils and friends.
"""
from distutils.core import setup
import os, sys

setup(
    name = 'sos',
    version = '1.9',
    author = 'Adam Stokes',
    author_email = 'astokes@fedoraproject.org',
    url = 'http://fedorahosted.org/sos',
    description = 'SOS - son of sysreport',
    packages = ['sos','sos.plugins'],
    scripts = ["sosreport", "extras/rh-upload"],
    data_files = data_files,
)

