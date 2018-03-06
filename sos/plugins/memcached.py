# Copyright (C) 2018 Mikel Olasagasti Uranga <mikel@olasagasti.info>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Memcached(Plugin):
    """memcached distributed memory caching system"""

    plugin_name = 'memcached'
    profiles = ('webserver',)
    packages = ('memcached',)


class RedHatMemcached(Memcached, RedHatPlugin):

    files = ('/etc/sysconfig/memcached',)

    def setup(self):
        super(RedHatMemcached, self).setup()
        self.add_copy_spec("/etc/sysconfig/memcached")


class DebianMemcached(Memcached, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/memcached',)

    def setup(self):
        super(DebianMemcached, self).setup()
        self.add_copy_spec([
            "/etc/memcached.conf",
            "/etc/default/memcached"
        ])

# vim: set et ts=4 sw=4 :
