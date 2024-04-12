# Copyright (C) Steve Conklin <sconklin@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import os
import sys
import re
from sos.policies.auth import DeviceAuthorizationClass

from sos.report.plugins import RedHatPlugin
from sos.presets.redhat import (RHEL_PRESETS, RHV, RHEL, CB, RHOSP,
                                RHOCP, RH_CFME, RH_SATELLITE, AAPEDA,
                                AAPCONTROLLER)
from sos.policies.distros import LinuxPolicy, ENV_HOST_SYSROOT
from sos.policies.package_managers.rpm import RpmPackageManager
from sos.policies.package_managers.flatpak import FlatpakPackageManager
from sos.policies.package_managers import MultiPackageManager
from sos.utilities import bold
from sos import _sos as _

try:
    import requests
    REQUESTS_LOADED = True
except ImportError:
    REQUESTS_LOADED = False

OS_RELEASE = "/etc/os-release"
RHEL_RELEASE_STR = "Red Hat Enterprise Linux"


class RedHatPolicy(LinuxPolicy):
    distro = "Red Hat"
    vendor = "Red Hat"
    vendor_urls = [
        ('Distribution Website', 'https://www.redhat.com/'),
        ('Commercial Support', 'https://access.redhat.com/')
    ]
    _tmp_dir = "/var/tmp"
    _in_container = False
    name_pattern = 'friendly'
    upload_url = None
    upload_user = None
    default_container_runtime = 'podman'
    sos_pkg_name = 'sos'
    sos_bin_path = '/usr/sbin'
    client_identifier_url = "https://sso.redhat.com/auth/"\
        "realms/redhat-external/protocol/openid-connect/auth/device"
    token_endpoint = "https://sso.redhat.com/auth/realms/"\
        "redhat-external/protocol/openid-connect/token"

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)
        self.usrmove = False

        self.package_manager = MultiPackageManager(
                primary=RpmPackageManager,
                fallbacks=[FlatpakPackageManager],
                chroot=self.sysroot,
                remote_exec=remote_exec)

        self.valid_subclasses += [RedHatPlugin]

        self.pkgs = self.package_manager.packages

        # If rpm query failed, exit
        if not self.pkgs:
            sys.stderr.write("Could not obtain installed package list")
            sys.exit(1)

        self.usrmove = self.check_usrmove(self.pkgs)

        if self.usrmove:
            self.PATH = "/usr/sbin:/usr/bin:/root/bin"
        else:
            self.PATH = "/sbin:/bin:/usr/sbin:/usr/bin:/root/bin"
        self.PATH += os.pathsep + "/usr/local/bin"
        self.PATH += os.pathsep + "/usr/local/sbin"
        if not self.remote_exec:
            self.set_exec_path()
        self.load_presets()

    @classmethod
    def check(cls, remote=''):
        """This method checks to see if we are running on Red Hat. It must be
        overriden by concrete subclasses to return True when running on a
        Fedora, RHEL or other Red Hat distribution or False otherwise.

        If `remote` is provided, it should be the contents of a remote host's
        os-release, or comparable, file to be used in place of the locally
        available one.
        """
        return False

    @classmethod
    def display_distro_help(cls, section):
        if cls is not RedHatPolicy:
            super(RedHatPolicy, cls).display_distro_help(section)
            return
        section.add_text(
            'This policy is a building block for all other Red Hat family '
            'distributions. You are likely looking for one of the '
            'distributions listed below.\n'
        )

        subs = {
            'centos': CentOsPolicy,
            'rhel': RHELPolicy,
            'redhatcoreos': RedHatCoreOSPolicy,
            'fedora': FedoraPolicy
        }

        for subc in subs:
            subln = bold(f"policies.{subc}")
            section.add_text(
                f"{' ':>8}{subln:<35}{subs[subc].distro:<30}",
                newline=False
            )

    def check_usrmove(self, pkgs):
        """Test whether the running system implements UsrMove.

            If the 'filesystem' package is present, it will check that the
            version is greater than 3. If the package is not present the
            '/bin' and '/sbin' paths are checked and UsrMove is assumed
            if both are symbolic links.

            :param pkgs: a packages dictionary
        """
        if 'filesystem' not in pkgs:
            return os.path.islink('/bin') and os.path.islink('/sbin')
        else:
            filesys_version = pkgs['filesystem']['version']
            return True if filesys_version[0] == '3' else False

    def mangle_package_path(self, files):
        """Mangle paths for post-UsrMove systems.

            If the system implements UsrMove, all files will be in
            '/usr/[s]bin'. This method substitutes all the /[s]bin
            references in the 'files' list with '/usr/[s]bin'.

            :param files: the list of package managed files
        """
        paths = []

        def transform_path(path):
            # Some packages actually own paths in /bin: in this case,
            # duplicate the path as both the / and /usr version.
            skip_paths = ["/bin/rpm", "/bin/mailx"]
            if path in skip_paths:
                return (path, os.path.join("/usr", path[1:]))
            return (re.sub(r'(^)(/s?bin)', r'\1/usr\2', path),)

        if self.usrmove:
            for f in files:
                paths.extend(transform_path(f))
            return paths
        else:
            return files

    def get_tmp_dir(self, opt_tmp_dir):
        if not opt_tmp_dir:
            return self._tmp_dir
        return opt_tmp_dir


# Legal disclaimer text for Red Hat products
disclaimer_text = """
Any information provided to %(vendor)s will be treated in \
accordance with the published support policies at:\n
  %(vendor_urls)s

The generated archive may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No changes will be made to system configuration.
"""

RH_API_HOST = "https://api.access.redhat.com"
RH_SFTP_HOST = "sftp://sftp.access.redhat.com"


class RHELPolicy(RedHatPolicy):
    """
    The RHEL policy is used specifically for Red Hat Enterprise Linux, of
    any release, and not forks or derivative distributions. For example, this
    policy will be loaded for any RHEL 8 installation, but will not be loaded
    for CentOS Stream 8 or Red Hat CoreOS, for which there are separate
    policies.

    Plugins activated by installed packages will only be activated if those
    packages are installed via RPM (dnf/yum inclusive). Packages installed by
    other means are not considered by this policy.

    By default, --upload will be directed to using the SFTP location provided
    by Red Hat for technical support cases. Users who provide login credentials
    for their Red Hat Customer Portal account will have their archives uploaded
    to a user-specific directory.

    If users provide those credentials as well as a case number, --upload will
    instead attempt to directly upload archives to the referenced case, thus
    streamlining the process of providing data to technical support engineers.

    If either or both of the credentials or case number are omitted or are
    incorrect, then a temporary anonymous user will be used for upload to the
    SFTP server, and users will need to provide that information to their
    technical support engineer. This information will be printed at the end of
    the upload process for any sos report execution.
    """
    distro = RHEL_RELEASE_STR
    vendor = "Red Hat"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system and installed \
applications.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.
""" + disclaimer_text + "%(vendor_text)s\n")
    _upload_url = RH_SFTP_HOST
    _upload_method = 'post'
    _device_token = None

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)
        self.register_presets(RHEL_PRESETS)

    @classmethod
    def check(cls, remote=''):
        """Test to see if the running host is a RHEL installation.

            Checks for the presence of the "Red Hat Enterprise Linux"
            release string at the beginning of the NAME field in the
            `/etc/os-release` file and returns ``True`` if it is
            found, and ``False`` otherwise.

            :returns: ``True`` if the host is running RHEL or ``False``
                      otherwise.
        """

        if remote:
            return cls.distro in remote

        if not os.path.exists(OS_RELEASE):
            return False

        with open(OS_RELEASE, "r") as f:
            for line in f:
                if line.startswith("NAME"):
                    (name, value) = line.split("=")
                    value = value.strip("\"'")
                    if value.startswith(cls.distro):
                        return True
        return False

    def prompt_for_upload_user(self):
        if self.commons['cmdlineopts'].upload_user:
            self.ui_log.info(
                _("The option --upload-user has been deprecated in favour"
                  " of device authorization in RHEL")
            )
        if not self.case_id:
            # no case id provided => failover to SFTP
            self.upload_url = RH_SFTP_HOST
            self.ui_log.info("No case id provided, uploading to SFTP")

    def prompt_for_upload_password(self):
        # With OIDC we don't ask for user/pass anymore
        if self.commons['cmdlineopts'].upload_pass:
            self.ui_log.info(
                _("The option --upload-pass has been deprecated in favour"
                  " of device authorization in RHEL")
            )
        return

    def get_upload_url(self):
        if self.upload_url:
            return self.upload_url
        elif self.commons['cmdlineopts'].upload_url:
            return self.commons['cmdlineopts'].upload_url
        elif self.commons['cmdlineopts'].upload_protocol == 'sftp':
            return RH_SFTP_HOST
        elif not self.commons['cmdlineopts'].case_id:
            self.ui_log.info("No case id provided, uploading to SFTP")
            return RH_SFTP_HOST
        else:
            rh_case_api = "/support/v1/cases/%s/attachments"
            return RH_API_HOST + rh_case_api % self.case_id

    def _get_upload_https_auth(self):
        str_auth = f"Bearer {self._device_token}"
        return {'Authorization': str_auth}

    def _upload_https_post(self, archive, verify=True):
        """If upload_https() needs to use requests.post(), use this method.

        Policies should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        files = {
            'file': (archive.name.split('/')[-1], archive,
                     self._get_upload_headers())
        }
        # Get the access token at this point. With this,
        # we cover the cases where report generation takes
        # longer than the token timeout
        RHELAuth = DeviceAuthorizationClass(
                self.client_identifier_url,
                self.token_endpoint
            )
        self._device_token = RHELAuth.get_access_token()
        self.ui_log.info("Device authorized correctly. Uploading file to "
                         f"{self.get_upload_url_string()}")
        return requests.post(self.get_upload_url(), files=files,
                             headers=self._get_upload_https_auth(),
                             verify=verify)

    def _get_upload_headers(self):
        if self.get_upload_url().startswith(RH_API_HOST):
            return {'isPrivate': 'false', 'cache-control': 'no-cache'}
        return {}

    def get_upload_url_string(self):
        if self.get_upload_url().startswith(RH_API_HOST):
            return "Red Hat Customer Portal"
        elif self.get_upload_url().startswith(RH_SFTP_HOST):
            return "Red Hat Secure FTP"
        return self.upload_url

    def _get_sftp_upload_name(self):
        """The RH SFTP server will only automatically connect file uploads to
        cases if the filename _starts_ with the case number
        """
        fname = self.upload_archive_name.split('/')[-1]
        if self.case_id:
            fname = f"{self.case_id}_{fname}"
        if self.upload_directory:
            fname = os.path.join(self.upload_directory, fname)
        return fname

    def upload_sftp(self):  # pylint: disable=too-many-branches
        """Override the base upload_sftp to allow for setting an on-demand
        generated anonymous login for the RH SFTP server if a username and
        password are not given
        """
        if RH_SFTP_HOST.split('//')[1] not in self.get_upload_url():
            return super().upload_sftp()

        if not REQUESTS_LOADED:
            raise Exception("python3-requests is not installed and is required"
                            " for obtaining SFTP auth token.")
        _token = None
        _user = None

        # We may have a device token already if we attempted
        # to upload via http but the upload failed. So
        # lets check first if there isn't one.
        if not self._device_token:
            try:
                RHELAuth = DeviceAuthorizationClass(
                    self.client_identifier_url,
                    self.token_endpoint
                )
            except Exception as e:
                # We end up here if the user cancels the device
                # authentication in the web interface
                if "end user denied" in str(e):
                    self.ui_log.info(
                        "Device token authorization "
                        "has been cancelled by the user."
                    )
            else:
                self._device_token = RHELAuth.get_access_token()
        if self._device_token:
            self.ui_log.info("Device authorized correctly. Uploading file to"
                             f" {self.get_upload_url_string()}")

        url = RH_API_HOST + '/support/v2/sftp/token'
        ret = None
        if self._device_token:
            headers = self._get_upload_https_auth()
            ret = requests.post(url, headers=headers, timeout=10)
            if ret.status_code == 200:
                # credentials are valid
                _user = json.loads(ret.text)['username']
                _token = json.loads(ret.text)['token']
            else:
                self.ui_log.debug(
                    f"DEBUG: auth attempt failed (status: {ret.status_code}): "
                    f"{ret.json()}"
                )
                self.ui_log.error(
                    "Unable to retrieve Red Hat auth token using provided "
                    "credentials. Will try anonymous."
                )
        else:
            adata = {"isAnonymous": True}
            anon = requests.post(url, data=json.dumps(adata), timeout=10)
            if anon.status_code == 200:
                resp = json.loads(anon.text)
                _user = resp['username']
                _token = resp['token']
                self.ui_log.info(
                    _(f"User {_user} used for anonymous upload. Please inform "
                      f"your support engineer so they may retrieve the data.")
                )
            else:
                self.ui_log.debug(
                    f"DEBUG: anonymous request failed (status: "
                    f"{anon.status_code}): {anon.json()}"
                )
        if _user and _token:
            return super().upload_sftp(user=_user, password=_token)
        raise Exception("Could not retrieve valid or anonymous credentials")

    def upload_archive(self, archive):
        """Override the base upload_archive to provide for automatic failover
        from RHCP failures to the public RH dropbox
        """
        try:
            if self.upload_url and self.upload_url.startswith(RH_API_HOST) and\
                    (not self.get_upload_user() or
                     not self.get_upload_password()):
                self.upload_url = RH_SFTP_HOST
            uploaded = super().upload_archive(archive)
        except Exception as e:
            uploaded = False
            if not self.upload_url.startswith(RH_API_HOST):
                raise
            else:
                self.ui_log.error(
                    _(f"Upload to Red Hat Customer Portal failed due to "
                      f"{e}. Trying {RH_SFTP_HOST}")
                )
                self.upload_url = RH_SFTP_HOST
                uploaded = super().upload_archive(archive)
        return uploaded

    def dist_version(self):
        try:
            rr = self.package_manager.all_pkgs_by_name_regex("redhat-release*")
            pkgname = self.pkgs[rr[0]]["version"]
            # this should always map to the major version number. This will not
            # be so on RHEL 5, but RHEL 5 does not support python3 and thus
            # should never run a version of sos with this check
            return int(pkgname[0])
        except Exception:
            pass
        return False

    def probe_preset(self):
        # Emergency or rescue mode?
        for target in ["rescue", "emergency"]:
            if self.init_system.is_running(f"{target}.target", False):
                return self.find_preset(CB)
        # Package based checks
        if self.pkg_by_name("satellite-common") is not None:
            return self.find_preset(RH_SATELLITE)
        if self.pkg_by_name("rhosp-release") is not None:
            return self.find_preset(RHOSP)
        if self.pkg_by_name("cfme") is not None:
            return self.find_preset(RH_CFME)
        if self.pkg_by_name("ovirt-engine") is not None or \
                self.pkg_by_name("vdsm") is not None:
            return self.find_preset(RHV)
        if self.pkg_by_name("automation-controller-server") is not None:
            return self.find_preset(AAPCONTROLLER)
        for pkg in ['automation-eda-controller',
                    'automation-eda-controller-server']:
            if self.pkg_by_name(pkg) is not None:
                return self.find_preset(AAPEDA)

        # Vanilla RHEL is default
        return self.find_preset(RHEL)


class CentOsPolicy(RHELPolicy):
    distro = "CentOS"
    vendor = "CentOS"
    vendor_urls = [('Community Website', 'https://www.centos.org/')]


class RedHatCoreOSPolicy(RHELPolicy):
    """
    Red Hat CoreOS is a containerized host built upon Red Hat Enterprise Linux
    and as such this policy is built on top of the RHEL policy. For users, this
    should be entirely transparent as any behavior exhibited or influenced on
    RHEL systems by that policy will be seen on RHCOS systems as well.

    The one change is that this policy ensures that sos collect will deploy a
    container on RHCOS systems in order to facilitate sos report collection,
    as RHCOS discourages non-default package installation via rpm-ostree which
    is used to maintain atomicity for RHCOS nodes. The default container image
    used by this policy is the support-tools image maintained by Red Hat on
    registry.redhat.io.

    Note that this policy is only loaded when sos is directly run on an RHCOS
    node - if sos collect uses the `oc` transport (the default transport that
    will be attempted by the ocp cluster profile), then the policy loaded
    inside the launched pod will be RHEL. Again, this is expected and will not
    impact how sos report collections are performed.
    """

    distro = "Red Hat CoreOS"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.
""" + disclaimer_text + "%(vendor_text)s\n")

    containerized = True
    container_runtime = 'podman'
    container_image = 'registry.redhat.io/rhel8/support-tools'
    sos_path_strip = '/host'
    container_version_command = 'rpm -q sos'
    container_authfile = '/var/lib/kubelet/config.json'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)

    @classmethod
    def check(cls, remote=''):

        if remote:
            return 'CoreOS' in remote

        coreos = False
        if ENV_HOST_SYSROOT not in os.environ:
            return coreos
        host_release = os.environ[ENV_HOST_SYSROOT] + OS_RELEASE
        try:
            with open(host_release, 'r') as hfile:
                for line in hfile.read().splitlines():
                    coreos |= 'Red Hat Enterprise Linux CoreOS' in line
        except IOError:
            # host release file not present, will fallback to RHEL policy check
            pass
        return coreos

    def probe_preset(self):
        # As of the creation of this policy, RHCOS is only available for
        # RH OCP environments.
        return self.find_preset(RHOCP)

    def create_sos_container(self, image=None, auth=None, force_pull=False):
        _image = image or self.container_image
        _pull = '--pull=always' if force_pull else ''
        return (
            f"{self.container_runtime} run -di "
            f"--name {self.sos_container_name} --privileged --ipc=host "
            f"--net=host --pid=host -e HOST=/host "
            f"-e NAME={self.sos_container_name} -e "
            f"IMAGE={_image} {_pull} "
            f"-v /run:/run -v /var/log:/var/log "
            f"-v /etc/machine-id:/etc/machine-id "
            f"-v /etc/localtime:/etc/localtime "
            f"-v /:/host "
            f"{auth or ''} {_image}"
        )

    def set_cleanup_cmd(self):
        return f'podman rm --force {self.sos_container_name}'


class FedoraPolicy(RedHatPolicy):
    """
    The policy for Fedora based systems, regardless of spin/edition. This
    policy is based on the parent Red Hat policy, and thus will only check for
    RPM packages when considering packaged-based plugin enablement. Packages
    installed by other sources are not considered.

    There is no default --upload location for this policy. If users need to
    upload an sos report archive from a Fedora system, they will need to
    provide the location via --upload-url, and optionally login credentials
    for that location via --upload-user and --upload-pass (or the appropriate
    environment variables).
    """

    distro = "Fedora"
    vendor = "the Fedora Project"
    vendor_urls = [
        ('Community Website', 'https://fedoraproject.org/'),
        ('Community Forums', 'https://discussion.fedoraproject.org/')
    ]

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)

    @classmethod
    def check(cls, remote=''):
        """This method checks to see if we are running on Fedora. It returns
        True or False."""

        if remote:
            return cls.distro in remote

        return os.path.isfile('/etc/fedora-release')

    def fedora_version(self):
        pkg = self.pkg_by_name("fedora-release") or \
            self.package_manager.all_pkgs_by_name_regex(
                "fedora-release-.*")[-1]
        return int(pkg["version"])

# vim: set et ts=4 sw=4 :
