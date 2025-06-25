# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Cephadm(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH distributed storage managed via cephadm'

    plugin_name = 'cephadm'
    profiles = ('storage')

    packages = (
        'cephadm'
    )

    def setup(self):
        all_logs = self.get_option("all_logs")

        if not all_logs:
            self.add_copy_spec([
                "/var/log/ceph/cephadm.log"
            ])
        else:
            self.add_copy_spec([
                "/var/log/ceph/cephadm*"
            ])

        self.add_copy_spec([
            "/etc/ceph/"
        ])

        cephadm_cmds = [
            "version",
            "gather-facts",
            "ls",
            "ceph-volume lvm list",
            "check-host"
        ]

        for s in cephadm_cmds:
            self.add_cmd_output(cmds="cephadm --timeout 5 %s" % s, suggest_filename="%s" % s)

        self.add_forbidden_path([
            "/etc/ceph/*keyring*",
            "/etc/ceph/*bindpass*"
        ])

# vim: set et ts=4 sw=4 :
