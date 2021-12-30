# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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

        # FIXME: provide a a long-term solution for #1299
        self.add_forbidden_path([
            "/proc/sys/net/ipv4/route/flush",
            "/proc/sys/net/ipv6/route/flush",
            "/proc/sys/net/ipv6/neigh/*/retrans_time",
            "/proc/sys/net/ipv6/neigh/*/base_reachable_time"
        ])

        # collect glibc tuning decisions
        self.add_cmd_output([
            "ld.so --help",
            "ld.so --list-diagnostics",
            "ld.so --list-tunables"
        ])


# vim: set et ts=4 sw=4 :
