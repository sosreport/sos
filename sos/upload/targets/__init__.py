# Copyright 2024 Red Hat, Inc. Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re
import logging

from getpass import getpass
from sos import _sos as _
from sos.utilities import is_executable, TIMEOUT_DEFAULT

try:
    import requests
    REQUESTS_LOADED = True
except ImportError:
    REQUESTS_LOADED = False

try:
    import boto3
    BOTO3_LOADED = True
except ImportError:
    BOTO3_LOADED = False


class UploadTarget():
    """
    This class is designed to upload files to a distribution
    defined location. These files can be either sos reports,
    sos collections, or other kind of files like: vmcores,
    application cores, logs, etc.

    """

    desc = """
            Upload a file (can be an sos report, a must-gather, or others) to
             a distribution defined remote location
            """
    # _ prefixed class attrs are used for storing any vendor-defined defaults
    # the non-prefixed attrs are used by the upload methods, and will be set
    # to the cmdline/config file values, if provided. If not provided, then
    # those attrs will be set to the _ prefixed values as a fallback.
    # TL;DR Use _upload_* for target default values, use upload_* when wanting
    # to actual use the value in a method/override
    upload_target_name = "Generic Upload"
    upload_target_id = "generic"
    _upload_file = None
    _upload_url = None
    _upload_directory = '/'
    _upload_user = None
    _upload_password = None
    _upload_method = None
    _upload_s3_endpoint = 'https://s3.amazonaws.com'
    _upload_s3_bucket = None
    _upload_s3_access_key = None
    _upload_s3_secret_key = None
    _upload_s3_region = None
    _upload_s3_object_prefix = ''
    upload_url = None
    upload_user = None
    upload_password = None
    upload_s3_endpoint = None
    upload_s3_bucket = None
    upload_s3_access_key = None
    upload_s3_secret_key = None
    upload_s3_region = None
    upload_s3_object_prefix = None
    upload_target = None

    arg_defaults = {
        'upload_file': '',
        'case_id': '',
        'low_priority': False,
        'profiles': [],
        'upload_url': None,
        'upload_directory': None,
        'upload_user': None,
        'upload_pass': None,
        'upload_method': 'auto',
        'upload_no_ssl_verify': False,
        'upload_protocol': 'auto',
        'upload_s3_endpoint': None,
        'upload_s3_region': None,
        'upload_s3_bucket': None,
        'upload_s3_access_key': None,
        'upload_s3_secret_key': None,
        'upload_s3_object_prefix': None,
        'upload_target': None,
    }

    def __init__(self, parser=None, args=None, cmdline=None):

        self.ui_log = logging.getLogger('sos_ui')
        self.parser = parser
        self.cmdline = cmdline
        self.args = args

    def check_distribution(self):
        """This should be overridden by upload targets

        This is called by sos upload on each target type that exists, and
        is meant to return True when the upload target matches a criteria
        that indicates that is the local upload target that should be used.

        Only the first upload target to determine a match is selected"""
        return False

    def get_target_id(self):
        return self.upload_target_id

    @classmethod
    def name(cls):
        """Returns the upload target's name as a string."""
        if cls.upload_target_name:
            return cls.upload_target_name
        return cls.__name__.lower()

    def get_commons(self):
        return {
            'cmdlineopts': self.hook_commons['cmdlineopts'],
            'policy': self.hook_commons['policy'],
            'case_id': self.hook_commons['cmdlineopts'].case_id,
            'upload_directory': self.hook_commons['cmdlineopts']
            .upload_directory
        }

    def set_commons(self, commons):
        """Set common host data for the Upload targets
            to reference
        """
        self.commons = commons

    def pre_work(self, hook_commons):

        self.hook_commons = hook_commons
        self.commons = self.get_commons()
        cmdline_opts = self.commons['cmdlineopts']
        policy = self.commons['policy']

        if cmdline_opts.low_priority:
            policy._configure_low_priority()

        # Set the cmdline settings to the class attrs that are referenced later
        # The target default '_' prefixed versions of these are untouched to
        # allow fallback
        self.upload_url = cmdline_opts.upload_url
        self.upload_user = cmdline_opts.upload_user
        self.upload_directory = cmdline_opts.upload_directory
        self.upload_password = cmdline_opts.upload_pass
        self.upload_archive_name = ''

        self.upload_s3_endpoint = cmdline_opts.upload_s3_endpoint
        self.upload_s3_region = cmdline_opts.upload_s3_region
        self.upload_s3_access_key = cmdline_opts.upload_s3_access_key
        self.upload_s3_bucket = cmdline_opts.upload_s3_bucket
        self.upload_s3_object_prefix = cmdline_opts.upload_s3_object_prefix
        self.upload_s3_secret_key = cmdline_opts.upload_s3_secret_key

        # set or query for upload credentials; this needs to be done after
        # setting case id, as below methods might rely on detection of it
        if not cmdline_opts.batch and not \
                cmdline_opts.quiet:
            # Targets will need to handle the prompts for user information
            if self.get_upload_url() and \
                    not cmdline_opts.upload_protocol == 's3':
                self.prompt_for_upload_user()
                self.prompt_for_upload_password()
            elif cmdline_opts.upload_protocol == 's3':
                self.prompt_for_upload_s3_bucket()
                self.prompt_for_upload_s3_endpoint()
                self.prompt_for_upload_s3_access_key()
                self.prompt_for_upload_s3_secret_key()
            self.ui_log.info('')

    def prompt_for_upload_s3_access_key(self):
        """Should be overridden by targets to determine if an access key needs
        to be provided for upload or not
        """
        if not self.get_upload_s3_access_key():

            msg = (
                "Please provide the upload access key for bucket"
                f" {self.get_upload_s3_bucket()} via endpoint"
                f" {self.get_upload_s3_endpoint()}: "
            )
            self.upload_s3_access_key = input(_(msg))

    def prompt_for_upload_s3_secret_key(self):
        """Should be overridden by targets to determine if a secret key needs
        to be provided for upload or not
        """
        if not self.get_upload_s3_secret_key():
            msg = (
                "Please provide the upload secret key for bucket"
                f" {self.get_upload_s3_bucket()} via endpoint"
                f" {self.get_upload_s3_endpoint()}: "
            )
            self.upload_s3_secret_key = getpass(msg)

    def prompt_for_upload_s3_bucket(self):
        """Should be overridden by targets to determine if a bucket needs to
        be provided for upload or not
        """
        if not self.upload_s3_bucket:
            if self.upload_url and self.upload_url.startswith('s3://'):
                self.upload_s3_bucket = self.upload_url[5:]
            else:
                user_input = input(_("Please provide the upload bucket: "))
                self.upload_s3_bucket = user_input.strip('/')
        return self.upload_s3_bucket

    def prompt_for_upload_s3_endpoint(self):
        """Should be overridden by targets to determine if an endpoint needs
        to be provided for upload or not
        """
        default_endpoint = self._upload_s3_endpoint
        if not self.upload_s3_endpoint:
            msg = (
                "Please provide the upload endpoint for bucket"
                f" {self.get_upload_s3_bucket()}"
                f" (default: {default_endpoint}): "
            )
            user_input = input(_(msg))
            self.upload_s3_endpoint = user_input or default_endpoint
        return self.upload_s3_endpoint

    def prompt_for_upload_user(self):
        """Should be overridden by targets to determine if a user needs to
        be provided or not
        """
        if not self.get_upload_user():
            msg = f"Please provide upload user for {self.get_upload_url()}: "
            self.upload_user = input(_(msg))

    def prompt_for_upload_password(self):
        """Should be overridden by targets to determine if a password needs to
        be provided for upload or not
        """
        if not self.get_upload_password() and (self.get_upload_user() !=
                                               self._upload_user):
            msg = ("Please provide the upload password for "
                   f"{self.get_upload_user()}: ")
            self.upload_password = getpass(msg)

    def upload_archive(self, archive):
        """
        Entry point for sos attempts to upload the generated archive to a
        target or user specified location.

        Currently there is support for HTTPS, SFTP, and FTP. HTTPS uploads are
        preferred for target-defined defaults.

        Targets that need to override uploading methods should override the
        respective upload_https(), upload_sftp(), and/or upload_ftp() methods
        and should NOT override this method.

        :param archive: The archive filepath to use for upload
        :type archive: ``str``

        In order to enable this for a target, that target needs to implement
        the following:

        Required Class Attrs

        :_upload_url:     The default location to use. Note these MUST include
                          protocol header
        :_upload_user:    Default username, if any else None
        :_upload_password: Default password, if any else None

        The following Class Attrs may optionally be overidden by the Target

        :_upload_directory:     Default FTP server directory, if any


        The following methods may be overridden by ``Target`` as needed

        `prompt_for_upload_user()`
            Determines if sos should prompt for a username or not.

        `get_upload_user()`
            Determines if the default or a different username should be used

        `get_upload_https_auth()`
            Format authentication data for HTTPS uploads

        `get_upload_url_string()`
            Print a more human-friendly string than vendor URLs
        """
        self.upload_archive_name = archive
        if not self.upload_url:
            self.upload_url = self.get_upload_url()
        if not self.upload_url:
            raise Exception("No upload destination provided by upload target"
                            " or by --upload-url")
        upload_func = self._determine_upload_type()
        self.ui_log.info(
            _(f"Attempting upload to {self.get_upload_url_string()}")
        )
        return upload_func()

    def _determine_upload_type(self):
        """Based on the url provided, determine what type of upload to attempt.

        Note that this requires users to provide a FQDN address, such as
        https://myvendor.com/api or ftp://myvendor.com instead of
        myvendor.com/api or myvendor.com
        """
        prots = {
            'ftp': self.upload_ftp,
            'sftp': self.upload_sftp,
            'https': self.upload_https,
            's3': self.upload_s3
        }
        if self.commons['cmdlineopts'].upload_protocol in prots:
            return prots[self.commons['cmdlineopts'].upload_protocol]
        if '://' not in self.upload_url:
            raise Exception("Must provide protocol in upload URL")
        prot, _ = self.upload_url.split('://')
        if prot not in prots:
            raise Exception(f"Unsupported or unrecognized protocol: {prot}")
        return prots[prot]

    def get_upload_https_auth(self, user=None, password=None):
        """Formats the user/password credentials using basic auth

        :param user: The username for upload
        :type user: ``str``

        :param password: Password for `user` to use for upload
        :type password: ``str``

        :returns: The user/password auth suitable for use in requests calls
        :rtype: ``requests.auth.HTTPBasicAuth()``
        """
        if not user:
            user = self.get_upload_user()
        if not password:
            password = self.get_upload_password()

        return requests.auth.HTTPBasicAuth(user, password)

    def get_upload_s3_access_key(self):
        """Helper function to determine if we should use the target default
        upload access key or one provided by the user

        :returns: The access_key to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADS3ACCESSKEY', None) or
                self.upload_s3_access_key or
                self._upload_s3_access_key)

    def get_upload_s3_endpoint(self):
        """Helper function to determine if we should use the target default
        upload endpoint or one provided by the user

        :returns: The S3 Endpoint to use for upload
        :rtype: ``str``
        """
        if not self.upload_s3_endpoint:
            self.prompt_for_upload_s3_endpoint()
        return self.upload_s3_endpoint

    def get_upload_s3_region(self):
        """Helper function to determine if we should use the target default
        upload region or one provided by the user

        :returns: The S3 region to use for upload
        :rtype: ``str``
        """
        return self.upload_s3_region or self._upload_s3_region

    def get_upload_s3_bucket(self):
        """Helper function to determine if we should use the target default
        upload bucket or one provided by the user

        :returns: The S3 bucket to use for upload
        :rtype: ``str``
        """
        if self.upload_url and self.upload_url.startswith('s3://'):
            bucket_and_prefix = self.upload_url[5:].split('/', 1)
            self.upload_s3_bucket = bucket_and_prefix[0]
            if len(bucket_and_prefix) > 1:
                self.upload_s3_object_prefix = bucket_and_prefix[1]
        if not self.upload_s3_bucket:
            self.prompt_for_upload_s3_bucket()
        return self.upload_s3_bucket or self._upload_s3_bucket

    def get_upload_s3_object_prefix(self):
        """Helper function to determine if we should use the target default
        upload object prefix or one provided by the user

        :returns: The S3 object prefix to use for upload
        :rtype: ``str``
        """
        return self.upload_s3_object_prefix or self._upload_s3_object_prefix

    def get_upload_s3_secret_key(self):
        """Helper function to determine if we should use the target default
        upload secret key or one provided by the user

        :returns: The S3 secret key to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADS3SECRETKEY', None) or
                self.upload_s3_secret_key or
                self._upload_s3_secret_key)

    def get_upload_url(self):
        """Helper function to determine if we should use the target default
        upload url or one provided by the user

        :returns: The URL to use for upload
        :rtype: ``str``
        """
        if not self.upload_url and (
            self.upload_s3_bucket and
            self.upload_s3_access_key and
            self.upload_s3_secret_key
        ):
            bucket = self.get_upload_s3_bucket()
            prefix = self.get_upload_s3_object_prefix()
            self._upload_url = f"s3://{bucket}/{prefix}"
        return self.upload_url or self._upload_url

    def _get_obfuscated_upload_url(self, url):
        pattern = r"([^:]+://[^:]+:)([^@]+)(@.+)"
        obfuscated_url = re.sub(pattern, r'\1********\3', url)
        return obfuscated_url

    def get_upload_url_string(self):
        """Used by upload targets to potentially change the string used to
        report upload location from the URL to a more human-friendly string
        """
        return self._get_obfuscated_upload_url(self.get_upload_url())

    def get_upload_user(self):
        """Helper function to determine if we should use the target default
        upload user or one provided by the user

        :returns: The username to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADUSER', None) or
                self.upload_user or
                self._upload_user)

    def get_upload_password(self):
        """Helper function to determine if we should use the target default
        upload password or one provided by the user

        A user provided password, either via option or the 'SOSUPLOADPASSWORD'
        environment variable will have precendent over any target value

        :returns: The password to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADPASSWORD', None) or
                self.upload_password or
                self._upload_password)

    def upload_sftp(self, user=None, password=None, user_dir=None):
        """Attempts to upload the archive to an SFTP location.

        Due to the lack of well maintained, secure, and generally widespread
        python libraries for SFTP, sos will shell-out to the system's local ssh
        installation in order to handle these uploads.

        Do not override this method with one that uses python-paramiko, as the
        upstream sos team will reject any PR that includes that dependency.
        """
        # if we somehow don't have sftp available locally, fail early
        if not is_executable('sftp'):
            raise Exception('SFTP is not locally supported')

        # soft dependency on python3-pexpect, which we need to use to control
        # sftp login since as of this writing we don't have a viable solution
        # via ssh python bindings commonly available among downstreams
        try:
            import pexpect
        except ImportError as err:
            raise Exception('SFTP upload requires python3-pexpect, which is '
                            'not currently installed') from err

        sftp_connected = False

        if not user:
            user = self.get_upload_user()
        if not password:
            password = self.get_upload_password()

        # need to strip the protocol prefix here
        sftp_url = self.get_upload_url().replace('sftp://', '')
        sftp_cmd = f"sftp -oStrictHostKeyChecking=no {user}@{sftp_url}"
        ret = pexpect.spawn(sftp_cmd, encoding='utf-8')

        sftp_expects = [
            'sftp>',
            'password:',
            'Connection refused',
            pexpect.TIMEOUT,
            pexpect.EOF
        ]

        idx = ret.expect(sftp_expects, timeout=15)

        if idx == 0:
            sftp_connected = True
        elif idx == 1:
            ret.sendline(password)
            pass_expects = [
                'sftp>',
                'Permission denied',
                pexpect.TIMEOUT,
                pexpect.EOF
            ]
            sftp_connected = ret.expect(pass_expects, timeout=10) == 0
            if not sftp_connected:
                ret.close()
                raise Exception("Incorrect username or password for "
                                f"{self.get_upload_url_string()}")
        elif idx == 2:
            raise Exception("Connection refused by "
                            f"{self.get_upload_url_string()}. Incorrect port?")
        elif idx == 3:
            raise Exception("Timeout hit trying to connect to "
                            f"{self.get_upload_url_string()}")
        elif idx == 4:
            raise Exception("Unexpected error trying to connect to sftp: "
                            f"{ret.before}")

        if not sftp_connected:
            ret.close()
            raise Exception("Unable to connect via SFTP to "
                            f"{self.get_upload_url_string()}")

        # certain implementations require file to be put in the user dir
        put_cmd = (
            f"put {self.upload_archive_name} "
            f"{f'{user_dir}/' if user_dir else ''}"
            f"{self._get_sftp_upload_name()}"
        )
        ret.sendline(put_cmd)
        put_expects = [
            '100%',
            pexpect.TIMEOUT,
            pexpect.EOF,
            'No such file or directory'
        ]

        put_success = ret.expect(put_expects, timeout=180)

        if put_success == 0:
            ret.sendline('bye')
            return True
        if put_success == 1:
            raise Exception("Timeout expired while uploading")
        if put_success == 2:
            raise Exception(f"Unknown error during upload: {ret.before}")
        if put_success == 3:
            raise Exception("Unable to write archive to destination")
        raise Exception(f"Unexpected response from server: {ret.before}")

    def _get_sftp_upload_name(self):
        """If a specific file name pattern is required by the SFTP server,
        override this method in the relevant Upload Target. Otherwise the
        archive's name on disk will be used

        :returns:       Filename as it will exist on the SFTP server
        :rtype:         ``str``
        """
        fname = self.upload_archive_name.split('/')[-1]
        if self.upload_directory:
            fname = os.path.join(self.upload_directory, fname)
        return fname

    def _upload_https_put(self, archive, verify=True):
        """If upload_https() needs to use requests.put(), use this method.

        Targets should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        return requests.put(self.get_upload_url(), data=archive,
                            auth=self.get_upload_https_auth(),
                            verify=verify, timeout=TIMEOUT_DEFAULT)

    def _get_upload_headers(self):
        """Define any needed headers to be passed with the POST request here
        """
        return {}

    def _upload_https_post(self, archive, verify=True):
        """If upload_https() needs to use requests.post(), use this method.

        Targets should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        files = {
            'file': (archive.name.split('/')[-1], archive,
                     self._get_upload_headers())
        }
        return requests.post(self.get_upload_url(), files=files,
                             auth=self.get_upload_https_auth(),
                             verify=verify, timeout=TIMEOUT_DEFAULT)

    def upload_https(self):
        """Attempts to upload the archive to an HTTPS location.

        :returns: ``True`` if upload is successful
        :rtype: ``bool``

        :raises: ``Exception`` if upload was unsuccessful
        """
        if not REQUESTS_LOADED:
            raise Exception("Unable to upload due to missing python requests "
                            "library")

        with open(self.upload_archive_name, 'rb') as arc:
            if self.commons['cmdlineopts'].upload_method == 'auto':
                method = self._upload_method
            else:
                method = self.commons['cmdlineopts'].upload_method
            verify = self.commons['cmdlineopts'].upload_no_ssl_verify is False
            if method == 'put':
                r = self._upload_https_put(arc, verify)
            else:
                r = self._upload_https_post(arc, verify)
            if r.status_code not in (200, 201):
                if r.status_code == 401:
                    raise Exception(
                        "Authentication failed: invalid user credentials"
                    )
                raise Exception(f"POST request returned {r.status_code}: "
                                f"{r.reason}")
            return True

    def upload_ftp(self, url=None, directory=None, user=None, password=None):
        """Attempts to upload the archive to either the target defined or user
        provided FTP location.

        :param url: The URL to upload to
        :type url: ``str``

        :param directory: The directory on the FTP server to write to
        :type directory: ``str`` or ``None``

        :param user: The user to authenticate with
        :type user: ``str``

        :param password: The password to use for `user`
        :type password: ``str``

        :returns: ``True`` if upload is successful
        :rtype: ``bool``

        :raises: ``Exception`` if upload in unsuccessful
        """
        import ftplib
        import socket

        if not url:
            url = self.get_upload_url()
        if url is None:
            raise Exception("no FTP server specified by upload target, "
                            "use --upload-url to specify a location")

        url = url.replace('ftp://', '')

        if not user:
            user = self.get_upload_user()

        if not password:
            password = self.get_upload_password()

        if not directory:
            directory = self.upload_directory or self._upload_directory

        try:
            session = ftplib.FTP(url, user, password, timeout=15)
            if not session:
                raise Exception("connection failed, did you set a user and "
                                "password?")
            session.cwd(directory)
        except socket.timeout as err:
            raise Exception(f"timeout hit while connecting to {url}") from err
        except socket.gaierror as err:
            raise Exception(f"unable to connect to {url}") from err
        except ftplib.error_perm as err:
            errno = str(err).split()[0]
            if errno == '503':
                raise Exception(f"could not login as '{user}'") from err
            if errno == '530':
                raise Exception(f"invalid password for user '{user}'") from err
            if errno == '550':
                raise Exception("could not set upload directory to "
                                f"{directory}") from err
            raise Exception(f"error trying to establish session: {str(err)}") \
                from err

        with open(self.upload_archive_name, 'rb') as _arcfile:
            session.storbinary(
                f"STOR {self.upload_archive_name.split('/')[-1]}", _arcfile
                )
        session.quit()
        return True

    def upload_s3(self, endpoint=None, region=None, bucket=None, prefix=None,
                  access_key=None, secret_key=None):
        """Attempts to upload the archive to an S3 bucket.

        :param endpoint: The S3 endpoint to upload to
        :type endpoint: str

        :param region: The S3 region to upload to
        :type region: str

        :param bucket: The name of the S3 bucket to upload to
        :type bucket: str

        :param prefix: The prefix for the S3 object/key
        :type prefix: str

        :param access_key: The access key for the S3 bucket
        :type access_key: str

        :param secret_key: The secret key for the S3 bucket
        :type secret_key: str

        :returns: True if upload is successful
        :rtype: bool

        :raises: Exception if upload is unsuccessful
        """
        if not BOTO3_LOADED:
            raise Exception("Unable to upload due to missing python boto3 "
                            "library")

        if not endpoint:
            endpoint = self.get_upload_s3_endpoint()
        if not region:
            region = self.get_upload_s3_region()

        if not bucket:
            bucket = self.get_upload_s3_bucket().strip('/')

        if not prefix:
            prefix = self.get_upload_s3_object_prefix()
            if prefix != '' and prefix.startswith('/'):
                prefix = prefix[1:]
            if prefix != '' and not prefix.endswith('/'):
                prefix = f'{prefix}/' if prefix else ''

        if not access_key:
            access_key = self.get_upload_s3_access_key()

        if not secret_key:
            secret_key = self.get_upload_s3_secret_key()

        s3_client = boto3.client('s3', endpoint_url=endpoint,
                                 region_name=region,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key)

        try:
            key = prefix + self.upload_archive_name.split('/')[-1]
            s3_client.upload_file(self.upload_archive_name,
                                  bucket, key)
            return True
        except Exception as e:
            raise Exception(f"Failed to upload to S3: {str(e)}") from e

# vim: set et ts=4 sw=4 :
