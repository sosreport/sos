# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

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


class MongoDb(Plugin, DebianPlugin, UbuntuPlugin):
    """MongoDB document database
    """

    plugin_name = 'mongodb'
    profiles = ('services',)

    packages = ('mongodb-server',)
    var_puppet_gen = "/var/lib/config-data/puppet-generated/mongodb"

    files = (
        '/etc/mongodb.conf',
        var_puppet_gen + '/etc/mongod.conf'
    )

    def setup(self):
        self.add_copy_spec([
            "/etc/mongodb.conf",
            self.var_puppet_gen + "/etc/",
            self.var_puppet_gen + "/etc/systemd/system/mongod.service.d/",
            "/var/log/mongodb/mongodb.log",
            "/var/log/containers/mongodb/mongodb.log"
        ])
        self.add_cmd_output("du -s /var/lib/mongodb/")

    def postproc(self):
        self.do_file_sub(
            "/etc/mongodb.conf",
            r"(mms-token\s*=\s*.*)",
            r"mms-token = ********"
        )

        self.do_file_sub(
            self.var_puppet_gen + "/etc/mongodb.conf",
            r"(mms-token\s*=\s*.*)",
            r"mms-token = ********"
        )


class RedHatMongoDb(MongoDb, RedHatPlugin):

    def setup(self):
        super(RedHatMongoDb, self).setup()
        self.add_copy_spec("/etc/sysconfig/mongodb")

# vim: set et ts=4 sw=4 :
