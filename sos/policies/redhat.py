# Copyright (C) Steve Conklin <sconklin@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

# This enables the use of with syntax in python 2.5 (e.g. jython)
from __future__ import print_function
import os
import sys

from sos.plugins import RedHatPlugin
from sos.policies import LinuxPolicy, PackageManager
from sos import _sos as _

sys.path.insert(0, "/usr/share/rhn/")
try:
    from up2date_client import up2dateAuth
    from up2date_client import config
    from rhn import rpclib
except ImportError:
    # might fail if non-RHEL
    pass

OS_RELEASE = "/etc/os-release"


class RedHatPolicy(LinuxPolicy):
    distro = "Red Hat"
    vendor = "Red Hat"
    vendor_url = "http://www.redhat.com/"
    _redhat_release = '/etc/redhat-release'
    _tmp_dir = "/var/tmp"
    _rpmq_cmd = 'rpm -qa --queryformat "%{NAME}|%{VERSION}|%{RELEASE}\\n"'
    _rpmv_cmd = 'rpm -V'
    _rpmv_filter = ["debuginfo", "-devel"]
    _in_container = False
    _host_sysroot = '/'
    default_scl_prefix = '/opt/rh'
    name_pattern = 'friendly'

    def __init__(self, sysroot=None):
        super(RedHatPolicy, self).__init__(sysroot=sysroot)
        self.ticket_number = ""
        # need to set _host_sysroot before PackageManager()
        if sysroot:
            self._container_init()
            self._host_sysroot = sysroot
        else:
            sysroot = self._container_init()

        self.package_manager = PackageManager(query_command=self._rpmq_cmd,
                                              verify_command=self._rpmv_cmd,
                                              verify_filter=self._rpmv_filter,
                                              chroot=sysroot)

        self.valid_subclasses = [RedHatPlugin]

        pkgs = self.package_manager.all_pkgs()

        # If rpm query failed, exit
        if not pkgs:
            print("Could not obtain installed package list", file=sys.stderr)
            sys.exit(1)

        # handle PATH for UsrMove
        if 'filesystem' not in pkgs:
            print("Could not find 'filesystem' package: "
                  "assuming PATH settings")
            usrmove = True
        else:
            filesys_version = pkgs['filesystem']['version']
            usrmove = True if filesys_version[0] == '3' else False

        if usrmove:
            self.PATH = "/usr/sbin:/usr/bin:/root/bin"
        else:
            self.PATH = "/sbin:/bin:/usr/sbin:/usr/bin:/root/bin"
        self.PATH += os.pathsep + "/usr/local/bin"
        self.PATH += os.pathsep + "/usr/local/sbin"
        self.set_exec_path()

    @classmethod
    def check(cls):
        """This method checks to see if we are running on Red Hat. It must be
        overriden by concrete subclasses to return True when running on a
        Fedora, RHEL or other Red Hat distribution or False otherwise."""
        return False

    def _container_init(self):
        """Check if sos is running in a container and perform container
        specific initialisation based on ENV_HOST_SYSROOT.
        """
        if ENV_CONTAINER in os.environ:
            if os.environ[ENV_CONTAINER] in ['docker', 'oci']:
                self._in_container = True
        if ENV_HOST_SYSROOT in os.environ:
            self._host_sysroot = os.environ[ENV_HOST_SYSROOT]
        use_sysroot = self._in_container and self._host_sysroot != '/'
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

    def get_local_name(self):
        return self.host_name()


# Container environment variables on Red Hat systems.
ENV_CONTAINER = 'container'
ENV_HOST_SYSROOT = 'HOST'

RHEL_RELEASE_STR = "Red Hat Enterprise Linux"


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

Any information provided to %(vendor)s will be treated in \
accordance with the published support policies at:\n
  %(vendor_url)s

The generated archive may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No changes will be made to system configuration.
%(vendor_text)s
""")

    def __init__(self, sysroot=None):
        super(RHELPolicy, self).__init__(sysroot=sysroot)

    @classmethod
    def check(cls):
        """Test to see if the running host is a RHEL installation.

            Checks for the presence of the "Red Hat Enterprise Linux"
            release string at the beginning of the NAME field in the
            `/etc/os-release` file and returns ``True`` if it is
            found, and ``False`` otherwise.

            :returns: ``True`` if the host is running RHEL or ``False``
                      otherwise.
        """
        if not os.path.exists(OS_RELEASE):
            return False

        with open(OS_RELEASE, "r") as f:
            for line in f:
                if line.startswith("NAME"):
                    (name, value) = line.split("=")
                    value = value.strip("\"'")
                    if value.startswith(RHEL_RELEASE_STR):
                        return True
        return False

    def dist_version(self):
        try:
            pkg = self.pkg_by_name("redhat-release") or \
                self.all_pkgs_by_name_regex("redhat-release-.*")[-1]
            pkgname = pkg["version"]
            if pkgname[0] == "4":
                return 4
            elif pkgname[0] in ["5Server", "5Client"]:
                return 5
            elif pkgname[0] == "6":
                return 6
            elif pkgname[0] == "7":
                return 7
        except Exception:
            pass
        return False

    def rhn_username(self):
        try:
            # cfg = config.initUp2dateConfig()
            rhn_username = rpclib.xmlrpclib.loads(
                up2dateAuth.getSystemId())[0][0]['username']
            return rhn_username.encode('utf-8', 'ignore')
        except Exception:
            # ignore any exception and return an empty username
            return ""

    def get_local_name(self):
        return self.rhn_username() or self.host_name()


class RedHatAtomicPolicy(RHELPolicy):
    distro = "Red Hat Atomic Host"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.

Any information provided to %(vendor)s will be treated in \
accordance with the published support policies at:\n
  %(vendor_url)s

The generated archive may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.
%(vendor_text)s
""")

    @classmethod
    def check(cls):
        atomic = False
        if ENV_HOST_SYSROOT not in os.environ:
            return atomic
        host_release = os.environ[ENV_HOST_SYSROOT] + cls._redhat_release
        if not os.path.exists(host_release):
            return False
        try:
            for line in open(host_release, "r").read().splitlines():
                atomic |= 'Atomic' in line
        except IOError:
            pass
        return atomic


class FedoraPolicy(RedHatPolicy):

    distro = "Fedora"
    vendor = "the Fedora Project"
    vendor_url = "https://fedoraproject.org/"

    def __init__(self, sysroot=None):
        super(FedoraPolicy, self).__init__(sysroot=sysroot)

    @classmethod
    def check(cls):
        """This method checks to see if we are running on Fedora. It returns
        True or False."""
        return os.path.isfile('/etc/fedora-release')

    def fedora_version(self):
        pkg = self.pkg_by_name("fedora-release") or \
            self.all_pkgs_by_name_regex("fedora-release-.*")[-1]
        return int(pkg["version"])


# vim: set et ts=4 sw=4 :
