# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Process(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """process information
    """

    plugin_name = 'process'
    profiles = ('system',)

    def setup(self):
        ps_axo = "ps axo"
        # process group and thread options
        ps_group_opts = "pid,ppid,user,group,lwp,nlwp,start_time,comm,cgroup"
        ps_sched_opts = "flags,state,uid,pid,ppid,pgid,sid,cls,pri,addr,sz,"
        ps_sched_opts += "wchan,stime,tty,time,cmd"
        self.add_copy_spec("/proc/sched_debug")
        self.add_cmd_output("ps auxwww", root_symlink="ps")
        self.add_cmd_output("pstree", root_symlink="pstree")
        self.add_cmd_output("lsof -b +M -n -l", root_symlink="lsof")
        self.add_cmd_output([
            "ps auxwwwm",
            "ps alxwww",
            "%s %s" % (ps_axo, ps_group_opts),
            "%s %s" % (ps_axo, ps_sched_opts)
        ])

# vim: set et ts=4 sw=4 :
