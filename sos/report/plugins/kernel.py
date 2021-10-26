# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt
import glob


class Kernel(Plugin, IndependentPlugin):
    """The Kernel plugin is aimed at collecting general information about
    the locally running kernel. This information should be distribution-neutral
    using commands and filesystem collections that are ubiquitous across
    distributions.

    Debugging information from /sys/kernel/debug is collected by default,
    however care is taken so that these collections avoid areas like
    /sys/kernel/debug/tracing/trace_pipe which would otherwise cause the
    sos collection attempt to appear to 'hang'.

    The 'trace' option will enable the collection of the
    /sys/kernel/debug/tracing/trace file specfically, but will not change the
    behavior stated above otherwise.
    """

    short_desc = 'Linux kernel'

    plugin_name = 'kernel'
    profiles = ('system', 'hardware', 'kernel')
    verify_packages = ('kernel$',)

    sys_module = '/sys/module'

    option_list = [
        PluginOpt('with-timer', default=False,
                  desc='gather /proc/timer* statistics'),
        PluginOpt('trace', default=False,
                  desc='gather /sys/kernel/debug/tracing/trace file')
    ]

    def setup(self):
        # compat
        self.add_cmd_output("uname -a", root_symlink="uname")
        self.add_cmd_output("lsmod", root_symlink="lsmod")
        self.add_cmd_output("ls -lt /sys/kernel/slab")

        try:
            modules = self.listdir(self.sys_module)
            self.add_cmd_output("modinfo " + " ".join(modules),
                                suggest_filename="modinfo_ALL_MODULES",
                                tags='modinfo_all')
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

        if extra_mod_paths:
            self.add_cmd_output("find %s -ls" % " ".join(extra_mod_paths))

        self.add_cmd_output([
            "dmesg",
            "sysctl -a",
            "dkms status"
        ], cmd_as_tag=True)

        clocksource_path = "/sys/devices/system/clocksource/clocksource0/"

        # FIXME: provide a a long-term solution for #1299
        self.add_forbidden_path([
            '/sys/kernel/debug/tracing/trace_pipe',
            '/sys/kernel/debug/tracing/README',
            '/sys/kernel/debug/tracing/trace_stat',
            '/sys/kernel/debug/tracing/per_cpu',
            '/sys/kernel/debug/tracing/events',
            '/sys/kernel/debug/tracing/free_buffer',
            '/sys/kernel/debug/tracing/trace_marker',
            '/sys/kernel/debug/tracing/trace_marker_raw',
            '/sys/kernel/debug/tracing/instances/*/per_cpu/*/snapshot_raw',
            '/sys/kernel/debug/tracing/instances/*/per_cpu/*/trace_pipe*',
            '/sys/kernel/debug/tracing/instances/*/trace_pipe'
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
            "/sys/kernel/livepatch/*",
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
            "/sys/kernel/debug/dynamic_debug/control",
            "/sys/kernel/debug/extfrag/unusable_index",
            "/sys/kernel/debug/extfrag/extfrag_index",
            clocksource_path + "available_clocksource",
            clocksource_path + "current_clocksource",
            "/proc/pressure/"
        ])

        if self.get_option("with-timer"):
            # This can be very slow, depending on the number of timers,
            # and may also cause softlockups
            self.add_copy_spec("/proc/timer*")

        if not self.get_option("trace"):
            self.add_forbidden_path("/sys/kernel/debug/tracing/trace")

# vim: set et ts=4 sw=4 :
