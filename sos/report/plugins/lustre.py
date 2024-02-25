# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
from sos.report.plugins import Plugin, RedHatPlugin


class Lustre(Plugin, RedHatPlugin):

    short_desc = 'Lustre filesystem'

    plugin_name = 'lustre'
    profiles = ('storage', 'network', 'cluster', )
    packages = ('lustre', 'lustre-client', )

    def get_params(self, name, param_list):
        """Use lctl get_param to collect a selection of parameters into a
            file.

        """
        self.add_cmd_output("lctl get_param %s" % " ".join(param_list),
                            suggest_filename="params-%s" % name,
                            stderr=False)

    def setup(self):
        self.add_cmd_output([
            "lctl debug_kernel",
            "lctl device_list",
            "lctl list_nids",
            "lctl route_list",
            "lnetctl net show -v"
        ])

        # Grab almost everything
        output = self.exec_cmd("lctl list_param -R *")['output']
        exclude = (".*@.*|.*dump_page_cache|peers|.*quota.*|osd-.*|.*osc.*|"
                   "mgs.*|.*mgc_irstate|ldlm.*state|.*job_stats|.*exports.*")
        params = [item for item in output.splitlines()
                  if not re.match(exclude, item)]
        self.get_params("all", params)

        self.get_params(
            "basic",
            ["version", "health_check", "debug"]
        )

        # Client Specific
        self.add_cmd_output([
            "lfs df",
            "lfs df -i"
        ])
        self.get_params("osc_client", [
            "osc.*.max_dirty_mb",
            "osc.*.max_pages_per_rpc",
            "osc.*.checksums",
            "osc.*.max_rpcs_in_flight"
        ])

        # Server Specific
        self.get_params(
            "osd",
            ["osd-*.*.{mntdev,files*,kbytes*,blocksize,brw_stats}"]
        )
        self.get_params("quota", ["osd-*.*.quota_slave.{info,limit_*,acct_*}"])
        self.get_params("mgs", ["mgs.MGS.ir_timeout", "mgs.MGS.live.*"])

        # mb_groups can be VERY large, and provide minimal debug usefulness
        self.add_forbidden_path("*/mb_groups")
        self.add_copy_spec([
            "/sys/fs/ldiskfs",
            "/proc/fs/ldiskfs",
        ])

        # Grab emergency ring buffer dumps and other largish info
        if self.get_option("all_logs"):
            self.add_copy_spec("/tmp/lustre-log.*")
            self.get_params("job-stats", ["*.*.job_stats"])
            self.get_params("peers", ["peers"])

# vim: set et ts=4 sw=4 :
