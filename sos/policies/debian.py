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

    def __init__(self):
        super(DebianPolicy, self).__init__()
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

    def debianVersion(self):
        try:
            fp = open("/etc/debian_version").read()
            if "wheezy/sid" in fp:
                return 6
            fp.close()
        except:
            pass
        return False

# vim: et ts=4 sw=4
