# Copyright (C) 2018 Mark Michelson <mmichels@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


pidfile = 'ovn-controller.pid'
pid_paths = [
        '/var/lib/openvswitch/ovn',
        '/usr/local/var/run/openvswitch',
        '/run/openvswitch'
]


class OVNHost(Plugin):

    short_desc = 'OVN Controller'
    plugin_name = "ovn_host"
    profiles = ('network', 'virt')

    def setup(self):
        if os.environ.get('OVS_RUNDIR'):
            pid_paths.append(os.environ.get('OVS_RUNDIR'))

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/ovn/")
        else:
            self.add_copy_spec("/var/log/ovn/*.log")

        self.add_copy_spec([self.path_join(pp, pidfile) for pp in pid_paths])

        self.add_copy_spec('/etc/sysconfig/ovn-controller')

        self.add_cmd_output([
            'ovs-ofctl -O OpenFlow13 dump-flows br-int',
            'ovs-vsctl list-br',
            'ovs-vsctl list Open_vSwitch',
        ])

        self.add_journal(units="ovn-controller")

    def check_enabled(self):
        return (any([self.path_isfile(
            self.path_join(pp, pidfile)) for pp in pid_paths]) or
            super(OVNHost, self).check_enabled())


class RedHatOVNHost(OVNHost, RedHatPlugin):

    packages = ('openvswitch-ovn-host', 'ovn.*-host', )


class DebianOVNHost(OVNHost, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-host', )
