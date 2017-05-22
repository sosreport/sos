# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os.path
import re


class Dlm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """DLM (Distributed lock manager)"""

    plugin_name = "dlm"
    profiles = ("cluster", )
    packages = ["cman", "dlm", "pacemaker"]
    option_list = [
        ("lockdump", "capture lock dumps for DLM", "slow", False),
    ]

    debugfs_path = "/sys/kernel/debug"
    _debugfs_cleanup = False

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
        if self._mount_debug():
            dlm_tool = "dlm_tool ls"
            result = self.call_ext_prog(dlm_tool)
            if result["status"] != 0:
                return

            lock_exp = r'^name\s+([^\s]+)$'
            lock_re = re.compile(lock_exp, re.MULTILINE)
            for lockspace in lock_re.findall(result["output"]):
                self.add_cmd_output(
                    "dlm_tool lockdebug -svw '%s'" % lockspace,
                    suggest_filename="dlm_locks_%s" % lockspace
                )

    def _mount_debug(self):
        if not os.path.ismount(self.debugfs_path):
            self._debugfs_cleanup = True
            r = self.call_ext_prog("mount -t debugfs debugfs %s"
                                   % self.debugfs_path)
            if r["status"] != 0:
                self._log_error("debugfs not mounted and mount attempt failed")
                self._debugfs_cleanup = False
        return os.path.ismount(self.debugfs_path)

    def postproc(self):
        if self._debugfs_cleanup and os.path.ismount(self.debugfs_path):
            r = self.call_ext_prog("umount %s" % self.debugfs_path)
            if r["status"] != 0:
                self._log_error("could not unmount %s" % self.debugfs_path)

        return

# vim: et ts=4 sw=4
