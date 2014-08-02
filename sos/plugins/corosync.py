# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Corosync(Plugin):
    """ corosync information
    """

    plugin_name = "corosync"
    packages = ('corosync',)

    def setup(self):
        self.add_copy_specs([
            "/etc/corosync",
            "/var/lib/corosync/fdata",
            "/var/log/cluster/corosync.log"
        ])
        self.add_cmd_outputs([
            "corosync-quorumtool -l",
            "corosync-quorumtool -s",
            "corosync-cpgtool",
            "corosync-objctl -a",
            "corosync-fplay",
            "corosync-objctl -w runtime.blackbox.dump_state=$(date +\%s)",
            "corosync-objctl -w runtime.blackbox.dump_flight_data=$(date +\%s)"
        ])
        self.call_ext_prog("killall -USR2 corosync")


class RedHatCorosync(Corosync, RedHatPlugin):
    """ corosync information for RedHat based distribution
    """

    def setup(self):
        super(RedHatCorosync, self).setup()


class DebianCorosync(Corosync, DebianPlugin, UbuntuPlugin):
    """ corosync information for Debian and Ubuntu distributions
    """

    def setup(self):
        super(DebianCorosync, self).setup()

    files = ('/usr/sbin/corosync',)

# vim: et ts=4 sw=4
