# Copyright (C) 2018 Mark Michelson <mmichels@redhat.com>

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

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OVNHost(Plugin):
    """ OVN Controller
    """
    plugin_name = "ovn_host"
    profiles = ('network', 'virt')

    def setup(self):
        pidfile = 'ovn-controller.pid'
        pid_paths = [
                '/var/lib/openvswitch/ovn',
                '/usr/local/var/run/openvswitch',
                '/var/run/openvswitch',
                '/run/openvswitch'
        ]
        if os.environ.get('OVS_RUNDIR'):
            pid_paths.append(os.environ.get('OVS_RUNDIR'))
        self.add_copy_spec([os.path.join(pp, pidfile) for pp in pid_paths])

        self.add_copy_spec('/etc/sysconfig/ovn-controller')

        self.add_cmd_output([
            'ovs-ofctl -O OpenFlow13 dump-flows br-int',
            'ovs-vsctl list-br',
            'ovs-vsctl list OpenVswitch',
        ])

        self.add_journal(units="ovn-controller")


class RedHatOVNHost(OVNHost, RedHatPlugin):

    packages = ('openvswitch-ovn-host', )


class DebianOVNHost(OVNHost, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-host', )
