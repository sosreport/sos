#!/usr/bin/python
"""
setup.py - Setup package with the help from Python's DistUtils and friends.
"""
from distutils.core import setup, Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build
from distutils.command.install_data import install_data as _install_data
from distutils.command.install_lib import install_lib as _install_lib
from distutils.command.install import install as _install
from unittest import TextTestRunner, TestLoader
from glob import glob
from os.path import splitext, basename, join as pjoin
import os, sys

locale = None
builddir = None

data_files = [ ('/etc', [ 'sos.conf']), 
    ('share/sos/', ['gpgkeys/rhsupport.pub']),
    ('share/man/man1', ['man/en/sosreport.1'])]


class refresh_translations(Command):
    user_options = []
    description = "Regenerate POT file and merge with current translations."
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass

    def run(self):
        # generate POT file
        files = [ "sos/*.py" ]
        pot_cmd = "xgettext --language=Python -o po/sos.pot"
        for f in files:
            pot_cmd += " %s " % f
        os.system(pot_cmd)

        # merge new template with existing translations
        for po in glob.glob(os.path.pjoin(os.getcwd(), 'po', '*.po')):
            os.system("msgmerge -U po/%s po/sos.pot" %
                      os.path.basename(po))

class sdist(_sdist):
    """ updates man pages """
    def run(self):
        self._update_manpages()
        _sdist.run(self)

    def _update_manpages(self):
        if os.system("make -C man/en"):
            raise RuntimeError("Couldn't generate man pages.")
        
class build(_build):
    """ compile i18n files """
    def run(self):
        global builddir
        if not os.path.exists("build/po"):
            os.makedirs("build/po")

        for filename in glob(pjoin(os.getcwd(), 'po', '*.po')):
            filename = os.path.basename(filename)
            lang = os.path.basename(filename)[0:len(filename)-3]
            if not os.path.exists("build/po/%s" % lang):
                os.makedirs("build/po/%s" % lang)
            newname = "build/po/%s/sos.mo" % lang

            print "Building %s from %s" % (newname, filename)
            os.system("msgfmt po/%s -o %s" % (filename, newname))

        _build.run(self)
        builddir = self.build_lib
        
class install(_install):
    """ extract install base for locale install """
    def finalize_options(self):
        global locale
        _install.finalize_options(self)
        locale = self.install_base + "/share/locale"
        
class install_lib(_install_lib):
    """ custom install_lib command to place locale location into library"""

    def run(self):
        for initfile in [ "sos/__init__.py" ]:
            cmd =  "cat %s | " % initfile
            cmd += """sed -e "s,::LOCALEDIR::,%s," > """ % locale
            cmd += "%s/%s" % (builddir, initfile)
            os.system(cmd)

        _install_lib.run(self)
                                                            
class install_data(_install_data):
    """ custom install_data command to prepare i18n/docs files for install"""
    def run(self):
        dirlist = os.listdir("build/po")
        for lang in dirlist:
            if lang != "." and lang != "..":
                install_path = "share/locale/%s/LC_MESSAGES/" % lang
                src_path = "build/po/%s/sos.mo" % lang
                print "Installing %s to %s" % (src_path, install_path)
                toadd = (install_path, [src_path])
                # Add these to the datafiles list
                data_files.append(toadd)

class TestBaseCommand(Command):
    user_options = []

    def initialize_options(self):
        self.debug = 0
        self._testfiles = []
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        tests = TestLoader().loadTestsFromNames(self._testfiles)
        t = TextTestRunner(verbosity = 1)

        result = t.run(tests)
        if len(result.failures) > 0 or len(result.errors) > 0:
            sys.exit(1)
        else:
            sys.exit(0)

class TestSOS(TestBaseCommand):
    description = "Runs unittest"
    user_options = TestBaseCommand.user_options + \
                   [("testfile=", None, "Specify test to run"),]

    def initialize_options(self):
        TestBaseCommand.initialize_options(self)
        self.testfile = None

    def finalize_options(self):
        TestBaseCommand.finalize_options(self)

    def run(self):
        """ find all tests """
        testfiles = []
        for t in glob(pjoin(self._dir, 'tests', '*.py')):
            if self.testfile:
                base = os.path.basename(t)
                check = os.path.basename(self.testfile)
                if base != check and base != (check + ".py"):
                    continue
            testfiles.append('.'.join(['tests',splitext(basename(t))[0]]))

        self._testfiles = testfiles
        TestBaseCommand.run(self)

setup(
    name = 'sos',
    version = '1.9',
    author = 'Adam Stokes',
    author_email = 'astokes@fedoraproject.org',
    url = 'http://fedorahosted.org/sos',
    description = 'SOS - son of sysreport',
    packages = ['sos'],
    scripts = ["sosreport"],
    data_files = data_files,
    cmdclass = {
        'test': TestSOS,
        'sdist': sdist, 'build' : build,
        'install_data' : install_data,
        'install_lib' : install_lib,
        'install' : install,
        'refresh_translations' : refresh_translations}
)

