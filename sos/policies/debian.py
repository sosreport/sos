from sos.plugins import DebianPlugin
from sos.policies import PackageManager, LinuxPolicy

import os


class DebianPolicy(LinuxPolicy):
    distro = "Debian"
    vendor = "the Debian project"
    vendor_url = "http://www.debian.org/"
    report_name = ""
    ticket_number = ""
    package_manager = PackageManager(
        "dpkg-query -W -f='${Package}|${Version}\\n' \*")
    valid_subclasses = [DebianPlugin]
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin"

    def __init__(self, sysroot=None):
        super(DebianPolicy, self).__init__(sysroot=sysroot)
        self.report_name = ""
        self.ticket_number = ""
        self.package_manager = PackageManager(
            "dpkg-query -W -f='${Package}|${Version}\\n' \*")
        self.valid_subclasses = [DebianPlugin]

    @classmethod
    def check(self):
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
        except:
            return False

# vim: set et ts=4 sw=4 :
