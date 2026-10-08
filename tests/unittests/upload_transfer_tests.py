# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import ftplib
import importlib.util
import json
import os
import socket
import tempfile
import unittest
from unittest.mock import ANY, MagicMock, patch

from sos.upload.targets import (BOTO3_LOADED, REQUESTS_LOADED, UploadTarget)
from sos.upload.targets.redhat import RHELUploadTarget
from sos.utilities import TIMEOUT_DEFAULT

# upload_sftp() imports pexpect lazily and raises if it is absent, so the
# SFTP cases are skipped rather than failed on a host without it.
PEXPECT_LOADED = importlib.util.find_spec('pexpect') is not None


# Mirrors SoSUpload.arg_defaults. A bare MagicMock() would make every
# option attribute truthy, which quietly sends the code down the wrong
# branch in upload_https() and _determine_upload_type().
UPLOAD_ARG_DEFAULTS = {
    'batch': True,
    'case_id': '',
    'low_priority': False,
    'quiet': False,
    'upload_directory': None,
    'upload_file': '',
    'upload_method': 'auto',
    'upload_no_ssl_verify': False,
    'upload_pass': None,
    'upload_protocol': 'auto',
    'upload_s3_access_key': None,
    'upload_s3_bucket': None,
    'upload_s3_endpoint': None,
    'upload_s3_object_prefix': None,
    'upload_s3_region': None,
    'upload_s3_secret_key': None,
    'upload_target': None,
    'upload_threads': 4,
    'upload_url': None,
    'upload_user': None,
}

# Credentials read straight from the environment by the get_upload_*
# helpers. Cleared per test so a developer's shell cannot change results.
SOS_UPLOAD_ENV_VARS = (
    'SOSUPLOADUSER',
    'SOSUPLOADPASSWORD',
    'SOSUPLOADS3ACCESSKEY',
    'SOSUPLOADS3SECRETKEY',
)

RH_SFTP_TOKEN_URL = f"{RHELUploadTarget.RH_API_HOST}/support/v2/sftp/token"


def make_opts(**overrides):
    """Build a stand-in for the parsed cmdline options."""
    opts = MagicMock()
    for name, value in {**UPLOAD_ARG_DEFAULTS, **overrides}.items():
        setattr(opts, name, value)
    return opts


def make_target(cls, opts=None, **attrs):
    """Build an upload target without running __init__."""
    target = cls.__new__(cls)
    target.ui_log = MagicMock()
    target.commons = {
        'cmdlineopts': opts if opts is not None else make_opts(),
        'policy': MagicMock(),
    }
    target.upload_url = None
    target.upload_user = None
    target.upload_password = None
    target.upload_directory = None
    target.upload_archive_name = ''
    target.upload_s3_access_key = None
    target.upload_s3_bucket = None
    target.upload_s3_endpoint = None
    target.upload_s3_object_prefix = None
    target.upload_s3_region = None
    target.upload_s3_secret_key = None
    for name, value in attrs.items():
        setattr(target, name, value)
    return target


class TransferTestCase(unittest.TestCase):
    """Base for transfer tests.

    Provides a real on-disk archive, because the transfer methods open the
    file and read its basename, and neutralises the upload environment
    variables so local shell settings cannot influence assertions.
    """

    def setUp(self):
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for var in SOS_UPLOAD_ENV_VARS:
            os.environ.pop(var, None)

        handle, self.archive = tempfile.mkstemp(
            prefix='sosreport-transfer-', suffix='.tar.xz')
        with os.fdopen(handle, 'wb') as archive:
            archive.write(b'not a real sos archive')
        self.addCleanup(os.unlink, self.archive)

    @property
    def archive_name(self):
        return os.path.basename(self.archive)


@unittest.skipUnless(REQUESTS_LOADED, 'python3-requests is not installed')
class S201HttpsTransferTests(TransferTestCase):
    """S2-01 - HTTPS PUT/POST upload success and error handling."""

    def _target(self, opts=None, **attrs):
        return make_target(UploadTarget, opts=opts,
                           upload_url='https://example.com/api',
                           upload_archive_name=self.archive,
                           upload_user='uploader',
                           upload_password='sup3rs3cret', **attrs)

    def test_put_upload_succeeds(self):
        target = self._target(opts=make_opts(upload_method='put'))
        with patch('sos.upload.targets.requests') as requests:
            requests.put.return_value = MagicMock(status_code=200)
            self.assertTrue(target.upload_https())
        requests.put.assert_called_once_with(
            'https://example.com/api', data=ANY, auth=ANY, verify=True,
            timeout=TIMEOUT_DEFAULT)
        self.assertFalse(requests.post.called)

    def test_post_upload_succeeds_on_201(self):
        target = self._target(opts=make_opts(upload_method='post'))
        with patch('sos.upload.targets.requests') as requests:
            requests.post.return_value = MagicMock(status_code=201)
            self.assertTrue(target.upload_https())
        self.assertFalse(requests.put.called)

    def test_auto_method_defaults_to_post(self):
        target = self._target(opts=make_opts(upload_method='auto'))
        with patch('sos.upload.targets.requests') as requests:
            requests.post.return_value = MagicMock(status_code=200)
            self.assertTrue(target.upload_https())
        self.assertTrue(requests.post.called)
        self.assertFalse(requests.put.called)

    def test_post_sends_archive_basename(self):
        target = self._target(opts=make_opts(upload_method='post'))
        with patch('sos.upload.targets.requests') as requests:
            requests.post.return_value = MagicMock(status_code=200)
            target.upload_https()
        files = requests.post.call_args.kwargs['files']
        self.assertEqual(files['file'][0], self.archive_name)

    def test_credentials_passed_as_basic_auth(self):
        target = self._target(opts=make_opts(upload_method='put'))
        with patch('sos.upload.targets.requests') as requests:
            requests.put.return_value = MagicMock(status_code=200)
            target.upload_https()
        requests.auth.HTTPBasicAuth.assert_called_once_with(
            'uploader', 'sup3rs3cret')

    def test_ssl_verification_can_be_disabled(self):
        target = self._target(
            opts=make_opts(upload_method='put', upload_no_ssl_verify=True))
        with patch('sos.upload.targets.requests') as requests:
            requests.put.return_value = MagicMock(status_code=200)
            target.upload_https()
        self.assertFalse(requests.put.call_args.kwargs['verify'])

    def test_401_reports_authentication_failure(self):
        target = self._target(opts=make_opts(upload_method='put'))
        with patch('sos.upload.targets.requests') as requests:
            requests.put.return_value = MagicMock(status_code=401)
            with self.assertRaisesRegex(
                    Exception, 'Authentication failed: invalid user'):
                target.upload_https()

    def test_other_status_reports_status_and_reason(self):
        # upload_https() hardcodes "POST" in this message regardless of
        # the method actually used, so a failed PUT still reports "POST
        # request returned ...". Asserted as-is to match the shipped
        # behaviour rather than the intended wording.
        target = self._target(opts=make_opts(upload_method='put'))
        with patch('sos.upload.targets.requests') as requests:
            requests.put.return_value = MagicMock(
                status_code=500, reason='Internal Server Error')
            with self.assertRaisesRegex(
                    Exception,
                    'POST request returned 500: Internal Server Error'):
                target.upload_https()


class S202FtpTransferTests(TransferTestCase):
    """S2-02 - FTP upload happy path and error-code mapping."""

    def _target(self, **attrs):
        return make_target(UploadTarget,
                           upload_url='ftp://ftp.example.com',
                           upload_archive_name=self.archive,
                           upload_user='ftpuser',
                           upload_password='ftppass', **attrs)

    def test_upload_succeeds(self):
        target = self._target()
        session = MagicMock()
        with patch('ftplib.FTP', return_value=session) as ftp:
            self.assertTrue(target.upload_ftp())
        ftp.assert_called_once_with('ftp.example.com', 'ftpuser', 'ftppass',
                                    timeout=15)
        session.cwd.assert_called_once_with('/')
        session.storbinary.assert_called_once_with(
            f'STOR {self.archive_name}', ANY)
        session.quit.assert_called_once_with()

    def test_upload_directory_is_used(self):
        target = self._target(upload_directory='/incoming')
        session = MagicMock()
        with patch('ftplib.FTP', return_value=session):
            self.assertTrue(target.upload_ftp())
        session.cwd.assert_called_once_with('/incoming')

    def test_missing_url_raises(self):
        target = make_target(UploadTarget,
                             upload_archive_name=self.archive)
        with self.assertRaisesRegex(Exception,
                                    'no FTP server specified by upload'):
            target.upload_ftp()

    def test_error_503_reports_login_failure(self):
        target = self._target()
        with patch('ftplib.FTP',
                   side_effect=ftplib.error_perm('503 Bad sequence')):
            with self.assertRaisesRegex(Exception,
                                        "could not login as 'ftpuser'"):
                target.upload_ftp()

    def test_error_530_reports_invalid_password(self):
        target = self._target()
        with patch('ftplib.FTP',
                   side_effect=ftplib.error_perm('530 Login incorrect')):
            with self.assertRaisesRegex(
                    Exception, "invalid password for user 'ftpuser'"):
                target.upload_ftp()

    def test_error_550_reports_bad_directory(self):
        target = self._target(upload_directory='/nope')
        session = MagicMock()
        session.cwd.side_effect = ftplib.error_perm('550 No such directory')
        with patch('ftplib.FTP', return_value=session):
            with self.assertRaisesRegex(
                    Exception, 'could not set upload directory to /nope'):
                target.upload_ftp()

    def test_unmapped_error_perm_is_reported(self):
        target = self._target()
        with patch('ftplib.FTP',
                   side_effect=ftplib.error_perm('999 Unknown')):
            with self.assertRaisesRegex(
                    Exception, 'error trying to establish session'):
                target.upload_ftp()

    def test_socket_timeout_is_reported(self):
        target = self._target()
        with patch('ftplib.FTP', side_effect=socket.timeout()):
            with self.assertRaisesRegex(
                    Exception,
                    'timeout hit while connecting to ftp.example.com'):
                target.upload_ftp()

    def test_name_resolution_failure_is_reported(self):
        target = self._target()
        with patch('ftplib.FTP', side_effect=socket.gaierror()):
            with self.assertRaisesRegex(
                    Exception, 'unable to connect to ftp.example.com'):
                target.upload_ftp()


@unittest.skipUnless(PEXPECT_LOADED, 'python3-pexpect is not installed')
class S203SftpTransferTests(TransferTestCase):
    """S2-03 - Base SFTP upload happy path and connection errors."""

    def _target(self, **attrs):
        return make_target(UploadTarget,
                           upload_url='sftp://sftp.example.com',
                           upload_archive_name=self.archive,
                           upload_user='sftpuser',
                           upload_password='sftppass', **attrs)

    @staticmethod
    def _run(target, expects, **kwargs):
        """Drive upload_sftp() with a scripted pexpect conversation."""
        child = MagicMock()
        child.expect.side_effect = expects
        child.before = ''
        with patch('sos.upload.targets.is_executable', return_value=True), \
                patch('pexpect.spawn', return_value=child):
            return target.upload_sftp(**kwargs), child

    def test_missing_sftp_binary_raises(self):
        target = self._target()
        with patch('sos.upload.targets.is_executable', return_value=False):
            with self.assertRaisesRegex(Exception,
                                        'SFTP is not locally supported'):
                target.upload_sftp()

    def test_key_based_login_succeeds(self):
        target = self._target()
        result, child = self._run(target, [0, 0])
        self.assertTrue(result)
        child.sendline.assert_any_call(
            f'put {self.archive} {self.archive_name}')
        child.sendline.assert_any_call('bye')

    def test_password_login_succeeds(self):
        target = self._target()
        result, child = self._run(target, [1, 0, 0])
        self.assertTrue(result)
        child.sendline.assert_any_call('sftppass')

    def test_wrong_password_raises(self):
        target = self._target()
        with self.assertRaisesRegex(Exception,
                                    'Incorrect username or password'):
            self._run(target, [1, 1])

    def test_connection_refused_raises(self):
        target = self._target()
        with self.assertRaisesRegex(Exception, 'Connection refused by'):
            self._run(target, [2])

    def test_connection_timeout_raises(self):
        target = self._target()
        with self.assertRaisesRegex(Exception,
                                    'Timeout hit trying to connect to'):
            self._run(target, [3])

    def test_unexpected_eof_raises(self):
        target = self._target()
        with self.assertRaisesRegex(
                Exception, 'Unexpected error trying to connect to sftp'):
            self._run(target, [4])

    def test_upload_timeout_raises(self):
        target = self._target()
        with self.assertRaisesRegex(Exception,
                                    'Timeout expired while uploading'):
            self._run(target, [0, 1])

    def test_upload_eof_raises(self):
        target = self._target()
        with self.assertRaisesRegex(Exception, 'Unknown error during upload'):
            self._run(target, [0, 2])

    def test_unwritable_destination_raises(self):
        target = self._target()
        with self.assertRaisesRegex(
                Exception, 'Unable to write archive to destination'):
            self._run(target, [0, 3])

    def test_user_dir_is_prepended_when_not_already_there(self):
        target = self._target()
        child = MagicMock()
        # connect, pwd, put
        child.expect.side_effect = [0, 0, 0]
        child.before = 'Remote working directory: /'
        with patch('sos.upload.targets.is_executable', return_value=True), \
                patch('pexpect.spawn', return_value=child):
            self.assertTrue(target.upload_sftp(user='bob', password='pw',
                                               user_dir='/users/bob'))
        child.sendline.assert_any_call(
            f'put {self.archive} /users/bob/{self.archive_name}')

    def test_user_dir_skipped_when_already_in_it(self):
        target = self._target()
        child = MagicMock()
        child.expect.side_effect = [0, 0, 0]
        child.before = 'Remote working directory: /users/bob'
        with patch('sos.upload.targets.is_executable', return_value=True), \
                patch('pexpect.spawn', return_value=child):
            self.assertTrue(target.upload_sftp(user='bob', password='pw',
                                               user_dir='/users/bob'))
        child.sendline.assert_any_call(
            f'put {self.archive} {self.archive_name}')


@unittest.skipUnless(REQUESTS_LOADED, 'python3-requests is not installed')
class S203RedHatSftpTokenTests(TransferTestCase):
    """S2-03 - Red Hat SFTP token retrieval and delegation."""

    def _target(self, **attrs):
        defaults = {
            'upload_url': RHELUploadTarget.RH_SFTP_HOST,
            'upload_archive_name': self.archive,
        }
        target = make_target(RHELUploadTarget,
                             opts=make_opts(case_id='01234567'),
                             **{**defaults, **attrs})
        target._device_token = None
        return target

    def test_non_redhat_url_delegates_to_base(self):
        target = self._target(upload_url='sftp://sftp.example.com')
        with patch.object(UploadTarget, 'upload_sftp',
                          return_value=True) as base:
            self.assertTrue(target.upload_sftp())
        base.assert_called_once_with()

    def test_missing_requests_raises(self):
        target = self._target()
        with patch('sos.upload.targets.redhat.REQUESTS_LOADED', False):
            with self.assertRaisesRegex(
                    Exception, 'python3-requests is not installed'):
                target.upload_sftp()

    def test_device_token_credentials_are_used(self):
        target = self._target()
        target._device_token = 'devtoken'
        response = MagicMock(status_code=200, text=json.dumps(
            {'username': 'rhuser', 'token': 'rhtoken'}))
        with patch('sos.upload.targets.redhat.requests') as requests, \
                patch.object(UploadTarget, 'upload_sftp',
                             return_value=True) as base:
            requests.post.return_value = response
            self.assertTrue(target.upload_sftp())
        requests.post.assert_called_once_with(
            RH_SFTP_TOKEN_URL,
            headers={'Authorization': 'Bearer devtoken'}, timeout=10)
        base.assert_called_once_with(user='rhuser', password='rhtoken',
                                     user_dir='/users/rhuser')

    def test_device_token_is_fetched_when_absent(self):
        target = self._target()
        auth = MagicMock()
        auth.get_access_token.return_value = 'freshtoken'
        response = MagicMock(status_code=200, text=json.dumps(
            {'username': 'rhuser', 'token': 'rhtoken'}))
        with patch('sos.upload.targets.redhat.DeviceAuthorizationClass',
                   return_value=auth), \
                patch('sos.upload.targets.redhat.requests') as requests, \
                patch.object(UploadTarget, 'upload_sftp',
                             return_value=True) as base:
            requests.post.return_value = response
            self.assertTrue(target.upload_sftp())
        self.assertEqual(target._device_token, 'freshtoken')
        base.assert_called_once_with(user='rhuser', password='rhtoken',
                                     user_dir='/users/rhuser')

    def test_rejected_token_request_raises(self):
        target = self._target()
        target._device_token = 'devtoken'
        with patch('sos.upload.targets.redhat.requests') as requests:
            requests.post.return_value = MagicMock(status_code=403)
            with self.assertRaisesRegex(
                    Exception,
                    'Could not retrieve valid or anonymous credentials'):
                target.upload_sftp()

    def test_cancelled_auth_falls_back_to_anonymous(self):
        target = self._target()
        response = MagicMock(status_code=200, text=json.dumps(
            {'username': 'anon-user', 'token': 'anon-token'}))
        with patch('sos.upload.targets.redhat.DeviceAuthorizationClass',
                   side_effect=Exception('end user denied the request')), \
                patch('sos.upload.targets.redhat.requests') as requests, \
                patch.object(UploadTarget, 'upload_sftp',
                             return_value=True) as base:
            requests.post.return_value = response
            self.assertTrue(target.upload_sftp())
        requests.post.assert_called_once_with(
            RH_SFTP_TOKEN_URL, data=json.dumps({'isAnonymous': True}),
            timeout=10)
        base.assert_called_once_with(user='anon-user', password='anon-token',
                                     user_dir=None)

    def test_failed_anonymous_request_raises(self):
        target = self._target()
        with patch('sos.upload.targets.redhat.DeviceAuthorizationClass',
                   side_effect=Exception('end user denied the request')), \
                patch('sos.upload.targets.redhat.requests') as requests:
            requests.post.return_value = MagicMock(status_code=500)
            with self.assertRaisesRegex(
                    Exception,
                    'Could not retrieve valid or anonymous credentials'):
                target.upload_sftp()


@unittest.skipUnless(BOTO3_LOADED, 'python3-boto3 is not installed')
class S204S3TransferTests(TransferTestCase):
    """S2-04 - S3 object upload and key composition."""

    def _target(self, **attrs):
        defaults = {
            'upload_archive_name': self.archive,
            'upload_s3_bucket': 'mybucket',
            'upload_s3_endpoint': 'https://s3.example.com',
            'upload_s3_region': 'us-east-1',
            'upload_s3_access_key': 'accesskey',
            'upload_s3_secret_key': 'secretkey',
        }
        return make_target(UploadTarget, **{**defaults, **attrs})

    @staticmethod
    def _upload(target):
        client = MagicMock()
        with patch('sos.upload.targets.boto3') as boto3:
            boto3.client.return_value = client
            result = target.upload_s3()
        return result, boto3, client

    def test_upload_succeeds(self):
        result, _, client = self._upload(self._target())
        self.assertTrue(result)
        client.upload_file.assert_called_once_with(
            self.archive, 'mybucket', self.archive_name)

    def test_client_built_from_endpoint_and_credentials(self):
        _, boto3, _ = self._upload(self._target())
        boto3.client.assert_called_once_with(
            's3', endpoint_url='https://s3.example.com',
            region_name='us-east-1', aws_access_key_id='accesskey',
            aws_secret_access_key='secretkey')

    def test_prefix_is_joined_to_basename(self):
        target = self._target(upload_s3_object_prefix='reports')
        _, _, client = self._upload(target)
        client.upload_file.assert_called_once_with(
            self.archive, 'mybucket', f'reports/{self.archive_name}')

    def test_leading_slash_is_stripped_from_prefix(self):
        target = self._target(upload_s3_object_prefix='/reports')
        _, _, client = self._upload(target)
        client.upload_file.assert_called_once_with(
            self.archive, 'mybucket', f'reports/{self.archive_name}')

    def test_trailing_slash_prefix_is_not_doubled(self):
        target = self._target(upload_s3_object_prefix='reports/')
        _, _, client = self._upload(target)
        client.upload_file.assert_called_once_with(
            self.archive, 'mybucket', f'reports/{self.archive_name}')

    def test_bucket_slashes_are_stripped(self):
        target = self._target(upload_s3_bucket='/mybucket/')
        _, _, client = self._upload(target)
        client.upload_file.assert_called_once_with(
            self.archive, 'mybucket', self.archive_name)

    def test_upload_failure_is_wrapped(self):
        target = self._target()
        client = MagicMock()
        client.upload_file.side_effect = Exception('access denied')
        with patch('sos.upload.targets.boto3') as boto3:
            boto3.client.return_value = client
            with self.assertRaisesRegex(
                    Exception, 'Failed to upload to S3: access denied'):
                target.upload_s3()


if __name__ == '__main__':
    unittest.main()

# vim: set et ts=4 sw=4 :
