# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt
import re


class Dlm(Plugin, IndependentPlugin):

    short_desc = 'DLM (Distributed lock manager)'

    plugin_name = "dlm"
    profiles = ("cluster", )
    packages = ("cman", "dlm", "pacemaker")
    option_list = [
        PluginOpt('lockdump', default=False, desc='capture lock dumps for DLM')
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/sysconfig/dlm"
        ])
        self.add_cmd_output([
            "dlm_tool log_plock",
            "dlm_tool dump",
            "dlm_tool ls -n"
        ])
        if self.get_option("lockdump"):
            self.do_lockdump()

    def do_lockdump(self):
        dlm_tool = "dlm_tool ls"
        result = self.collect_cmd_output(dlm_tool)
        if result["status"] != 0:
            return

        lock_exp = r'^name\s+([^\s]+)$'
        lock_re = re.compile(lock_exp, re.MULTILINE)
        for lockspace in lock_re.findall(result["output"]):
            self.add_cmd_output(
                "dlm_tool lockdebug -svw '%s'" % lockspace,
                suggest_filename="dlm_locks_%s" % lockspace
            )

# vim: et ts=4 sw=4
