# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class MongoDb(Plugin, DebianPlugin, UbuntuPlugin):

    short_desc = 'MongoDB document database'

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
            "/var/lib/mongodb/mongodb.log*"
        ])
        self.add_cmd_output("du -sh /var/lib/mongodb/")

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

    packages = (
        'mongodb-server',
        'rh-mongodb32-mongodb-server',
        'rh-mongodb34-mongodb-server',
        'rh-mongodb36-mongodb-server'
    )

    def setup(self):
        super(RedHatMongoDb, self).setup()
        self.add_copy_spec([
            "/etc/sysconfig/mongodb",
            "/etc/rh-mongodb*-mongo*.conf",
            "/etc/opt/rh/rh-mongodb*/mongo*.conf",
            "/var/opt/rh/rh-mongodb*/log/mongodb/mongod.log"
        ])

# vim: set et ts=4 sw=4 :
