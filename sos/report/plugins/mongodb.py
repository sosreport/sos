# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
import yaml
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class MongoDb(Plugin):

    short_desc = 'MongoDB document database'

    plugin_name = 'mongodb'
    profiles = ('services',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/mongodb"

    files = (
        '/etc/mongodb.conf',
        var_puppet_gen + '/etc/mongod.conf'
    )

    db_folder = "/var/lib/mongodb"

    def setup(self):
        self.add_copy_spec([
            "/etc/mongodb.conf",
            self.var_puppet_gen + "/etc/",
            self.var_puppet_gen + "/etc/systemd/system/mongod.service.d/",
            "/var/log/mongodb/mongodb.log",
            "/var/lib/mongodb/mongodb.log*"
        ])
        self.add_cmd_output(f"du -sh {self.db_folder}/")

    def postproc(self):
        for file in ["/etc/mongodb.conf",
                     self.var_puppet_gen + "/etc/mongodb.conf"]:
            self.do_file_sub(
                file,
                r"(mms-token)\s*=\s*(.*)",
                r"\1 = ********"
            )


class RedHatMongoDb(MongoDb, RedHatPlugin):

    packages = (
        'mongodb-server',
        'rh-mongodb32-mongodb-server',
        'rh-mongodb34-mongodb-server',
        'rh-mongodb36-mongodb-server'
    )

    def setup(self):
        super().setup()
        self.add_copy_spec([
            "/etc/sysconfig/mongodb",
            "/etc/rh-mongodb*-mongo*.conf",
            "/etc/opt/rh/rh-mongodb*/mongo*.conf",
            "/var/opt/rh/rh-mongodb*/log/mongodb/mongod.log"
        ])


class UbuntuMongodb(MongoDb, DebianPlugin, UbuntuPlugin):

    packages = (
        'mongodb-server',
        'mongodb-server-core',
        'juju-db',
    )

    files = (
        '/var/lib/juju/db',
        '/var/snap/juju-db/current/db',
    )

    services = (
        'juju-db',
        'mongodb',
    )

    def setup(self):
        if get_juju_info := self.path_exists('/var/lib/juju/db'):
            self.db_folder = "/var/lib/juju/db"
        elif get_juju_info := self.path_exists('/var/snap/juju-db/curent/db'):
            self.db_folder = "/var/snap/juju-db/current/db"

        super().setup()

        if get_juju_info:
            for the_dir in self.listdir('/var/lib/juju/agents'):
                if re.search('machine-*', the_dir):
                    username = the_dir
                    with open(f'/var/lib/juju/agents/{username}/agent.conf',
                              'r', encoding='UTF-8') as f:
                        data = yaml.safe_load(f)
                        password = data['statepassword']

                        self._capture_db_data(username, password)
                    break

    def _capture_db_data(self, username, password):
        if self.path_exists("/usr/bin/mongo"):
            client = "/usr/bin/mongo"
        elif self.path_exists("/usr/lib/juju/mongo*/bin/mongo"):
            client = "/usr/lib/juju/mongo*/bin/mongo"
        else:
            client = "/snap/bin/juju-db.mongo"

        cmds_to_check = [
            'db.hostInfo()',
            'db.getCollectionInfos()',
            'db.getCollectionNames()',
            'db.getProfilingStatus()',
            'db.replicationInfo()',
            'db.serverStatus()',
            'db.stats()',
            'rs.conf()',
            'rs.status()',
        ]

        for cmd in cmds_to_check:
            self.add_cmd_output(
                f"{client} 127.0.0.1:37017/juju --authenticationDatabase admin"
                f" --ssl --sslAllowInvalidCertificates --username {username}"
                f" --password {password} --eval {cmd}",
                suggest_filename=cmd, subdir="db_commands"
            )


# vim: set et ts=4 sw=4 :
