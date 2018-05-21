# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
        self.add_copy_spec(log_path + "access.log", sizelimit=log_size)
        self.add_copy_spec(log_path + "cache.log", sizelimit=log_size)
        self.add_copy_spec(log_path + "squid.out", sizelimit=log_size)


class DebianSquid(Squid, DebianPlugin, UbuntuPlugin):

    plugin_name = 'squid'
    files = ('/etc/squid3/squid.conf',)
    packages = ('squid3',)

    def setup(self):
        self.add_copy_spec("/etc/squid3/squid.conf",
                           sizelimit=self.get_option('log_size'))
        self.add_copy_spec("/var/log/squid3/*",
                           sizelimit=self.get_option('log_size'))
        self.add_copy_spec(['/etc/squid-deb-proxy'])
        self.add_copy_spec("/var/log/squid-deb-proxy/*",
                           sizelimit=self.get_option('log_size'))
# vim: set et ts=4 sw=4 :
