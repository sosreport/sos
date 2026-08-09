# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class WireGuard(Plugin, IndependentPlugin):

    short_desc = 'WireGuard VPN tunnels'

    plugin_name = 'wireguard'
    profiles = ('network', 'security')

    packages = ('wireguard-tools',)
    files = ('/etc/wireguard',)
    kernel_mods = ('wireguard',)

    def setup(self):
        self.add_copy_spec('/etc/wireguard/*.conf')

        # "wg show" masks private and preshared keys as "(hidden)" unless
        # WG_HIDE_KEYS=never is set in the environment, so the default
        # output is safe to collect. "wg showconf" is deliberately not
        # run, as it prints the private key verbatim.
        self.add_cmd_output('wg show all', tags='wg_show')

        self.add_service_status('wg-quick@*')
        self.add_journal(units='wg-quick@*')

    def postproc(self):
        # Interface configuration files hold the interface private key
        # and any per-peer preshared key in cleartext.
        #
        # PrivateKey = 8Gt...=    ->    PrivateKey = ********
        self.do_path_regex_sub(
            '/etc/wireguard/.*',
            r'((?:Private|Preshared)Key\s*=\s*)\S+',
            r'\1********')

# vim: set et ts=4 sw=4 :
