# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
