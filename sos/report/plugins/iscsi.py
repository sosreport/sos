# Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
