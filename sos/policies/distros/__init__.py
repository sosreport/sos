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
from sos.policies.runtimes.podman import PodmanContainerRuntime
from sos.policies.runtimes.docker import DockerContainerRuntime

from sos.utilities import shell_out


try:
    import requests
    REQUESTS_LOADED = True
except ImportError:
    REQUESTS_LOADED = False


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
    _use_https_streaming = False
    default_container_runtime = 'docker'
    _preferred_hash_name = None
    upload_url = None
    upload_user = None
    upload_password = None
    # collector-focused class attrs
    containerized = False
    container_image = None
    sos_path_strip = None
    sos_pkg_name = None
    sos_bin_path = '/usr/bin'
    sos_container_name = 'sos-collector-tmp'
    container_version_command = None

    def __init__(self, sysroot=None, init=None, probe_runtime=True):
        super(LinuxPolicy, self).__init__(sysroot=sysroot,
                                          probe_runtime=probe_runtime)
        self.init_kernel_modules()

        if init is not None:
            self.init_system = init
        elif os.path.isdir("/run/systemd/system/"):
            self.init_system = SystemdInit()
        else:
            self.init_system = InitSystem()

        self.runtimes = {}
        if self.probe_runtime:
            _crun = [
                PodmanContainerRuntime(policy=self),
                DockerContainerRuntime(policy=self)
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

    def default_runlevel(self):
        try:
            with open("/etc/inittab") as fp:
                pattern = r"id:(\d{1}):initdefault:"
                text = fp.read()
                return int(re.findall(pattern, text)[0])
        except (IndexError, IOError):
            return 3

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

    def init_kernel_modules(self):
        """Obtain a list of loaded kernel modules to reference later for plugin
        enablement and SoSPredicate checks
        """
        lines = shell_out("lsmod", timeout=0).splitlines()
        self.kernel_mods = [line.split()[0].strip() for line in lines]

    def pre_work(self):
        # this method will be called before the gathering begins

        cmdline_opts = self.commons['cmdlineopts']
        caseid = cmdline_opts.case_id if cmdline_opts.case_id else ""

        # Set the cmdline settings to the class attrs that are referenced later
        # The policy default '_' prefixed versions of these are untouched to
        # allow fallback
        self.upload_url = cmdline_opts.upload_url
        self.upload_user = cmdline_opts.upload_user
        self.upload_directory = cmdline_opts.upload_directory
        self.upload_password = cmdline_opts.upload_pass

        if not cmdline_opts.batch and not \
                cmdline_opts.quiet:
            try:
                if caseid:
                    self.case_id = caseid
                else:
                    self.case_id = input(_("Please enter the case id "
                                           "that you are generating this "
                                           "report for [%s]: ") % caseid)
                # Policies will need to handle the prompts for user information
                if cmdline_opts.upload and self.get_upload_url():
                    self.prompt_for_upload_user()
                    self.prompt_for_upload_password()
                self._print()
            except KeyboardInterrupt:
                self._print()
                raise

        if cmdline_opts.case_id:
            self.case_id = cmdline_opts.case_id

        return

    def prompt_for_upload_user(self):
        """Should be overridden by policies to determine if a user needs to
        be provided or not
        """
        if not self.get_upload_user():
            msg = "Please provide upload user for %s: " % self.get_upload_url()
            self.upload_user = input(_(msg))

    def prompt_for_upload_password(self):
        """Should be overridden by policies to determine if a password needs to
        be provided for upload or not
        """
        if not self.get_upload_password() and (self.get_upload_user() !=
                                               self._upload_user):
            msg = ("Please provide the upload password for %s: "
                   % self.get_upload_user())
            self.upload_password = getpass(msg)

    def upload_archive(self, archive):
        """
        Entry point for sos attempts to upload the generated archive to a
        policy or user specified location.

        Curerntly there is support for HTTPS, SFTP, and FTP. HTTPS uploads are
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
        :_use_https_streaming: Set to True if the HTTPS endpoint supports
                               streaming data

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
        self.upload_archive = archive
        if not self.upload_url:
            self.upload_url = self.get_upload_url()
        if not self.upload_url:
            raise Exception("No upload destination provided by policy or by "
                            "--upload-url")
        upload_func = self._determine_upload_type()
        print(_("Attempting upload to %s" % self.get_upload_url_string()))
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
            'https': self.upload_https
        }
        if '://' not in self.upload_url:
            raise Exception("Must provide protocol in upload URL")
        prot, url = self.upload_url.split('://')
        if prot not in prots.keys():
            raise Exception("Unsupported or unrecognized protocol: %s" % prot)
        return prots[prot]

    def get_upload_https_auth(self, user=None, password=None):
        """Formats the user/password credentials using basic auth

        :param user: The username for upload
        :type user: ``str``

        :param password: Password for `user` to use for upload
        :type password: ``str``

        :returns: The user/password auth suitable for use in reqests calls
        :rtype: ``requests.auth.HTTPBasicAuth()``
        """
        if not user:
            user = self.get_upload_user()
        if not password:
            password = self.get_upload_password()

        return requests.auth.HTTPBasicAuth(user, password)

    def get_upload_url(self):
        """Helper function to determine if we should use the policy default
        upload url or one provided by the user

        :returns: The URL to use for upload
        :rtype: ``str``
        """
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

    def upload_sftp(self):
        """Attempts to upload the archive to an SFTP location.

        Due to the lack of well maintained, secure, and generally widespread
        python libraries for SFTP, sos will shell-out to the system's local ssh
        installation in order to handle these uploads.

        Do not override this method with one that uses python-paramiko, as the
        upstream sos team will reject any PR that includes that dependency.
        """
        raise NotImplementedError("SFTP support is not yet implemented")

    def _upload_https_streaming(self, archive):
        """If upload_https() needs to use requests.put(), this method is used
        to provide streaming functionality

        Policies should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        return requests.put(self.get_upload_url(), data=archive,
                            auth=self.get_upload_https_auth())

    def _get_upload_headers(self):
        """Define any needed headers to be passed with the POST request here
        """
        return {}

    def _upload_https_no_stream(self, archive):
        """If upload_https() needs to use requests.post(), this method is used
        to provide non-streaming functionality

        Policies should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        files = {
            'file': (archive.name.split('/')[-1], archive,
                     self._get_upload_headers())
        }
        return requests.post(self.get_upload_url(), files=files,
                             auth=self.get_upload_https_auth())

    def upload_https(self):
        """Attempts to upload the archive to an HTTPS location.

        Policies may define whether this upload attempt should use streaming
        or non-streaming data by setting the `use_https_streaming` class
        attr to True

        :returns: ``True`` if upload is successful
        :rtype: ``bool``

        :raises: ``Exception`` if upload was unsuccessful
        """
        if not REQUESTS_LOADED:
            raise Exception("Unable to upload due to missing python requests "
                            "library")

        with open(self.upload_archive, 'rb') as arc:
            if not self._use_https_streaming:
                r = self._upload_https_no_stream(arc)
            else:
                r = self._upload_https_streaming(arc)
            if r.status_code != 201:
                if r.status_code == 401:
                    raise Exception(
                        "Authentication failed: invalid user credentials"
                    )
                raise Exception("POST request returned %s: %s"
                                % (r.status_code, r.reason))
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
            raise Exception("timeout hit while connecting to %s" % url)
        except socket.gaierror:
            raise Exception("unable to connect to %s" % url)
        except ftplib.error_perm as err:
            errno = str(err).split()[0]
            if errno == '503':
                raise Exception("could not login as '%s'" % user)
            if errno == '530':
                raise Exception("invalid password for user '%s'" % user)
            if errno == '550':
                raise Exception("could not set upload directory to %s"
                                % directory)
            raise Exception("error trying to establish session: %s"
                            % str(err))

        try:
            with open(self.upload_archive, 'rb') as _arcfile:
                session.storbinary(
                    "STOR %s" % self.upload_archive.split('/')[-1],
                    _arcfile
                )
            session.quit()
            return True
        except IOError:
            raise Exception("could not open archive file")

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

    def create_sos_container(self):
        """Returns the command that will create the container that will be
        used for running commands inside a container on hosts that require it.

        This will use the container runtime defined for the host type to
        launch a container. From there, we use the defined runtime to exec into
        the container's namespace.
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
        return "%s start %s" % (self.container_runtime,
                                self.sos_container_name)

    def format_container_command(self, cmd):
        """Returns the command that allows us to exec into the created
        container for sos collect.

        :param cmd: The command to run in the sos container
        :type cmd: ``str``

        :returns: The command to execute to run `cmd` in the container
        :rtype: ``str``
        """
        if self.container_runtime:
            return '%s exec %s %s' % (self.container_runtime,
                                      self.sos_container_name,
                                      cmd)
        else:
            return cmd
