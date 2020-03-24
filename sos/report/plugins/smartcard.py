# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Smartcard(Plugin, RedHatPlugin):
    """PKCS#11 smart cards
    """

    plugin_name = 'smartcard'
    profiles = ('security', 'identity', 'hardware')

    files = ('/etc/pam_pkcs11/pam_pkcs11.conf',)
    packages = ('pam_pkcs11', 'pcsc-tools', 'opensc')

    def setup(self):
        self.add_copy_spec([
            "/etc/reader.conf",
            "/etc/reader.conf.d/",
            "/etc/pam_pkcs11/",
            "/etc/opensc-*.conf"
        ])
        self.add_cmd_output([
            "pklogin_finder debug",
            "ls -nl /usr/lib*/pam_pkcs11/",
            "pcsc_scan",
            "pkcs11-tool --show-info",
            "pkcs11-tool --list-mechanisms",
            "pkcs11-tool --list-slots",
            "pkcs11-tool --list-objects"
        ])
        self.add_forbidden_path("/etc/pam_pkcs11/nssdb/key[3-4].db")

# vim: set et ts=4 sw=4 :
