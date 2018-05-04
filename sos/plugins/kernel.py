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
import os
import glob
import json


class Kernel(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Linux kernel
    """

    plugin_name = 'kernel'
    profiles = ('system', 'hardware', 'kernel')
    verify_packages = ('kernel$',)

    sys_module = '/sys/module'

    option_list = [
        ("with-timer", "gather /proc/timer* statistics", "slow", False)
    ]

    def get_bpftool_prog_ids(self, prog_file):
        out = []
        try:
            prog_data = json.load(open(prog_file))
        except Exception, e:
            self._log_info("Could not parse bpftool prog list as JSON: %s" % e)
            return out
        for item in range(len(prog_data)):
            out.append(prog_data[item]["id"])
        return out

    def get_bpftool_map_ids(self, map_file):
        out = []
        try:
            map_data = json.load(open(map_file))
        except Exception, e:
            self._log_info("Could not parse bpftool map list as JSON: %s" % e)
            return out
        for item in range(len(map_data)):
            out.append(map_data[item]["id"])
        return out

    def setup(self):
        # compat
        self.add_cmd_output("uname -a", root_symlink="uname")
        self.add_cmd_output("lsmod", root_symlink="lsmod")
        self.add_cmd_output("ls -lt /sys/kernel/slab")

        try:
            modules = os.listdir(self.sys_module)
            self.add_cmd_output("modinfo " + " ".join(modules),
                                suggest_filename="modinfo_ALL_MODULES")
        except OSError:
            self._log_warn("could not list %s" % self.sys_module)

        # find /lib/modules/*/{extras,updates,weak-updates} -ls
        extra_mod_patterns = [
            "/lib/modules/*/extra",
            "/lib/modules/*/updates",
            "/lib/modules/*/weak-updates",
        ]
        extra_mod_paths = []
        for pattern in extra_mod_patterns:
            extra_mod_paths.extend(glob.glob(pattern))

        self.add_cmd_output([
            "dmesg",
            "sysctl -a",
            "dkms status",
            "find %s -ls" % " ".join(extra_mod_paths)
        ])

        clocksource_path = "/sys/devices/system/clocksource/clocksource0/"

        self.add_forbidden_path([
            '/sys/kernel/debug/tracing/trace_pipe',
            '/sys/kernel/debug/tracing/README',
            '/sys/kernel/debug/tracing/trace_stat/*',
            '/sys/kernel/debug/tracing/per_cpu/*',
            '/sys/kernel/debug/tracing/events/*'
        ])

        self.add_copy_spec([
            "/proc/modules",
            "/proc/sys/kernel/random/boot_id",
            "/sys/module/*/parameters",
            "/sys/module/*/initstate",
            "/sys/module/*/refcnt",
            "/sys/module/*/taint",
            "/sys/module/*/version",
            "/sys/firmware/acpi/*",
            "/sys/kernel/debug/tracing/*",
            "/proc/kallsyms",
            "/proc/buddyinfo",
            "/proc/slabinfo",
            "/proc/zoneinfo",
            "/lib/modules/%s/modules.dep" % self.policy.kernel_version(),
            "/etc/conf.modules",
            "/etc/modules.conf",
            "/etc/modprobe.conf",
            "/etc/modprobe.d",
            "/etc/sysctl.conf",
            "/etc/sysctl.d",
            "/lib/sysctl.d",
            "/proc/cmdline",
            "/proc/driver",
            "/proc/sys/kernel/tainted",
            "/proc/softirqs",
            "/proc/lock*",
            "/proc/misc",
            "/var/log/dmesg",
            "/sys/fs/pstore",
            clocksource_path + "available_clocksource",
            clocksource_path + "current_clocksource"
        ])

        if self.get_option("with-timer"):
            # This can be very slow, depending on the number of timers,
            # and may also cause softlockups
            self.add_copy_spec("/proc/timer*")

        # collect list of eBPF programs and maps and their dumps
        prog_file = self.get_cmd_output_now("bpftool -j prog list")
        for prog_id in self.get_bpftool_prog_ids(prog_file):
            for dumpcmd in ["xlated", "jited"]:
                self.add_cmd_output("bpftool prog dump %s id %s" %
                                    (dumpcmd, prog_id))
        map_file = self.get_cmd_output_now("bpftool -j map list")
        for map_id in self.get_bpftool_map_ids(map_file):
            self.add_cmd_output("bpftool map dump id %s" % map_id)

# vim: set et ts=4 sw=4 :
