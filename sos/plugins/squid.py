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
    """Squid caching proxy
    """

    plugin_name = 'squid'
    profiles = ('webserver', 'services', 'sysmgmt')


class RedHatSquid(Squid, RedHatPlugin):

    files = ('/etc/squid/squid.conf',)
    packages = ('squid',)

    def setup(self):
        log_size = self.get_option('log_size')
        log_path = "/var/log/squid/"
        self.add_copy_spec("/etc/squid/squid.conf")
        self.add_copy_spec_limit(log_path + "access.log", sizelimit=log_size)
        self.add_copy_spec_limit(log_path + "cache.log", sizelimit=log_size)
        self.add_copy_spec_limit(log_path + "squid.out", sizelimit=log_size)


class DebianSquid(Squid, DebianPlugin, UbuntuPlugin):

    plugin_name = 'squid'
    files = ('/etc/squid3/squid.conf',)
    packages = ('squid3',)

    def setup(self):
        self.add_copy_spec_limit("/etc/squid3/squid.conf",
                                 sizelimit=self.get_option('log_size'))
        self.add_copy_spec_limit("/var/log/squid3/*",
                                 sizelimit=self.get_option('log_size'))
        self.add_copy_spec(['/etc/squid-deb-proxy'])
        self.add_copy_spec_limit("/var/log/squid-deb-proxy/*",
                                 sizelimit=self.get_option('log_size'))
# vim: set et ts=4 sw=4 :
