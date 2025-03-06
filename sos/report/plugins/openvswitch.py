# Copyright (C) 2014 Adam Stokes <adam.stokes@ubuntu.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from os import environ
import re
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenVSwitch(Plugin):

    short_desc = 'OpenVSwitch networking'
    plugin_name = "openvswitch"
    profiles = ('network', 'virt')
    actl = "ovs-appctl"
    vctl = "ovs-vsctl"
    ofctl = "ovs-ofctl"
    dpctl = "ovs-dpctl"
    check_dpdk = False
    check_6wind = False

    def setup(self):

        all_logs = self.get_option("all_logs")

        log_dirs = [
            '/var/log/openvswitch/',
            '/usr/local/var/log/openvswitch/',
        ]

        dpdk_enabled = self.collect_cmd_output(
            f"{self.vctl} -t 5 get Open_vSwitch . other_config:dpdk-init")
        self.check_dpdk = (dpdk_enabled["status"] == 0 and
                           dpdk_enabled["output"].startswith('"true"'))
        self.check_6wind = any(self.is_installed(p) for p in
                               ['6windgate-fp', 'nuage-openvswitch'])

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

        self.add_file_tags({
            "/var/log/openvswitch/ovs-vswitchd.log":
                "openvswitch_daemon_log",
            "/var/log/openvswitch/ovsdb-server.log":
                "openvswitch_server_log"
        })

        self.add_dir_listing([
            '/run/openvswitch',
            '/dev/hugepages/',
            '/dev/vfio',
            '/var/lib/vhost_sockets',
        ])

        self.add_cmd_output([
            # List devices and their drivers
            "dpdk_nic_bind --status",
            "dpdk-devbind.py --status",
            "driverctl list-devices",
            "driverctl -v list-devices",
            "driverctl list-overrides",
            "driverctl -v list-overrides",
            "driverctl list-persisted",
            # Capture a list of all bond devices
            f"{self.actl} bond/list",
            # Capture more details from bond devices
            f"{self.actl} bond/show",
            # Capture LACP details
            f"{self.actl} lacp/show",
            f"{self.actl} lacp/show-stats",
            # Capture coverage stats"
            f"{self.actl} coverage/show",
            # Capture cached routes
            f"{self.actl} ovs/route/show",
            # Capture tnl arp table"
            f"{self.actl} tnl/arp/show",
            # Capture a list of listening ports"
            f"{self.actl} tnl/ports/show -v",
            # Capture upcall information
            f"{self.actl} upcall/show",
            # Capture OVS list
            f"{self.vctl} -t 5 list Open_vSwitch",
            # Capture OVS manager
            f"{self.vctl} -t 5 list manager",
            # Capture OVS interface list
            f"{self.vctl} -t 5 list interface",
            # Capture OVS detailed information from all the bridges
            f"{self.vctl} -t 5 list bridge",
            # Capture OVS datapath list
            f"{self.vctl} -t 5 list datapath",
            # Capture DPDK queue to pmd mapping
            f"{self.actl} dpif-netdev/pmd-rxq-show -secs 5",
            f"{self.actl} dpif-netdev/pmd-rxq-show -secs 30",
            f"{self.actl} dpif-netdev/pmd-rxq-show",
            # Capture DPDK pmd stats
            f"{self.actl} dpif-netdev/pmd-stats-show",
            # Capture DPDK pmd performance counters
            f"{self.actl} dpif-netdev/pmd-perf-show",
            # Capture ofproto tunnel configs
            f"{self.actl} ofproto/list-tunnels",
            # Capture ipsec tunnel information
            f"{self.actl} -t ovs-monitor-ipsec tunnels/show",
            f"{self.actl} -t ovs-monitor-ipsec xfrm/state",
            f"{self.actl} -t ovs-monitor-ipsec xfrm/policies",
            # Capture OVS offload enabled flows
            f"{self.dpctl} dump-flows --name -m type=offloaded",
            # Capture OVS slowdatapth flows
            f"{self.dpctl} dump-flows --name -m type=ovs",
            # Capture dpcls implementations
            f"{self.actl} dpif-netdev/subtable-lookup-prio-get",
            # Capture dpif implementations
            f"{self.actl} dpif-netdev/dpif-impl-get",
            # Capture miniflow extract implementations
            f"{self.actl} dpif-netdev/miniflow-parser-get",
            # Capture DPDK pmd sleep config
            f"{self.actl} dpif-netdev/pmd-sleep-show",
            # Capture additional DPDK info
            f"{self.actl} dpdk/lcore-list",
            f"{self.actl} dpdk/log-list",
            f"{self.actl} dpdk/get-malloc-stats",
            # Capture dpdk mempool info
            f"{self.actl} netdev-dpdk/get-mempool-info"
        ])
        # Capture DPDK and other parameters
        self.add_cmd_output(
            f"{self.vctl} -t 5 get Open_vSwitch . other_config",
            tags="openvswitch_other_config")
        # The '-t 5' adds an upper bound on how long to wait to connect
        # to the Open vSwitch server, avoiding hangs when running sos.
        self.add_cmd_output(f"{self.vctl} -t 5 show",
                            tags="ovs_vsctl_show")

        # Gather systemd services logs
        self.add_journal(units="openvswitch")
        self.add_journal(units="openvswitch-nonetwork")
        self.add_journal(units="ovs-vswitchd")
        self.add_journal(units="ovsdb-server")
        self.add_journal(units="ovs-configuration")
        self.add_journal(units="openvswitch-ipsec")
        self.collect_ovs_info()
        self.collect_datapath()
        self.collect_ovs_bridge_info()

    def collect_ovs_info(self):
        """ Collect output of OVS commands """

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

        if self.check_6wind:
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
                f"{self.actl} vm/port-detailed-show",
                f"{self.actl} upcall/show",
                "fp-cli nfct4",
                f"{self.actl} vm/port-vip-list-show",
                "fp-shmem-ports -s",
                f"{self.dpctl} show -s",
                "fpcmd fp-vswitch-flows",
                "fp-cli fp-vswitch-ports percore",
                "fp-cli dpdk-debug-pool",
                "fp-cli dump-size",
                "fp-cli conf runtime",
                "fp-cli conf compiled",
                "fp-cli iface",
                f"{self.actl} memory/show",
            ])
            self.add_journal(units="virtual-accelerator")
            for table in ['filter', 'mangle', 'raw', 'nat']:
                self.add_cmd_output([f"fpcmd nf4-rules {table}"])

            # 6wind doesn't care on which bridge the ports are, there's only
            # one bridge and it's alubr0
            port_list = self.collect_cmd_output("fp-cli fp-vswitch-ports")
            if port_list['status'] == 0:
                for port in port_list['output'].splitlines():
                    mport = re.match(r'^([\d]+):[\s]+([^\s]+)', port)
                    if mport:
                        port_name = mport.group(2)
                        self.add_cmd_output([
                            f"fp-cli dpdk-cp-filter-budget {port_name}",
                        ])

    def collect_datapath(self):
        """ Gather the datapath information for each datapath """
        dp_list_result = self.collect_cmd_output(f'{self.actl} dpctl/dump-dps')
        if dp_list_result['status'] == 0:
            for dps in dp_list_result['output'].splitlines():
                self.add_cmd_output([
                    f"{self.actl} dpctl/show -s {dps}",
                    f"{self.actl} dpctl/dump-flows -m {dps}",
                    f"{self.actl} dpctl/dump-conntrack -m {dps}",
                    f"{self.actl} dpctl/ct-stats-show -m {dps}",
                    f"{self.actl} dpctl/ipf-get-status {dps}",
                ])

    def collect_ovs_bridge_info(self):
        """ Gather additional output for each OVS bridge on the host. """

        br_list_result = self.collect_cmd_output(f"{self.vctl} -t 5 list-br")
        if br_list_result['status'] != 0:
            return

        for bri in br_list_result['output'].splitlines():
            self.add_cmd_output([
                f"{self.actl} bridge/dump-flows --offload-stats {bri}",
                f"{self.actl} dpif/show-dp-features {bri}",
                f"{self.actl} fdb/show {bri}",
                f"{self.actl} fdb/stats-show {bri}",
                f"{self.actl} mdb/show {bri}",
                f"{self.ofctl} dump-flows {bri}",
                f"{self.ofctl} dump-ports-desc {bri}",
                f"{self.ofctl} dump-ports {bri}",
                f"{self.ofctl} queue-get-config {bri}",
                f"{self.ofctl} queue-stats {bri}",
                f"{self.ofctl} show {bri}",
                f"{self.ofctl} dump-groups {bri}",
            ])

            self.get_flow_versions(bri)

            self.get_port_list(bri)

            if self.check_dpdk:
                iface_list_result = self.exec_cmd(
                    f"{self.vctl} -t 5 list-ifaces {bri}"
                )
                if iface_list_result['status'] == 0:
                    for iface in iface_list_result['output'].splitlines():
                        self.add_cmd_output(
                            f"{self.actl} netdev-dpdk/get-mempool-info {iface}"
                        )
            if self.check_6wind:
                self.add_cmd_output([
                    f"{self.actl} evpn/vip-list-show {bri}",
                    f"{self.actl} bridge/dump-conntracks-summary {bri}",
                    f"{self.actl} bridge/acl-table ingress/egress {bri}",
                    f"{self.actl} bridge/acl-table {bri}",
                    f"{self.actl} ofproto/show {bri}",
                ])

                vrf_list = self.collect_cmd_output(
                    f"{self.actl} vrf/list {bri}")
                if vrf_list['status'] == 0:
                    vrfs = vrf_list['output'].split()[1:]
                    for vrf in vrfs:
                        self.add_cmd_output([
                            f"{self.actl} vrf/route-table {vrf}",
                        ])

                evpn_list = self.collect_cmd_output(
                    f"{self.actl} evpn/list {bri}")
                if evpn_list['status'] == 0:
                    evpns = evpn_list['output'].split()[1:]
                    for evpn in evpns:
                        self.add_cmd_output([
                            f"{self.actl} evpn/mac-table {evpn}",
                            f"{self.actl} evpn/arp-table {evpn}",
                            f"{self.actl} evpn/dump-flows {bri} {evpn}",
                            f"{self.actl} evpn/dhcp-pool-show {bri} {evpn}",
                            f"{self.actl} evpn/dhcp-relay-show {bri} {evpn}",
                            f"{self.actl} evpn/dhcp-static-show {bri} {evpn}",
                            f"{self.actl} evpn/dhcp-table-show {bri} {evpn}",
                            f"{self.actl} evpn/proxy-arp-filter-list "
                            f"{bri} {evpn}",
                            f"{self.actl} evpn/show {bri} {evpn}",
                            f"{self.actl} port/dscp-table {bri} {evpn}",
                        ])

    def get_flow_versions(self, bridge):
        """ Collect flow version of the given bridge """
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

        ofp_ver_result = self.collect_cmd_output(f"{self.vctl} -t 5 --version")

        # List protocols currently in use, if any
        br_info = self.collect_cmd_output(
            f"{self.vctl} -t 5 list bridge {bridge}")

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
                    ver_sp = line.split("OpenFlow versions ")
                    ver = ver_sp[1].split(":")
                    ver_range = range(int(ver[0], 16),
                                      int(ver[1], 16)+1)

            for protocol in ver_range:
                if protocol in ofp_versions:
                    br_protos.append(ofp_versions[protocol])

        # Collect flow information for relevant protocol versions only
        for flow in flow_versions:
            if flow in br_protos:
                self.add_cmd_output([
                    f"{self.ofctl} -O {flow} show {bridge}",
                    f"{self.ofctl} -O {flow} dump-groups {bridge}",
                    f"{self.ofctl} -O {flow} dump-group-stats {bridge}",
                    f"{self.ofctl} -O {flow} dump-flows {bridge}",
                    f"{self.ofctl} -O {flow} dump-tlv-map {bridge}",
                    f"{self.ofctl} -O {flow} dump-ports-desc {bridge}",
                    f"{self.ofctl} -O {flow} dump-meters {bridge}",
                    f"{self.ofctl} -O {flow} meter-stats {bridge}",
                ])

    def get_port_list(self, bridge):
        """ Collect port list of the given bridge """
        port_list_result = self.exec_cmd(
            f"{self.vctl} -t 5 list-ports {bridge}")

        if port_list_result['status'] == 0:
            for port in port_list_result['output'].splitlines():
                self.add_cmd_output([
                    f"{self.actl} cfm/show {port}",
                    f"{self.actl} qos/show {port}",
                    # Not all ports are "bond"s, but all "bond"s are
                    # a single port
                    f"{self.actl} bond/show {port}",
                    # In the case of IPSec, we should pull the config
                    f"{self.actl} get Interface {port} options",
                    ])

                if self.check_dpdk:
                    self.add_cmd_output(
                        f"{self.actl} netdev-dpdk/get-mempool-info {port}")


class RedHatOpenVSwitch(OpenVSwitch, RedHatPlugin):

    packages = ('openvswitch', 'openvswitch[2-9].*',
                'openvswitch-dpdk', 'nuage-openvswitch'
                '6windgate-fp')


class DebianOpenVSwitch(OpenVSwitch, DebianPlugin, UbuntuPlugin):

    packages = ('openvswitch-switch', 'nuage-openvswitch')

    files = (
        '/var/snap/openstack-hypervisor/common/etc/openvswitch/system-id.conf',
    )

    def setup(self):

        if self.is_installed('openstack-hypervisor'):

            self.ovs_cmd_pre = "openstack-hypervisor."

            self.actl = f"{self.ovs_cmd_pre}{self.actl}"
            self.vctl = f"{self.ovs_cmd_pre}{self.vctl}"
            self.ofctl = f"{self.ovs_cmd_pre}{self.ofctl}"
            self.dpctl = f"{self.ovs_cmd_pre}{self.dpctl}"

        super().setup()

# vim: set et ts=4 sw=4 :
