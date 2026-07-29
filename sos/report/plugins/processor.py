# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
from sos.report.plugins import (Plugin, IndependentPlugin, SoSPredicate,
                                PluginOpt)
from sos.policies.distros.ubuntu import UbuntuPolicy


class Processor(Plugin, IndependentPlugin):

    short_desc = 'CPU information'

    plugin_name = 'processor'
    profiles = ('system', 'hardware', 'memory')
    files = ('/proc/cpuinfo',)
    packages = ('cpufreq-utils', 'cpuid')
    option_list = [
        PluginOpt('max_cpu_dirs', default=64, val_type=int,
                  desc='Maximum number of cpu[0-9]+ directories '
                       'to collect from /sys/devices/system/cpu'),
    ]

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
        # Limit cpu[0-9]* directories to avoid excessive collection.
        # All non-cpu* directories are always collected.
        max_cpu_dirs = self.get_option('max_cpu_dirs')
        if max_cpu_dirs < 0:
            self._log_info(f"Invalid {max_cpu_dirs=} value provided, "
                           f"replacing by 0."
                           )
            max_cpu_dirs = 0
        cdirs = self.listdir('/sys/devices/system/cpu')

        if len(cdirs) > max_cpu_dirs:
            # separate cpu from non-cpu, then limit cpu dirs
            cpu_pattern = re.compile(r'cpu(\d+)')
            cpu_dirs = []
            other_dirs = []

            for cdir in cdirs:
                if cpu_pattern.fullmatch(cdir):
                    cpu_dirs.append(cdir)
                else:
                    other_dirs.append(cdir)

            # Only limit if cpu_dirs specifically exceeds max
            if len(cpu_dirs) > max_cpu_dirs:
                self._log_info(
                    f"Limiting cpu directories from {len(cpu_dirs)} to "
                    f"{max_cpu_dirs} (use '-k processor.max_cpu_dirs=N' "
                    f"to change)."
                )
                cpu_dirs = sorted(cpu_dirs)[:max_cpu_dirs]

            cdirs = other_dirs + cpu_dirs

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
                self.policy.dist_version() >= 20.04):
            self.cpu_kmods = ['msr']

        cpupower_pred = SoSPredicate(self, kmods=self.cpu_kmods)

        self.add_cmd_output([
            "cpupower frequency-info",
            "cpupower info",
            "cpupower idle-info",
        ], cmd_as_tag=True, pred=cpupower_pred)

        self.add_cmd_output("turbostat --debug sleep 10", cmd_as_tag=True,
                            pred=cpupower_pred, timeout=15)

        if '86' in self.policy.get_arch():
            self.add_cmd_output("x86info -a")


# vim: set et ts=4 sw=4 :
