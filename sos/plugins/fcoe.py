# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class fcoe(Plugin, RedHatPlugin):
    """Fibre Channel over Ethernet
    """

    plugin_name = 'fcoe'
    profiles = ('storage', 'hardware')
    packages = ('fcoe-utils',)

    def setup(self):
        # Here we capture the information about all
        # FCoE instances with the -i option, and
        # information about all discovered FCFs
        # with the -f option
        self.add_cmd_output([
            "fcoeadm -i",
            "fcoeadm -f"
        ])
        # Here we grab information about the
        # interfaces's config files
        self.add_copy_spec("/etc/fcoe")

# vim: set et ts=4 sw=4 :
