# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import DebianPlugin
from sos.policies.distros import LinuxPolicy
from sos.policies import PackageManager

import os


class DebianPolicy(LinuxPolicy):
    distro = "Debian"
    vendor = "the Debian project"
    vendor_urls = [('Community Website', 'https://www.debian.org/')]
    ticket_number = ""
    _debq_cmd = "dpkg-query -W -f='${Package}|${Version}\\n'"
    _debv_cmd = "dpkg --verify"
    _debv_filter = ""
    name_pattern = 'friendly'
    valid_subclasses = [DebianPlugin]
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin"
    sos_pkg_name = 'sosreport'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(DebianPolicy, self).__init__(sysroot=sysroot, init=init,
                                           probe_runtime=probe_runtime)
        self.ticket_number = ""
        self.package_manager = PackageManager(query_command=self._debq_cmd,
                                              verify_command=self._debv_cmd,
                                              verify_filter=self._debv_filter,
                                              chroot=sysroot,
                                              remote_exec=remote_exec)
        self.valid_subclasses += [DebianPlugin]

    def _get_pkg_name_for_binary(self, binary):
        # for binary not specified inside {..}, return binary itself
        return {
            "xz": "xz-utils"
        }.get(binary, binary)

    @classmethod
    def check(cls, remote=''):
        """This method checks to see if we are running on Debian.
           It returns True or False."""

        if remote:
            return cls.distro in remote

        return os.path.isfile('/etc/debian_version')

    def dist_version(self):
        try:
            with open('/etc/lsb-release', 'r') as fp:
                rel_string = fp.read()
                if "wheezy/sid" in rel_string:
                    return 6
                elif "jessie/sid" in rel_string:
                    return 7
            return False
        except IOError:
            return False

# vim: set et ts=4 sw=4 :
