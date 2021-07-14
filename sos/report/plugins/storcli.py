# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class StorCLI(Plugin, IndependentPlugin):

    short_desc = 'LSI MegaRAID devices'

    plugin_name = 'storcli'
    profiles = ('system', 'storage', 'hardware',)
    packages = ('storcli',)

    def setup(self):
        cmd = '/opt/MegaRAID/storcli/storcli64'
        subcmds = [
            'show ctrlcount J',
            '/call show AliLog',
            '/call show all',
            '/call show events',
            '/call show termlog',
            '/call/bbu show all',
            '/call/cv show all',
            '/call/dall show J',
            '/call/eall show all',
            '/call/eall/sall show all',
            '/call/sall show all',
            '/call/vall show all',
        ]

        logpath = self.get_cmd_output_path()

        for subcmd in subcmds:
            self.add_cmd_output(
                "%s %s" % (cmd, subcmd),
                suggest_filename="storcli64_%s" % subcmd, runat=logpath)

# vim: set et ts=4 sw=4 :
