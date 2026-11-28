# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import bz2
import logging
import shutil
import tempfile
import unittest
from unittest.mock import Mock

from sos.archive import TarFileArchive
from sos.component import SoSComponent
from sos.policies import Policy


class UploadPasswordTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.component = SoSComponent.__new__(SoSComponent)
        self.component.ui_log = Mock(spec=logging.Logger)
        self.component.archive = TarFileArchive(
            'test', self.tmpdir, Policy(), 1, {'encrypt': False}, '/')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_plain_bzh_upload_password(self):
        archive = self.component.archive
        archive.add_string('BZh --upload-pass=SECRET', 'sos_logs/sos.log')
        self.component._obfuscate_upload_passwords()
        with archive.open_file('sos_logs/sos.log') as output:
            self.assertEqual(output.read(), 'BZh --upload-pass=********')

    def test_corrupt_stream_stops_before_packaging(self):
        archive = self.component.archive
        content = bz2.compress(b'--upload-pass=SECRET')[:10]
        archive.add_binary(content, 'sos_logs/sos.log')
        with self.assertRaises(SystemExit) as raised:
            self.component._obfuscate_upload_passwords()
        self.assertEqual(raised.exception.code, 1)
        message = str(self.component.ui_log.error.call_args_list)
        self.assertNotIn('SECRET', message)
        self.assertIn('will not be packaged or uploaded', message)
        with open(archive.dest_path('sos_logs/sos.log'), 'rb') as source:
            self.assertEqual(source.read(), content)

    def test_limit_stops_before_packaging(self):
        archive = self.component.archive
        archive._substitution_limit = 8
        archive.add_binary(bz2.compress(b'--upload-pass=SECRET'),
                           'sos_logs/sos.log')
        with self.assertRaises(SystemExit):
            self.component._obfuscate_upload_passwords()

    def test_io_error_is_not_logged_with_secret(self):
        archive = self.component.archive
        archive.add_string('--upload-pass=SECRET', 'sos_logs/sos.log')
        archive.do_file_sub = Mock(side_effect=OSError('SECRET'))
        with self.assertRaises(SystemExit):
            self.component._obfuscate_upload_passwords()
        self.assertNotIn('SECRET', str(
            self.component.ui_log.error.call_args_list))

    def test_prior_plugin_failure_stops_build_and_upload(self):
        archive = self.component.archive
        archive.add_binary(bz2.compress(b'password=SECRET')[:10], 'plugin.bz2')
        with self.assertRaises(OSError):
            archive.do_file_sub('plugin.bz2', 'SECRET', 'MASK')
        with self.assertRaises(SystemExit):
            self.component._obfuscate_upload_passwords()
        with self.assertRaises(OSError):
            archive.finalize('gzip')
