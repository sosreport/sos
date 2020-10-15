# Copyright (C) Steve Conklin <sconklin@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import sys
import re

from sos.report.plugins import RedHatPlugin
from sos.policies import LinuxPolicy, PackageManager, PresetDefaults
from sos import _sos as _
from sos.options import SoSOptions

OS_RELEASE = "/etc/os-release"


class RedHatPolicy(LinuxPolicy):
    distro = "Red Hat"
    vendor = "Red Hat"
    vendor_url = "https://www.redhat.com/"
    _redhat_release = '/etc/redhat-release'
    _tmp_dir = "/var/tmp"
    _rpmq_cmd = 'rpm -qa --queryformat "%{NAME}|%{VERSION}|%{RELEASE}\\n"'
    _rpmql_cmd = 'rpm -qal'
    _rpmv_cmd = 'rpm -V'
    _rpmv_filter = ["debuginfo", "-devel"]
    _in_container = False
    _host_sysroot = '/'
    default_scl_prefix = '/opt/rh'
    name_pattern = 'friendly'
    upload_url = 'dropbox.redhat.com'
    upload_user = 'anonymous'
    upload_directory = '/incoming'
    default_container_runtime = 'podman'
    sos_pkg_name = 'sos'
    sos_bin_path = '/usr/sbin'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RedHatPolicy, self).__init__(sysroot=sysroot, init=init,
                                           probe_runtime=probe_runtime)
        self.ticket_number = ""
        self.usrmove = False
        # need to set _host_sysroot before PackageManager()
        if sysroot:
            self._container_init()
            self._host_sysroot = sysroot
        else:
            sysroot = self._container_init()

        self.package_manager = PackageManager(query_command=self._rpmq_cmd,
                                              verify_command=self._rpmv_cmd,
                                              verify_filter=self._rpmv_filter,
                                              files_command=self._rpmql_cmd,
                                              chroot=sysroot,
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
            if os.environ[ENV_CONTAINER] in ['docker', 'oci']:
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

_opts_verify = SoSOptions(verify=True)
_opts_all_logs = SoSOptions(all_logs=True)
_opts_all_logs_verify = SoSOptions(all_logs=True, verify=True)
_cb_profiles = ['boot', 'storage', 'system']
_cb_plugopts = ['boot.all-images=on', 'rpm.rpmva=on', 'rpm.rpmdb=on']

RHEL_RELEASE_STR = "Red Hat Enterprise Linux"

RHV = "rhv"
RHV_DESC = "Red Hat Virtualization"

RHEL = "rhel"
RHEL_DESC = RHEL_RELEASE_STR

RHOSP = "rhosp"
RHOSP_DESC = "Red Hat OpenStack Platform"

RHOCP = "ocp"
RHOCP_DESC = "OpenShift Container Platform by Red Hat"
RHOSP_OPTS = SoSOptions(plugopts=[
                             'process.lsof=off',
                             'networking.ethtool_namespaces=False',
                             'networking.namespaces=200'])

RH_CFME = "cfme"
RH_CFME_DESC = "Red Hat CloudForms"

RH_SATELLITE = "satellite"
RH_SATELLITE_DESC = "Red Hat Satellite"
SAT_OPTS = SoSOptions(log_size=100, plugopts=['apache.log=on'])

CB = "cantboot"
CB_DESC = "For use when normal system startup fails"
CB_OPTS = SoSOptions(
            verify=True, all_logs=True, profiles=_cb_profiles,
            plugopts=_cb_plugopts
          )
CB_NOTE = ("Data collection will be limited to a boot-affecting scope")

NOTE_SIZE = "This preset may increase report size"
NOTE_TIME = "This preset may increase report run time"
NOTE_SIZE_TIME = "This preset may increase report size and run time"

rhel_presets = {
    RHV: PresetDefaults(name=RHV, desc=RHV_DESC, note=NOTE_TIME,
                        opts=_opts_verify),
    RHEL: PresetDefaults(name=RHEL, desc=RHEL_DESC),
    RHOSP: PresetDefaults(name=RHOSP, desc=RHOSP_DESC, opts=RHOSP_OPTS),
    RHOCP: PresetDefaults(name=RHOCP, desc=RHOCP_DESC, note=NOTE_SIZE_TIME,
                          opts=_opts_all_logs_verify),
    RH_CFME: PresetDefaults(name=RH_CFME, desc=RH_CFME_DESC, note=NOTE_TIME,
                            opts=_opts_verify),
    RH_SATELLITE: PresetDefaults(name=RH_SATELLITE, desc=RH_SATELLITE_DESC,
                                 note=NOTE_TIME, opts=SAT_OPTS),
    CB: PresetDefaults(name=CB, desc=CB_DESC, note=CB_NOTE, opts=CB_OPTS)
}

# Legal disclaimer text for Red Hat products
disclaimer_text = """
Any information provided to %(vendor)s will be treated in \
accordance with the published support policies at:\n
  %(vendor_url)s

The generated archive may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No changes will be made to system configuration.
"""

RH_API_HOST = "https://access.redhat.com"
RH_FTP_HOST = "ftp://dropbox.redhat.com"


class RHELPolicy(RedHatPolicy):
    distro = RHEL_RELEASE_STR
    vendor = "Red Hat"
    vendor_url = "https://access.redhat.com/support/"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system and installed \
applications.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.
""" + disclaimer_text + "%(vendor_text)s\n")
    _upload_url = RH_FTP_HOST
    _upload_user = 'anonymous'
    _upload_directory = '/incoming'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RHELPolicy, self).__init__(sysroot=sysroot, init=init,
                                         probe_runtime=probe_runtime,
                                         remote_exec=remote_exec)
        self.register_presets(rhel_presets)

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
                "Enter your Red Hat Customer Portal username (empty to use "
                "public dropbox): ")
            )
            if not self.upload_user:
                self.upload_url = RH_FTP_HOST
                self.upload_user = self._upload_user

    def _upload_user_set(self):
        user = self.get_upload_user()
        return user and (user != 'anonymous')

    def get_upload_url(self):
        if self.upload_url:
            return self.upload_url
        if self.commons['cmdlineopts'].upload_url:
            return self.commons['cmdlineopts'].upload_url
        # anonymous FTP server should be used as fallback when either:
        # - case id is not set, or
        # - upload user isn't set AND batch mode prevents to prompt for it
        if (not self.case_id) or \
           ((not self._upload_user_set()) and
               self.commons['cmdlineopts'].batch):
            self.upload_user = self._upload_user
            if self.upload_directory is None:
                self.upload_directory = self._upload_directory
            self.upload_password = None
            return RH_FTP_HOST
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
        return self.upload_url or RH_FTP_HOST

    def get_upload_user(self):
        # if this is anything other than dropbox, annonymous won't work
        if self.upload_url != RH_FTP_HOST:
            return os.getenv('SOSUPLOADUSER', None) or self.upload_user
        return self._upload_user

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
    vendor_url = "https://www.centos.org/"


ATOMIC = "atomic"
ATOMIC_RELEASE_STR = "Atomic"
ATOMIC_DESC = "Red Hat Enterprise Linux Atomic Host"

atomic_presets = {
    ATOMIC: PresetDefaults(name=ATOMIC, desc=ATOMIC_DESC, note=NOTE_TIME,
                           opts=_opts_verify)
}


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
        self.register_presets(atomic_presets)

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
    vendor_url = "https://www.centos.org/"


class FedoraPolicy(RedHatPolicy):

    distro = "Fedora"
    vendor = "the Fedora Project"
    vendor_url = "https://fedoraproject.org/"

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
