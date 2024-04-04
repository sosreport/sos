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


class OVNHost(Plugin):

    short_desc = 'OVN Controller'
    plugin_name = "ovn_host"
    profiles = ('network', 'virt', 'openstack_edpm')
    pidfile = 'ovn-controller.pid'
    pid_paths = [
        '/var/lib/openvswitch/ovn',
        '/usr/local/var/run/openvswitch',
        '/run/openvswitch',
    ]
    ovs_cmd_pre = ""

    def setup(self):
        if os.environ.get('OVS_RUNDIR'):
            self.pid_paths.append(os.environ.get('OVS_RUNDIR'))

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/ovn/")
        else:
            self.add_copy_spec("/var/log/ovn/*.log")

        self.add_copy_spec([self.path_join(pp, self.pidfile)
                           for pp in self.pid_paths])

        self.add_copy_spec('/etc/sysconfig/ovn-controller')

        self.add_cmd_output([
            f'{self.ovs_cmd_pre}ovs-ofctl -O OpenFlow13 dump-flows br-int',
            f'{self.ovs_cmd_pre}ovs-vsctl list-br',
            f'{self.ovs_cmd_pre}ovs-vsctl list Open_vSwitch',
        ])

        self.add_journal(units="ovn-controller")

    def check_enabled(self):
        return (any(self.path_isfile(self.path_join(pid_path, self.pidfile))
                for pid_path in self.pid_paths) or super().check_enabled())


class RedHatOVNHost(OVNHost, RedHatPlugin):

    packages = ('openvswitch-ovn-host', 'ovn.*-host', )
    var_ansible_gen = "/var/lib/config-data/ansible-generated/ovn-bgp-agent"

    def setup(self):
        super().setup()
        self.add_copy_spec([
            self.var_ansible_gen,
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/containers/ovn-bgp-agent/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/containers/ovn-bgp-agent/*.log",
            ])


class DebianOVNHost(OVNHost, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-host', )

    sunbeam_common_dir = '/var/snap/openstack-hypervisor/common'

    pid_paths = [
        f'{sunbeam_common_dir}/run/ovn',
    ]

    def setup(self):

        if self.is_installed('openstack-hypervisor'):
            self.ovs_cmd_pre = "openstack-hypervisor."

            self.add_copy_spec([
                f'{self.sunbeam_common_dir}/lib/ovn-metadata-proxy/*.conf',
            ])

            if self.get_option("all_logs"):
                self.add_copy_spec([
                    f"{self.sunbeam_common_dir}/var/log/ovn/",
                ])
            else:
                self.add_copy_spec([
                    f"{self.sunbeam_common_dir}/var/log/ovn/*.log",
                ])

        super().setup()
