# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import shutil
import stat
import tarfile
from avocado.utils import process
from sos_tests import StageTwoReportTest


class PermissionsReportTest(StageTwoReportTest):
    """Base class that overrides _extract_archive to use Python's tarfile
    module, which preserves permissions (via explicit os.chmod).

    :avocado: disable
    """

    def _extract_archive(self, arc_path):
        _extract_path = self._get_extracted_tarball_path()
        os.makedirs(_extract_path, exist_ok=True)
        try:
            with tarfile.open(arc_path) as tf:
                members = tf.getmembers()
                tf.extractall(_extract_path)
                for member in members:
                    target = os.path.join(_extract_path, member.name)
                    if os.path.exists(target) and not os.path.islink(target):
                        os.chmod(target, member.mode)
            self.archive_path = self._get_archive_path()
        except Exception as err:
            self.cancel(f"Could not extract archive: {err}")


class FilePermissionsPreserved(PermissionsReportTest):  # Test for bz888724
    """Test that sos preserves permissions of collected files

    :avocado: tags=stagetwo
    """

    install_plugins = ['permissions']
    sos_cmd = '-o permissions'

    no_perms_file = '/etc/no_perms_file.conf'
    some_perms_file = '/var/log/some_perms_file.log'

    def pre_sos_setup(self):
        process.run(f'touch {self.no_perms_file}')
        os.chmod(self.no_perms_file, 0o000)
        process.run(f'touch {self.some_perms_file}')
        os.chmod(self.some_perms_file, 0o666)

    def test_file_permissions_preserved(self):
        for fname, mode in [(self.no_perms_file, 0o000),
                            (self.some_perms_file, 0o666)]:
            self.assertFileCollected(fname)
            extracted_file = self.get_name_in_archive(fname)
            extracted_permissions = stat.S_IMODE(
                os.lstat(extracted_file).st_mode)
            self.assertEqual(
                extracted_permissions, mode,
                f"Permissions not preserved: expected {mode}, "
                f"got {oct(extracted_permissions)}"
            )

    def post_test_tear_down(self):
        for f in [self.no_perms_file, self.some_perms_file]:
            if os.path.exists(f):
                os.remove(f)


class DirectoryPermissionsPreserved(  # Test for bz1069786
        PermissionsReportTest):
    """Test that sos preserves permissions of collected directories

    :avocado: tags=stagetwo
    """

    install_plugins = ['permissions']
    sos_cmd = '-o permissions'

    test_root = '/var/tmp/permissions-test'

    def pre_sos_setup(self):
        os.makedirs(f'{self.test_root}/d1/d2/d3', exist_ok=True)
        with open(f'{self.test_root}/d1/d2/d3/data', 'w',
                  encoding='utf-8') as dfile:
            dfile.write('test data\n')

        os.chmod(f'{self.test_root}/d1/d2/d3', 0o777)
        os.chmod(f'{self.test_root}/d1/d2', 0o770)
        os.chmod(f'{self.test_root}/d1', 0o700)

    def test_top_dir_permissions_preserved(self):
        extracted_file = self.get_name_in_archive(f'{self.test_root}/d1')
        self.assertFileExists(extracted_file)
        extracted_permissions = stat.S_IMODE(
            os.stat(extracted_file).st_mode)
        self.assertEqual(
            extracted_permissions, 0o700,
            f"d1 permissions not preserved: expected 0o700, "
            f"got {oct(extracted_permissions)}"
        )

    def test_nested_dir_permissions_preserved(self):
        extracted_file = self.get_name_in_archive(f'{self.test_root}/d1/d2')
        self.assertFileExists(extracted_file)
        extracted_permissions = stat.S_IMODE(
            os.stat(extracted_file).st_mode)
        self.assertEqual(
            extracted_permissions, 0o770,
            f"d2 permissions not preserved: expected 0o770, "
            f"got {oct(extracted_permissions)}"
        )

    def test_deep_nested_dir_permissions_preserved(self):
        extracted_file = self.get_name_in_archive(
            f'{self.test_root}/d1/d2/d3')
        self.assertFileExists(extracted_file)
        extracted_permissions = stat.S_IMODE(
            os.stat(extracted_file).st_mode)
        self.assertEqual(
            extracted_permissions, 0o777,
            f"d3 permissions not preserved: expected 0o777, "
            f"got {oct(extracted_permissions)}"
        )

    def post_test_tear_down(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)
