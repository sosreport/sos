# Copyright (C) 2018 Mikel Olasagasti Uranga <mikel@olasagasti.info>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
