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


class Squid(Plugin):
    """squid related information
    """

    plugin_name = 'squid'


class RedHatSquid(Squid, RedHatPlugin):
    """squid Red Hat related information
    """

    files = ('/etc/squid/squid.conf',)
    packages = ('squid',)

    def setup(self):
        self.add_copy_spec_limit("/etc/squid/squid.conf",
                                 sizelimit=self.get_option('log_size'))


class DebianSquid(Squid, DebianPlugin, UbuntuPlugin):
    """squid related information for Debian and Ubuntu
    """

    plugin_name = 'squid'
    files = ('/etc/squid3/squid.conf',)
    packages = ('squid3',)

    def setup(self):
        self.add_copy_spec_limit("/etc/squid3/squid.conf",
                                 sizelimit=self.get_option('log_size'))
        self.add_copy_spec_limit("/var/log/squid3/*",
                                 sizelimit=self.get_option('log_size'))
        self.add_copy_specs(['/etc/squid-deb-proxy'])
        self.add_copy_spec_limit("/var/log/squid-deb-proxy/*",
                                 sizelimit=self.get_option('log_size'))
# vim: et ts=4 sw=4
