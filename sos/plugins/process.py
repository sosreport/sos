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


class Process(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """process information
    """

    plugin_name = 'process'
    profiles = ('system',)

    option_list = [
        ("lsof-threads", "gathers threads' open file info if supported",
         "slow", False)
    ]

    def setup(self):
        ps_axo = "ps axo"
        # process group and thread options
        ps_group_opts = "pid,ppid,user,group,lwp,nlwp,start_time,comm,cgroup"
        ps_sched_opts = "flags,state,uid,pid,ppid,pgid,sid,cls,pri,addr,sz,"
        ps_sched_opts += "wchan,stime,tty,time,cmd"
        self.add_copy_spec("/proc/sched_debug")
        self.add_cmd_output("ps auxwww", root_symlink="ps")
        self.add_cmd_output("pstree", root_symlink="pstree")
        self.add_cmd_output("lsof -b +M -n -l -c ''", root_symlink="lsof")
        if self.get_option("lsof-threads") or self.get_option("all_logs"):
            self.add_cmd_output("lsof -b +M -n -l")
        self.add_cmd_output([
            "ps auxwwwm",
            "ps alxwww",
            "%s %s" % (ps_axo, ps_group_opts),
            "%s %s" % (ps_axo, ps_sched_opts)
        ])

# vim: set et ts=4 sw=4 :
