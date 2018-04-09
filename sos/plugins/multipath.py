# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Multipath(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Device-mapper multipath tools
    """

    plugin_name = 'multipath'
    profiles = ('system', 'storage', 'hardware')

    def setup(self):
        self.add_copy_spec([
            "/etc/multipath/",
            "/etc/multipath.conf"
        ])
        self.add_cmd_output([
            "multipath -l",
            "multipath -v4 -ll",
            "multipathd show config"
        ])


# vim: set et ts=4 sw=4 :
