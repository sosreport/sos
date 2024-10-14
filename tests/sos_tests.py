# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from fnmatch import fnmatch

import glob
import inspect
import json
import os
import pickle
import shutil
import socket
import re

from avocado.core.exceptions import TestSkipError
from avocado.core.output import LOG_UI
from avocado import Test
from avocado.utils import archive, process, distro, software_manager
from avocado.utils.cpu import get_arch
from avocado.utils.software_manager import distro_packages

SOS_TEST_DIR = os.path.dirname(os.path.realpath(__file__))
SOS_REPO_ROOT = os.path.realpath(os.path.join(SOS_TEST_DIR, '../'))
SOS_PLUGIN_DIR = os.path.realpath(
    os.path.join(SOS_REPO_ROOT, 'sos/report/plugins'))
SOS_TEST_DATA_DIR = os.path.realpath(os.path.join(SOS_TEST_DIR, 'test_data'))
SOS_TEST_BIN = os.path.realpath(os.path.join(SOS_TEST_DIR, '../bin/sos'))

RH_DIST = ['rhel', 'centos', 'fedora', 'centos-stream']
UBUNTU_DIST = ['Ubuntu', 'debian']


def skipIf(cond, message=None):
    # pylint: disable=unused-argument
    def decorator(function):
        def wrapper(self, *args, **kwargs):
            if callable(cond):
                if cond(self):
                    raise TestSkipError(message)
            elif cond:
                raise TestSkipError(message)
        return wrapper
    return decorator


# pylint: disable=unused-argument
def redhat_only(tst):
    def wrapper(func):
        if distro.detect().name not in RH_DIST:
            raise TestSkipError('Not running on a Red Hat distro')
    return wrapper


# pylint: disable=unused-argument
def ubuntu_only(tst):
    def wrapper(func):
        if distro.detect().name not in UBUNTU_DIST:
            raise TestSkipError('Not running on a Ubuntu or Debian distro')
    return wrapper


class BaseSoSTest(Test):
    """Base class for all our test classes to build off of.

    Subclasses avocado.Test and then adds wrappers and helper methods that are
    needed across sos components. Component specific test classes should in
    turn subclass ``BaseSoSTest`` rather than ``avocado.Test`` directly
    """

    _klass_name = None
    _tmpdir = None
    _exception_expected = False
    _local_sos_bin = shutil.which('sos') or SOS_TEST_BIN
    sos_cmd = ''
    sos_timeout = 600
    redhat_only = False
    ubuntu_only = False
    end_of_test_case = False
    arch = []

    @property
    def klass_name(self):
        if not self._klass_name:
            self._klass_name = (f"{os.path.basename(__file__)}."
                                f"{self.__class__.__name__}")
        return self._klass_name

    @property
    def tmpdir(self):
        if not self._tmpdir:
            self._tmpdir = (f"{os.getenv('AVOCADO_TESTS_COMMON_TMPDIR')}"
                            f"{self.klass_name}")
        return self._tmpdir

    @property
    def sos_bin(self):
        if self.params.get('TESTLOCAL') == 'true':
            return self._local_sos_bin
        return SOS_TEST_BIN

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

    def _generate_sos_command(self):
        """Based on the specific test class that is subclassing BaseSoSTest,
        perform whatever logic is necessary to create the sos command that will
        be executed
        """
        raise NotImplementedError

    def _execute_sos_cmd(self):
        """Run the sos command for this test case, and extract it
        """
        exec_cmd = self._generate_sos_command()
        try:
            self.cmd_output = process.run(exec_cmd, timeout=self.sos_timeout,
                                          env={'SOS_TEST_LOGS': 'keep'})
        except Exception as err:
            if not hasattr(err, 'result'):
                # can't inspect the exception raised, just bail out
                raise
            if self._exception_expected:
                self.cmd_output = err.result
            else:
                # pylint: disable=no-member
                # We've already checked above for the result attribute for err
                msg = err.result.stderr.decode() or err.result.stdout.decode()
                # a little hacky, but using self.log methods here will not
                # print to console unless we ratchet up the verbosity for the
                # entire test suite, which will become very difficult to read

                # don't flood w/ super verbose logs
                LOG_UI.error(f'ERROR:\n{msg[:8196]}')
                if err.result.interrupted:
                    raise Exception("Timeout exceeded, see output "
                                    "above") from err
                raise Exception("Command failed, see output above: "
                                f"'{err.command.split('bin/')[1]}'") from err
        with open(os.path.join(self.tmpdir, 'output'), 'wb') as pfile:
            pickle.dump(self.cmd_output, pfile)
        self.cmd_output.stdout = self.cmd_output.stdout.decode()
        self.cmd_output.stderr = self.cmd_output.stderr.decode()

    def _setup_tmpdir(self):
        if not os.path.isdir(self.tmpdir):
            os.mkdir(self.tmpdir)

    def _write_file_to_tmpdir(self, fname, content):
        """Write the given content to fname within the test's tmpdir
        """
        fname = os.path.join(self.tmpdir, fname)
        if isinstance(content, bytes):
            content = content.decode()
        with open(fname, 'w', encoding='utf-8') as wfile:
            wfile.write(content)

    def read_file_from_tmpdir(self, fname):
        fname = os.path.join(self.tmpdir, fname)
        try:
            with open(fname, 'r', encoding='utf-8') as tfile:
                return tfile.read()
        except Exception:
            pass
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

    def check_distro_for_enablement(self):
        """Check if the test case is meant only for a specific distro family,
        and if it is and we are not running on that family, skip all the tests
        for that test case.

        This allows us to define distro-specific test classes much the same way
        we can define distro-specific tests _within_ a test class using the
        appropriate decorators. We can't use the decorators for the class
        however due to how avocado catches instantiation exceptions, so instead
        we need to raise the skip exception after instantiation is done.
        """
        if self.redhat_only:
            if self.local_distro not in RH_DIST:
                raise TestSkipError('Not running on a Red Hat distro')
        elif self.ubuntu_only:
            if self.local_distro not in UBUNTU_DIST:
                raise TestSkipError("Not running on a Ubuntu or Debian distro")

    def check_arch_for_enablement(self):
        """
        Check if the test case is meant only for a specific architecture, and
        if it is, that we're also currently running on (one of) those arches.

        This relies on the `arch` class attr, which should be a list. If the
        list is empty, assume all arches are acceptable. Otherwise, raise a
        TestSkipError.
        """
        sys_arch = get_arch()
        if not self.arch or sys_arch in self.arch:
            return True
        raise TestSkipError(f"Unsupported architecture {sys_arch} for test "
                            f"(supports: {self.arch})")

    def setUp(self):
        """Setup the tmpdir and any needed mocking for the test, then execute
        the defined sos command. Ensure that we only run the sos command once
        for every test case, instead of once for every test_* method defined.
        """
        self.local_distro = distro.detect().name
        self.check_distro_for_enablement()
        self.check_arch_for_enablement()
        # check to prevent multiple setUp() runs
        if not os.path.isdir(self.tmpdir):
            # setup our class-shared tmpdir
            self._setup_tmpdir()

            # do mocking called for in stage 2+ tests
            self.setup_mocking()

            # do any pre-execution setup
            self.pre_sos_setup()

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
                if fnmatch(f, '*sosreport*.tar.??'):
                    self.archive = os.path.join(self.tmpdir, f)
                    break
        self.sysinfo = self.get_sysinfo()

    def tearDown(self):
        """If a test being run is the last one defined for a test case, then
        we should remove the extracted tarball directory so that we can upload
        a reasonably sized artifact to the GCE storage bucket if any tests
        fail during the test execution.

        The use of `end_of_test_case` is a bit wonky because we don't have a
        different/more reliable way to identify that a test class has completed
        all tests - mainly because avocado re-initializes the entire class
        for each `test_*` method defined within it.
        """
        if self.end_of_test_case:
            self.post_test_tear_down()
            # remove the extracted directory only if we have the tarball
            if self.archive and os.path.exists(self.archive):
                if os.path.exists(self.archive_path):
                    shutil.rmtree(self.archive_path)

    def post_test_tear_down(self):
        """Called at the end of a test run to ensure that any needed per-test
        cleanup can be done.
        """

    def setup_mocking(self):
        """Since we need to use setUp() in our overrides of avocado.Test,
        provide an alternate method for test cases that subclass BaseSoSTest
        to use.
        """

    def pre_sos_setup(self):
        """Do any needed non-mocking setup prior to the sos execution that is
        called in setUp()
        """

    def assertFileExists(self, fname):
        """Asserts that fname exists on the filesystem"""
        assert os.path.exists(fname), f"{fname} does not exist"

    def assertFileNotExists(self, fname):
        """Asserts that fname does not exist on the filesystem"""
        assert not os.path.exists(fname), f"{fname} exists"

    def assertOutputContains(self, content):
        """Ensure that stdout did contain the given content string

        :param content:  The string that should not be in stdout
        :type content:  ``str``
        """
        found = re.search(
            fr"(.*)?{content}(.*)?",
            self.cmd_output.stdout + self.cmd_output.stderr)
        assert found, f"Content string '{content}' not in output"

    def assertOutputNotContains(self, content):
        """Ensure that stdout did NOT contain the given content string

        :param content:  The string that should not be in stdout
        :type content:  ``str``
        """
        found = re.search(
            fr"(.*)?{content}(.*)?",
            self.cmd_output.stdout + self.cmd_output.stderr)
        assert not found, f"String '{content}' present in stdout"


class BaseSoSReportTest(BaseSoSTest):
    """This is the class to use for building sos report tests with.

    An instance of this test is expected to set at minimum a ``sos_cmd`` class
    attribute that represets the options handed to a specific execution of an
    sos command. This should be anything following ``sos report --batch``.

    """

    archive = None
    _manifest = None
    _exception_expected = False
    encrypt_pass = None
    sos_component = 'report'

    @property
    def manifest(self):
        if self._manifest is None:
            try:
                content = self.read_file_from_tmpdir(
                    self.get_name_in_archive('sos_reports/manifest.json'))
                self._manifest = json.loads(content)
            except Exception:
                self._manifest = ''
                self.log.warn('Could not load manifest for test')
        return self._manifest

    @property
    def encrypted_path(self):
        return self.get_encrypted_path()

    def _decrypt_archive(self, archive_arg):
        _archive = archive_arg.strip('.gpg')
        cmd = (f"gpg --batch --passphrase {self.encrypt_pass} -o {_archive} "
               f"--decrypt {archive_arg}")
        try:
            process.run(cmd, timeout=10)
        except Exception as err:
            # pylint: disable=no-member
            if err.result.interrupted:
                self.error("Timeout while decrypting")
            if 'Bad session key' in err.result.stderr.decode():
                self.fail("Decryption with well-known passphrase failed")
            raise
        return _archive

    def grep_for_content(self, search, regexp=False):
        """Call out to grep for finding a specific string 'search' in any place
        in the archive

        :param search: string to search
        :param regexp: use regular expression search (default False
                       means "grep -F")
        """
        fixed_opt = "" if regexp else "F"
        cmd = f"grep -ril{fixed_opt} '{search}' {self.archive_path}"
        try:
            out = process.run(cmd)
            rc = out.exit_status
        except process.CmdError as err:
            out = err.result
            rc = err.result.exit_status

        if rc == 1:
            # grep will return an exit code of 1 if no matches are found,
            # which is what we want
            return False
        flist = []
        for ln in out.stdout.decode('utf-8').splitlines():
            flist.append(ln.split(self.tmpdir)[-1])
        return flist

    def get_encrypted_path(self):
        """Since avocado re-instantiates a new object for every test_ method,
        we need to be able to retrieve the original path for the encrypted
        archive and cannot rely on it being set by the _extract_archive()
        override
        """
        try:
            return re.findall(
                r'/.*sosreport-.*tar.*\.gpg',
                self.cmd_output.stdout
            )[-1]
        except Exception:
            return None

    def _extract_archive(self, arc_path):
        """Extract an archive to the temp directory
        """
        if '--encrypt' in self.sos_cmd:
            arc_path = self._decrypt_archive(arc_path)
        _extract_path = self._get_extracted_tarball_path()
        try:
            archive.extract(arc_path, _extract_path)
            self.archive_path = self._get_archive_path()
        except Exception as err:
            self.cancel(f"Could not extract archive: {err}")

    def _get_extracted_tarball_path(self):
        """Based on the klass id setup earlier, provide a name to extract the
        archive to within the tmpdir
        """
        return os.path.join(
            self.tmpdir,
            f"sosreport-{self.__class__.__name__}"
        )

    def _generate_sos_command(self):
        return (f"{self.sos_bin} {self.sos_component} -v --batch "
                f"--tmp-dir {self.tmpdir} {self.sos_cmd}")

    def _execute_sos_cmd(self):
        super()._execute_sos_cmd()
        self.archive = re.findall(
            '/.*sosreport-.*tar.*',
            self.cmd_output.stdout
        )
        if self.archive:
            self.archive = self.archive[-1]
            self._extract_archive(self.archive)

    def _get_archive_path(self):
        path = glob.glob(self._get_extracted_tarball_path() + '/sosreport*')
        if path:
            return path[0]
        return None

    def setUp(self):
        super().setUp()
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
        with open(self.get_name_in_archive(fname), 'r',
                  encoding='utf-8') as gfile:
            content = gfile.read()
        return content

    def assertFileCollected(self, fname):
        """Ensure that a given fname is in the extracted archive if it exists
        on the host system

        :param fname:  The name of the file within the archive
        :type fname:  ``str``
        """
        if fname.startswith(('sos_', '/sos_')) or os.path.exists(fname):
            self.assertFileExists(self.get_name_in_archive(fname))
        else:
            assert True

    def assertFileNotCollected(self, fname):
        """Ensure that a given fname is NOT in the extracted archive

        :param fname:  The name of the file within the archive
        :type fname:  ``str``
        """
        self.assertFileNotExists(self.get_name_in_archive(fname))

    def assertFileGlobInArchive(self, fname):
        """Ensure that at least one file in the archive matches a given fname
        glob, iff it exists on the host system

        :param fname:  The glob to match filenames of
        :type fname:  ``str``
        """
        if fname.startswith(('sos_', '/sos_')):
            files = glob.glob(
                os.path.join(self.archive_path, fname.lstrip('/'))
            )
        elif not glob.glob(fname):
            # force the test to pass since the file glob could not have been
            # collected
            files = True
        else:
            files = glob.glob(
                os.path.join(self.archive_path, fname.lstrip('/'))
            )
        assert files, f"No files matching {fname} found"

    def assertFileGlobNotInArchive(self, fname):
        """Ensure that there are NO files in the archive matching a given fname
        glob

        :param fname:  The glob to match filename(s) of
        :type fname:  ``str``
        """
        files = glob.glob(os.path.join(self.tmpdir, fname.lstrip('/')))
        self.log.debug(files)
        assert \
            not files, \
            f"Found files in archive matching {fname}: {files}"

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
        with open(fname, 'r', encoding='utf-8') as lfile:
            _contents = lfile.read()
            for line in _contents.splitlines():
                if re.match(f".*{content}.*", line, re.I):
                    matched = True
                    break
        assert \
            matched, \
            f"Content '{content}' does not appear in {fname}\n{_contents}"

    def assertFileNotHasContent(self, fname, content):
        """Ensure that the file file fname does NOT contain the given content

        :param fname:  The name of the file
        :type fname:  ``str``

        :param content:  The content to (not) match
        :type content:   ``str``
        """
        matched = False
        fname = self.get_name_in_archive(fname)
        with open(fname, 'r', encoding='utf-8') as mfile:
            for line in mfile.read().splitlines():
                if re.match(f".*{content}.*", line, re.I):
                    matched = True
                    break
        assert \
            not matched, \
            f"Content '{content}' appears in file {fname}"

    def assertSosLogContains(self, content):
        """Ensure that the given content string exists in sos.log
        """
        self.assertFileHasContent('sos_logs/sos.log', content)

    def assertSosLogNotContains(self, content):
        """Ensure that the given content string does NOT exist in sos.log
        """
        self.assertFileNotHasContent('sos_logs/sos.log', content)

    def assertSosUILogContains(self, content):
        """Ensure that the given content string exists in ui.log
        """
        self.assertFileHasContent('sos_logs/ui.log', content)

    def assertSosUILogNotContains(self, content):
        """Ensure that the given content string does NOT exist in ui.log
        """
        self.assertFileNotHasContent('sos_logs/ui.log', content)

    def assertPluginIncluded(self, plugin):
        """Ensure that the specified plugin did run for the sos execution

        Note that this relies on manifest.json being successfully created

        :param plugin:  The name of the plugin
        :type plugin:  `` str``
        """
        if not self.manifest:
            self.error(
                f"No manifest found, cannot check for {plugin} execution"
            )
        if isinstance(plugin, str):
            plugin = [plugin]
        for plug in plugin:
            assert \
                plug in self.manifest['components']['report']['plugins'], \
                f"Plugin '{plug}' not recorded in manifest"

    def assertPluginNotIncluded(self, plugin):
        """Ensure that the specified plugin did NOT run for the sos execution
        Note that this relies on manifest.json being successfully created

        :param plugin:  The name of the plugin
        :type plugin:  `` str``
        """
        if not self.manifest:
            self.error(
                f"No manifest found, cannot check for {plugin} execution"
            )
        if isinstance(plugin, str):
            plugin = [plugin]
        for plug in plugin:
            assert \
                plug not in self.manifest['components']['report']['plugins'], \
                f"Plugin '{plug}' is recorded in manifest"

    def assertOnlyPluginsIncluded(self, plugins):
        """Ensure that only the specified plugins are in the manifest

        :param plugins:  The plugin names
        :type plugins:  ``str`` or ``list`` of strings
        """
        if not self.manifest:
            self.error(
                f"No manifest found, cannot check for {plugins} execution"
            )
        if isinstance(plugins, str):
            plugins = [plugins]
        _executed = self.manifest['components']['report']['plugins'].keys()

        # test that all requested plugins did run
        for i in plugins:
            assert i in _executed, f"Requested plugin '{i}' did not run"

        # test that no unrequested plugins ran
        for j in _executed:
            assert j in plugins, f"Unrequested plugin '{j}' ran as well"

    def get_plugin_manifest(self, plugin):
        """Get the manifest data for the specified plugin

        :param plugin:  The name of the plugin
        :type plugin:   ``str``

        :returns: The section of the manifest for the plugin
        :rtype:   ``dict``
        """
        if not self.manifest['components']['report']['plugins'][plugin]:
            raise Exception(f"Manifest for {plugin} not present")
        return self.manifest['components']['report']['plugins'][plugin]


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
    :avocado: tags=stageone,foreman
    """

    sos_cmd = ''

    def test_archive_created(self):
        """Ensure that the archive tarball was created and has the right owner
        """
        self.assertFileExists(self.archive)
        self.assertTrue(os.stat(self.archive).st_uid == 0)

    def test_checksum_is_valid(self):
        """Ensure that a checksum was generated, reported, and is correct
        """
        _chk = re.findall('sha256\t.*\n', self.cmd_output.stdout)
        _chk = _chk[0].split('sha256\t')[1].strip()
        assert _chk, "No checksum reported"
        cmd = f"sha256sum {(self.encrypted_path or self.archive)}"
        _found = process.run(cmd).stdout.decode().split()[0]
        self.assertEqual(_chk, _found)

    def test_no_new_kmods_loaded(self):
        """Ensure that no additional kernel modules have been loaded during an
        execution of a test
        """
        self.assertCountEqual(self.sysinfo['pre']['modules'],
                              self.sysinfo['post']['modules'])

    def test_archive_has_sos_dirs(self):
        """Ensure that we have the expected directory layout with in the
        archive
        """
        self.assertFileCollected('sos_commands')
        self.assertFileCollected('sos_logs')

    def test_manifest_created(self):
        self.assertFileCollected('sos_reports/manifest.json')

    @skipIf(lambda x: '--no-report' in x.sos_cmd,
            '--no-report used in command')
    def test_html_reports_created(self):
        self.assertFileCollected('sos_reports/sos.html')

    def test_no_ip_changes(self):
        # I.E. make sure we didn't cause any NIC flaps that for some reason
        # resulted in a new primary IP address. TODO: build this out to make
        # sure this IP is still bound to the same NIC
        self.assertEqual(self.sysinfo['pre']['networking']['ip_addr'],
                         self.sysinfo['post']['networking']['ip_addr'])

    def test_no_exceptions_during_execution(self):
        self.end_of_test_case = True
        self.assertSosLogNotContains('caught exception in plugin')
        self.assertFileGlobNotInArchive('sos_logs/*-plugin-errors.txt')


class StageTwoReportTest(BaseSoSReportTest):
    """This is the testing class to subclass when light mocking is needed to
    perform the test.

    Light mocking for our uses is restricted to dropping files in well-known
    locations, temporarily replacing binaries, and installing packages.

    Note: Stage 2 tests should NOT be run on any system that is considered
    either production, or is a workstation that cannot be easily re-imaged or
    re-deployed. While efforts are taken to ensure that systems are left in
    their original state after mocking tests are done, the assumption is that
    these tests are being run on "throw-away" test systems where it does not
    matter if that original state is indeed attained or not.

    This kind of mocking is described in the class attributes as follows for
    each test case that is a Stage 2 test:

    files   -   a list containing the files to drop on the test system's real
                filesystem. Mocked files should be placed in the same locations
                under tests/test_data. If list items are tuples, then the tuple
                elements are (source_path, dest_path), which will allow the
                project to store multiple versions of files in the tree without
                interfering with other tests

    packages -  a dict where the keys are the distribution names (e.g. 'rhel',
                'ubuntu') and the values are the package names optionally with
                version

    install_plugins - a list containing the names of test plugins to be dropped
                      inside the test repo for testing specific use cases.
                      The list values are strings that match the test plugin's
                      filename, and test plugins should be placed under
                      tests/test_data/fake_plugins

    :avocado: disable
    :avocado: tags=stagetwo,scrub,foreman2
    """

    sos_cmd = ''
    files = []
    packages = {}
    install_plugins = []
    _created_files = []

    def setUp(self):
        self.end_of_test_case = False
        self.sm = software_manager.manager.SoftwareManager()

        for dist, value in self.packages.items():
            if isinstance(value, str):
                self.packages[dist] = [value]

        keys = self.packages.keys()
        # allow for single declaration of packages for the RH family
        # for our purposes centos == rhel here
        if 'fedora' in keys and 'rhel' not in keys:
            self.packages['rhel'] = self.packages['fedora']
        elif 'rhel' in keys and 'fedora' not in keys:
            self.packages['fedora'] = self.packages['rhel']
        if 'rhel' in keys:
            self.packages['centos'] = self.packages['rhel']
            self.packages['centos-stream'] = self.packages['rhel']

        super().setUp()

    def tearDown(self):
        if self.end_of_test_case:
            self.teardown_mocking()
            super().tearDown()

    def teardown_mocking(self):
        """Undo any and all mocked setup that we did for tests
        """
        self.teardown_mocked_packages()
        self.teardown_mocked_files()
        self.teardown_mocked_plugins()

    def setup_mocking(self):
        """Main entrypoint for setting up our mocking for the test"""
        self.setup_mocked_packages()
        self.setup_mocked_files()
        self.setup_mocked_plugins()

    def setup_mocked_plugins(self):
        """Drop any plugins specified from tests/test_data/fake_plugins into
        the test repo root (as created by CirrusCI).
        """
        _installed = []
        for plug in self.install_plugins:
            if not plug.endswith('.py'):
                plug += '.py'
            fake_plug = os.path.join(
                os.path.dirname(inspect.getfile(self.__class__)),
                plug
            )
            if os.path.exists(fake_plug):
                shutil.copy(fake_plug, SOS_PLUGIN_DIR)
                _installed.append(
                    os.path.realpath(os.path.join(SOS_PLUGIN_DIR, plug))
                )
        self._write_file_to_tmpdir('mocked_plugins', json.dumps(_installed))

    def teardown_mocked_plugins(self):
        """Remove any test plugins dropped into the repo during setup
        """
        _plugins = self.read_file_from_tmpdir('mocked_plugins')
        if not _plugins:
            return
        _plugins = json.loads(_plugins)
        for plug in _plugins:
            os.remove(plug)

    def setup_mocked_packages(self):
        """Install any required packages using avocado's software manager
        abstraction
        """
        if self.local_distro in self.packages:
            # remove any packages already locally installed, as otherwise
            # our call to SoftwareManager will return False
            self._strip_installed_packages()
            if not self.packages[self.local_distro]:
                return
            installed = distro_packages.install_distro_packages(self.packages)
            if not installed:
                raise Exception(
                    f"Unable to install requested packages "
                    f"{', '.join(self.packages[self.local_distro])}"
                )
            # save installed package list to our tmpdir to be removed later
            self._write_file_to_tmpdir(
                'mocked_packages',
                json.dumps(self.packages[self.local_distro])
            )

    def _strip_installed_packages(self):
        """For the list of packages given for a test, if any of the packages
        already exist on the test system, remove them from the list of packages
        to be installed.
        """
        self.packages[self.local_distro] = [
            p for p in self.packages[self.local_distro] if not
            self.sm.check_installed(p)
        ]

    def teardown_mocked_packages(self):
        """Uninstall any packages that we installed for this test
        """
        pkgs = self.read_file_from_tmpdir('mocked_packages')
        if not pkgs:
            return
        pkgs = json.loads(pkgs)
        for pkg in pkgs:
            self.sm.remove(pkg)

    def _copy_test_file(self, filetup):
        """Helper to copy files from tests/test_data to relevant locations on
        the test system. If ``dest`` is provided, use that as the destination
        filename instead of using the ``src`` name
        """
        src, dest = filetup
        dir_added = False
        if os.path.exists(dest):
            os.rename(dest, dest + '.sostesting')
        _dir = os.path.dirname(dest)
        if not os.path.exists(_dir):
            os.makedirs(_dir)
            self._created_files.append(_dir)
            dir_added = True
        _test_file = os.path.join(
            os.path.dirname(inspect.getfile(self.__class__)),
            src.lstrip('/')
        )
        shutil.copy(_test_file, dest)
        if not dir_added:
            self._created_files.append(dest)

    def setup_mocked_files(self):
        """Place any requested files from under tests/test_data into "proper"
        locations on the test system's filesystem.

        If any of these files already exist, rename the existing copy with a
        '.sostesting' extension, so we can easily undo any changes after the
        test(s) have run.
        """
        for mfile in self.files:
            if not isinstance(mfile, tuple):
                raise Exception("Mocked files must be provided via tuples,"
                                f"not {mfile.__class__}")
            self._copy_test_file(mfile)
        if self._created_files:
            self._write_file_to_tmpdir(
                'mocked_files',
                json.dumps(self._created_files)
            )

    def teardown_mocked_files(self):
        """Remove any mocked files from the test system's filesystem, and
        if applicable, restore previously moved files
        """
        _files = self.read_file_from_tmpdir('mocked_files')
        if not _files:
            return
        _files = json.loads(_files)
        for mocked in _files:
            if os.path.isdir(mocked):
                shutil.rmtree(mocked)
            else:
                os.remove(mocked)
            if os.path.exists(mocked + '.sostesting'):
                os.rename(mocked + '.sostesting', mocked)

    def test_archive_created(self):
        """Ensure that the archive tarball was created and has the right owner
        """
        # kind of a hack, but since avocado test order is predicatable, we can
        # use this to avoid calling setUp() and tearDown() at each test_ method
        # for stagetwo like we use the tmpdir for stageone.
        # THIS TEST MUST ALWAYS BE DEFINED LAST IN THIS CLASS FOR THIS TO WORK
        self.end_of_test_case = True

        self.assertFileExists(self.archive)
        self.assertTrue(os.stat(self.archive).st_uid == 0)


class StageOneReportExceptionTest(BaseSoSReportTest):
    """This test class should be used when we expect to generate an exception
    with a given command invocation.

    By default, this class assumes no archive will be generated and the exit
    code from the sos command will be nonzero. If this is not the case for
    the specific test being run, e.g. testing plugin exception handling, then
    set the ``archive_still_expected`` class attr to ``True``

    :avocado: disable
    :avocado: tags=stageone
    """

    _exception_expected = True

    # set this to True if the exception generated is not expected to halt
    # archive generation
    archive_still_expected = False

    sos_cmd = ''

    @skipIf(lambda x: x.archive_still_expected, "0 exit code still expected")
    def test_nonzero_return_code(self):
        self.assertFalse(self.cmd_output.exit_status == 0)

    @skipIf(lambda x: x.archive_still_expected, "Output expected in test")
    def test_no_archive_generated(self):
        self.assertTrue(self.archive is None)


class StageOneOutputTest(BaseSoSTest):
    """This test class should be used for tests that are only checking or
    validating output from a specific command or option, such as --help or
    --list.

    :avocado: disable
    :avocado: tags=stageone
    """

    sos_cmd = ''

    def _generate_sos_command(self):
        return f"{self.sos_bin} {self.sos_cmd}"

    @skipIf(lambda x: x._exception_expected, "Non-zero exit code expected")
    def test_help_output_successful(self):
        self.assertTrue(self.cmd_output.exit_status == 0)
        assert self.cmd_output.stdout, "No stdout output generated"
        assert not self.cmd_output.stderr, (
            f"stderr received, but not expected: {self.cmd_output.stderr}")

    @skipIf(lambda x: not x._exception_expected,
            "Not anticipating stderr output")
    def test_help_error_reported(self):
        self.assertTrue(self.cmd_output.exit_status != 0)
        assert not self.cmd_output.stdout, (
            f"stdout received, but not expected: {self.cmd_output.stdout}")
        assert self.cmd_output.stderr, "No stderr output generated"
