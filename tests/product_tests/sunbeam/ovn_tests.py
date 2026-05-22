# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest


class OvnBasicTest(StageOneReportTest):
    """Ensure that a basic execution runs as expected with simple deployment.

    :avocado: tags=sunbeam
    """

    sos_cmd = '-v -o ovn_host'
    arch = ['x86_64']

    ubuntu_only = True

    def test_ovn_cmds_collected(self):
        ran_cmds = [
            'openstack-hypervisor.ovs-vsctl_list_Open_vSwitch',
            'openstack-hypervisor.ovs-ofctl_-O_OpenFlow13_dump-flows_br-int',
            'openstack-hypervisor.ovs-vsctl_list-br',
        ]
        for cmd in ran_cmds:
            self.assertFileCollected(f'sos_commands/ovn_host/{cmd}')

# vim: et ts=4 sw=4
