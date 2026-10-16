# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Avahi(Plugin, IndependentPlugin):

    short_desc = 'Avahi mDNS/DNS-SD stack'

    plugin_name = 'avahi'
    profiles = ('network', 'services')

    packages = ('avahi', 'avahi-daemon', 'avahi-dnsconfd')
    files = ('/etc/avahi/avahi-daemon.conf',)

    def setup(self):
        self.add_copy_spec([
            '/etc/avahi/avahi-daemon.conf',
            '/etc/avahi/hosts',
            '/etc/avahi/services/',
            '/etc/avahi/avahi-dnsconfd.action',
        ])

        self.add_cmd_output([
            'avahi-browse --all --terminate --resolve',
            'avahi-daemon --check',
        ], tags='avahi_browse')

        self.add_service_status([
            'avahi-daemon',
            'avahi-daemon.socket',
            'avahi-dnsconfd',
        ])

        self.add_journal(units=['avahi-daemon', 'avahi-dnsconfd'])

# vim: set et ts=4 sw=4 :
