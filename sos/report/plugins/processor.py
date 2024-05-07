# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate
from sos.policies.distros.ubuntu import UbuntuPolicy


class Processor(Plugin, IndependentPlugin):

    short_desc = 'CPU information'

    plugin_name = 'processor'
    profiles = ('system', 'hardware', 'memory')
    files = ('/proc/cpuinfo',)
    packages = ('cpufreq-utils', 'cpuid')

    cpu_kmods = []

    def setup(self):

        cpupath = '/sys/devices/system/cpu'

        self.add_file_tags({
            f"{cpupath}/smt/control": 'cpu_smt_control',
            f"{cpupath}/smt/active": 'cpu_smt_active',
            f"{cpupath}/vulnerabilities/.*": 'cpu_vulns',
            f"{cpupath}/vulnerabilities/spectre_v2": 'cpu_vulns_spectre_v2',
            f"{cpupath}/vulnerabilities/meltdown": 'cpu_vulns_meltdown',
            f"{cpupath}/cpu.*/online": 'cpu_cores',
            f"{cpupath}/cpu/cpu0/cpufreq/cpuinfo_max_freq":
                'cpuinfo_max_freq'
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
            "cpufreq-info",
            "cpuid",
            "cpuid -r",
        ], cmd_as_tag=True)

        if (isinstance(self.policy, UbuntuPolicy) and
                self.policy.dist_version() >= 24.04):
            self.cpu_kmods = ['msr']

        cpupower_pred = SoSPredicate(self, kmods=self.cpu_kmods)

        self.add_cmd_output([
            "cpupower frequency-info",
            "cpupower info",
            "cpupower idle-info",
            "turbostat --debug sleep 10",
        ], cmd_as_tag=True, pred=cpupower_pred)

        if '86' in self.policy.get_arch():
            self.add_cmd_output("x86info -a")


# vim: set et ts=4 sw=4 :
