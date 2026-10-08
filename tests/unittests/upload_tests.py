# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from sos.policies.distros.redhat import RHELPolicy
from sos.policies.distros.ubuntu import UbuntuPolicy
from sos.upload import SoSUpload
from sos.upload.targets import UploadTarget
from sos.upload.targets.redhat import RHELUploadTarget
from sos.upload.targets.ubuntu import UbuntuUploadTarget


# Mirrors SoSUpload.arg_defaults. A bare MagicMock() would make every
# option attribute truthy, which quietly sends the code down the wrong
# branch in get_upload_url() and _determine_upload_type().
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

RH_ATTACHMENTS_URL = (
    f"{RHELUploadTarget.RH_API_HOST}"
    f"{RHELUploadTarget.RH_HYDRA_ATTACHMENTS_PATH}"
)
CANONICAL_URL = 'https://files.support.canonical.com/uploads/'
ARCHIVE = '/var/tmp/sosreport-testhost-2026-09-17.tar.xz'
ARCHIVE_NAME = 'sosreport-testhost-2026-09-17.tar.xz'


# The only environment variables the get_upload_*() helpers consult.
# Tests scope just these so that everything else in os.environ stays
# available to the code under test.
SOS_UPLOAD_ENV_VARS = (
    'SOSUPLOADUSER',
    'SOSUPLOADPASSWORD',
    'SOSUPLOADS3ACCESSKEY',
    'SOSUPLOADS3SECRETKEY',
)


@contextmanager
def upload_env(**overrides):
    """Scope the upload credential variables without clearing os.environ.

    Removes only the variables listed in SOS_UPLOAD_ENV_VARS so a
    developer's shell cannot influence a result, applies any overrides,
    and restores the previous environment on exit.
    """
    with patch.dict(os.environ):
        for name in SOS_UPLOAD_ENV_VARS:
            os.environ.pop(name, None)
        os.environ.update(overrides)
        yield


def make_opts(**overrides):
    """Build a stand-in for the parsed cmdline options."""
    opts = MagicMock()
    for name, value in {**UPLOAD_ARG_DEFAULTS, **overrides}.items():
        setattr(opts, name, value)
    return opts


def make_target(cls, opts=None, **attrs):
    """Build an upload target without running __init__.

    Follows the RedHatCoreOSArchiveNameTests precedent: the instance is
    created via __new__, and the attributes that pre_work() would
    normally populate are set by hand.
    """
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


def make_upload_component(**attrs):
    """Build a SoSUpload component without running __init__."""
    comp = SoSUpload.__new__(SoSUpload)
    comp.args = None
    comp.cmdline = None
    comp.parser = None
    comp.opts = make_opts()
    comp.policy = MagicMock()
    comp.ui_log = MagicMock()
    comp.upload_target = None
    for name, value in attrs.items():
        setattr(comp, name, value)
    return comp


class UT01ObfuscatedUploadUrlTests(unittest.TestCase):
    """UT01 - URL password obfuscation."""

    def setUp(self):
        self.target = make_target(UploadTarget)

    def test_https_password_is_masked(self):
        self.assertEqual(
            self.target._get_obfuscated_upload_url(
                'https://user:sup3rs3cret@example.com/upload'),
            'https://user:********@example.com/upload')

    def test_ftp_password_is_masked(self):
        self.assertEqual(
            self.target._get_obfuscated_upload_url(
                'ftp://anon:pass123@ftp.example.com/incoming'),
            'ftp://anon:********@ftp.example.com/incoming')

    def test_url_without_credentials_is_unchanged(self):
        url = 'https://example.com/upload'
        self.assertEqual(self.target._get_obfuscated_upload_url(url), url)

    def test_port_is_not_mistaken_for_credentials(self):
        url = 'https://example.com:8080/upload'
        self.assertEqual(self.target._get_obfuscated_upload_url(url), url)

    def test_sftp_host_is_unchanged(self):
        url = RHELUploadTarget.RH_SFTP_HOST
        self.assertEqual(self.target._get_obfuscated_upload_url(url), url)


class UT02DetermineUploadTypeTests(unittest.TestCase):
    """UT02 - Upload protocol dispatch, override and error paths."""

    def test_https_url_selects_https(self):
        target = make_target(UploadTarget,
                             upload_url='https://example.com/api')
        self.assertEqual(target._determine_upload_type(),
                         target.upload_https)

    def test_ftp_url_selects_ftp(self):
        target = make_target(UploadTarget,
                             upload_url='ftp://ftp.example.com')
        self.assertEqual(target._determine_upload_type(), target.upload_ftp)

    def test_sftp_url_selects_sftp(self):
        target = make_target(UploadTarget,
                             upload_url='sftp://sftp.example.com')
        self.assertEqual(target._determine_upload_type(), target.upload_sftp)

    def test_s3_url_selects_s3(self):
        target = make_target(UploadTarget,
                             upload_url='s3://mybucket/prefix')
        self.assertEqual(target._determine_upload_type(), target.upload_s3)

    def test_protocol_option_overrides_url_scheme(self):
        target = make_target(UploadTarget,
                             opts=make_opts(upload_protocol='sftp'),
                             upload_url='https://example.com/api')
        self.assertEqual(target._determine_upload_type(), target.upload_sftp)

    def test_url_without_protocol_raises(self):
        target = make_target(UploadTarget, upload_url='example.com/api')
        with self.assertRaisesRegex(Exception,
                                    'Must provide protocol in upload URL'):
            target._determine_upload_type()

    def test_unsupported_protocol_raises(self):
        target = make_target(UploadTarget,
                             upload_url='gopher://example.com')
        with self.assertRaisesRegex(
                Exception, 'Unsupported or unrecognized protocol: gopher'):
            target._determine_upload_type()


class UT03CredentialPrecedenceTests(unittest.TestCase):
    """UT03 - Credential precedence: env > cmdline > target default."""

    def test_user_env_beats_cmdline_and_default(self):
        target = make_target(UploadTarget, upload_user='cmdline-user')
        target._upload_user = 'target-default'
        with upload_env(SOSUPLOADUSER='env-user'):
            self.assertEqual(target.get_upload_user(), 'env-user')

    def test_user_cmdline_beats_default(self):
        target = make_target(UploadTarget, upload_user='cmdline-user')
        target._upload_user = 'target-default'
        with upload_env():
            self.assertEqual(target.get_upload_user(), 'cmdline-user')

    def test_user_falls_back_to_default(self):
        target = make_target(UploadTarget)
        target._upload_user = 'target-default'
        with upload_env():
            self.assertEqual(target.get_upload_user(), 'target-default')

    def test_password_env_beats_cmdline_and_default(self):
        target = make_target(UploadTarget, upload_password='cmdline-pass')
        target._upload_password = 'target-default'
        with upload_env(SOSUPLOADPASSWORD='env-pass'):
            self.assertEqual(target.get_upload_password(), 'env-pass')

    def test_password_cmdline_beats_default(self):
        target = make_target(UploadTarget, upload_password='cmdline-pass')
        target._upload_password = 'target-default'
        with upload_env():
            self.assertEqual(target.get_upload_password(), 'cmdline-pass')

    def test_password_falls_back_to_default(self):
        target = make_target(UploadTarget)
        target._upload_password = 'target-default'
        with upload_env():
            self.assertEqual(target.get_upload_password(), 'target-default')


class UT04S3UrlAndBucketTests(unittest.TestCase):
    """UT04 - S3 URL synthesis and bucket/prefix parsing."""

    def test_bucket_and_prefix_parsed_from_url(self):
        target = make_target(UploadTarget,
                             upload_url='s3://mybucket/some/prefix')
        self.assertEqual(target.get_upload_s3_bucket(), 'mybucket')
        self.assertEqual(target.upload_s3_object_prefix, 'some/prefix')

    def test_bucket_only_url_leaves_prefix_unset(self):
        target = make_target(UploadTarget, upload_url='s3://mybucket')
        self.assertEqual(target.get_upload_s3_bucket(), 'mybucket')
        self.assertIsNone(target.upload_s3_object_prefix)

    def test_explicit_bucket_is_returned(self):
        target = make_target(UploadTarget, upload_s3_bucket='mybucket')
        self.assertEqual(target.get_upload_s3_bucket(), 'mybucket')

    def test_url_synthesised_from_bucket_and_prefix(self):
        target = make_target(UploadTarget,
                             upload_s3_bucket='mybucket',
                             upload_s3_access_key='access',
                             upload_s3_secret_key='secret',
                             upload_s3_object_prefix='reports')
        self.assertEqual(target.get_upload_url(), 's3://mybucket/reports')

    def test_url_synthesised_with_empty_prefix(self):
        target = make_target(UploadTarget,
                             upload_s3_bucket='mybucket',
                             upload_s3_access_key='access',
                             upload_s3_secret_key='secret')
        self.assertEqual(target.get_upload_url(), 's3://mybucket/')

    def test_existing_url_is_not_replaced(self):
        target = make_target(UploadTarget,
                             upload_url='https://example.com/api',
                             upload_s3_bucket='mybucket',
                             upload_s3_access_key='access',
                             upload_s3_secret_key='secret')
        self.assertEqual(target.get_upload_url(), 'https://example.com/api')

    def test_url_not_synthesised_without_keys(self):
        target = make_target(UploadTarget, upload_s3_bucket='mybucket')
        self.assertIsNone(target.get_upload_url())


class UT05BaseSftpUploadNameTests(unittest.TestCase):
    """UT05 - Base SFTP upload filename."""

    def test_basename_is_used(self):
        target = make_target(UploadTarget, upload_archive_name=ARCHIVE)
        self.assertEqual(target._get_sftp_upload_name(), ARCHIVE_NAME)

    def test_upload_directory_is_prepended(self):
        target = make_target(UploadTarget, upload_archive_name=ARCHIVE,
                             upload_directory='/incoming')
        self.assertEqual(target._get_sftp_upload_name(),
                         f'/incoming/{ARCHIVE_NAME}')

    def test_name_without_path_is_unchanged(self):
        target = make_target(UploadTarget, upload_archive_name=ARCHIVE_NAME)
        self.assertEqual(target._get_sftp_upload_name(), ARCHIVE_NAME)


class UT06MissingOptionalDepsTests(unittest.TestCase):
    """UT06 - Missing optional dependencies raise."""

    def test_upload_https_without_requests_raises(self):
        target = make_target(UploadTarget, upload_archive_name=ARCHIVE)
        with patch('sos.upload.targets.REQUESTS_LOADED', False):
            with self.assertRaisesRegex(
                    Exception, 'missing python requests library'):
                target.upload_https()

    def test_upload_s3_without_boto3_raises(self):
        target = make_target(UploadTarget, upload_archive_name=ARCHIVE)
        with patch('sos.upload.targets.BOTO3_LOADED', False):
            with self.assertRaisesRegex(
                    Exception, 'missing python boto3 library'):
                target.upload_s3()


class UT07RedHatUploadUrlTests(unittest.TestCase):
    """UT07 - Red Hat upload URL routing."""

    def test_instance_url_wins(self):
        target = make_target(RHELUploadTarget,
                             opts=make_opts(case_id='01234567'),
                             upload_url='https://custom.example.com/api')
        self.assertEqual(target.get_upload_url(),
                         'https://custom.example.com/api')

    def test_cmdline_url_is_used(self):
        opts = make_opts(case_id='01234567',
                         upload_url='https://cmdline.example.com/api')
        target = make_target(RHELUploadTarget, opts=opts)
        self.assertEqual(target.get_upload_url(),
                         'https://cmdline.example.com/api')

    def test_sftp_protocol_selects_sftp_host(self):
        opts = make_opts(case_id='01234567', upload_protocol='sftp')
        target = make_target(RHELUploadTarget, opts=opts)
        self.assertEqual(target.get_upload_url(),
                         RHELUploadTarget.RH_SFTP_HOST)

    def test_missing_case_id_falls_back_to_sftp_host(self):
        target = make_target(RHELUploadTarget, opts=make_opts(case_id=''))
        self.assertEqual(target.get_upload_url(),
                         RHELUploadTarget.RH_SFTP_HOST)

    def test_case_id_routes_to_attachments_api(self):
        target = make_target(RHELUploadTarget,
                             opts=make_opts(case_id='01234567'))
        self.assertEqual(target.get_upload_url(), RH_ATTACHMENTS_URL)


class UT08RedHatSftpUploadNameTests(unittest.TestCase):
    """UT08 - Red Hat SFTP filename prepends the case id."""

    def test_case_id_is_prepended(self):
        target = make_target(RHELUploadTarget,
                             opts=make_opts(case_id='01234567'),
                             upload_archive_name=ARCHIVE)
        self.assertEqual(target._get_sftp_upload_name(),
                         f'01234567_{ARCHIVE_NAME}')

    def test_without_case_id_basename_is_used(self):
        target = make_target(RHELUploadTarget, opts=make_opts(case_id=''),
                             upload_archive_name=ARCHIVE)
        self.assertEqual(target._get_sftp_upload_name(), ARCHIVE_NAME)

    def test_upload_directory_is_prepended_to_case_id_name(self):
        target = make_target(RHELUploadTarget,
                             opts=make_opts(case_id='01234567'),
                             upload_archive_name=ARCHIVE,
                             upload_directory='/incoming')
        self.assertEqual(target._get_sftp_upload_name(),
                         f'/incoming/01234567_{ARCHIVE_NAME}')


class UT09RedHatUrlStringAndHeadersTests(unittest.TestCase):
    """UT09 - Red Hat URL string and headers mapping."""

    def test_api_host_reports_customer_portal(self):
        target = make_target(RHELUploadTarget, upload_url=RH_ATTACHMENTS_URL)
        self.assertEqual(target.get_upload_url_string(),
                         'Red Hat Customer Portal')

    def test_sftp_host_reports_secure_ftp(self):
        target = make_target(RHELUploadTarget,
                             upload_url=RHELUploadTarget.RH_SFTP_HOST)
        self.assertEqual(target.get_upload_url_string(),
                         'Red Hat Secure FTP')

    def test_other_url_is_obfuscated(self):
        target = make_target(
            RHELUploadTarget,
            upload_url='https://user:sup3rs3cret@example.com/api')
        self.assertEqual(target.get_upload_url_string(),
                         'https://user:********@example.com/api')

    def test_api_host_sets_private_and_cache_headers(self):
        target = make_target(RHELUploadTarget, upload_url=RH_ATTACHMENTS_URL)
        self.assertEqual(target._get_upload_headers(),
                         {'isPrivate': 'false', 'cache-control': 'no-cache'})

    def test_non_api_host_sends_no_headers(self):
        target = make_target(RHELUploadTarget,
                             upload_url=RHELUploadTarget.RH_SFTP_HOST)
        self.assertEqual(target._get_upload_headers(), {})


class UT10RedHatOversizeFailoverTests(unittest.TestCase):
    """UT10 - Red Hat oversize handling and failover to SFTP."""

    def test_archive_at_limit_enables_multipart(self):
        target = make_target(RHELUploadTarget)
        target._upload_multipart = False
        with patch('os.path.getsize',
                   return_value=RHELUploadTarget._max_size_request):
            target.check_file_too_big(ARCHIVE)
        self.assertTrue(target._upload_multipart)

    def test_archive_under_limit_stays_simple(self):
        target = make_target(RHELUploadTarget)
        target._upload_multipart = False
        with patch('os.path.getsize',
                   return_value=RHELUploadTarget._max_size_request - 1):
            target.check_file_too_big(ARCHIVE)
        self.assertFalse(target._upload_multipart)

    def test_portal_failure_fails_over_to_sftp(self):
        target = make_target(RHELUploadTarget,
                             opts=make_opts(case_id='01234567'),
                             upload_url=RH_ATTACHMENTS_URL)
        with patch.object(RHELUploadTarget, 'check_file_too_big'), \
                patch.object(UploadTarget, 'upload_archive',
                             side_effect=[Exception('portal down'), True]):
            self.assertTrue(target.upload_archive(ARCHIVE))
        self.assertEqual(target.upload_url, RHELUploadTarget.RH_SFTP_HOST)

    def test_sftp_failure_is_not_retried(self):
        target = make_target(RHELUploadTarget,
                             opts=make_opts(case_id=''),
                             upload_url=RHELUploadTarget.RH_SFTP_HOST)
        with patch.object(UploadTarget, 'upload_archive',
                          side_effect=Exception('sftp down')):
            with self.assertRaisesRegex(Exception, 'sftp down'):
                target.upload_archive(ARCHIVE)


class UT11UbuntuUploadTests(unittest.TestCase):
    """UT11 - Ubuntu URL and auth handling."""

    def test_default_url_without_archive_name(self):
        target = make_target(UbuntuUploadTarget)
        self.assertEqual(target.get_upload_url(), CANONICAL_URL)

    def test_archive_name_is_appended_to_default_url(self):
        target = make_target(UbuntuUploadTarget,
                             upload_archive_name=ARCHIVE)
        self.assertEqual(target.get_upload_url(),
                         f'{CANONICAL_URL}{ARCHIVE_NAME}')

    def test_custom_url_is_delegated_to_base(self):
        target = make_target(UbuntuUploadTarget,
                             upload_url='https://example.com/upload')
        self.assertEqual(target.get_upload_url(),
                         'https://example.com/upload')

    def test_default_url_uses_static_credentials(self):
        target = make_target(UbuntuUploadTarget,
                             upload_url=f'{CANONICAL_URL}{ARCHIVE_NAME}')
        self.assertEqual(target.get_upload_https_auth(),
                         ('ubuntu', 'ubuntu'))

    def test_custom_url_uses_basic_auth(self):
        target = make_target(UbuntuUploadTarget,
                             upload_url='https://example.com/upload',
                             upload_user='alice',
                             upload_password='sup3rs3cret')
        with patch('sos.upload.targets.requests') as mock_requests, \
                upload_env():
            auth = target.get_upload_https_auth()
        mock_requests.auth.HTTPBasicAuth.assert_called_once_with(
            'alice', 'sup3rs3cret')
        self.assertIs(auth, mock_requests.auth.HTTPBasicAuth.return_value)

    def test_default_url_reports_canonical_file_server(self):
        target = make_target(UbuntuUploadTarget, upload_url=CANONICAL_URL)
        self.assertEqual(target.get_upload_url_string(),
                         'Canonical Support File Server')


class UT12TargetDiscoveryTests(unittest.TestCase):
    """UT12 - Target discovery and selection."""

    def test_load_upload_targets_finds_known_targets(self):
        comp = make_upload_component()
        targets = comp.load_upload_targets()
        self.assertIn('generic', targets)
        self.assertIn('redhat', targets)
        self.assertIn('canonical', targets)

    def test_loaded_targets_are_keyed_by_target_id(self):
        comp = make_upload_component()
        targets = comp.load_upload_targets()
        self.assertIsInstance(targets['redhat'], RHELUploadTarget)
        self.assertIsInstance(targets['canonical'], UbuntuUploadTarget)

    def test_matching_target_is_selected(self):
        generic = MagicMock()
        generic.check_distribution.return_value = False
        redhat = MagicMock()
        redhat.check_distribution.return_value = True
        redhat.name.return_value = 'Red Hat Upload Target'
        comp = make_upload_component(
            upload_targets={'generic': generic, 'redhat': redhat})
        comp.determine_upload_target()
        self.assertIs(comp.upload_target, redhat)
        self.assertEqual(comp.upload_name, 'Red Hat Upload Target')

    def test_no_match_falls_back_to_generic(self):
        generic = MagicMock()
        generic.check_distribution.return_value = False
        generic.name.return_value = 'Generic Upload'
        redhat = MagicMock()
        redhat.check_distribution.return_value = False
        comp = make_upload_component(
            upload_targets={'generic': generic, 'redhat': redhat})
        comp.determine_upload_target()
        self.assertIs(comp.upload_target, generic)
        self.assertEqual(comp.upload_name, 'Generic Upload')


class UT13CheckDistributionTests(unittest.TestCase):
    """UT13 - Distribution detection per target."""

    @staticmethod
    def _target_with_policy(target_cls, policy_cls):
        target = make_target(target_cls)
        target.commons['policy'] = policy_cls.__new__(policy_cls)
        return target

    def test_redhat_target_matches_rhel_policy(self):
        target = self._target_with_policy(RHELUploadTarget, RHELPolicy)
        self.assertTrue(target.check_distribution())

    def test_redhat_target_rejects_ubuntu_policy(self):
        target = self._target_with_policy(RHELUploadTarget, UbuntuPolicy)
        self.assertFalse(target.check_distribution())

    def test_ubuntu_target_matches_ubuntu_policy(self):
        target = self._target_with_policy(UbuntuUploadTarget, UbuntuPolicy)
        self.assertTrue(target.check_distribution())

    def test_ubuntu_target_rejects_rhel_policy(self):
        target = self._target_with_policy(UbuntuUploadTarget, RHELPolicy)
        self.assertFalse(target.check_distribution())

    def test_base_target_never_matches(self):
        target = self._target_with_policy(UploadTarget, RHELPolicy)
        self.assertFalse(target.check_distribution())


class UT14PreauthorizeTests(unittest.TestCase):
    """UT14 - --preauth token pre-authorization per target.

    Not part of the original UT01-UT13 list; added to cover the
    preauthorize() hook introduced alongside --preauth.
    """

    # Stand-in for the OIDC access token. Never validated; the auth
    # client is mocked, so any opaque string will do.
    PUMP_UP_THE_JAM_TOKEN = 'pump-up-the-jam'

    def test_base_target_declares_it_unsupported(self):
        target = make_target(UploadTarget)
        with self.assertRaises(NotImplementedError):
            target.preauthorize()

    def test_ubuntu_target_declares_it_unsupported(self):
        target = make_target(UbuntuUploadTarget)
        with self.assertRaises(NotImplementedError):
            target.preauthorize()

    def test_redhat_target_stores_the_access_token(self):
        target = make_target(RHELUploadTarget)
        target._device_token = None
        auth = MagicMock()
        auth.get_access_token.return_value = self.PUMP_UP_THE_JAM_TOKEN
        with patch('sos.upload.targets.redhat.DeviceAuthorizationClass',
                   return_value=auth) as device_auth:
            target.preauthorize()
        self.assertEqual(target._device_token,
                         self.PUMP_UP_THE_JAM_TOKEN)
        device_auth.assert_called_once_with(
            RHELUploadTarget.client_identifier_url,
            RHELUploadTarget.token_endpoint,
            Path.home())

    def test_redhat_target_requires_requests(self):
        target = make_target(RHELUploadTarget)
        with patch('sos.upload.targets.redhat.REQUESTS_LOADED', False):
            with self.assertRaisesRegex(
                    Exception, 'python3-requests is not installed'):
                target.preauthorize()

    def test_redhat_target_reports_a_cancelled_grant(self):
        target = make_target(RHELUploadTarget)
        with patch('sos.upload.targets.redhat.DeviceAuthorizationClass',
                   side_effect=Exception('end user denied the request')):
            with self.assertRaisesRegex(
                    Exception, 'Device authorization was cancelled'):
                target.preauthorize()

    def test_redhat_target_reraises_other_auth_errors(self):
        target = make_target(RHELUploadTarget)
        with patch('sos.upload.targets.redhat.DeviceAuthorizationClass',
                   side_effect=Exception('sso.redhat.com unreachable')):
            with self.assertRaisesRegex(Exception, 'unreachable'):
                target.preauthorize()

    def test_redhat_target_rejects_an_empty_token(self):
        target = make_target(RHELUploadTarget)
        target._device_token = None
        auth = MagicMock()
        auth.get_access_token.return_value = None
        with patch('sos.upload.targets.redhat.DeviceAuthorizationClass',
                   return_value=auth):
            with self.assertRaisesRegex(
                    Exception, 'Failed to obtain a valid auth token'):
                target.preauthorize()


if __name__ == '__main__':
    unittest.main()

# vim: set et ts=4 sw=4 :
