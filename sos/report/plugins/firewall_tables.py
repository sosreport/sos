# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, IndependentPlugin, SoSPredicate)


class firewall_tables(Plugin, IndependentPlugin):

    short_desc = 'firewall tables'

    plugin_name = "firewall_tables"
    profiles = ('network', 'system')

    def collect_iptable(self, tablename):
        """ Collecting iptables rules for a table loads either kernel module
        of the table name (for kernel <= 3), or nf_tables (for kernel >= 4).
        If neither module is present, the rules must be empty."""

        modname = "iptable_" + tablename
        cmd = "iptables -t " + tablename + " -nvL"
        self.add_cmd_output(
            cmd,
            pred=SoSPredicate(self, kmods=[modname, 'nf_tables']))

    def collect_ip6table(self, tablename):
        """ Same as function above, but for ipv6 """

        modname = "ip6table_" + tablename
        cmd = "ip6tables -t " + tablename + " -nvL"
        self.add_cmd_output(
            cmd,
            pred=SoSPredicate(self, kmods=[modname, 'nf_tables']))

    def collect_nftables(self):
        """ Collects nftables rulesets with 'nft' commands if the modules
        are present """

        # collect nftables ruleset
        nft_pred = SoSPredicate(self,
                                kmods=['nf_tables', 'nfnetlink'],
                                required={'kmods': 'all'})
        self.add_cmd_output("nft list ruleset", pred=nft_pred, changes=True)

    def setup(self):
        # collect iptables -t for any existing table, if we can't read the
        # tables, collect 2 default ones (mangle, filter)
        try:
            ip_tables_names = open("/proc/net/ip_tables_names").read()
        except IOError:
            ip_tables_names = "mangle\nfilter\n"
        for table in ip_tables_names.splitlines():
            self.collect_iptable(table)
        # collect the same for ip6tables
        try:
            ip_tables_names = open("/proc/net/ip6_tables_names").read()
        except IOError:
            ip_tables_names = "mangle\nfilter\n"
        for table in ip_tables_names.splitlines():
            self.collect_ip6table(table)

        self.collect_nftables()

        # When iptables is called it will load the modules
        # iptables_filter (for kernel <= 3) or
        # nf_tables (for kernel >= 4) if they are not loaded.
        # The same goes for ipv6.
        self.add_cmd_output(
            "iptables -vnxL",
            pred=SoSPredicate(self, kmods=['iptable_filter', 'nf_tables'])
        )

        self.add_cmd_output(
            "ip6tables -vnxL",
            pred=SoSPredicate(self, kmods=['ip6table_filter', 'nf_tables'])
        )

        self.add_copy_spec([
            "/etc/nftables",
            "/etc/sysconfig/nftables.conf",
            "/etc/nftables.conf",
        ])

# vim: set et ts=4 sw=4 :
