# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Booth(Plugin, IndependentPlugin):

    short_desc = 'Booth cluster ticket manager'

    plugin_name = 'booth'
    profiles = ('cluster',)

    packages = ('booth', 'booth-core', 'booth-arbitrator', 'booth-site')
    files = ('/etc/booth/booth.conf',)

    def setup(self):
        # A site or arbitrator may set "authfile" in booth.conf, pointing
        # at a shared secret used to authenticate ticket messages. The
        # default location is under the configuration directory, so
        # exclude key material before collecting it.
        self.add_forbidden_path([
            '/etc/booth/*.key',
            '/etc/booth/authkey',
        ])

        self.add_copy_spec('/etc/booth/*.conf')

        self.add_copy_spec('/var/log/booth.log')

        if self.get_option('all_logs'):
            self.add_copy_spec('/var/log/booth.log*')

        self.add_dir_listing('/var/run/booth', tags='booth_run_dir')

        self.add_cmd_output([
            'booth list',
            'booth peers',
            'booth status',
        ], tags='booth_status')

        self.add_service_status('booth-arbitrator')
        self.add_journal(units=['booth-arbitrator', 'booth@*'])

# vim: set et ts=4 sw=4 :
