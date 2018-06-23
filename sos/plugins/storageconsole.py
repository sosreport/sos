# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class StorageConsole(Plugin, RedHatPlugin, DebianPlugin):
    """Red Hat Storage Console
    """

    plugin_name = 'storageconsole'
    profiles = ('storage',)

    packages = ('rhscon-core',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        if not all_logs:
            self.add_copy_spec([
                "/var/log/skyring/skyring.log",
                "/var/log/skyring/bigfin.log",
                "/var/log/carbon/console.log",
                "/var/log/graphite-web/info.log",
                "/var/log/graphite-web/exception.log",
            ])
        else:
            self.add_copy_spec([
                "/var/log/skyring/",
                "/var/log/carbon/",
                "/var/log/graphite-web/"
            ])

        self.add_copy_spec([
            "/etc/skyring/",
            "/etc/carbon/",
            "/etc/graphite-web/"
        ])

        self.add_cmd_output(
            "mongo skyring --eval 'db.getCollectionNames()'",
            suggest_filename="mongo_skyring_collectionnames.txt")
        self.add_cmd_output(
            "mongo skyring --eval 'DBQuery.shellBatchSize = 10000;"
            "db.storage_nodes.find()'",
            suggest_filename="mongo_skyring_storagenodes.txt")

# vim: set et ts=4 sw=4 :
