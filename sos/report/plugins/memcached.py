# Copyright (C) 2018 Mikel Olasagasti Uranga <mikel@olasagasti.info>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Memcached(Plugin):

    short_desc = 'memcached distributed memory caching system'

    plugin_name = 'memcached'
    profiles = ('webserver',)
    packages = ('memcached',)

    mm_tool = "memcached-tool"

    def setup(self):
        host = "127.0.0.1:11211"

        subcmds = [
            "display",
            "dump",
            "keys",
            "stats",
            "settings",
        ]

        self.add_cmd_output([
            f"{self.mm_tool} {host} {subcmd}" for subcmd in subcmds])


class RedHatMemcached(Memcached, RedHatPlugin):

    files = ('/etc/sysconfig/memcached',)

    def setup(self):
        super().setup()
        self.add_copy_spec("/etc/sysconfig/memcached",
                           tags="sysconfig_memcached")


class DebianMemcached(Memcached, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/memcached',)

    def setup(self):
        self.mm_tool = "/usr/share/memcached/scripts/memcached-tool"
        super().setup()
        self.add_copy_spec([
            "/etc/memcached.conf",
            "/etc/default/memcached"
        ])

# vim: set et ts=4 sw=4 :
