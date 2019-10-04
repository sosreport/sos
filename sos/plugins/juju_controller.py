# This file is part of the sos project: https://github.com/sosreport/sos
# Copyright (C) 2019 Nick Niehoff <nick.niehoff@canonical.com>
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
import os
from sos.plugins import Plugin, UbuntuPlugin


# A Juju Controller is a juju machine so this plugin assumes the juju_machine
# plugin will be executed to collect that information
class JujuController(Plugin, UbuntuPlugin):
    """ Juju orchestration tool - Controller
    """

    plugin_name = 'juju_controller'
    profiles = ('virt', 'sysmgmt')

    # Use files instead of packages here because there is no package installed
    #  on a juju controller that uniquely identifies it:
    files = '/var/lib/juju/db'

    option_list = [
        ('export-mongodb',
         'Export mongodb collections as json files', '', False,)
    ]

    def export_mongodb(self, juju_machine_id, dbpass):
        # We are gonna grab the output of the mongo command
        # and do some regexp and replace()/split() it to a list.
        # Usually when connecting with ssl on localhost, the cli send some
        # output which unfortunately ends up in stdin instead of stderr
        # and we need to do this extra work to parse it.
        collections_query = ("mongo 127.0.0.1:37017/juju "
                             + "--authenticationDatabase admin "
                             + "--ssl --sslAllowInvalidCertificates --quiet "
                             + "--username {} --password {} ".format(
                               juju_machine_id, dbpass)
                             + "--eval 'db.getCollectionNames();'")

        _collections = self.get_command_output(collections_query)

        if _collections['status'] == 0:
            collections_output = _collections['output']
        else:
            collections_output = ''

        collections_regexp = re.compile(r'(?ms)^\[(.*)\]')
        collections = collections_regexp.findall(collections_output)[0]
        subs = [
            ('\"', ''),
            (',', ''),
        ]
        # In order to be able to properly query the mongodb collection
        # tables we need to cleanup the output from the collections_query
        # as those return the " and , symbols, which we cannot cleanly use
        # those to cleanly query after
        for search, replace in subs:
            collections = collections.replace(search, replace)
        collections = collections.split()

        # We don't collect txns.log, statuseshistory, metrics, txns due to size
        collections_ignore = ['txns.log', 'statuseshistory', 'metrics', 'txns']
        for item in collections_ignore:
            if item in collections:
                collections.remove(item)

        for collection in collections:
            filename = "mongoexport_collection_{}.json".format(collection)
            # This will execute a mongoexport command, note it will add the
            # password to the sos log, however we remove it from the filename
            mongoexport_cmd = (
                "mongoexport --host 127.0.0.1 --port 37017 --db juju "
                + "--authenticationDatabase admin --ssl "
                + "--sslAllowInvalidCertificates --username '{}' --password "
                + "'{}' --collection {} --jsonArray"
            )
            self.add_cmd_output(
                mongoexport_cmd.format(juju_machine_id, dbpass, collection),
                suggest_filename=filename,
            )

    def get_juju_machine_id(self):
        # get the juju machine name machine-X
        for dirpath, dirnames, filenames in os.walk('/var/lib/juju/agents'):
            for dirname in dirnames:
                match = re.match(r'(machine-\d+)', dirname)
                if match:
                    return match.group(1)
        return None

    def get_jujudb_pass(self, juju_machine_id):
        # Get agent config and figure out password
        try:
            fp = open(
                '/var/lib/juju/agents/' + juju_machine_id + '/agent.conf', 'r'
            )
            filecontents = fp.read()
            fp.close()
        except Exception:
            return None
        for line in iter(filecontents.splitlines()):
            match = re.match(r'^statepassword: (\S+)', line)
            if match:
                return match.group(1)
        return None

    def add_query(self, juju_machine_id, dbpass, queryname, query):
        # Run a command for a single query
        filename = 'mongo_{}.json'.format(queryname)
        # This will execute a mongo command, note it will add the password to
        # the sos log we remove it from the filename however
        mongocmd = (
            "mongo 127.0.0.1:37017/juju --authenticationDatabase admin"
            + " --ssl --sslAllowInvalidCertificates --quiet --username '{}' "
            + "--password '{}' --eval '{}'"
        )
        self.add_cmd_output(
            mongocmd.format(juju_machine_id, dbpass, query),
            suggest_filename=filename,
        )

    def setup(self):

        self.add_copy_spec([
            '/etc/default/mongodb',
            '/var/lib/juju/bootstrap-params',
            '/lib/systemd/system/juju-db/juju-db.service'
        ])

        # The key is the queryname to be used as the file name instead of the
        # entire query
        mongo_db_queries = {
            "rs.status": "JSON.stringify(rs.status());",
            "db.serverStatus": "JSON.stringify(db.serverStatus());",
            "db.stats": "JSON.stringify(db.stats());",
            "getCollectionInfos": "JSON.stringify(db.getCollectionInfos());",
            "collections.stats": "stats = new Array(); "
            + "db.getCollectionNames().forEach(function(coll) { "
            + "var c = db.getCollection(coll); "
            + "stats.push(JSON.stringify(c.stats())); "
            + "}); "
            + 'print("["); print(stats.join(",")); print("]")',
        }

        juju_machine_id = self.get_juju_machine_id()
        dbpass = self.get_jujudb_pass(juju_machine_id)

        # If we got the password we can run some queries and export if needed
        if dbpass:
            for queryname, query in mongo_db_queries.items():
                self.add_query(juju_machine_id, dbpass, queryname, query)
            if self.get_option('export-mongodb'):
                self.export_mongodb(juju_machine_id, dbpass)


# vim: set et ts=4 sw=4 :
