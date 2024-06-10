# Copyright (c) 2024 Rudnei Bertol Jr <rudnei@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
from sos.report.plugins import Plugin, RedHatPlugin


class AAPreceptorPlugin(Plugin, RedHatPlugin):
    short_desc = 'AAP receptor plugin'
    plugin_name = 'aap_receptor'
    profiles = ('sysmgmt', 'ansible')
    packages = ('receptor', 'receptorctl')
    services = ('receptor',)

    def setup(self):
        self.add_copy_spec([
            "/etc/receptor",
            "/tmp/receptor/*/status",
            "/var/lib/receptor",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/receptor"
            ])
        else:
            self.add_copy_spec([
                "/var/log/receptor/*.log"
            ])

        self.add_forbidden_path([
            "/etc/receptor/tls",
            "/etc/receptor/*key.pem"
        ])

        self.add_dir_listing([
            "/etc/receptor",
            "/var/run/receptor",
            "/var/run/awx-receptor"
        ])

        for s in glob.glob('/var/run/*receptor/*.sock'):
            self.add_cmd_output(f"receptorctl --socket {s} status",
                                suggest_filename="receptorctl_status")
            self.add_cmd_output(f"receptorctl --socket {s} status --json",
                                suggest_filename="receptorctl_status.json")
            self.add_cmd_output(f"receptorctl --socket {s} work list",
                                suggest_filename="receptorctl_work_list.json")
            break

# vim: set et ts=4 sw=4 :
