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
    sos_bin_path = '/usr/sbin/sosreport'

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

        self.valid_subclasses = [RedHatPlugin]

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


# vim: set et ts=4 sw=4 :
