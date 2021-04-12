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
        self.add_copy_spec([
            "/proc/cpuinfo",
            "/sys/class/cpuid",
            "/sys/devices/system/cpu"
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
        ])

        if '86' in self.policy.get_arch():
            self.add_cmd_output("x86info -a")


# vim: set et ts=4 sw=4 :
