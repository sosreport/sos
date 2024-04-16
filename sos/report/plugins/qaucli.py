# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Qaucli(Plugin, IndependentPlugin):

    short_desc = 'QLogic information'

    plugin_name = 'qaucli'
    profiles = ('system', 'storage', 'hardware',)
    packages = ('QConvergeConsoleCLI',)

    def setup(self):
        cmd = "/opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli"
        subcmds = ['-c', '-g', '-pr fc -z', '-t']

        for subcmd in subcmds:
            self.add_cmd_output(
                f"{cmd} {subcmd}",
                suggest_filename=f"qaucli_{subcmd}")

        result = self.collect_cmd_output(
                     f"{cmd} -i",
                     suggest_filename="qaucli_-i")

        if result['status'] == 0:
            for line in result['output'].splitlines():
                if "HBA Instance" in line:
                    hba = line.split(':')[1].strip()
                    self.add_cmd_output(
                        f"{cmd} -l {hba}",
                        suggest_filename=f"qaucli_-l_{hba}")

# vim: set et ts=4 sw=4 :
