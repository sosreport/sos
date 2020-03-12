# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Stratis(Plugin, RedHatPlugin):
    '''Stratis Storage'''

    packages = ('stratis-cli', 'stratisd')
    services = ('stratisd',)
    profiles = ('storage',)

    def setup(self):
        subcmds = [
            'pool list',
            'filesystem list',
            'blockdev list',
            'daemon redundancy',
            'daemon version'
        ]

        self.add_cmd_output(["stratis %s" % subcmd for subcmd in subcmds])
        self.add_journal(units='stratisd')

# vim: set et ts=4 sw=4 :
