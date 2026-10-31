# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin)


class Exim(Plugin):

    short_desc = 'Exim mail transfer agent'

    plugin_name = 'exim'
    profiles = ('mail', 'services')

    def setup(self):
        self.add_cmd_output([
            'exim -bV',
            'exim -bp',
        ], tags='exim_queue')

        self.add_service_status('exim')


class RedHatExim(Exim, RedHatPlugin):

    packages = ('exim',)
    files = ('/etc/exim/exim.conf',)

    def setup(self):
        super().setup()

        # SMTP authentication credentials are held in the passwd maps
        # referenced by the authenticators; they must not be collected.
        self.add_forbidden_path([
            '/etc/exim/passwd',
            '/etc/exim/passwd.client',
        ])

        self.add_copy_spec('/etc/exim')

        self.add_copy_spec([
            '/var/log/exim/main.log',
            '/var/log/exim/reject.log',
            '/var/log/exim/panic.log',
        ])

        if self.get_option('all_logs'):
            self.add_copy_spec('/var/log/exim/')

        self.add_journal(units='exim')


class DebianExim(Exim, DebianPlugin, UbuntuPlugin):

    packages = ('exim4', 'exim4-base', 'exim4-daemon-light',
                'exim4-daemon-heavy')
    files = ('/etc/exim4/update-exim4.conf.conf',)

    def setup(self):
        super().setup()

        # As above; exim4 keeps its client and server credentials under
        # the split configuration directory.
        self.add_forbidden_path([
            '/etc/exim4/passwd',
            '/etc/exim4/passwd.client',
        ])

        self.add_copy_spec('/etc/exim4')

        self.add_copy_spec([
            '/var/log/exim4/mainlog',
            '/var/log/exim4/rejectlog',
            '/var/log/exim4/paniclog',
        ])

        if self.get_option('all_logs'):
            self.add_copy_spec('/var/log/exim4/')

        self.add_journal(units='exim4')

# vim: set et ts=4 sw=4 :
