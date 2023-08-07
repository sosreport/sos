# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class UltraPath(Plugin, RedHatPlugin):

    short_desc = 'HUAWEI UltraPath'

    plugin_name = 'ultrapath'
    profiles = ('storage', 'hardware')
    packages = ('UltraPath',)
    kernel_mods = ('nxup', 'nxupext_a')

    def setup(self):
        """ Huawei UltraPath specific information - commands
        """
        self.add_cmd_output([
            "upadm show version",
            "upadm show connectarray",
            "upadm show option",
            "upadm show upconfig",
            "upadm show diskarray",
            "upadmin show vlun",
        ])

        result = self.collect_cmd_output('upadm show path')
        if result['status'] == 0:
            for line in result['output'].splitlines():
                if line.startswith("Array ID :"):
                    self.add_cmd_output("upadm show lun array=%s" %
                                        line.split(':')[1].strip())

# vim: set et ts=4 sw=4 :
