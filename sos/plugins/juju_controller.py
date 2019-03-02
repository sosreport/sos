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

    plugin_name = "juju_controller"
    profiles = ("virt", "sysmgmt")

    # Use files instead of packages here because there is no package installed
    #  on a juju controller that uniquely identifies it:
    files = "/var/lib/juju/db"

    option_list = [
        (
            "export-mongodb",
            "Export mongodb collections as json files",
            "",
            False,
        )
    ]

    def export_mongodb(self, machineid, dbpass):
        collections = [
            "actionnotifications",
            "actions",
            "annotations",
            "applicationOfferConnections",
            "applicationOffers",
            "applications",
            "bakeryStorageItems",
            "blockdevices",
            "charms",
            "cleanups",
            "cloudCredentials",
            "cloudimagemetadata",
            "clouds",
            "constraints",
            "containerRefs",
            "controllers",
            "controllerusers",
            "deviceConstraints",
            "endpointbindings",
            "filesystems",
            "generations",
            "globalRefcounts",
            "globalSettings",
            "instanceData",
            "ip.addresses",
            "leaseholders",
            "leases",
            "linklayerdevices",
            "linklayerdevicesrefs",
            "machineUpgradeSeriesLocks",
            "machineremovals",
            "machines",
            "managedStoredResources",
            "meterStatus",
            "metricsmanager",
            "migrations",
            "modelEntityRefs",
            "modelUserLastConnection",
            "models",
            "modelusers",
            "openedPorts",
            "payloads",
            "permissions",
            "providerIDs",
            "refcounts",
            "relationNetworks",
            "relations",
            "relationscopes",
            "remoteEntities",
            "resources",
            "sequence",
            "settings",
            "sshhostkeys",
            "statuses",
            "storageattachments",
            "storageconstraints",
            "storageinstances",
            "storedResources",
            "subnets",
            "toolsmetadata",
            "txns.prune",
            "txns.stash",
            "units",
            "userLastLogin",
            "usermodelname",
            "users",
            "volumes",
        ]
        # We don't collect txns.log, statuseshistory, metrics, txns due to size

        for collection in collections:
            filename = "mongoexport_collection_{}.json".format(collection)
            # This will execute a mongoexport command, note it will add the
            # password to the sos log
            mongocmd = (
                "mongoexport --host 127.0.0.1 --port 37017 --db juju "
                + "--authenticationDatabase admin --ssl "
                + "--sslAllowInvalidCertificates --username '{}' --password "
                + "'{}' --collection {} --jsonArray"
            )
            self.add_cmd_output(
                mongocmd.format(machineid, dbpass, collection),
                suggest_filename=filename,
            )

    def get_machine_id(self):
        # get the juju machine name machine-X
        for dirpath, dirnames, filenames in os.walk("/var/lib/juju/agents"):
            for dirname in dirnames:
                match = re.match(r"(machine-\d+)", dirname)
                if match:
                    return match.group(1)
        return None

    def get_jujudb_pass(self, machineid):
        # Get agent config and figure out password
        try:
            fp = open("/var/lib/juju/agents/" + machineid + "/agent.conf", "r")
            filecontents = fp.read()
            fp.close()
        except Exception:
            return None
        for line in iter(filecontents.splitlines()):
            match = re.match(r"^statepassword: (\S+)", line)
            if match:
                return match.group(1)
        return None

    def add_query(self, machineid, dbpass, queryname, query):
        # Run a command for a single query
        filename = "mongo_{}.json".format(queryname)
        # This will execute a mongo command, note it will add the password to
        # the sos log
        mongocmd = (
            "mongo 127.0.0.1:37017/juju --authenticationDatabase admin"
            + " --ssl --sslAllowInvalidCertificates --quiet --username '{}' "
            + "--password '{}' --eval '{}'"
        )
        self.add_cmd_output(
            mongocmd.format(machineid, dbpass, query),
            suggest_filename=filename,
        )

    def setup(self):
        self.add_copy_spec("/etc/default/mongodb")
        self.add_copy_spec("/var/lib/juju/bootstrap-params")
        self.add_copy_spec("/lib/systemd/system/juju-db/juju-db.service")

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

        machineid = self.get_machine_id()
        dbpass = self.get_jujudb_pass(machineid)

        # If we got the password we can run some queries and export if needed
        if dbpass:
            for queryname, query in mongo_db_queries.items():
                self.add_query(machineid, dbpass, queryname, query)
            if self.get_option("export-mongodb"):
                self.export_mongodb(machineid, dbpass)


# vim: set et ts=4 sw=4 :
