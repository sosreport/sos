# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies import PackageManager, LinuxPolicy
from sos.plugins import ArchPlugin
from sos.utilities import shell_out


class ArchPolicy(LinuxPolicy):

    distro = "Arch Linux"
    vendor = "Arch Linux"
    vendor_url = "https://www.archlinux.org/"
    vendor_text = ""
    # package_manager = PackageManager(
    #   "pacman --query | awk 'BEGIN {OFS = \"|\"} {print $1,$2}'")
    valid_subclasses = [ArchPlugin]

    def __init__(self, sysroot=None):
        super(ArchPolicy, self).__init__(sysroot=sysroot)
        self.package_manager = Pacman()

    @classmethod
    def check(cls):
        """This method checks to see if we are running on Arch.
            It returns True or False."""
        try:
            with open('/etc/os-release', 'r') as f:
                return "archlinux" in f.read()
        except IOError:
            return False


class Pacman(PackageManager):

    def get_pkg_list(self):
        cmd = "pacman --query"
        pkg_list = shell_out(
            cmd, timeout=0, chroot=self.chroot
        ).splitlines()

        for pkg in pkg_list:
            name, version = pkg.split()
            self.packages[name] = {
                'name': name,
                'version': version.split(".")
            }

        return self.packages

# vim: set et ts=4 sw=4 :
