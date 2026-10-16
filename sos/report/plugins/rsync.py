# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Rsync(Plugin, IndependentPlugin):

    short_desc = 'Rsync file synchronisation daemon'

    plugin_name = 'rsync'
    profiles = ('services', 'network')

    packages = ('rsync', 'rsync-daemon')
    files = ('/etc/rsyncd.conf',)
    services = ('rsyncd', 'rsyncd.socket')

    def setup(self):
        # The secrets file referenced by an "auth users" module holds
        # username:password pairs in cleartext. It must never be
        # collected, at either of its conventional locations or under
        # the drop-in directory.
        self.add_forbidden_path([
            '/etc/rsyncd.secrets',
            '/etc/rsync.secrets',
            '/etc/rsyncd.d/*.secrets',
        ])

        self.add_copy_spec([
            '/etc/rsyncd.conf',
            '/etc/rsyncd.d/',
            '/etc/default/rsync',
            '/etc/sysconfig/rsyncd',
        ])

        self.add_copy_spec('/var/log/rsyncd.log')

        if self.get_option('all_logs'):
            self.add_copy_spec('/var/log/rsyncd.log*')

        self.add_cmd_output('rsync --version', tags='rsync_version')

        # Templated unit, not covered by the services tuple.
        self.add_journal(units='rsyncd@.service')

# vim: set et ts=4 sw=4 :
