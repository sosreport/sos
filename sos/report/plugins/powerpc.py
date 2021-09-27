# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

# This plugin enables collection of logs for Power systems and more
# specific logs for Pseries, PowerNV platforms.

from sos.report.plugins import Plugin, IndependentPlugin


class PowerPC(Plugin, IndependentPlugin):

    short_desc = 'IBM Power systems'

    plugin_name = 'powerpc'
    profiles = ('system', 'hardware')
    architectures = ('ppc.*',)

    def setup(self):
        try:
            with open(self.path_join('/proc/cpuinfo'), 'r') as fp:
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
                "ppc64_cpu --info",
                "ppc64_cpu --smt",
                "ppc64_cpu --cores-present",
                "ppc64_cpu --cores-on",
                "ppc64_cpu --run-mode",
                "ppc64_cpu --frequency",
                "ppc64_cpu --dscr",
                "diag_encl -v",
                "lsvpd -D",
                "lsmcode -A",
                "lscfg -v"
            ])

        if ispSeries:
            self.add_copy_spec([
                "/proc/ppc64/lparcfg",
                "/proc/ppc64/eeh",
                "/proc/ppc64/systemcfg",
                "/var/log/platform",
                "/var/log/drmgr",
                "/var/log/drmgr.0",
                "/var/log/hcnmgr",
                "/var/ct/IBM.DRM.stderr",
                "/var/ct/IW/log/mc/IBM.DRM/trace*"
            ])
            ctsnap_path = self.get_cmd_output_path(name="ctsnap", make=True)
            self.add_cmd_output([
                "servicelog --dump",
                "servicelog_notify --list",
                "usysattn",
                "usysident",
                "serv_config -l",
                "bootlist -m both -r",
                "lparstat -i",
                "ctsnap -xrunrpttr -d %s" % (ctsnap_path),
                "lsdevinfo"
            ])
            self.add_service_status("hcn-init")

        if isPowerNV:
            self.add_copy_spec([
                "/proc/ppc64/eeh",
                "/proc/ppc64/systemcfg",
                "/proc/ppc64/topology_updates",
                "/sys/firmware/opal/msglog",
                "/var/log/opal-elog/",
                "/var/log/opal-prd",
                "/var/log/opal-prd.log*"
            ])
            if self.path_isdir("/var/log/dump"):
                self.add_cmd_output("ls -l /var/log/dump")


# vim: set et ts=4 sw=4 :
