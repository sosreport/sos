# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, CosPlugin)


class Process(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, CosPlugin):

    short_desc = 'process information'

    plugin_name = 'process'
    profiles = ('system',)

    option_list = [
        ("lsof", "gathers information on all open files", "slow", True),
        ("lsof-threads", "gathers threads' open file info if supported",
         "slow", False),
        ("smaps", "gathers all /proc/*/smaps files", "", False),
        ("samples", "specify the number of samples that iotop will capture, "
            "with an interval of 0.5 seconds between samples", "", "20")
    ]

    def setup(self):
        ps_axo = "ps axo"
        # process group and thread options
        ps_group_opts = "pid,ppid,user,group,lwp,nlwp,start_time,comm,cgroup"
        ps_sched_opts = "flags,state,uid,pid,ppid,pgid,sid,cls,pri,addr,sz,"
        ps_sched_opts += "wchan:20,lstart,tty,time,cmd"

        self.add_copy_spec([
            "/proc/sched_debug",
            "/proc/stat"
        ])

        if self.get_option("smaps"):
            self.add_copy_spec("/proc/[0-9]*/smaps")

        self.add_cmd_output("ps auxwww", root_symlink="ps")
        self.add_cmd_output("pstree -lp", root_symlink="pstree")
        if self.get_option("lsof"):
            self.add_cmd_output("lsof -b +M -n -l -c ''", root_symlink="lsof")

        if self.get_option("lsof-threads"):
            self.add_cmd_output("lsof -b +M -n -l")

        self.add_cmd_output([
            "ps auxwwwm",
            "ps alxwww",
            "ps -elfL",
            "%s %s" % (ps_axo, ps_group_opts),
            "%s %s" % (ps_axo, ps_sched_opts)
        ])

        if self.get_option("samples"):
            self.add_cmd_output("iotop -b -o -d 0.5 -t -n %s"
                                % self.get_option("samples"))
# vim: set et ts=4 sw=4 :
