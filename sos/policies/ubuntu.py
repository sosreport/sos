from __future__ import with_statement

from sos.plugins import UbuntuPlugin, DebianPlugin
from sos.policies.debian import DebianPolicy


class UbuntuPolicy(DebianPolicy):
    distro = "Ubuntu"
    vendor = "Ubuntu"
    vendor_url = "http://www.ubuntu.com/"

    def __init__(self, sysroot=None):
        super(UbuntuPolicy, self).__init__(sysroot=sysroot)
        self.valid_subclasses = [UbuntuPlugin, DebianPlugin]

    @classmethod
    def check(self):
        """This method checks to see if we are running on Ubuntu.
           It returns True or False."""
        try:
            with open('/etc/lsb-release', 'r') as fp:
                return "Ubuntu" in fp.read()
        except:
            return False

    def dist_version(self):
        """ Returns the version stated in DISTRIB_RELEASE
        """
        try:
            with open('/etc/lsb-release', 'r') as fp:
                lines = fp.readlines()
                for line in lines:
                    if "DISTRIB_RELEASE" in line:
                        return line.split("=")[1].strip()
            return False
        except:
            return False

# vim: set et ts=4 sw=4 :
