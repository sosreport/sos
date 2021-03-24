# Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Iscsi(Plugin):

    short_desc = 'iSCSI initiator'

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

    def postproc(self):
        # Example for scrubbing node.session.auth.password
        #
        # node.session.auth.password = jfaiu1nNQJcsa,sti4lho'jZia=ia
        #
        # to
        #
        # node.session.auth.password = ********
        nodesessionpwd = r"(node\.session\.auth\.password\s+=\s+)(\S+)"
        discoverypwd = r"(discovery\.sendtargets\.auth\.password\s+=\s+)(\S+)"
        repl = r"\1********\n"
        self.do_path_regex_sub('/etc/iscsi/iscsid.conf', nodesessionpwd, repl)
        self.do_path_regex_sub('/etc/iscsi/iscsid.conf', discoverypwd, repl)


class RedHatIscsi(Iscsi, RedHatPlugin):

    packages = ('iscsi-initiator-utils',)

    def setup(self):
        super(RedHatIscsi, self).setup()


class DebianIscsi(Iscsi, DebianPlugin, UbuntuPlugin):

    packages = ('open-iscsi',)

    def setup(self):
        super(DebianIscsi, self).setup()

# vim: set et ts=4 sw=4 :
