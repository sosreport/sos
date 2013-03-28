from sos.plugins import DebianPlugin
from sos.policies import PackageManager, LinuxPolicy

import os

class DebianPolicy(LinuxPolicy):
    distro = "Debian"
    vendor = "the Debian project"
    vendor_url = "http://www.debian.org/"
    report_name = ""
    ticket_number = ""
    package_manager = PackageManager("dpkg-query -W -f='${Package}|${Version}\\n' \*")
    valid_subclasses = [DebianPlugin]

    def __init__(self):
        super(DebianPolicy, self).__init__()

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
