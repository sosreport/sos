# Copyright (C) 2023 Pablo Acevedo <pacevedo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class MicroshiftOVN(Plugin, RedHatPlugin):
    """This plugin is used to collect MicroShift 4.x OVN logs.
    """
    short_desc = 'MicroShift OVN'
    plugin_name = "microshift_ovn"
    plugin_timeout = 300
    containers = ('ovnkube-node', 'ovnkube-master',)
    packages = ('microshift-networking',)
    profiles = ('microshift',)

    def setup(self):
        self.add_copy_spec([
            '/etc/openvswitch/conf.db',
            '/etc/openvswitch/default.conf',
            '/etc/openvswitch/system-id.conf'])

        _ovs_cmd = 'ovs-appctl -t /var/run/ovn/'
        _subcmds = [
            'coverage/show',
            'memory/show',
            'ovsdb-server/sync-status'
        ]
        for file, db in [('ovnnb_db.ctl', 'OVN_Northbound'),
                         ('ovnsb_db.ctl', 'OVN_Southbound')]:
            self.add_cmd_output(
                [f"{_ovs_cmd}{file} {cmd}" for cmd in _subcmds],
                timeout=MicroshiftOVN.plugin_timeout)
            self.add_cmd_output(
                f"{_ovs_cmd}{file} ovsdb-server/get-db-storage-status {db}",
                timeout=MicroshiftOVN.plugin_timeout)

        self.add_cmd_output(
            f'{_ovs_cmd}ovn-controller.*.ctl ct-zone-list',
            timeout=MicroshiftOVN.plugin_timeout)
