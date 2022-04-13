# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class SeagateSES(Plugin, IndependentPlugin):
    """The seagate_ses plugin collect information about all
    connected seagate storage shelves.
    It captures Controller status information, ID, controllers' VPD
    information, Environmental zone, Drive, PHY details, Cooling Module
    and PSU information.
    """

    short_desc = 'Seagate SES status'
    plugin_name = 'seagate_ses'
    plugin_timeout = 600
    profiles = ('system', 'storage', 'hardware',)
    packages = ('fwdownloader_megaraid',)

    def setup(self):
        res = self.collect_cmd_output('fwdownloader -ses')

        # Finding actual SES devices and ignoring 0th element
        # as it does not contain any device information
        op_lst = []
        if res['status'] == 0:
            op_lst = res['output'].split("SES Device")[1:]
        devices = [
            i for i in range(len(op_lst))
            if "Vendor ID: SEAGATE" in op_lst[i]
        ]

        cmd = 'getstatus -d'
        subcmds = [
            'ddump_canmgr',
            'ddump_cblmgr',
            'ddump_drvmgr',
            'ddump_phycounters',
            'ddump_pwrmgr',
            'ddump_envctrl',
            'envctrl_fan',
            'envctrl_zone',
            'fwstatus',
            'getboardid',
            'getvpd',
            'report_faults',
            'ver',
          ]

        for devid in devices:
            self.add_cmd_output([
                "%s %d -CLI %s" % (cmd, devid, subcmd) for subcmd in subcmds
            ])

            self.add_cmd_output([
                "%s %d -cli %s" % (cmd, devid, subcmd) for subcmd in subcmds
            ])

# vim: set et ts=4 sw=4 :
