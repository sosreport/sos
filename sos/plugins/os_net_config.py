# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class OsNetConfig(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """OpenStack Net Config"""

    plugin_name = "os_net_config"
    profiles = ('openstack')
    packages = ('os-net-config',)

    def setup(self):
        self.add_copy_spec("/etc/os-net-config")
        self.add_copy_spec("/var/lib/os-net-config")


# vim: set et ts=4 sw=4 :
