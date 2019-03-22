# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Candlepin(Plugin, RedHatPlugin):
    """Candlepin entitlement management"""

    plugin_name = 'candlepin'
    packages = ('candlepin',)

    def setup(self):

        # Always collect the full active log of these
        self.add_copy_spec([
            "/var/log/candlepin/error.log",
            "/var/log/candlepin/candlepin.log"
        ], sizelimit=0)

        # Allow limiting on logrotated logs
        self.add_copy_spec([
            "/etc/candlepin/candlepin.conf",
            "/var/log/candlepin/audit*.log*",
            "/var/log/candlepin/candlepin.log[.-]*",
            "/var/log/candlepin/cpdb*.log*",
            "/var/log/candlepin/cpinit*.log*",
            "/var/log/candlepin/error.log[.-]*"
        ])

        self.add_cmd_output("du -sh /var/lib/candlepin/*/*")

    def postproc(self):
        reg = r"(((.*)(pass|token|secret)(.*))=)(.*)"
        repl = r"\1********"
        self.do_file_sub("/etc/candlepin/candlepin.conf", reg, repl)
        cpdbreg = r"(--password=)([a-zA-Z0-9]*)"
        self.do_file_sub("/var/log/candlepin/cpdb.log", cpdbreg, repl)

# vim: set et ts=4 sw=4 :
