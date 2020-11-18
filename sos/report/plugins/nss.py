# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class NSS(Plugin, IndependentPlugin):

    short_desc = 'Network Security Services configuration'

    plugin_name = "nss"
    profiles = ('network', 'security')
    packages = ('nss',)
    verify_packages = ('nss.*',)

    def setup(self):
        self.add_forbidden_path([
            "/etc/pki/nssdb/cert*",
            "/etc/pki/nssdb/key*",
            "/etc/pki/nssdb/secmod.db"
        ])

        self.add_copy_spec("/etc/pki/nssdb/pkcs11.txt")

# vim: set et ts=4 sw=4 :
