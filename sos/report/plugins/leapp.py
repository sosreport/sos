# Copyright (C) 2019 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Leapp(Plugin, RedHatPlugin):

    short_desc = 'Leapp upgrade handling tool'

    plugin_name = 'leapp'
    packages = ('leapp',)
    files = ('/var/lib/leapp',)

    def setup(self):
        self.add_copy_spec([
            '/etc/migration-results',
            '/etc/leapp/actor_cond.d',
            '/etc/leapp/files/dnf.conf',
            '/var/log/leapp/answerfile',
            '/var/log/leapp/dnf-debugdata/',
            '/var/log/leapp/leapp-preupgrade.log',
            '/var/log/leapp/leapp-upgrade.log',
            '/var/log/leapp/leapp-report.txt',
            '/var/log/leapp/dnf-plugin-data.txt'
        ])

        # capture DB without sizelimit
        self.add_copy_spec('/var/lib/leapp/leapp.db', sizelimit=0)

        self.add_cmd_output('leapp --version')

    def postproc(self):
        # Scrub password and proxy_password likewise from dnf.conf
        self.do_file_sub("/etc/leapp/files/dnf.conf",
                         r"(password(\s)*=(\s)*)(\S+)\n",
                         r"\1********\n")

# vim: set et ts=4 sw=4 :
