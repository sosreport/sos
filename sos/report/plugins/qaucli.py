# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin
import os


class Qaucli(Plugin, IndependentPlugin):

    short_desc = 'QLogic information'

    plugin_name = 'qaucli'
    profiles = ('system', 'storage', 'hardware',)
    packages = ('QConvergeConsoleCLI',)

    def setup(self):
        os.environ['PATH'] += os.pathsep + \
            "/opt/QLogic_Corporation/QConvergeConsoleCLI"

        subcmds = ['-c', '-g', '-pr fc -z', '-t']
        self.add_cmd_output([
            "qaucli %s" % subcmd for subcmd in subcmds
        ])

        result = self.collect_cmd_output('qaucli -i')
        if result['status'] == 0:
            for line in result['output'].splitlines():
                if "HBA Instance" in line:
                    hba = line.split(':')[1].strip()
                    self.add_cmd_output("qaucli -l %s" % hba)

# vim: set et ts=4 sw=4 :
