# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Lilo(Plugin, RedHatPlugin, UbuntuPlugin):
    """Lilo bootloader
    """

    plugin_name = 'lilo'
    profiles = ('system', 'boot')
    packages = ('lilo',)

    def setup(self):
        self.add_copy_spec("/etc/lilo.conf")
        self.add_cmd_output("lilo -q")

# vim: set et ts=4 sw=4 :
