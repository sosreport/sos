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
    packages = ('gdm', 'gdm3',)

    def setup(self):
        self.add_copy_spec([
            "/etc/gdm/*",
            "/etc/gdm3/*"
        ])
        self.add_journal(units="gdm")
        self.add_service_status("gdm")

# vim: set et ts=4 sw=4 :
