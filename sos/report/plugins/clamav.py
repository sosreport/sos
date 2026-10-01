# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class ClamAV(Plugin, IndependentPlugin):

    short_desc = 'ClamAV antivirus'

    plugin_name = 'clamav'
    profiles = ('security', 'services')

    packages = ('clamav', 'clamd', 'clamav-freshclam', 'clamav-daemon')
    files = ('/etc/clamd.conf', '/etc/clamav/clamd.conf')
    services = ('clamav-daemon', 'clamav-freshclam', 'freshclam')

    def setup(self):
        # Red Hat splits the daemon configuration into /etc/clamd.d/,
        # Debian keeps everything under /etc/clamav/.
        self.add_copy_spec([
            '/etc/clamd.conf',
            '/etc/clamd.d/',
            '/etc/freshclam.conf',
            '/etc/clamav/',
            '/etc/sysconfig/clamav-milter',
        ])

        self.add_copy_spec([
            '/var/log/clamav/*.log',
            '/var/log/freshclam.log',
            '/var/log/clamd.scan',
        ])

        if self.get_option('all_logs'):
            self.add_copy_spec([
                '/var/log/clamav/',
                '/var/log/freshclam.log*',
            ])

        # DatabaseDirectory is configurable; fall back to the upstream
        # default if freshclam.conf does not set it or cannot be read.
        db_dir = '/var/lib/clamav'
        config_files = (
            '/etc/freshclam.conf',
            '/etc/clamav/freshclam.conf',
        )
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='UTF-8') as cfile:
                    for line in cfile.read().splitlines():
                        words = line.split()
                        if words and words[0] == 'DatabaseDirectory':
                            db_dir = words[1]
            except IOError:
                continue

        # The signature database is large and binary; a listing is enough
        # to show which definitions are present and how old they are.
        self.add_dir_listing(db_dir, tags='clamav_database')

        self.add_cmd_output('clamconf', tags='clamconf')

    def postproc(self):
        # freshclam.conf may hold credentials for an outbound proxy.
        #
        # HTTPProxyPassword mypass    ->    HTTPProxyPassword ********
        self.do_path_regex_sub(
            r'/etc/(clamav/)?freshclam\.conf',
            r'(HTTPProxy(?:Password|Username)\s+)\S+',
            r'\1********')

# vim: set et ts=4 sw=4 :
