# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
        ps_sched_opts += "wchan,lstart,tty,time,cmd"

        self.add_copy_spec([
            "/proc/sched_debug",
            "/proc/stat"
        ])

        self.add_cmd_output("ps auxwww", root_symlink="ps")
        self.add_cmd_output("pstree", root_symlink="pstree")
        self.add_cmd_output("lsof -b +M -n -l -c ''", root_symlink="lsof")

        if self.get_option("lsof-threads") or self.get_option("all_logs"):
            self.add_cmd_output("lsof -b +M -n -l")

        self.add_cmd_output([
            "ps auxwwwm",
            "ps alxwww",
            "ps -elfL",
            "%s %s" % (ps_axo, ps_group_opts),
            "%s %s" % (ps_axo, ps_sched_opts)
        ])

# vim: set et ts=4 sw=4 :
