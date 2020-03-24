# Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin


class Dpkg(Plugin, DebianPlugin, UbuntuPlugin):
    """Debian Package Management
    """

    plugin_name = 'dpkg'
    profiles = ('sysmgmt', 'packagemanager')

    def setup(self):
        self.add_cmd_output("dpkg -l", root_symlink="installed-debs")
        if self.get_option("verify"):
            self.add_cmd_output("dpkg -V")
            self.add_cmd_output("dpkg -C")
        self.add_copy_spec([
            "/var/cache/debconf/config.dat",
            "/etc/debconf.conf"
        ])
        if not self.get_option("all_logs"):
            self.add_copy_spec("/var/log/dpkg.log")
        else:
            self.add_copy_spec("/var/log/dpkg.log*")

# vim: set et ts=4 sw=4 :
