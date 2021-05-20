# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re

from sos.report.plugins import Plugin, IndependentPlugin


class Process(Plugin, IndependentPlugin):

    short_desc = 'process information'

    plugin_name = 'process'
    profiles = ('system',)

    option_list = [
        ("lsof", "gathers information on all open files", "slow", True),
        ("lsof-threads", "gathers threads' open file info if supported",
         "slow", False),
        ("smaps", "gathers all /proc/*/smaps files", "", False),
        ("samples", "specify the number of samples that iotop will capture, "
            "with an interval of 0.5 seconds between samples", "", "20"),
        ("numprocs", "number of processes to collect /proc data of", '', 2048)
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

        procs = [p for p in os.listdir("/proc") if re.match("[0-9]", p)]
        if self.get_option("numprocs"):
            procs = procs[:self.get_option("numprocs")]

        for proc in procs:
            self.add_copy_spec([
                "/proc/%s/status" % proc,
                "/proc/%s/cpuset" % proc,
                "/proc/%s/oom_*" % proc,
                "/proc/%s/stack" % proc,
                "/proc/%s/limits" % proc
            ])

        if self.get_option("smaps"):
            self.add_copy_spec("/proc/[0-9]*/smaps")

        self.add_cmd_output("ps auxwwwm", root_symlink="ps",
                            tags=['ps_aux', 'ps_auxww', 'ps_auxwww',
                                  'ps_auxwwwm'], priority=1)
        self.add_cmd_output("pstree -lp", root_symlink="pstree")
        if self.get_option("lsof"):
            self.add_cmd_output("lsof +M -n -l -c ''", root_symlink="lsof",
                                timeout=15, priority=50)

        if self.get_option("lsof-threads"):
            self.add_cmd_output("lsof +M -n -l", timeout=15, priority=50)

        self.add_cmd_output([
            "ps alxwww",
            "ps -elfL",
            "%s %s" % (ps_axo, ps_group_opts),
            "%s %s" % (ps_axo, ps_sched_opts)
        ])

        if self.get_option("samples"):
            self.add_cmd_output("iotop -b -o -d 0.5 -t -n %s"
                                % self.get_option("samples"), priority=100)

        self.add_cmd_output([
            "pidstat -p ALL -rudvwsRU --human -h",
            "pidstat -tl"
        ])
# vim: set et ts=4 sw=4 :
