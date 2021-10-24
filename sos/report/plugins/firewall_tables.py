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
        return self.collect_cmd_output("nft list ruleset", pred=nft_pred,
                                       changes=True)

    def setup(self):
        # first, collect "nft list ruleset" as collecting commands like
        # ip6tables -t mangle -nvL
        # depends on its output
        # store in nft_ip_tables lists of ip[|6] tables from nft list
        nft_list = self.collect_nftables()
        nft_ip_tables = {'ip': [], 'ip6': []}
        nft_lines = nft_list['output'] if nft_list['status'] == 0 else ''
        for line in nft_lines.splitlines():
            words = line.split()[0:3]
            if len(words) == 3 and words[0] == 'table' and \
                    words[1] in nft_ip_tables.keys():
                nft_ip_tables[words[1]].append(words[2])
        # collect iptables -t for any existing table, if we can't read the
        # tables, collect 2 default ones (mangle, filter)
        # do collect them only when relevant nft list ruleset exists
        default_ip_tables = "mangle\nfilter\n"
        try:
            ip_tables_names = open("/proc/net/ip_tables_names").read()
        except IOError:
            ip_tables_names = default_ip_tables
        for table in ip_tables_names.splitlines():
            if nft_list['status'] == 0 and table in nft_ip_tables['ip']:
                self.collect_iptable(table)
        # collect the same for ip6tables
        try:
            ip_tables_names = open("/proc/net/ip6_tables_names").read()
        except IOError:
            ip_tables_names = default_ip_tables
        for table in ip_tables_names.splitlines():
            if nft_list['status'] == 0 and table in nft_ip_tables['ip6']:
                self.collect_ip6table(table)

        # When iptables is called it will load:
        # 1) the modules iptables_filter (for kernel <= 3) or
        #    nf_tables (for kernel >= 4) if they are not loaded.
        # 2) nft 'ip filter' table will be created
        # The same goes for ipv6.
        if nft_list['status'] != 0 or 'filter' in nft_ip_tables['ip']:
            self.add_cmd_output(
                "iptables -vnxL",
                pred=SoSPredicate(self, kmods=['iptable_filter', 'nf_tables'])
            )
        if nft_list['status'] != 0 or 'filter' in nft_ip_tables['ip6']:
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
