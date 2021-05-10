# Copyright (C) 2017 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Crypto(Plugin, IndependentPlugin):

    short_desc = 'System crypto services information'

    plugin_name = 'crypto'
    profiles = ('system', 'hardware')

    def setup(self):

        cpth = '/etc/crypto-policies/back-ends'

        self.add_file_tags({
            "%s/bind.config" % cpth: 'crypto_policies_bind',
            "%s/opensshserver.config" % cpth: 'crypto_policies_opensshserver',
            '/etc/crypto-policies/.*/current': 'crypto_policies_state_current',
            '/etc/crypto-policies/config': 'crypto_policies_config'
        })

        self.add_copy_spec([
            "/proc/crypto",
            "/proc/sys/crypto/fips_enabled",
            "/etc/system-fips",
            "/etc/crypto-policies/*"
        ])

        self.add_cmd_output([
            "fips-mode-setup --check",
            "update-crypto-policies --show",
            "update-crypto-policies --is-applied"
        ])

# vim: et ts=4 sw=4
