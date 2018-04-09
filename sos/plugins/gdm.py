# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Gdm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """GNOME display manager
    """

    plugin_name = 'gdm'
    profiles = ('desktop',)
    packages = ('gdm',)

    def setup(self):
        self.add_copy_spec("/etc/gdm/*")
        self.add_journal(units="gdm")
        self.add_cmd_output("systemctl status gdm.service")

# vim: set et ts=4 sw=4 :
