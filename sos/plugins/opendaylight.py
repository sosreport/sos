# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin


class OpenDaylight(Plugin, RedHatPlugin):
    """OpenDaylight network manager
    """

    plugin_name = 'opendaylight'
    profiles = ('openstack', 'openstack_controller')

    packages = ('opendaylight', 'puppet-opendaylight')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/opendaylight"

    def setup(self):
        self.add_copy_spec([
            "/opt/opendaylight/etc/",
            self.var_puppet_gen + "/opt/opendaylight/etc/",
        ])

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/opt/opendaylight/data/log/",
                "/var/log/containers/opendaylight/",
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/opt/opendaylight/data/log/*.log*",
                "/var/log/containers/opendaylight/*.log*",
            ], sizelimit=self.limit)

        self.add_cmd_output("docker logs opendaylight_api")

# vim: set et ts=4 sw=4 :
