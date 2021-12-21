# Copyright (C) 2019 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Rpmostree(Plugin, RedHatPlugin):

    short_desc = 'rpm-ostree image/package system'

    plugin_name = 'rpmostree'
    packages = ('rpm-ostree',)

    def setup(self):
        self.add_copy_spec('/etc/ostree/remotes.d/')

        subcmds = [
            'status -v',
            'kargs',
            'db list',
            'db diff',
            '--version'
        ]

        self.add_cmd_output(["rpm-ostree %s" % subcmd for subcmd in subcmds])

        units = [
            'rpm-ostreed',
            'rpm-ostreed-automatic',
            'rpm-ostree-bootstatus'
        ]
        for unit in units:
            self.add_journal(unit)

# vim: set et ts=4 sw=4 :
