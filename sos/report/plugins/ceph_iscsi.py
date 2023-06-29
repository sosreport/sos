# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephISCSI(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = "CEPH iSCSI"

    plugin_name = "ceph_iscsi"
    profiles = ("storage", "virt", "container", "ceph")
    packages = ("ceph-iscsi",)
    services = ("rbd-target-api", "rbd-target-gw")
    containers = ("rbd-target-api.*", "rbd-target-gw.*")

    def setup(self):
        self.add_copy_spec([
            "/etc/tcmu/tcmu.conf",
            "/var/log/**/ceph-client.*.log",
            "/var/log/**/rbd-target-api.log",
            "/var/log/**/rbd-target-gw.log",
            "/var/log/**/tcmu-runner.log",
            "/var/log/tcmu-runner.log"
        ])

        self.add_cmd_output([
            "gwcli info",
            "gwcli ls"
        ])

# vim: set et ts=4 sw=4 :
