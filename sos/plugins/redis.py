# Copyright (C) 2015 Red Hat, Inc., Abhijeet Kasurde <akasurde@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin


class Redis(Plugin, RedHatPlugin):
    """Redis, in-memory data structure store
    """

    plugin_name = 'redis'
    profiles = ('services',)

    packages = ('redis',)
    files = ('/etc/redis.conf', '/var/log/redis')

    def setup(self):
        self.add_copy_spec("/etc/redis.conf")
        self.limit = self.get_option("log_size")
        self.add_cmd_output("redis-cli info")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/redis/redis.log*",
                               sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/redis/redis.log",
                               sizelimit=self.limit)

    def postproc(self):
        self.do_file_sub(
            "/etc/redis.conf",
            r"(masterauth\s).*",
            r"\1********"
        )
        self.do_file_sub(
            "/etc/redis.conf",
            r"(requirepass\s).*",
            r"\1********"
        )

# vim: set et ts=4 sw=4 :
