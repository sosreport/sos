# Copyright (C) 2014 Adam Stokes <adam.stokes@ubuntu.com>

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


class OpenVSwitch(Plugin):
    """ OpenVSwitch networking
    """
    plugin_name = "openvswitch"
    profiles = ('network', 'virt')

    def setup(self):
        self.add_copy_spec([
            "/var/log/openvswitch/ovs-vswitchd.log",
            "/var/log/openvswitch/ovsdb-server.log"
        ])
        # The '-s' option enables dumping of packet counters on the
        # ports.
        self.add_cmd_output("ovs-dpctl -s show")

        # The '-t 5' adds an upper bound on how long to wait to connect
        # to the Open vSwitch server, avoiding hangs when running sosreport.
        self.add_cmd_output("ovs-vsctl -t 5 show")

        # Gather additional output for each OVS bridge on the host.
        br_list_result = self.call_ext_prog("ovs-vsctl list-br")
        if br_list_result['status'] == 0:
            for br in br_list_result['output'].splitlines():
                self.add_cmd_output("ovs-ofctl show %s" % br)
                self.add_cmd_output("ovs-ofctl dump-flows %s" % br)
                self.add_cmd_output("ovs-appctl fdb/show %s" % br)

        # Gather the database.
        self.add_cmd_output("ovsdb-client dump")


class RedHatOpenVSwitch(OpenVSwitch, RedHatPlugin):

    packages = ('openvswitch',)


class DebianOpenVSwitch(OpenVSwitch, DebianPlugin, UbuntuPlugin):

    packages = ('openvswitch-switch',)


# vim: set et ts=4 sw=4 :
