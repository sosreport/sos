from __future__ import with_statement

from sos.plugins import DebianPlugin
from sos.policies import PackageManager, LinuxPolicy
from sos.utilities import shell_out

import os

class DebianPackageManager(PackageManager):

    def _get_deb_list(self):
        pkg_list = shell_out(["dpkg-query",
            "-W",
            "-f=",
        "'${Package}|${Version}\\n' \*"]).splitlines()
        self._debs = {}
        for pkg in pkg_list:
            name, version = pkg.split("|")
            self._debs[name] = {
                    'name': name,
                    'version': version
                    }

    def allPkgs(self):
        if not self._debs:
            self._debs = self._get_deb_list()
        return self._debs


class DebianPolicy(LinuxPolicy):
    def __init__(self):
        super(DebianPolicy, self).__init__()
        self.reportName = ""
        self.ticketNumber = ""
        self.package_manager = DebianPackageManager()
        self.valid_subclasses = [DebianPlugin]
        self.distro = "Debian"

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
