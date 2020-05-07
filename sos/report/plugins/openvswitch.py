# Copyright (C) 2014 Adam Stokes <adam.stokes@ubuntu.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

from os.path import join as path_join
from os import environ


class OpenVSwitch(Plugin):

    short_desc = 'OpenVSwitch networking'
    plugin_name = "openvswitch"
    profiles = ('network', 'virt')

    def setup(self):

        all_logs = self.get_option("all_logs")

        log_dirs = [
            '/var/log/openvswitch/',
            '/usr/local/var/log/openvswitch/',
        ]

        dpdk_enabled = self.collect_cmd_output(
            "ovs-vsctl -t 5 get Open_vSwitch . other_config:dpdk-init")
        check_dpdk = (dpdk_enabled["status"] == 0 and
                      dpdk_enabled["output"].startswith('"true"'))

        if environ.get('OVS_LOGDIR'):
            log_dirs.append(environ.get('OVS_LOGDIR'))

        if not all_logs:
            self.add_copy_spec([path_join(ld, '*.log') for ld in log_dirs])
        else:
            self.add_copy_spec(log_dirs)

        self.add_copy_spec([
            "/run/openvswitch/ovsdb-server.pid",
            "/run/openvswitch/ovs-vswitchd.pid"
        ])

        self.add_cmd_output([
            # The '-t 5' adds an upper bound on how long to wait to connect
            # to the Open vSwitch server, avoiding hangs when running sos.
            "ovs-vsctl -t 5 show",
            # Gather the database.
            "ovsdb-client -f list dump",
            # List the contents of important runtime directories
            "ls -laZ /run/openvswitch",
            "ls -laZ /dev/hugepages/",
            "ls -laZ /dev/vfio",
            "ls -laZ /var/lib/vhost_sockets",
            # List devices and their drivers
            "dpdk_nic_bind --status",
            "dpdk_devbind.py --status",
            "driverctl list-devices",
            "driverctl list-overrides",
            # Capture a list of all bond devices
            "ovs-appctl bond/list",
            # Capture more details from bond devices
            "ovs-appctl bond/show",
            # Capture LACP details
            "ovs-appctl lacp/show",
            # Capture coverage stats"
            "ovs-appctl coverage/show",
            # Capture cached routes
            "ovs-appctl ovs/route/show",
            # Capture tnl arp table"
            "ovs-appctl tnl/arp/show",
            # Capture a list of listening ports"
            "ovs-appctl tnl/ports/show -v",
            # Capture upcall information
            "ovs-appctl upcall/show",
            # Capture DPDK and other parameters
            "ovs-vsctl -t 5 get Open_vSwitch . other_config",
            # Capture OVS list
            "ovs-vsctl -t 5 list Open_vSwitch",
            # Capture OVS interface list
            "ovs-vsctl -t 5 list interface",
            # Capture OVS detailed information from all the bridges
            "ovs-vsctl -t 5 list bridge",
            # Capture DPDK queue to pmd mapping
            "ovs-appctl dpif-netdev/pmd-rxq-show",
            # Capture DPDK pmd stats
            "ovs-appctl dpif-netdev/pmd-stats-show",
            # Capture DPDK pmd performance counters
            "ovs-appctl dpif-netdev/pmd-perf-show",
            # Capture ofproto tunnel configs
            "ovs-appctl ofproto/list-tunnels"
        ])

        # Gather systemd services logs
        self.add_journal(units="openvswitch")
        self.add_journal(units="openvswitch-nonetwork")
        self.add_journal(units="ovs-vswitchd")
        self.add_journal(units="ovsdb-server")

        # Gather the datapath information for each datapath
        dp_list_result = self.collect_cmd_output('ovs-appctl dpctl/dump-dps')
        if dp_list_result['status'] == 0:
            for dp in dp_list_result['output'].splitlines():
                self.add_cmd_output([
                    "ovs-appctl dpctl/show -s %s" % dp,
                    "ovs-appctl dpctl/dump-flows -m %s" % dp,
                    "ovs-appctl dpctl/dump-conntrack -m %s" % dp,
                    "ovs-appctl dpctl/ct-stats-show -m %s" % dp,
                    "ovs-appctl dpctl/ipf-get-status %s" % dp,
                ])

        # Gather additional output for each OVS bridge on the host.
        br_list_result = self.collect_cmd_output("ovs-vsctl -t 5 list-br")
        if br_list_result['status'] == 0:
            for br in br_list_result['output'].splitlines():
                self.add_cmd_output([
                    "ovs-appctl bridge/dump-flows --offload-stats %s" % br,
                    "ovs-appctl dpif/show-dp-features %s" % br,
                    "ovs-appctl fdb/show %s" % br,
                    "ovs-appctl fdb/stats-show %s" % br,
                    "ovs-appctl mdb/show %s" % br,
                    "ovs-ofctl dump-flows %s" % br,
                    "ovs-ofctl dump-ports-desc %s" % br,
                    "ovs-ofctl dump-ports %s" % br,
                    "ovs-ofctl queue-get-config %s" % br,
                    "ovs-ofctl queue-stats %s" % br,
                    "ovs-ofctl show %s" % br,
                ])

                # Flow protocols currently supported
                flow_versions = [
                    "OpenFlow10",
                    "OpenFlow11",
                    "OpenFlow12",
                    "OpenFlow13",
                    "OpenFlow14",
                    "OpenFlow15"
                ]

                # List protocols currently in use, if any
                ovs_list_bridge_cmd = "ovs-vsctl -t 5 list bridge %s" % br
                br_info = self.collect_cmd_output(ovs_list_bridge_cmd)

                for line in br_info['output'].splitlines():
                    if "protocols" in line:
                        br_protos_ln = line[line.find("[")+1:line.find("]")]
                        br_protos = br_protos_ln.replace('"', '').split(", ")

                # Collect flow information for relevant protocol versions only
                for flow in flow_versions:
                    if flow in br_protos:
                        self.add_cmd_output([
                            "ovs-ofctl -O %s show %s" % (flow, br),
                            "ovs-ofctl -O %s dump-groups %s" % (flow, br),
                            "ovs-ofctl -O %s dump-group-stats %s" % (flow, br),
                            "ovs-ofctl -O %s dump-flows %s" % (flow, br),
                            "ovs-ofctl -O %s dump-ports-desc %s" % (flow, br)
                        ])

                port_list_result = self.exec_cmd(
                    "ovs-vsctl -t 5 list-ports %s" % br
                )
                if port_list_result['status'] == 0:
                    for port in port_list_result['output'].splitlines():
                        if check_dpdk:
                            self.add_cmd_output(
                                "ovs-appctl netdev-dpdk/get-mempool-info %s" %
                                port
                            )


class RedHatOpenVSwitch(OpenVSwitch, RedHatPlugin):

    packages = ('openvswitch', 'openvswitch2.*',
                'openvswitch-dpdk', 'nuage-openvswitch')


class DebianOpenVSwitch(OpenVSwitch, DebianPlugin, UbuntuPlugin):

    packages = ('openvswitch-switch', 'nuage-openvswitch')


# vim: set et ts=4 sw=4 :
