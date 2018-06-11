# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
        return "ppc64" in self.policy.get_arch()

    def setup(self):
        try:
            with open('/proc/cpuinfo', 'r') as fp:
                contents = fp.read()
                ispSeries = "pSeries" in contents
                isPowerNV = "PowerNV" in contents
        except IOError:
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
                "diag_encl -v"
            ])

        if ispSeries:
            self.add_copy_spec([
                "/proc/ppc64/lparcfg",
                "/proc/ppc64/eeh",
                "/proc/ppc64/systemcfg",
                "/var/log/platform"
            ])
            self.add_cmd_output([
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
                "/proc/ppc64/systemcfg",
                "/proc/ppc64/topology_updates",
                "/sys/firmware/opal/msglog",
                "/var/log/opal-elog/",
                "/var/log/opal-prd"
            ])
            if os.path.isdir("/var/log/dump"):
                self.add_cmd_output("ls -l /var/log/dump")


# vim: set et ts=4 sw=4 :
