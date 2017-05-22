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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class SaltMaster(Plugin, RedHatPlugin, DebianPlugin):
    """Salt Master
    """

    plugin_name = 'saltmaster'
    profiles = ('sysmgmt',)

    packages = ('salt-master',)

    def setup(self):
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
        else:
            limit = 0

        self.add_copy_spec("/var/log/salt/master", sizelimit=limit)
        self.add_cmd_output("salt-key --list all")

# vim: set et ts=4 sw=4 :
