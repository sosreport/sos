# Copyright (C) 2014 Adam Stokes <adam.stokes@ubuntu.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

from os import environ

import re


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
        check_6wind = any([self.is_installed(p) for p in
                           ['6windgate-fp', 'nuage-openvswitch']])
        actl = "ovs-appctl"

        files_6wind = [
            "/etc/systemd/system/multi-user.target.wants/openvswitch.service",
            "/etc/sysctl.d/60-6wind-system-auto-reboot.conf",
            "/etc/openvswitch/system-id.conf",
            "/etc/openvswitch/*.db",
            "/etc/ld.so.conf.d/linux-fp-sync-fptun.conf",
            "/etc/NetworkManager/conf.d/fpn0.conf",
            "/etc/default/openvswitch",
            "/etc/logrotate.d/openvswitch",
            "/etc/linux-fp-sync.env",
            "/etc/fp-daemons.env",
            "/etc/fp-vdev.ini",
            "/etc/fpm.env",
            "/etc/6WINDGate/fp.config",
            "/etc/6WINDGate/fpnsdk.config",
            "/etc/dms.d/fp-dms.conf",
            "/etc/dms.d/fpmd-dms.conf",
            "/etc/dms.d/fpsd-dms.conf",
            "/etc/fast-path.env",
            "/etc/fps-fp.env",
        ]

        if environ.get('OVS_LOGDIR'):
            log_dirs.append(environ.get('OVS_LOGDIR'))

        if not all_logs:
            self.add_copy_spec([
                self.path_join(ld, '*.log') for ld in log_dirs
            ])
        else:
            self.add_copy_spec(log_dirs)

        self.add_copy_spec([
            "/run/openvswitch/ovsdb-server.pid",
            "/run/openvswitch/ovs-vswitchd.pid",
            "/run/openvswitch/ovs-monitor-ipsec.pid"
        ])

        self.add_copy_spec([
            self.path_join('/usr/local/etc/openvswitch', 'conf.db'),
            self.path_join('/etc/openvswitch', 'conf.db'),
            self.path_join('/var/lib/openvswitch', 'conf.db'),
        ])
        ovs_dbdir = environ.get('OVS_DBDIR')
        if ovs_dbdir:
            self.add_copy_spec(self.path_join(ovs_dbdir, 'conf.db'))

        self.add_cmd_output([
            # The '-t 5' adds an upper bound on how long to wait to connect
            # to the Open vSwitch server, avoiding hangs when running sos.
            "ovs-vsctl -t 5 show",
            # List the contents of important runtime directories
            "ls -laZ /run/openvswitch",
            "ls -laZ /dev/hugepages/",
            "ls -laZ /dev/vfio",
            "ls -laZ /var/lib/vhost_sockets",
            # List devices and their drivers
            "dpdk_nic_bind --status",
            "dpdk-devbind.py --status",
            "driverctl list-devices",
            "driverctl list-overrides",
            # Capture a list of all bond devices
            "ovs-appctl bond/list",
            # Capture more details from bond devices
            "ovs-appctl bond/show",
            # Capture LACP details
            "ovs-appctl lacp/show",
            "ovs-appctl lacp/show-stats",
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
            # Capture OVS datapath list
            "ovs-vsctl -t 5 list datapath",
            # Capture DPDK queue to pmd mapping
            "ovs-appctl dpif-netdev/pmd-rxq-show",
            # Capture DPDK pmd stats
            "ovs-appctl dpif-netdev/pmd-stats-show",
            # Capture DPDK pmd performance counters
            "ovs-appctl dpif-netdev/pmd-perf-show",
            # Capture ofproto tunnel configs
            "ovs-appctl ofproto/list-tunnels",
            # Capture ipsec tunnel information
            "ovs-appctl -t ovs-monitor-ipsec tunnels/show",
            "ovs-appctl -t ovs-monitor-ipsec xfrm/state",
            "ovs-appctl -t ovs-monitor-ipsec xfrm/policies",
            # Capture OVS offload enabled flows
            "ovs-dpctl dump-flows --name -m type=offloaded",
            # Capture OVS slowdatapth flows
            "ovs-dpctl dump-flows --name -m type=ovs",
            # Capture dpcls implementations
            "ovs-appctl dpif-netdev/subtable-lookup-prio-get",
            # Capture dpif implementations
            "ovs-appctl dpif-netdev/dpif-impl-get",
            # Capture miniflow extract implementations
            "ovs-appctl dpif-netdev/miniflow-parser-get"
        ])

        # Gather systemd services logs
        self.add_journal(units="openvswitch")
        self.add_journal(units="openvswitch-nonetwork")
        self.add_journal(units="ovs-vswitchd")
        self.add_journal(units="ovsdb-server")
        self.add_journal(units="ovs-configuration")
        self.add_journal(units="openvswitch-ipsec")

        if check_6wind:
            self.add_copy_spec(files_6wind)
            self.add_cmd_output([
                # Various fast-path stats
                "fp-cli fp-vswitch-stats",
                "fp-cli dpdk-core-port-mapping",
                "fp-cpu-usage",
                "fp-cli fp-vswitch-masks",
                "fp-cli fp-vswitch-flows",
                "fp-shmem-dpvi",
                "fp-cli stats non-zero",
                "fp-cli stats",
                "fp-cli dpdk-cp-filter-budget",
                "ovs-appctl vm/port-detailed-show",
                "ovs-appctl upcall/show",
                "fp-cli nfct4",
                "ovs-appctl vm/port-vip-list-show",
                "fp-shmem-ports -s",
                "ovs-dpctl show -s",
                "fpcmd fp-vswitch-flows",
                "fp-cli fp-vswitch-ports percore",
                "fp-cli dpdk-debug-pool",
                "fp-cli dump-size",
                "fp-cli conf runtime",
                "fp-cli conf compiled",
                "fp-cli iface",
                "ovs-appctl memory/show",
            ])
            self.add_journal(units="virtual-accelerator")
            for table in ['filter', 'mangle', 'raw', 'nat']:
                self.add_cmd_output(["fpcmd nf4-rules %s" % table])

            # 6wind doesn't care on which bridge the ports are, there's only
            # one bridge and it's alubr0
            port_list = self.collect_cmd_output("fp-cli fp-vswitch-ports")
            if port_list['status'] == 0:
                for port in port_list['output'].splitlines():
                    m = re.match(r'^([\d]+):[\s]+([^\s]+)', port)
                    if m:
                        port_name = m.group(2)
                        self.add_cmd_output([
                            "fp-cli dpdk-cp-filter-budget %s" % port_name,
                        ])

        # Gather the datapath information for each datapath
        dp_list_result = self.collect_cmd_output('ovs-appctl dpctl/dump-dps')
        if dp_list_result['status'] == 0:
            for dp in dp_list_result['output'].splitlines():
                self.add_cmd_output([
                    "%s dpctl/show -s %s" % (actl, dp),
                    "%s dpctl/dump-flows -m %s" % (actl, dp),
                    "%s dpctl/dump-conntrack -m %s" % (actl, dp),
                    "%s dpctl/ct-stats-show -m %s" % (actl, dp),
                    "%s dpctl/ipf-get-status %s" % (actl, dp),
                ])

        # Gather additional output for each OVS bridge on the host.
        br_list_result = self.collect_cmd_output("ovs-vsctl -t 5 list-br")
        ofp_ver_result = self.collect_cmd_output("ovs-ofctl -t 5 --version")
        if br_list_result['status'] == 0:
            for br in br_list_result['output'].splitlines():
                self.add_cmd_output([
                    "%s bridge/dump-flows --offload-stats %s" % (actl, br),
                    "%s dpif/show-dp-features %s" % (actl, br),
                    "%s fdb/show %s" % (actl, br),
                    "%s fdb/stats-show %s" % (actl, br),
                    "%s mdb/show %s" % (actl, br),
                    "ovs-ofctl dump-flows %s" % br,
                    "ovs-ofctl dump-ports-desc %s" % br,
                    "ovs-ofctl dump-ports %s" % br,
                    "ovs-ofctl queue-get-config %s" % br,
                    "ovs-ofctl queue-stats %s" % br,
                    "ovs-ofctl show %s" % br,
                    "ovs-ofctl dump-groups %s" % br,
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

                # Flow protocol hex identifiers
                ofp_versions = {
                    0x01: "OpenFlow10",
                    0x02: "OpenFlow11",
                    0x03: "OpenFlow12",
                    0x04: "OpenFlow13",
                    0x05: "OpenFlow14",
                    0x06: "OpenFlow15",
                }

                # List protocols currently in use, if any
                ovs_list_bridge_cmd = "ovs-vsctl -t 5 list bridge %s" % br
                br_info = self.collect_cmd_output(ovs_list_bridge_cmd)

                br_protos = []
                for line in br_info['output'].splitlines():
                    if "protocols" in line:
                        br_protos_ln = line[line.find("[")+1:line.find("]")]
                        br_protos = br_protos_ln.replace('"', '').split(", ")

                # If 'list bridge' yeilded no protocols, use the range of
                # protocols enabled by default on this version of ovs.
                if br_protos == [''] and ofp_ver_result['output']:
                    ofp_version_range = ofp_ver_result['output'].splitlines()
                    ver_range = []

                    for line in ofp_version_range:
                        if "OpenFlow versions" in line:
                            v = line.split("OpenFlow versions ")[1].split(":")
                            ver_range = range(int(v[0], 16), int(v[1], 16)+1)

                    for protocol in ver_range:
                        if protocol in ofp_versions:
                            br_protos.append(ofp_versions[protocol])

                # Collect flow information for relevant protocol versions only
                for flow in flow_versions:
                    if flow in br_protos:
                        self.add_cmd_output([
                            "ovs-ofctl -O %s show %s" % (flow, br),
                            "ovs-ofctl -O %s dump-groups %s" % (flow, br),
                            "ovs-ofctl -O %s dump-group-stats %s" % (flow, br),
                            "ovs-ofctl -O %s dump-flows %s" % (flow, br),
                            "ovs-ofctl -O %s dump-tlv-map %s" % (flow, br),
                            "ovs-ofctl -O %s dump-ports-desc %s" % (flow, br)
                        ])

                port_list_result = self.exec_cmd(
                    "ovs-vsctl -t 5 list-ports %s" % br
                )
                if port_list_result['status'] == 0:
                    for port in port_list_result['output'].splitlines():
                        self.add_cmd_output([
                            "ovs-appctl cfm/show %s" % port,
                            "ovs-appctl qos/show %s" % port,
                            # Not all ports are "bond"s, but all "bond"s are
                            # a single port
                            "ovs-appctl bond/show %s" % port,
                            # In the case of IPSec, we should pull the config
                            "ovs-vsctl get Interface %s options" % port,
                        ])

                        if check_dpdk:
                            self.add_cmd_output(
                                "ovs-appctl netdev-dpdk/get-mempool-info %s" %
                                port
                            )

                if check_dpdk:
                    iface_list_result = self.exec_cmd(
                        "ovs-vsctl -t 5 list-ifaces %s" % br
                    )
                    if iface_list_result['status'] == 0:
                        for iface in iface_list_result['output'].splitlines():
                            self.add_cmd_output(
                                "ovs-appctl netdev-dpdk/get-mempool-info %s" %
                                iface)
                if check_6wind:
                    self.add_cmd_output([
                        "%s evpn/vip-list-show %s" % (actl, br),
                        "%s bridge/dump-conntracks-summary %s" % (actl, br),
                        "%s bridge/acl-table ingress/egress %s" % (actl, br),
                        "%s bridge/acl-table %s" % (actl, br),
                        "%s ofproto/show %s" % (actl, br),
                    ])

                    vrf_list = self.collect_cmd_output(
                        "%s vrf/list %s" % (actl, br))
                    if vrf_list['status'] == 0:
                        vrfs = vrf_list['output'].split()[1:]
                        for vrf in vrfs:
                            self.add_cmd_output([
                                "%s vrf/route-table %s" % (actl, vrf),
                            ])

                    evpn_list = self.collect_cmd_output(
                        "ovs-appctl evpn/list %s" % br)
                    if evpn_list['status'] == 0:
                        evpns = evpn_list['output'].split()[1:]
                        for evpn in evpns:
                            self.add_cmd_output([
                                "%s evpn/mac-table %s" % (actl, evpn),
                                "%s evpn/arp-table %s" % (actl, evpn),
                                "%s evpn/dump-flows %s %s" % (actl, br, evpn),
                                "%s evpn/dhcp-pool-show %s %s" % (
                                    actl, br, evpn),
                                "%s evpn/dhcp-relay-show %s %s" % (
                                    actl, br, evpn),
                                "%s evpn/dhcp-static-show %s %s" % (
                                    actl, br, evpn),
                                "%s evpn/dhcp-table-show %s %s" % (
                                    actl, br, evpn),
                                "%s evpn/proxy-arp-filter-list %s %s" % (
                                    actl, br, evpn),
                                "%s evpn/show %s %s" % (actl, br, evpn),
                                "%s port/dscp-table %s %s" % (actl, br, evpn),
                            ])


class RedHatOpenVSwitch(OpenVSwitch, RedHatPlugin):

    packages = ('openvswitch', 'openvswitch[2-9].*',
                'openvswitch-dpdk', 'nuage-openvswitch'
                '6windgate-fp')


class DebianOpenVSwitch(OpenVSwitch, DebianPlugin, UbuntuPlugin):

    packages = ('openvswitch-switch', 'nuage-openvswitch')


# vim: set et ts=4 sw=4 :
