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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class StorageConsole(Plugin, RedHatPlugin, DebianPlugin):
    """Red Hat Storage Console
    """

    plugin_name = 'storageconsole'
    profiles = ('storage',)

    packages = ('rhscon-core',)

    def setup(self):
        all_logs = self.get_option("all_logs")
        limit = self.get_option("log_size")

        if not all_logs:
            self.add_copy_spec([
                "/var/log/skyring/skyring.log",
                "/var/log/skyring/bigfin.log",
                "/var/log/carbon/console.log",
                "/var/log/graphite-web/info.log",
                "/var/log/graphite-web/exception.log",
            ], sizelimit=limit)
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
