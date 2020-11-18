# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Ctdb(Plugin, DebianPlugin, UbuntuPlugin):

    short_desc = 'Samba Clustered TDB'
    packages = ('ctdb',)
    profiles = ('cluster', 'storage')
    plugin_name = "ctdb"

    def setup(self):
        self.add_copy_spec([
            "/etc/ctdb/ctdb.conf",
            "/etc/ctdb/*.options",
            "/etc/ctdb/nodes",
            "/etc/ctdb/public_addresses",
            "/etc/ctdb/static-routes",
            "/etc/ctdb/multipathd",
            "/var/log/log.ctdb"
        ])

        self.add_cmd_output([
            "ctdb ip",
            "ctdb ping",
            "ctdb status",
            "ctdb ifaces",
            "ctdb listnodes",
            "ctdb listvars",
            "ctdb statistics",
            "ctdb getdbmap",
            "ctdb event script list legacy"
        ])


class RedHatCtdb(Ctdb, RedHatPlugin):
    def setup(self):
        super(RedHatCtdb, self).setup()
        self.add_copy_spec("/etc/sysconfig/ctdb")

# vim: set et ts=4 sw=4 :
