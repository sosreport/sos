# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, IndependentPlugin


class System(Plugin, IndependentPlugin):

    short_desc = 'core system information'

    plugin_name = "system"
    profiles = ('system', 'kernel')
    verify_packages = ('glibc', 'initscripts', 'zlib')

    def setup(self):
        self.add_copy_spec([
            "/proc/sys",
            "/etc/sysconfig",
            "/etc/default",
            "/etc/environment",
        ])

        self.add_forbidden_path([
            "/proc/sys/net/ipv4/route/flush",
            "/proc/sys/net/ipv6/route/flush",
            "/proc/sys/net/ipv6/neigh/*/retrans_time",
            "/proc/sys/net/ipv6/neigh/*/base_reachable_time",
            "/etc/default/grub.d/50-curtin-settings.cfg",
        ])

        # collect glibc tuning decisions
        self.add_cmd_output([
            "ld.so --help",
            "ld.so --list-diagnostics",
            "ld.so --list-tunables"
        ])

        var_names = list(os.environ.keys())
        var_names.sort()
        self.add_string_as_file('\n'.join(var_names),
                                "environment_varnames",
                                plug_dir=True)

    def postproc(self):
        self.do_paths_http_sub([
            "/etc/sysconfig",
            "/etc/default",
            "/etc/environment",
        ])

# vim: set et ts=4 sw=4 :
