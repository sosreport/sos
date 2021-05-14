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

from sos.report.plugins import RedHatPlugin
from sos.presets.redhat import (RHEL_PRESETS, ATOMIC_PRESETS, RHV, RHEL,
                                CB, RHOSP, RHOCP, RH_CFME, RH_SATELLITE,
                                ATOMIC)
from sos.policies.distros import LinuxPolicy
from sos.policies.package_managers.rpm import RpmPackageManager
from sos import _sos as _

try:
    import requests
    REQUESTS_LOADED = True
except ImportError:
    REQUESTS_LOADED = False

OS_RELEASE = "/etc/os-release"
RHEL_RELEASE_STR = "Red Hat Enterprise Linux"
ATOMIC_RELEASE_STR = "Atomic"


class RedHatPolicy(LinuxPolicy):
    distro = "Red Hat"
    vendor = "Red Hat"
    vendor_urls = [
        ('Distribution Website', 'https://www.redhat.com/'),
        ('Commercial Support', 'https://www.access.redhat.com/')
    ]
    _redhat_release = '/etc/redhat-release'
    _tmp_dir = "/var/tmp"
    _in_container = False
    _host_sysroot = '/'
    default_scl_prefix = '/opt/rh'
    name_pattern = 'friendly'
    upload_url = None
    upload_user = None
    default_container_runtime = 'podman'
    sos_pkg_name = 'sos'
    sos_bin_path = '/usr/sbin'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RedHatPolicy, self).__init__(sysroot=sysroot, init=init,
                                           probe_runtime=probe_runtime)
        self.usrmove = False
        # need to set _host_sysroot before PackageManager()
        if sysroot:
            self._container_init()
            self._host_sysroot = sysroot
        else:
            sysroot = self._container_init()

        self.package_manager = RpmPackageManager(chroot=sysroot,
                                                 remote_exec=remote_exec)

        self.valid_subclasses += [RedHatPlugin]

        self.pkgs = self.package_manager.all_pkgs()

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

    def _container_init(self):
        """Check if sos is running in a container and perform container
        specific initialisation based on ENV_HOST_SYSROOT.
        """
        if ENV_CONTAINER in os.environ:
            if os.environ[ENV_CONTAINER] in ['docker', 'oci', 'podman']:
                self._in_container = True
        if ENV_HOST_SYSROOT in os.environ:
            self._host_sysroot = os.environ[ENV_HOST_SYSROOT]
        use_sysroot = self._in_container and self._host_sysroot is not None
        if use_sysroot:
            host_tmp_dir = os.path.abspath(self._host_sysroot + self._tmp_dir)
            self._tmp_dir = host_tmp_dir
        return self._host_sysroot if use_sysroot else None

    def runlevel_by_service(self, name):
        from subprocess import Popen, PIPE
        ret = []
        p = Popen("LC_ALL=C /sbin/chkconfig --list %s" % name,
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  bufsize=-1,
                  close_fds=True)
        out, err = p.communicate()
        if err:
            return ret
        for tabs in out.split()[1:]:
            try:
                (runlevel, onoff) = tabs.split(":", 1)
            except IndexError:
                pass
            else:
                if onoff == "on":
                    ret.append(int(runlevel))
        return ret

    def get_tmp_dir(self, opt_tmp_dir):
        if not opt_tmp_dir:
            return self._tmp_dir
        return opt_tmp_dir


# Container environment variables on Red Hat systems.
ENV_CONTAINER = 'container'
ENV_HOST_SYSROOT = 'HOST'

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

RH_API_HOST = "https://access.redhat.com"
RH_SFTP_HOST = "sftp://sftp.access.redhat.com"


class RHELPolicy(RedHatPolicy):
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

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RHELPolicy, self).__init__(sysroot=sysroot, init=init,
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
            return
        # Not using the default, so don't call this prompt for RHCP
        if self.commons['cmdlineopts'].upload_url:
            super(RHELPolicy, self).prompt_for_upload_user()
            return
        if self.case_id and not self.get_upload_user():
            self.upload_user = input(_(
                "Enter your Red Hat Customer Portal username for uploading ["
                "empty for anonymous SFTP]: ")
            )

    def get_upload_url(self):
        if self.upload_url:
            return self.upload_url
        elif self.commons['cmdlineopts'].upload_url:
            return self.commons['cmdlineopts'].upload_url
        elif self.commons['cmdlineopts'].upload_protocol == 'sftp':
            return RH_SFTP_HOST
        else:
            rh_case_api = "/hydra/rest/cases/%s/attachments"
            return RH_API_HOST + rh_case_api % self.case_id

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
        if self.case_id:
            return "%s_%s" % (self.case_id,
                              self.upload_archive_name.split('/')[-1])
        return self.upload_archive_name

    def upload_sftp(self):
        """Override the base upload_sftp to allow for setting an on-demand
        generated anonymous login for the RH SFTP server if a username and
        password are not given
        """
        if RH_SFTP_HOST.split('//')[1] not in self.get_upload_url():
            return super(RHELPolicy, self).upload_sftp()

        if not REQUESTS_LOADED:
            raise Exception("python3-requests is not installed and is required"
                            " for obtaining SFTP auth token.")
        _token = None
        _user = None
        # we have a username and password, but we need to reset the password
        # to be the token returned from the auth endpoint
        if self.get_upload_user() and self.get_upload_password():
            url = RH_API_HOST + '/hydra/rest/v1/sftp/token'
            auth = self.get_upload_https_auth()
            ret = requests.get(url, auth=auth, timeout=10)
            if ret.status_code == 200:
                # credentials are valid
                _user = self.get_upload_user()
                _token = json.loads(ret.text)['token']
            else:
                print("Unable to retrieve Red Hat auth token using provided "
                      "credentials. Will try anonymous.")
        # we either do not have a username or password/token, or both
        if not _token:
            aurl = RH_API_HOST + '/hydra/rest/v1/sftp/token?isAnonymous=true'
            anon = requests.get(aurl, timeout=10)
            if anon.status_code == 200:
                resp = json.loads(anon.text)
                _user = resp['username']
                _token = resp['token']
                print("Using anonymous user %s for upload. Please inform your "
                      "support engineer." % _user)
        if _user and _token:
            return super(RHELPolicy, self).upload_sftp(user=_user,
                                                       password=_token)
        raise Exception("Could not retrieve valid or anonymous credentials")

    def upload_archive(self, archive):
        """Override the base upload_archive to provide for automatic failover
        from RHCP failures to the public RH dropbox
        """
        try:
            if not self.get_upload_user() or not self.get_upload_password():
                self.upload_url = RH_SFTP_HOST
            uploaded = super(RHELPolicy, self).upload_archive(archive)
        except Exception:
            uploaded = False
            if not self.upload_url.startswith(RH_API_HOST):
                raise
            else:
                print("Upload to Red Hat Customer Portal failed. Trying %s"
                      % RH_SFTP_HOST)
                self.upload_url = RH_SFTP_HOST
                uploaded = super(RHELPolicy, self).upload_archive(archive)
        return uploaded

    def dist_version(self):
        try:
            rr = self.package_manager.all_pkgs_by_name_regex("redhat-release*")
            pkgname = self.pkgs[rr[0]]["version"]
            if pkgname[0] == "4":
                return 4
            elif pkgname[0] in ["5Server", "5Client"]:
                return 5
            elif pkgname[0] == "6":
                return 6
            elif pkgname[0] == "7":
                return 7
            elif pkgname[0] == "8":
                return 8
        except Exception:
            pass
        return False

    def probe_preset(self):
        # Emergency or rescue mode?
        for target in ["rescue", "emergency"]:
            if self.init_system.is_running("%s.target" % target):
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

        # Vanilla RHEL is default
        return self.find_preset(RHEL)


class CentOsPolicy(RHELPolicy):
    distro = "CentOS"
    vendor = "CentOS"
    vendor_urls = [('Community Website', 'https://www.centos.org/')]


class RedHatAtomicPolicy(RHELPolicy):
    distro = "Red Hat Atomic Host"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.
""" + disclaimer_text + "%(vendor_text)s\n")

    containerzed = True
    container_runtime = 'docker'
    container_image = 'registry.access.redhat.com/rhel7/support-tools'
    sos_path_strip = '/host'
    container_version_command = 'rpm -q sos'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RedHatAtomicPolicy, self).__init__(sysroot=sysroot, init=init,
                                                 probe_runtime=probe_runtime,
                                                 remote_exec=remote_exec)
        self.register_presets(ATOMIC_PRESETS)

    @classmethod
    def check(cls, remote=''):

        if remote:
            return cls.distro in remote

        atomic = False
        if ENV_HOST_SYSROOT not in os.environ:
            return atomic
        host_release = os.environ[ENV_HOST_SYSROOT] + cls._redhat_release
        if not os.path.exists(host_release):
            return False
        try:
            for line in open(host_release, "r").read().splitlines():
                atomic |= ATOMIC_RELEASE_STR in line
        except IOError:
            pass
        return atomic

    def probe_preset(self):
        if self.pkg_by_name('atomic-openshift'):
            return self.find_preset(RHOCP)

        return self.find_preset(ATOMIC)

    def create_sos_container(self):
        _cmd = ("{runtime} run -di --name {name} --privileged --ipc=host"
                " --net=host --pid=host -e HOST=/host -e NAME={name} -e "
                "IMAGE={image} -v /run:/run -v /var/log:/var/log -v "
                "/etc/machine-id:/etc/machine-id -v "
                "/etc/localtime:/etc/localtime -v /:/host {image}")
        return _cmd.format(runtime=self.container_runtime,
                           name=self.sos_container_name,
                           image=self.container_image)

    def set_cleanup_cmd(self):
        return 'docker rm --force sos-collector-tmp'


class RedHatCoreOSPolicy(RHELPolicy):
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

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RedHatCoreOSPolicy, self).__init__(sysroot=sysroot, init=init,
                                                 probe_runtime=probe_runtime,
                                                 remote_exec=remote_exec)

    @classmethod
    def check(cls, remote=''):

        if remote:
            return 'CoreOS' in remote

        coreos = False
        if ENV_HOST_SYSROOT not in os.environ:
            return coreos
        host_release = os.environ[ENV_HOST_SYSROOT] + cls._redhat_release
        try:
            for line in open(host_release, 'r').read().splitlines():
                coreos |= 'Red Hat Enterprise Linux CoreOS' in line
        except IOError:
            pass
        return coreos

    def probe_preset(self):
        # As of the creation of this policy, RHCOS is only available for
        # RH OCP environments.
        return self.find_preset(RHOCP)

    def create_sos_container(self):
        _cmd = ("{runtime} run -di --name {name} --privileged --ipc=host"
                " --net=host --pid=host -e HOST=/host -e NAME={name} -e "
                "IMAGE={image} -v /run:/run -v /var/log:/var/log -v "
                "/etc/machine-id:/etc/machine-id -v "
                "/etc/localtime:/etc/localtime -v /:/host {image}")
        return _cmd.format(runtime=self.container_runtime,
                           name=self.sos_container_name,
                           image=self.container_image)

    def set_cleanup_cmd(self):
        return 'podman rm --force %s' % self.sos_container_name


class CentOsAtomicPolicy(RedHatAtomicPolicy):
    distro = "CentOS Atomic Host"
    vendor = "CentOS"
    vendor_urls = [('Community Website', 'https://www.centos.org/')]


class FedoraPolicy(RedHatPolicy):

    distro = "Fedora"
    vendor = "the Fedora Project"
    vendor_urls = [
        ('Community Website', 'https://fedoraproject.org/'),
        ('Community Forums', 'https://discussion.fedoraproject.org/')
    ]

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(FedoraPolicy, self).__init__(sysroot=sysroot, init=init,
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
            self.all_pkgs_by_name_regex("fedora-release-.*")[-1]
        return int(pkg["version"])

# vim: set et ts=4 sw=4 :
