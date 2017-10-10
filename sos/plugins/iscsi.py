# Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>

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


class Iscsi(Plugin):
    """iSCSI initiator
    """

    plugin_name = "iscsi"
    profiles = ('storage',)

    def setup(self):
        var_puppet_gen = "/var/lib/config-data/puppet-generated/iscsid"
        self.add_copy_spec([
            "/etc/iscsi/iscsid.conf",
            "/etc/iscsi/initiatorname.iscsi",
            var_puppet_gen + "/etc/iscsi/initiatorname.iscsi",
            "/var/lib/iscsi"
        ])
        self.add_cmd_output([
            "iscsiadm -m session -P 3",
            "iscsiadm -m node -P 1",
            "iscsiadm -m iface -P 1",
            "iscsiadm -m node --op=show"
        ])


class RedHatIscsi(Iscsi, RedHatPlugin):

    packages = ('iscsi-initiator-utils',)

    def setup(self):
        super(RedHatIscsi, self).setup()


class DebianIscsi(Iscsi, DebianPlugin, UbuntuPlugin):

    packages = ('open-iscsi',)

    def setup(self):
        super(DebianIscsi, self).setup()

# vim: set et ts=4 sw=4 :
