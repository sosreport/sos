# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Keylime(Plugin, IndependentPlugin):

    short_desc = 'Keylime remote attestation'

    plugin_name = 'keylime'
    profiles = ('security', 'services')

    packages = (
        'keylime',
        'keylime-base',
        'keylime-agent',
        'keylime-verifier',
        'keylime-registrar',
        'keylime-tenant',
        'keylime-agent-rust',
    )
    files = ('/etc/keylime',)

    def setup(self):
        # The CA directory under /var/lib/keylime holds the deployment's
        # private keys, written as <name>-private.pem, and the same tree
        # is used for decrypted payloads. None of it is collected; a
        # listing is taken instead. PEM files are forbidden outright so
        # that no key material can be picked up from either location.
        self.add_forbidden_path([
            '/etc/keylime/**/*.pem',
            '/var/lib/keylime/**',
        ])

        self.add_copy_spec([
            '/etc/keylime/*.conf',
            '/etc/keylime/agent.conf.d/',
            '/etc/keylime/ca.conf.d/',
            '/etc/keylime/logging.conf.d/',
            '/etc/keylime/registrar.conf.d/',
            '/etc/keylime/tenant.conf.d/',
            '/etc/keylime/verifier.conf.d/',
        ])

        self.add_dir_listing('/var/lib/keylime', recursive=True,
                             tags='keylime_data_dir')

        self.add_service_status([
            'keylime_agent',
            'keylime_registrar',
            'keylime_verifier',
        ])

        self.add_journal(units=[
            'keylime_agent',
            'keylime_registrar',
            'keylime_verifier',
        ])

# vim: set et ts=4 sw=4 :
