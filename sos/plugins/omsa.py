# Copyright (C) 2015 Dell, Inc. Charles Rose <charles_rose@dell.com>
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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class omsa(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    '''Dell OpenManage Server Administrator (OMSA)
    '''

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
            "{0} system alertaction".format(self.omreport),
            "{0} system alertlog".format(self.omreport),
            "{0} system cmdlog".format(self.omreport),
            "{0} system pedestinations".format(self.omreport),
            "{0} system platformevents".format(self.omreport),
            "{0} system summary".format(self.omreport),
            "{0} system events".format(self.omreport),
            "{0} chassis info".format(self.omreport),
        ], timeout=30)

# vim: et ts=4 sw=4
