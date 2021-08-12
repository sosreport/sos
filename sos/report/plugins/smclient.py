# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class SMcli(Plugin, IndependentPlugin):

    short_desc = 'SANtricity storage device'

    plugin_name = 'smclient'
    plugin_timeout = 900
    profiles = ('system', 'storage', 'hardware',)
    packages = ('SMclient',)

    option_list = [
        PluginOpt('debug', default=False, desc='capture support debug data')
    ]

    def setup(self):
        subcmds = [
            "show storagearray;",
            "show storagearray connections;",
            "show storagearray healthstatus;",
        ]

        ssnames = []

        # Get list of storage arrays
        result = self.collect_cmd_output('SMcli -d -S')
        if result['status'] == 0:
            for line in result['output'].splitlines():
                if 'localhost' in line:
                    ssnames.append(line.split()[0])

        # Collect status of each storage array
        for ssname in ssnames:
            self.add_cmd_output([
                "SMcli localhost -n %s -c '%s'" % (ssname, subcmd)
                for subcmd in subcmds
            ])

        if self.get_option("debug"):
            self.do_debug(ssnames)

    def do_debug(self, ssnames):
        logpath = self.get_cmd_output_path(make=False)

        cmd = 'SMcli localhost -n'
        subcmd = 'save storageArray supportData file='
        for ssname in ssnames:
            self.add_cmd_output(
                "%s %s -c '%s\"support-%s\";'" % (cmd, ssname, subcmd, ssname),
                runat=logpath, timeout=450)

# vim: set et ts=4 sw=4 :
