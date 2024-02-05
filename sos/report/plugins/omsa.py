# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class omsa(Plugin, IndependentPlugin):

    short_desc = 'Dell OpenManage Server Administrator (OMSA)'

    plugin_name = 'omsa'
    profiles = ('hardware', 'debug')

    files = ('/opt/dell/srvadmin/bin/omreport',)
    packages = ('srvadmin-omacore',)

    omreport = '/opt/dell/srvadmin/bin/omreport'

    def setup(self):
        self.add_copy_spec([
            "/var/log/dell/updatepackage/log/support",
            "/opt/dell/srvadmin/var/log/openmanage/Inventory.xml*",
            "/opt/dell/srvadmin/etc/omreg.cfg",
            "/opt/dell/srvadmin/etc/openmanage/oma/ini",
            "/opt/dell/srvadmin/etc/srvadmin-deng/ini",
            "/opt/dell/srvadmin/etc/srvadmin-isvc/ini/d*ini",
        ])

        self.add_cmd_output([
            f"{self.omreport} system alertaction",
            f"{self.omreport} system alertlog",
            f"{self.omreport} system cmdlog",
            f"{self.omreport} system pedestinations",
            f"{self.omreport} system platformevents",
            f"{self.omreport} system summary",
            f"{self.omreport} system events",
            f"{self.omreport} chassis info",
            f"{self.omreport} chassis biossetup",
            f"{self.omreport} storage controller",
        ], timeout=30)

# vim: et ts=4 sw=4
