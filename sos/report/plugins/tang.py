# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Tang(Plugin, IndependentPlugin):

    short_desc = 'Tang network-bound disk encryption server'

    plugin_name = 'tang'
    profiles = ('security', 'storage', 'services')
    packages = ('tang',)

    def setup(self):
        # The key database holds Tang's signing and exchange keys. The
        # private key material must never leave the host, so forbid the
        # JWK files outright and collect only a listing of the directory,
        # which is enough to review the key set, rotation state (keys
        # renamed with a leading '.' are no longer advertised) and file
        # ownership.
        self.add_forbidden_path([
            '/var/db/tang/*.jwk',
            '/var/db/tang/.*.jwk',
            '/usr/share/tang/db/*.jwk',
            '/usr/share/tang/db/.*.jwk',
        ])

        self.add_dir_listing([
            '/var/db/tang',
            '/usr/share/tang/db',
        ], tags='tang_keydir')

        self.add_copy_spec('/etc/systemd/system/tangd.socket.d/')

        # Advertised key thumbprints only; no private key material.
        self.add_cmd_output('tang-show-keys', tags='tang_show_keys')

        self.add_service_status('tangd.socket')
        self.add_journal(units=['tangd.socket', 'tangd@.service'])

# vim: set et ts=4 sw=4 :
