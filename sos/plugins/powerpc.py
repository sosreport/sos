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

# This plugin enables collection of logs for Power systems and more
# specific logs for Pseries, PowerNV platforms.

import os
from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class PowerPC(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """IBM Power systems
    """

    plugin_name = 'powerpc'
    profiles = ('system', 'hardware')

    def check_enabled(self):
        return "ppc64" in self.policy().get_arch()

    def setup(self):
        try:
            with open('/proc/cpuinfo', 'r') as fp:
                contents = fp.read()
                ispSeries = "pSeries" in contents
                isPowerNV = "PowerNV" in contents
        except:
            ispSeries = False
            isPowerNV = False

        if ispSeries or isPowerNV:
            self.add_copy_spec([
                "/proc/device-tree/",
                "/proc/loadavg",
                "/proc/locks",
                "/proc/misc",
                "/proc/swaps",
                "/proc/version",
                "/dev/nvram",
                "/var/lib/lsvpd/"
            ])
            self.add_cmd_output([
                "ppc64_cpu --smt",
                "ppc64_cpu --cores-present",
                "ppc64_cpu --cores-on",
                "ppc64_cpu --run-mode",
                "ppc64_cpu --frequency",
                "ppc64_cpu --dscr",
                "lscfg -vp",
                "lsmcode -A",
                "lsvpd --debug"
            ])

        if ispSeries:
            self.add_copy_spec([
                "/proc/ppc64/lparcfg",
                "/proc/ppc64/eeh",
                "/proc/ppc64/systemcfg",
                "/var/log/platform"
            ])
            self.add_cmd_output([
                "lsvio -des",
                "servicelog --dump",
                "servicelog_notify --list",
                "usysattn",
                "usysident",
                "serv_config -l",
                "bootlist -m both -r",
                "lparstat -i"
            ])

        if isPowerNV:
            self.add_copy_spec([
                "/proc/ppc64/eeh",
                "/proc/ppc64/systemcfg"
                "/proc/ppc64/topology_updates"
                "/sys/firmware/opal/msglog",
                "/var/log/opal-elog/"
            ])
            if os.path.isdir("/var/log/dump"):
                self.add_cmd_output("ls -l /var/log/dump")


# vim: set et ts=4 sw=4 :
