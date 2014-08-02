# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

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


class Snmp(Plugin):
    """snmp related information
    """
    plugin_name = "snmp"

    files = ('/etc/snmp/snmpd.conf',)

    def setup(self):
        self.add_copy_spec("/etc/snmp")


class RedHatSnmp(Snmp, RedHatPlugin):
    """snmp related information for RedHat based distributions
    """

    packages = ('net-snmp',)

    def setup(self):
        super(RedHatSnmp, self).setup()


class DebianSnmp(Snmp, DebianPlugin, UbuntuPlugin):
    """snmp related information for Debian based distributions
    """

    packages = ('snmp',)

    def setup(self):
        super(DebianSnmp, self).setup()

# vim: et ts=4 sw=4
