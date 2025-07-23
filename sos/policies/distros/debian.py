# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import DebianPlugin
from sos.policies.distros import LinuxPolicy
from sos.policies.package_managers.dpkg import DpkgPackageManager


class DebianPolicy(LinuxPolicy):
    vendor = "the Debian project"
    vendor_urls = [('Community Website', 'https://www.debian.org/')]
    os_release_name = 'Debian'
    os_release_file = '/etc/debian_version'
    _tmp_dir = "/var/tmp"
    name_pattern = 'friendly'
    valid_subclasses = [DebianPlugin]
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin"
    sos_pkg_name = 'sosreport'

    deb_versions = {
        'squeeze':  6,
        'wheezy':   7,
        'jessie':   8,
        'stretch':  9,
        'buster':   10,
        'bullseye': 11,
        'bookworm': 12,
        'trixie':   13,
        'forky':    14,
        'duke':     15,
        }

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)
        self.package_manager = DpkgPackageManager(chroot=self.sysroot,
                                                  remote_exec=remote_exec)
        self.valid_subclasses += [DebianPlugin]

    def _get_pkg_name_for_binary(self, binary):
        # for binary not specified inside {..}, return binary itself
        return {
            "xz": "xz-utils"
        }.get(binary, binary)

    def dist_version(self):
        try:
            with open('/etc/os-release', 'r', encoding='utf-8') as fp:
                rel_string = ""
                lines = fp.readlines()
                for line in lines:
                    if "VERSION_CODENAME" in line:
                        rel_string = line.split("=")[1].strip()
                        break
                if rel_string in self.deb_versions:
                    return self.deb_versions[rel_string]
            return False
        except IOError:
            return False

    def get_tmp_dir(self, opt_tmp_dir):
        if not opt_tmp_dir:
            return self._tmp_dir
        return opt_tmp_dir

# vim: set et ts=4 sw=4 :
