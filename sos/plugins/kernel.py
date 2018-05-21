# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os
import glob


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

# vim: set et ts=4 sw=4 :
