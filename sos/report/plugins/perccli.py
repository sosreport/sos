# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class PercCLI(Plugin, IndependentPlugin):

    short_desc = 'PowerEdge RAID Controller management'

    plugin_name = 'perccli'
    profiles = ('system', 'storage', 'hardware',)
    packages = ('perccli',)

    option_list = [
        PluginOpt('json', default=False, desc='collect data in JSON format')
    ]

    def setup(self):
        cmd = '/opt/MegaRAID/perccli/perccli64'
        subcmds = [
            'show ctrlcount',
            '/call show AliLog',
            '/call show all',
            '/call show termlog',
            '/call/bbu show all',
            '/call/cv show all',
            '/call/dall show',
            '/call/eall show all',
            '/call/eall/sall show all',
            '/call/sall show all',
            '/call/vall show all',
        ]

        json = ' J' if self.get_option('json') else ''

        logpath = self.get_cmd_output_path()

        for subcmd in subcmds:
            self.add_cmd_output(
                "%s %s%s" % (cmd, subcmd, json),
                suggest_filename="perccli64_%s%s" % (subcmd, json),
                runat=logpath)

        # /call show events need 'file=' option to get adapter info like below
        # "Adapter: # - Number of Events: xxx".
        subcmd = '/call show events'
        self.add_cmd_output(
            "%s %s file=/dev/stdout%s" % (cmd, subcmd, json),
            suggest_filename="perccli64_%s%s" % (subcmd, json),
            runat=logpath)

# vim: set et ts=4 sw=4 :
