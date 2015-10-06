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
import os
import glob


class Kernel(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Linux kernel
    """

    plugin_name = 'kernel'
    profiles = ('system', 'hardware', 'kernel')

    sys_module = '/sys/module'

    def setup(self):
        # compat
        self.add_cmd_output("uname -a", root_symlink="uname")
        self.add_cmd_output("lsmod", root_symlink="lsmod")
        self.add_cmd_output("ls -lt /sys/kernel/slab")

        try:
            modules = os.listdir(self.sys_module)
            self.add_cmd_output("modinfo " + " ".join(modules))
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
        self.add_copy_spec([
            "/proc/modules",
            "/proc/sys/kernel/random/boot_id",
            "/sys/module/*/parameters",
            "/sys/module/*/initstate",
            "/sys/module/*/refcnt",
            "/sys/module/*/taint",
            "/sys/firmware/acpi/*",
            "/proc/kallsyms",
            "/proc/buddyinfo",
            "/proc/slabinfo",
            "/proc/zoneinfo",
            "/lib/modules/%s/modules.dep" % self.policy().kernel_version(),
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
            "/proc/timer*",
            "/proc/lock*",
            "/proc/misc",
            "/var/log/dmesg",
            clocksource_path + "available_clocksource",
            clocksource_path + "current_clocksource"
        ])

# vim: set et ts=4 sw=4 :
