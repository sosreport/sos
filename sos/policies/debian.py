from sos.plugins import DebianPlugin
from sos.policies import PackageManager, LinuxPolicy

import os


class DebianPolicy(LinuxPolicy):
    distro = "Debian"
    vendor = "the Debian project"
    vendor_url = "http://www.debian.org/"
    ticket_number = ""
    _debq_cmd = "dpkg-query -W -f='${Package}|${Version}\\n'"
    _debv_cmd = "dpkg --verify"
    _debv_filter = ""
    valid_subclasses = [DebianPlugin]
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin"

    def __init__(self, sysroot=None):
        super(DebianPolicy, self).__init__(sysroot=sysroot)
        self.ticket_number = ""
        self.package_manager = PackageManager(query_command=self._debq_cmd,
                                              verify_command=self._debv_cmd,
                                              verify_filter=self._debv_filter,
                                              chroot=sysroot)

        self.valid_subclasses = [DebianPlugin]

    def _get_pkg_name_for_binary(self, binary):
        # for binary not specified inside {..}, return binary itself
        return {
            "xz": "xz-utils"
        }.get(binary, binary)

    @classmethod
    def check(cls):
        """This method checks to see if we are running on Debian.
           It returns True or False."""
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
