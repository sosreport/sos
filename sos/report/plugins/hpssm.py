# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt
import re


class Hpssm(Plugin, IndependentPlugin):
    """
    This plugin will capture details for each controller from Smart Storage
    Array Administrator, an Array diagnostic report from Smart Storage
    Administrator Diagnostics Utility and, when the plugins debug option is
    enabled will gather the Active Health System log via the RESTful Interface
    Tool (iLOREST).
    """
    short_desc = 'HP Smart Storage Management'

    plugin_name = 'hpssm'
    profiles = ('system', 'storage', 'hardware',)
    packages = ('ilorest', 'ssacli', 'ssaducli',)

    option_list = [
        PluginOpt('debug', default=False, desc='capture debug data')
    ]

    def setup(self):
        cmd = 'ssacli'
        subcmds = [
            'ctrl all show status'
        ]
        slot_subcmds = [
            'ld all show',
            'ld all show detail',
            'pd all show',
            'pd all show detail'
        ]
        self.add_cmd_output(
            ["%s %s" % (cmd, subcmd) for subcmd in subcmds]
        )

        pattern = re.compile("^HP.*Smart Array (.*) in Slot ([0123456789])")
        config_detail_cmd = cmd + ' ctrl all show config detail'
        config_detail = self.collect_cmd_output(config_detail_cmd)
        ctrl_slots = []
        if config_detail['status'] == 0:
            ctrl_slots = [m.group(2)
                          for line in config_detail['output'].splitlines()
                          for m in [pattern.search(line)] if m]
        ssacli_ctrl_slot_cmd = cmd + ' ctrl slot='
        self.add_cmd_output(
            ["%s%s %s" % (
                ssacli_ctrl_slot_cmd,
                slot,
                slot_subcmd
            )
             for slot in ctrl_slots
             for slot_subcmd in slot_subcmds]
        )

        logpath = self.get_cmd_output_path()

        self.add_cmd_output(
            'ssaducli -v -adu -f %s/adu-log.zip' % logpath,
            suggest_filename='ssaducli_-v_-adu.log'
        )

        if self.get_option("debug"):
            self.do_debug(logpath)

    def do_debug(self, logpath):
        self.add_cmd_output(
            'ilorest serverlogs --selectlog=AHS --directorypath=%s' % logpath,
            runat=logpath, suggest_filename='ilorest.log'
        )

# vim: set et ts=4 sw=4 :
