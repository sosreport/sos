# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Processor(Plugin, IndependentPlugin):

    short_desc = 'CPU information'

    plugin_name = 'processor'
    profiles = ('system', 'hardware', 'memory')
    files = ('/proc/cpuinfo',)
    packages = ('cpufreq-utils', 'cpuid')

    def setup(self):

        cpupath = '/sys/devices/system/cpu'

        self.add_file_tags({
            "%s/smt/control" % cpupath: 'cpu_smt_control',
            "%s/smt/active" % cpupath: 'cpu_smt_active',
            "%s/vulnerabilities/.*" % cpupath: 'cpu_vulns',
            "%s/vulnerabilities/spectre_v2" % cpupath: 'cpu_vulns_spectre_v2',
            "%s/vulnerabilities/meltdown" % cpupath: 'cpu_vulns_meltdown',
            "%s/cpu.*/online" % cpupath: 'cpu_cores'
        })

        self.add_copy_spec([
            "/proc/cpuinfo",
            "/sys/class/cpuid",
        ])
        # copy /sys/devices/system/cpu/cpuX with separately applied sizelimit
        # this is required for systems with tens/hundreds of CPUs where the
        # cumulative directory size exceeds 25MB or even 100MB.
        cdirs = self.listdir('/sys/devices/system/cpu')
        self.add_copy_spec([
            self.path_join('/sys/devices/system/cpu', cdir) for cdir in cdirs
        ])

        self.add_cmd_output([
            "lscpu",
            "lscpu -ae",
            "cpupower info",
            "cpupower idle-info",
            "cpupower frequency-info",
            "cpufreq-info",
            "cpuid",
            "cpuid -r",
            "turbostat --debug sleep 10"
        ], cmd_as_tag=True)

        if '86' in self.policy.get_arch():
            self.add_cmd_output("x86info -a")


# vim: set et ts=4 sw=4 :
