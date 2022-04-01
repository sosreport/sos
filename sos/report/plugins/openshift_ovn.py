# Copyright (C) 2021 Nadia Pinaeva <npinaeva@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OpenshiftOVN(Plugin, RedHatPlugin):
    """This plugin is used to collect OCP 4.x OVN logs.
    """
    short_desc = 'Openshift OVN'
    plugin_name = "openshift_ovn"
    containers = ('ovnkube-master', 'ovnkube-node', 'ovn-ipsec')
    profiles = ('openshift',)

    def setup(self):
        self.add_copy_spec([
            "/var/lib/ovn/etc/ovnnb_db.db",
            "/var/lib/ovn/etc/ovnsb_db.db",
            "/var/lib/openvswitch/etc/keys",
            "/var/log/openvswitch/libreswan.log",
            "/var/log/openvswitch/ovs-monitor-ipsec.log"
        ])

        self.add_cmd_output([
            'ovn-appctl -t /var/run/ovn/ovnnb_db.ctl ' +
            'cluster/status OVN_Northbound',
            'ovn-appctl -t /var/run/ovn/ovnsb_db.ctl ' +
            'cluster/status OVN_Southbound'],
            container='ovnkube-master')
        self.add_cmd_output([
            'ovs-appctl -t /var/run/ovn/ovn-controller.*.ctl ' +
            'ct-zone-list'],
            container='ovnkube-node')
        self.add_cmd_output([
            'ovs-appctl -t ovs-monitor-ipsec tunnels/show',
            'ipsec status',
            'certutil -L -d sql:/etc/ipsec.d'],
            container='ovn-ipsec')
