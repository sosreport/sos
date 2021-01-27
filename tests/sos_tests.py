# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from avocado.core.exceptions import TestSkipError
from avocado import Test
from avocado.utils import archive, process
from fnmatch import fnmatch

import glob
import json
import os
import pickle
import socket
import re

SOS_TEST_DIR = os.path.dirname(os.path.realpath(__file__))
SOS_BIN = os.path.realpath(os.path.join(SOS_TEST_DIR, '../bin/sos'))


def skipIf(cond, message=None):
    def decorator(function):
        def wrapper(self, *args, **kwargs):
            if callable(cond):
                if cond(self):
                    raise TestSkipError(message)
            elif cond:
                raise TestSkipError(message)
        return wrapper
    return decorator


class BaseSoSTest(Test):
    """Base class for all our test classes to build off of.

    Subclasses avocado.Test and then adds wrappers and helper methods that are
    needed across sos components. Component specific test classes should in
    turn subclass ``BaseSoSTest`` rather than ``avocado.Test`` directly
    """

    _klass_name = None
    _tmpdir = None
    sos_cmd = ''

    @property
    def klass_name(self):
        if not self._klass_name:
            self._klass_name = os.path.basename(__file__) + '.' + self.__class__.__name__
        return self._klass_name

    @property
    def tmpdir(self):
        if not self._tmpdir:
            self._tmpdir = os.getenv('AVOCADO_TESTS_COMMON_TMPDIR') + self.klass_name
        return self._tmpdir

    def generate_sysinfo(self):
        """Collects some basic information about the system for later reference
        in individual tests
        """
        sysinfo = {}

        # get kernel modules
        mods = []
        _out = process.run('lsmod').stdout.decode()
        for line in _out.splitlines()[1:]:
            mods.append(line.split()[0])
        # this particular kmod is both innocuous and unpredictable in terms of
        # pre-loading even within the same distribution. For now, turn a blind
        # eye to it with regards to the "no new kmods loaded" perspective
        if 'binfmt_misc' in mods:
            mods.remove('binfmt_misc')
        sysinfo['modules'] = sorted(mods, key=str.lower)

        # get networking info
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)
        sysinfo['networking'] = {}
        sysinfo['networking']['hostname'] = hostname
        sysinfo['networking']['ip_addr'] = ip_addr

        return sysinfo

    def _write_file_to_tmpdir(self, fname, content):
        """Write the given content to fname within the test's tmpdir
        """
        fname = os.path.join(self.tmpdir, fname)
        if isinstance(content, bytes):
            content = content.decode()
        with open(fname, 'w') as wfile:
            wfile.write(content)

    def read_file_from_tmpdir(self, fname):
        fname = os.path.join(self.tmpdir, fname)
        with open(fname, 'r') as tfile:
            return tfile.read()
        return ''

    def _write_sysinfo(self, fname):
        """Get the current state of sysinfo and write it into our shared
        tempdir so it can be loaded in setUp() later

        :param fname:  The name of the file to be written in the tempdir
        :type fname: ``str``
        """
        sysinfo = self.generate_sysinfo()
        self._write_file_to_tmpdir(fname, json.dumps(sysinfo))

    def _read_sysinfo(self, fname):
        sysinfo = {}
        content = self.read_file_from_tmpdir(fname)
        if content:
            sysinfo = json.loads(content)
        return sysinfo

    def set_pre_sysinfo(self):
        self._write_sysinfo('pre_sysinfo')

    def get_pre_sysinfo(self):
        return self._read_sysinfo('pre_sysinfo')

    def set_post_sysinfo(self):
        self._write_sysinfo('post_sysinfo')

    def get_post_sysinfo(self):
        return self._read_sysinfo('post_sysinfo')

    def get_sysinfo(self):
        sinfo = {
            'pre': self.get_pre_sysinfo(),
            'post': self.get_post_sysinfo()
        }
        return sinfo

    def assertFileExists(self, fname):
        """Asserts that fname exists on the filesystem"""
        assert os.path.exists(fname), "%s does not exist" % fname

    def assertFileNotExists(self, fname):
        """Asserts that fname does not exist on the filesystem"""
        assert not os.path.exists(fname), "%s exists" % fname
        

class BaseSoSReportTest(BaseSoSTest):
    """This is the class to use for building sos report tests with.

    An instance of this test is expected to set at minimum a ``sos_cmd`` class
    attribute that represets the options handed to a specific execution of an
    sos command. This should be anything following ``sos report --batch``.

    """

    archive = None
    _manifest = None


    @property
    def manifest(self):
        if self._manifest is None:
            try:
                content = self.read_file_from_tmpdir(self.get_name_in_archive('sos_reports/manifest.json'))
                self._manifest = json.loads(content)
            except Exception:
                self._manifest = ''
                self.warn('Could not load manifest for test')
        return self._manifest

    def _extract_archive(self, arc_path):
        """Extract an archive to the temp directory
        """
        _extract_path = self._get_extracted_tarball_path()
        try:
            archive.extract(arc_path, _extract_path)
            self.archive_path = self._get_archive_path()
        except Exception as err:
            self.cancel("Could not extract archive: %s" % err)

    def _get_extracted_tarball_path(self):
        """Based on the klass id setup earlier, provide a name to extract the
        archive to within the tmpdir
        """
        return os.path.join(self.tmpdir, "sosreport-%s" % self.__class__.__name__)
        

    def _execute_sos_cmd(self):
        """Run the sos command for this test case, and extract it
        """
        _cmd = '%s report --batch --tmp-dir %s %s'
        exec_cmd = _cmd % (SOS_BIN, self.tmpdir, self.sos_cmd)
        self.cmd_output = process.run(exec_cmd, timeout=300)
        with open(os.path.join(self.tmpdir, 'output'), 'wb') as pfile:
            pickle.dump(self.cmd_output, pfile)
        self.cmd_output.stdout = self.cmd_output.stdout.decode()
        self.cmd_output.stderr = self.cmd_output.stderr.decode()
        self.archive = re.findall('/.*sosreport-.*tar.*', self.cmd_output.stdout)[-1]
        if self.archive:
            self._extract_archive(self.archive)
        

    def _setup_tmpdir(self):
        if not os.path.isdir(self.tmpdir):
            os.mkdir(self.tmpdir)

    def _get_archive_path(self):
        return glob.glob(self._get_extracted_tarball_path() + '/sosreport*')[0]

    def setup_mocking(self):
        """Since we need to use setUp() in our overrides of avocado.Test,
        provide an alternate method for test cases that subclass BaseSoSTest
        to use.
        """
        pass

    def setUp(self):
        """Execute and extract the sos report to our temporary location, then
        call sos_setup() for individual test case setup and/or mocking.
        """
        # check to prevent multiple setUp() runs
        if not os.path.isdir(self.tmpdir):
            # setup our class-shared tmpdir
            self._setup_tmpdir()

            # do our mocking called for in sos_setup
            self.setup_mocking()

            # gather some pre-execution information
            self.set_pre_sysinfo()

            # run the sos command for this test case
            self._execute_sos_cmd()
            self.set_post_sysinfo()
        else:
            with open(os.path.join(self.tmpdir, 'output'), 'rb') as pfile:
                self.cmd_output = pickle.load(pfile)
            if isinstance(self.cmd_output.stdout, bytes):
                self.cmd_output.stdout = self.cmd_output.stdout.decode()
                self.cmd_output.stderr = self.cmd_output.stderr.decode()
            for f in os.listdir(self.tmpdir):
                if fnmatch(f, 'sosreport*.tar.??'):
                    self.archive = os.path.join(self.tmpdir, f)
                    break
        self.sysinfo = self.get_sysinfo()
        self.archive_path = self._get_archive_path()

    def get_name_in_archive(self, fname):
        """Get the full path to fname as it (would) exist in the archive
        """
        return os.path.join(self.archive_path, fname.lstrip('/'))

    def get_file_content(self, fname):
        """Reads the content of fname from within the archive and returns it

        :param fname:  The name of the file
        :type fname:  ``str``

        :returns: Content of fname
        :rtype: ``str``
        """
        content = ''
        with open(self.get_name_in_archive(fname), 'r') as gfile:
            content = gfile.read()
        return content

    def assertFileCollected(self, fname):
        """Ensure that a given fname is in the extracted archive if it exists
        on the host system

        :param fname:  The name of the file within the archive
        :type fname:  ``str``
        """
        if os.path.exists(fname):
            self.assertFileExists(self.get_name_in_archive(fname))
        assert True

    def assertFileNotCollected(self, fname):
        """Ensure that a given fname is NOT in the extracted archive

        :param fname:  The name of the file within the archive
        :type fname:  ``str``
        """
        self.assertFileNotExists(self.get_name_in_archive(fname))

    def assertFileGlobInArchive(self, fname):
        """Ensure that at least one file in the archive matches a given fname
        glob

        :param fname:  The glob to match filenames of
        :type fname:  ``str``
        """
        files = glob.glob(os.path.join(self.archive_path, fname.lstrip('/')))
        assert files, "No files matching %s found" % fname

    def assertFileGlobNotInArchive(self, fname):
        """Ensure that there are NO files in the archive matching a given fname
        glob

        :param fname:  The glob to match filename(s) of
        :type fname:  ``str``
        """
        files = glob.glob(os.path.join(self.tmpdir, fname.lstrip('/')))
        self.log.debug(files)
        assert not files, "Found files in archive matching %s: %s" % (fname, files)

    def assertFileHasContent(self, fname, content):
        """Ensure that the given file fname contains the given content

        :param fname:  The name of the file
        :type fname:  ``str``

        :param content:  The content to match
        :type content: ``str``
        """
        matched = False
        fname = self.get_name_in_archive(fname)
        self.assertFileExists(fname)
        with open(fname, 'r') as lfile:
            _contents = lfile.read()
            for line in _contents.splitlines():
                if re.match(".*%s.*" % content, line, re.I):
                    matched = True
                    break
        assert matched, "Content '%s' does not appear in %s\n%s" % (content, fname, _contents)

    def assertFileNotHasContent(self, fname, content):
        """Ensure that the file file fname does NOT contain the given content

        :param fname:  The name of the file
        :type fname:  ``str``

        :param content:  The content to (not) match
        :type content:   ``str``
        """
        matched = False
        fname = self.get_name_in_archive(fname)
        with open(fname, 'r') as mfile:
            for line in mfile.read().splitlines():
                if re.match(".*%s.*" % content, line, re.I):
                    matched = True
                    break
        assert not matched, "Content '%s' appears in file %s" % (content, fname)

    def assertSosLogContains(self, content):
        """Ensure that the given content string exists in sos.log
        """
        self.assertFileHasContent('sos_logs/sos.log', content)

    def assertSosLogNotContains(self, content):
        """Ensure that the given content string does NOT exist in sos.log
        """
        self.assertFileNotHasContent('sos_logs/sos.log', content)

    def assertOutputContains(self, content):
        """Ensure that stdout did contain the given content string

        :param content:  The string that should not be in stdout
        :type content:  ``str``
        """
        assert content in self.cmd_output.stdout, 'Content string not in output'

    def assertOutputNotContains(self, content):
        """Ensure that stdout did NOT contain the given content string

        :param content:  The string that should not be in stdout
        :type content:  ``str``
        """
        assert not re.match(".*%s.*" % content, self.cmd_output.stdout), "String '%s' present in stdout" % content

    def assertPluginIncluded(self, plugin):
        """Ensure that the specified plugin did run for the sos execution

        Note that this relies on manifest.json being successfully created

        :param plugin:  The name of the plugin
        :type plugin:  `` str``
        """
        if not self.manifest:
            self.error("No manifest found, cannot check for %s execution" % plugin)
        assert plugin in self.manifest['components']['report']['plugins'].keys(), 'Plugin not recorded in manifest'

    def assertPluginNotIncluded(self, plugin):
        """Ensure that the specified plugin did NOT run for the sos execution
        Note that this relies on manifest.json being successfully created

        :param plugin:  The name of the plugin
        :type plugin:  `` str``
        """
        if not self.manifest:
            self.error("No manifest found, cannot check for %s execution" % plugin)
        assert plugin not in self.manifest['components']['report']['plugins'].keys(), 'Plugin is recorded in manifest'

    def assertOnlyPluginsIncluded(self, plugins):
        """Ensure that only the specified plugins are in the manifest

        :param plugins:  The plugin names
        :type plugins:  ``str`` or ``list`` of strings
        """
        if not self.manifest:
            self.error("No manifest found, cannot check for %s execution" % plugins)
        if isinstance(plugins, str):
            plugins = [plugins]
        _executed = self.manifest['components']['report']['plugins'].keys()

        # test that all requested plugins did run
        for i in plugins:
            assert i in _executed, "Requested plugin '%s' did not run" % i

        # test that no unrequested plugins ran
        for j in _executed:
            assert j in plugins, "Unrequested plugin '%s' ran as well" % j

class StageOneReportTest(BaseSoSReportTest):
    """This is the test class to subclass for all Stage One (no mocking) tests
    within the sos test suite.

    In addition to any test_* methods defined in the test cases that subclass
    this, the methods defined here will ALSO run, to ensure basic consistency
    across test cases

    NOTE: You MUST replace the following line in the docstring of your own
    test cases, as otherwise the test will be disabled. This line is here to
    prevent this base class from being treated as a valid test case. Also, if
    you add any tests to this base class, make sure to add a line such as
    ':avocado: tags=stageone' to ensure the base tests run with new test cases

    :avocado: disable
    :avocado: tags=stageone
    """

    sos_cmd = ''

    def test_archive_created(self):
        """Ensure that the archive tarball was created and has the right owner

        :avocado: tags=stageone
        """
        self.assertFileExists(self.archive)
        self.assertTrue(os.stat(self.archive).st_uid == 0)

    def test_no_new_kmods_loaded(self):
        """Ensure that no additional kernel modules have been loaded during an
        execution of a test

        :avocado: tags=stageone
        """
        self.assertCountEqual(self.sysinfo['pre']['modules'],
                              self.sysinfo['post']['modules'])

    def test_archive_has_sos_dirs(self):
        """Ensure that we have the expected directory layout with in the
        archive

        :avocado: tags=stageone
        """
        self.assertFileCollected('sos_commands')
        self.assertFileCollected('sos_logs')

    def test_manifest_created(self):
        """
        :avocado: tags=stageone
        """
        self.assertFileCollected('sos_reports/manifest.json')

    @skipIf(lambda x: '--no-report' in x.sos_cmd, '--no-report used in command')
    def test_html_reports_created(self):
        """
        :avocado: tags=stageone
        """
        self.assertFileCollected('sos_reports/sos.html')

    def test_no_exceptions_during_execution(self):
        """
        :avocado: tags=stageone
        """
        self.assertSosLogNotContains('caught exception in plugin')
        self.assertFileGlobNotInArchive('sos_logs/*-plugin-errors.txt')

    def test_no_ip_changes(self):
        """
        :avocado: tags=stageone
        """
        # I.E. make sure we didn't cause any NIC flaps that for some reason
        # resulted in a new primary IP address. TODO: build this out to make
        # sure this IP is still bound to the same NIC
        self.assertEqual(self.sysinfo['pre']['networking']['ip_addr'],
                         self.sysinfo['post']['networking']['ip_addr'])
