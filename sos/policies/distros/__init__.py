# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re

from getpass import getpass

from sos import _sos as _
from sos.policies import Policy
from sos.policies.init_systems import InitSystem
from sos.policies.init_systems.systemd import SystemdInit
from sos.policies.runtimes.crio import CrioContainerRuntime
from sos.policies.runtimes.podman import PodmanContainerRuntime
from sos.policies.runtimes.docker import DockerContainerRuntime
from sos.policies.runtimes.lxd import LxdContainerRuntime

from sos.utilities import (shell_out, is_executable, bold,
                           sos_get_command_output)


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

# Container environment variables for detecting if we're in a container
ENV_CONTAINER = 'container'
ENV_HOST_SYSROOT = 'HOST'


class LinuxPolicy(Policy):
    """This policy is meant to be an abc class that provides common
    implementations used in Linux distros"""

    distro = "Linux"
    vendor = "None"
    PATH = "/bin:/sbin:/usr/bin:/usr/sbin"
    init = None
    # _ prefixed class attrs are used for storing any vendor-defined defaults
    # the non-prefixed attrs are used by the upload methods, and will be set
    # to the cmdline/config file values, if provided. If not provided, then
    # those attrs will be set to the _ prefixed values as a fallback.
    # TL;DR Use _upload_* for policy default values, use upload_* when wanting
    # to actual use the value in a method/override
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
    default_container_runtime = 'docker'
    _preferred_hash_name = None
    upload_url = None
    upload_user = None
    upload_password = None
    upload_s3_endpoint = None
    upload_s3_bucket = None
    upload_s3_access_key = None
    upload_s3_secret_key = None
    upload_s3_region = None
    upload_s3_object_prefix = None
    # collector-focused class attrs
    containerized = False
    container_image = None
    sos_path_strip = None
    sos_pkg_name = None
    sos_bin_path = '/usr/bin'
    sos_container_name = 'sos-collector-tmp'
    container_version_command = None
    container_authfile = None

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(LinuxPolicy, self).__init__(sysroot=sysroot,
                                          probe_runtime=probe_runtime,
                                          remote_exec=remote_exec)

        if sysroot:
            self.sysroot = sysroot
        else:
            self.sysroot = self._container_init() or '/'

        self.init_kernel_modules()

        if init is not None:
            self.init_system = init
        elif os.path.isdir("/run/systemd/system/"):
            self.init_system = SystemdInit(chroot=self.sysroot)
        else:
            self.init_system = InitSystem()

        self.runtimes = {}
        if self.probe_runtime:
            _crun = [
                PodmanContainerRuntime(policy=self),
                DockerContainerRuntime(policy=self),
                CrioContainerRuntime(policy=self),
                LxdContainerRuntime(policy=self),
            ]
            for runtime in _crun:
                if runtime.check_is_active():
                    self.runtimes[runtime.name] = runtime
                    if runtime.name == self.default_container_runtime:
                        self.runtimes['default'] = self.runtimes[runtime.name]
                    self.runtimes[runtime.name].load_container_info()

            if self.runtimes and 'default' not in self.runtimes.keys():
                # still allow plugins to query a runtime present on the system
                # even if that is not the policy default one
                idx = list(self.runtimes.keys())
                self.runtimes['default'] = self.runtimes[idx[0]]

    @classmethod
    def set_forbidden_paths(cls):
        return [
            '/etc/passwd',
            '/etc/shadow'
        ]

    def kernel_version(self):
        return self.release

    def host_name(self):
        return self.hostname

    def is_kernel_smp(self):
        return self.smp

    def get_arch(self):
        return self.machine

    def get_local_name(self):
        """Returns the name usd in the pre_work step"""
        return self.host_name()

    def sanitize_filename(self, name):
        return re.sub(r"[^-a-z,A-Z.0-9]", "", name)

    @classmethod
    def display_help(cls, section):
        if cls == LinuxPolicy:
            cls.display_self_help(section)
        else:
            section.set_title(f"{cls.distro} Distribution Policy")
            cls.display_distro_help(section)

    @classmethod
    def display_self_help(cls, section):
        section.set_title("SoS Distribution Policies")
        section.add_text(
            'Distributions supported by SoS will each have a specific policy '
            'defined for them, to ensure proper operation of SoS on those '
            'systems.'
        )

    @classmethod
    def display_distro_help(cls, section):
        if cls.__doc__ and cls.__doc__ is not LinuxPolicy.__doc__:
            section.add_text(cls.__doc__)
        else:
            section.add_text(
                '\nDetailed help information for this policy is not available'
            )

        # instantiate the requested policy so we can report more interesting
        # information like $PATH and loaded presets
        _pol = cls(None, None, False)
        section.add_text(
            f"Default --upload location: {_pol._upload_url}"
        )
        section.add_text(
            f"Default container runtime: {_pol.default_container_runtime}",
            newline=False
        )
        section.add_text(
            f"$PATH used when running report: {_pol.PATH}",
            newline=False
        )

        refsec = section.add_section('Reference URLs')
        for url in cls.vendor_urls:
            refsec.add_text(f"{' ':>8}{url[0]:<30}{url[1]:<40}", newline=False)

        presec = section.add_section('Presets Available With This Policy\n')
        presec.add_text(
            bold(
                f"{' ':>8}{'Preset Name':<20}{'Description':<45}"
                f"{'Enabled Options':<30}"
            ),
            newline=False
        )
        for preset in _pol.presets:
            _preset = _pol.presets[preset]
            _opts = ' '.join(_preset.opts.to_args())
            presec.add_text(
                f"{' ':>8}{preset:<20}{_preset.desc:<45}{_opts:<30}",
                newline=False
            )

    def _container_init(self):
        """Check if sos is running in a container and perform container
        specific initialisation based on ENV_HOST_SYSROOT.
        """
        if ENV_CONTAINER in os.environ:
            if os.environ[ENV_CONTAINER] in ['docker', 'oci', 'podman']:
                self._in_container = True
                if ENV_HOST_SYSROOT in os.environ:
                    if not os.environ[ENV_HOST_SYSROOT]:
                        # guard against blank/improperly unset values
                        return None
                    self._tmp_dir = os.path.abspath(
                        os.environ[ENV_HOST_SYSROOT] + self._tmp_dir
                    )
                    return os.environ[ENV_HOST_SYSROOT]
        return None

    def init_kernel_modules(self):
        """Obtain a list of loaded kernel modules to reference later for plugin
        enablement and SoSPredicate checks
        """
        self.kernel_mods = []
        release = os.uname().release

        # first load modules from lsmod
        lines = shell_out("lsmod", timeout=0, chroot=self.sysroot).splitlines()
        self.kernel_mods.extend([
            line.split()[0].strip() for line in lines[1:]
        ])

        # next, include kernel builtins
        builtins = self.join_sysroot(
            f"/usr/lib/modules/{release}/modules.builtin"
        )
        try:
            with open(builtins, "r") as mfile:
                for line in mfile:
                    kmod = line.split('/')[-1].split('.ko')[0]
                    self.kernel_mods.append(kmod)
        except IOError as err:
            self.soslog.warning(f"Unable to read kernel builtins: {err}")

        # finally, parse kconfig looking for specific kconfig strings that
        # have been verified to not appear in either lsmod or modules.builtin
        # regardless of how they are built
        config_strings = {
            'devlink': 'CONFIG_NET_DEVLINK',
            'dm_mod': 'CONFIG_BLK_DEV_DM'
        }

        booted_config = self.join_sysroot(f"/boot/config-{release}")
        kconfigs = []
        try:
            with open(booted_config, "r") as kfile:
                for line in kfile:
                    if '=y' in line:
                        kconfigs.append(line.split('=y')[0])
        except IOError as err:
            self.soslog.warning(f"Unable to read booted kernel config: {err}")

        for builtin in config_strings:
            if config_strings[builtin] in kconfigs:
                self.kernel_mods.append(builtin)

    def join_sysroot(self, path):
        if self.sysroot and self.sysroot != '/':
            path = os.path.join(self.sysroot, path.lstrip('/'))
        return path

    def pre_work(self):
        # this method will be called before the gathering begins

        cmdline_opts = self.commons['cmdlineopts']
        caseid = cmdline_opts.case_id if cmdline_opts.case_id else ""

        if cmdline_opts.low_priority:
            self._configure_low_priority()

        # Set the cmdline settings to the class attrs that are referenced later
        # The policy default '_' prefixed versions of these are untouched to
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

        # set or query for case id
        if not cmdline_opts.batch and not \
                cmdline_opts.quiet:
            try:
                if caseid:
                    self.commons['cmdlineopts'].case_id = caseid
                else:
                    self.commons['cmdlineopts'].case_id = input(
                        _("Optionally, please enter the case id that you are "
                          "generating this report for [%s]: ") % caseid
                    )
            except KeyboardInterrupt:
                raise
        if cmdline_opts.case_id:
            self.case_id = cmdline_opts.case_id

        # set or query for upload credentials; this needs to be done after
        # setting case id, as below methods might rely on detection of it
        if not cmdline_opts.batch and not \
                cmdline_opts.quiet:
            try:
                # Policies will need to handle the prompts for user information
                if cmdline_opts.upload and self.get_upload_url() and \
                        not cmdline_opts.upload_protocol == 's3':
                    self.prompt_for_upload_user()
                    self.prompt_for_upload_password()
                elif cmdline_opts.upload_protocol == 's3':
                    self.prompt_for_upload_s3_bucket()
                    self.prompt_for_upload_s3_endpoint()
                    self.prompt_for_upload_s3_access_key()
                    self.prompt_for_upload_s3_secret_key()
                self.ui_log.info('')
            except KeyboardInterrupt:
                raise

        return

    def _configure_low_priority(self):
        """Used to constrain sos to a 'low priority' execution, potentially
        letting individual policies set their own definition of what that is.

        By default, this will attempt to assign sos to an idle io class via
        ionice if available. We will also renice our own pid to 19 in order to
        not cause competition with other host processes for CPU time.
        """
        _pid = os.getpid()
        if is_executable('ionice'):
            ret = sos_get_command_output(
                f"ionice -c3 -p {_pid}", timeout=5
            )
            if ret['status'] == 0:
                self.soslog.info('Set IO class to idle')
            else:
                msg = (f"Error setting IO class to idle: {ret['output']} "
                       f"(exit code {ret['status']})")
                self.soslog.error(msg)
        else:
            self.ui_log.warning(
                "Warning: unable to constrain report to idle IO class: "
                "ionice is not available."
            )

        try:
            os.nice(20)
            self.soslog.info('Set niceness of report to 19')
        except Exception as err:
            self.soslog.error(f"Error setting report niceness to 19: {err}")

    def prompt_for_upload_s3_access_key(self):
        """Should be overridden by policies to determine if an access key needs
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
        """Should be overridden by policies to determine if a secret key needs
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
        """Should be overridden by policies to determine if a bucket needs to
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
        """Should be overridden by policies to determine if an endpoint needs
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
        """Should be overridden by policies to determine if a user needs to
        be provided or not
        """
        if not self.get_upload_user():
            msg = f"Please provide upload user for {self.get_upload_url()}: "
            self.upload_user = input(_(msg))

    def prompt_for_upload_password(self):
        """Should be overridden by policies to determine if a password needs to
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
        policy or user specified location.

        Currently there is support for HTTPS, SFTP, and FTP. HTTPS uploads are
        preferred for policy-defined defaults.

        Policies that need to override uploading methods should override the
        respective upload_https(), upload_sftp(), and/or upload_ftp() methods
        and should NOT override this method.

        :param archive: The archive filepath to use for upload
        :type archive: ``str``

        In order to enable this for a policy, that policy needs to implement
        the following:

        Required Class Attrs

        :_upload_url:     The default location to use. Note these MUST include
                          protocol header
        :_upload_user:    Default username, if any else None
        :_upload_password: Default password, if any else None

        The following Class Attrs may optionally be overidden by the Policy

        :_upload_directory:     Default FTP server directory, if any


        The following methods may be overridden by ``Policy`` as needed

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
            raise Exception("No upload destination provided by policy or by "
                            "--upload-url")
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
        if self.commons['cmdlineopts'].upload_protocol in prots.keys():
            return prots[self.commons['cmdlineopts'].upload_protocol]
        elif '://' not in self.upload_url:
            raise Exception("Must provide protocol in upload URL")
        prot, url = self.upload_url.split('://')
        if prot not in prots.keys():
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
        """Helper function to determine if we should use the policy default
        upload access key or one provided by the user

        :returns: The access_key to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADS3ACCESSKEY', None) or
                self.upload_s3_access_key or
                self._upload_s3_access_key)

    def get_upload_s3_endpoint(self):
        """Helper function to determine if we should use the policy default
        upload endpoint or one provided by the user

        :returns: The S3 Endpoint to use for upload
        :rtype: ``str``
        """
        if not self.upload_s3_endpoint:
            self.prompt_for_upload_s3_endpoint()
        return self.upload_s3_endpoint

    def get_upload_s3_region(self):
        """Helper function to determine if we should use the policy default
        upload region or one provided by the user

        :returns: The S3 region to use for upload
        :rtype: ``str``
        """
        return self.upload_s3_region or self._upload_s3_region

    def get_upload_s3_bucket(self):
        """Helper function to determine if we should use the policy default
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
        """Helper function to determine if we should use the policy default
        upload object prefix or one provided by the user

        :returns: The S3 object prefix to use for upload
        :rtype: ``str``
        """
        return self.upload_s3_object_prefix or self._upload_s3_object_prefix

    def get_upload_s3_secret_key(self):
        """Helper function to determine if we should use the policy default
        upload secret key or one provided by the user

        :returns: The S3 secret key to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADS3SECRETKEY', None) or
                self.upload_s3_secret_key or
                self._upload_s3_secret_key)

    def get_upload_url(self):
        """Helper function to determine if we should use the policy default
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

    def get_upload_url_string(self):
        """Used by distro policies to potentially change the string used to
        report upload location from the URL to a more human-friendly string
        """
        return self.get_upload_url()

    def get_upload_user(self):
        """Helper function to determine if we should use the policy default
        upload user or one provided by the user

        :returns: The username to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADUSER', None) or
                self.upload_user or
                self._upload_user)

    def get_upload_password(self):
        """Helper function to determine if we should use the policy default
        upload password or one provided by the user

        A user provided password, either via option or the 'SOSUPLOADPASSWORD'
        environment variable will have precendent over any policy value

        :returns: The password to use for upload
        :rtype: ``str``
        """
        return (os.getenv('SOSUPLOADPASSWORD', None) or
                self.upload_password or
                self._upload_password)

    def upload_sftp(self, user=None, password=None):
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
        except ImportError:
            raise Exception('SFTP upload requires python3-pexpect, which is '
                            'not currently installed')

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
            u'sftp>',
            u'password:',
            u'Connection refused',
            pexpect.TIMEOUT,
            pexpect.EOF
        ]

        idx = ret.expect(sftp_expects, timeout=15)

        if idx == 0:
            sftp_connected = True
        elif idx == 1:
            ret.sendline(password)
            pass_expects = [
                u'sftp>',
                u'Permission denied',
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

        put_cmd = (f'put {self.upload_archive_name} '
                   f'{self._get_sftp_upload_name()}')
        ret.sendline(put_cmd)

        put_expects = [
            u'100%',
            pexpect.TIMEOUT,
            pexpect.EOF,
            u'No such file or directory'
        ]

        put_success = ret.expect(put_expects, timeout=180)

        if put_success == 0:
            ret.sendline('bye')
            return True
        elif put_success == 1:
            raise Exception("Timeout expired while uploading")
        elif put_success == 2:
            raise Exception(f"Unknown error during upload: {ret.before}")
        elif put_success == 3:
            raise Exception("Unable to write archive to destination")
        else:
            raise Exception(f"Unexpected response from server: {ret.before}")

    def _get_sftp_upload_name(self):
        """If a specific file name pattern is required by the SFTP server,
        override this method in the relevant Policy. Otherwise the archive's
        name on disk will be used

        :returns:       Filename as it will exist on the SFTP server
        :rtype:         ``str``
        """
        fname = self.upload_archive_name.split('/')[-1]
        if self.upload_directory:
            fname = os.path.join(self.upload_directory, fname)
        return fname

    def _upload_https_put(self, archive, verify=True):
        """If upload_https() needs to use requests.put(), use this method.

        Policies should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        return requests.put(self.get_upload_url(), data=archive,
                            auth=self.get_upload_https_auth(),
                            verify=verify)

    def _get_upload_headers(self):
        """Define any needed headers to be passed with the POST request here
        """
        return {}

    def _upload_https_post(self, archive, verify=True):
        """If upload_https() needs to use requests.post(), use this method.

        Policies should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        files = {
            'file': (archive.name.split('/')[-1], archive,
                     self._get_upload_headers())
        }
        return requests.post(self.get_upload_url(), files=files,
                             auth=self.get_upload_https_auth(),
                             verify=verify)

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
            if r.status_code != 200 and r.status_code != 201:
                if r.status_code == 401:
                    raise Exception(
                        "Authentication failed: invalid user credentials"
                    )
                raise Exception(f"POST request returned {r.status_code}: "
                                f"{r.reason}")
            return True

    def upload_ftp(self, url=None, directory=None, user=None, password=None):
        """Attempts to upload the archive to either the policy defined or user
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
        try:
            import ftplib
            import socket
        except ImportError:
            # socket is part of the standard library, should only fail here on
            # ftplib
            raise Exception("missing python ftplib library")

        if not url:
            url = self.get_upload_url()
        if url is None:
            raise Exception("no FTP server specified by policy, use --upload-"
                            "url to specify a location")

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
        except socket.timeout:
            raise Exception(f"timeout hit while connecting to {url}")
        except socket.gaierror:
            raise Exception(f"unable to connect to {url}")
        except ftplib.error_perm as err:
            errno = str(err).split()[0]
            if errno == '503':
                raise Exception(f"could not login as '{user}'")
            if errno == '530':
                raise Exception(f"invalid password for user '{user}'")
            if errno == '550':
                raise Exception("could not set upload directory to "
                                f"{directory}")
            raise Exception(f"error trying to establish session: {str(err)}")

        try:
            with open(self.upload_archive_name, 'rb') as _arcfile:
                session.storbinary(
                    f"STOR {self.upload_archive_name.split('/')[-1]}",
                    _arcfile
                )
            session.quit()
            return True
        except IOError:
            raise Exception("could not open archive file")

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

    def set_sos_prefix(self):
        """If sosreport commands need to always be prefixed with something,
        for example running in a specific container image, then it should be
        defined here.

        If no prefix should be set, return an empty string instead of None.
        """
        return ''

    def set_cleanup_cmd(self):
        """If a host requires additional cleanup, the command should be set and
        returned here
        """
        return ''

    def create_sos_container(self, image=None, auth=None, force_pull=False):
        """Returns the command that will create the container that will be
        used for running commands inside a container on hosts that require it.

        This will use the container runtime defined for the host type to
        launch a container. From there, we use the defined runtime to exec into
        the container's namespace.

        :param image:   The name of the image if not using the policy default
        :type image:    ``str`` or ``None``

        :param auth:    The auth string required by the runtime to pull an
                        image from the registry
        :type auth:     ``str`` or ``None``

        :param force_pull:  Should the runtime forcibly pull the image
        :type force_pull:   ``bool``

        :returns:   The command to execute to launch the temp container
        :rtype:     ``str``
        """
        return ''

    def restart_sos_container(self):
        """Restarts the container created for sos collect if it has stopped.

        This is called immediately after create_sos_container() as the command
        to create the container will exit and the container will stop. For
        current container runtimes, subsequently starting the container will
        default to opening a bash shell in the container to keep it running,
        thus allowing us to exec into it again.
        """
        return f"{self.container_runtime} start {self.sos_container_name}"

    def format_container_command(self, cmd):
        """Returns the command that allows us to exec into the created
        container for sos collect.

        :param cmd: The command to run in the sos container
        :type cmd: ``str``

        :returns: The command to execute to run `cmd` in the container
        :rtype: ``str``
        """
        if self.container_runtime:
            return (f'{self.container_runtime} exec {self.sos_container_name} '
                    f'{cmd}')
        else:
            return cmd


class GenericLinuxPolicy(LinuxPolicy):
    """This Policy will be returned if no other policy can be loaded. This
    should allow for IndependentPlugins to be executed on any system"""

    vendor_urls = [('Upstream Project', 'https://github.com/sosreport/sos')]
    vendor = 'SoS'
    vendor_text = ('SoS was unable to determine that the distribution of this '
                   'system is supported, and has loaded a generic '
                   'configuration. This may not provide desired behavior, and '
                   'users are encouraged to request a new distribution-specifc'
                   ' policy at the GitHub project above.\n')


# vim: set et ts=4 sw=4 :
