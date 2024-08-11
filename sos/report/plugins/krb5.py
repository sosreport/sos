# Copyright (C) 2013,2018 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
import socket
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Krb5(Plugin):
    """This plugin handles the collection of kerberos authentication config
    files and logging. Users should expect to see their krb5 config(s) in the
    final archive, along with krb5 logging and `klist` output.

    kdc configs and acls will also be collected from the distribution-spcecific
    kdc directory.
    """

    short_desc = 'Kerberos authentication'
    plugin_name = 'krb5'
    profiles = ('identity', 'system')
    kdcdir = None

    def setup(self):
        self.add_copy_spec([
            "/etc/krb5.conf",
            "/etc/krb5.conf.d/*",
            f"{self.kdcdir}/kadm5.acl",
            f"{self.kdcdir}/kdc.conf",
            "/var/log/kadmind.log"
        ])
        self.collect_kinit()
        self.add_copy_spec("/var/log/krb5kdc.log", tags="kerberos_kdc_log")
        self.add_cmd_output(f"klist -ket {self.kdcdir}/.k5*")
        self.add_cmd_output("klist -ket /etc/krb5.keytab")

    def collect_kinit(self):
        """
        Collect the kinit command output for the system with id_provider "AD"
        or "IPA" domains.

        While integrating the Linux M/c with AD the realmd will create a
        computer object on the AD side. The realmd and AD restrict the
        Hostname/SPN to 15 Characters.
        """

        hostname = socket.getfqdn()
        sssd_conf = "/etc/sssd/sssd.conf"
        if self.path_isfile(sssd_conf):
            with open(sssd_conf, 'r', encoding='utf-8') as f:
                for line in f:
                    if re.match(r'\s*id_provider\s*=\s*ad',
                                line, re.IGNORECASE):
                        hostname = hostname.split('.')[0][:15].upper()
                        self.add_cmd_output(f"KRB5_TRACE=/dev/stdout \
                                            kinit -k '{hostname}$'")
                        break
                    if re.match(r'\s*id_provider\s*=\s*ipa',
                                line, re.IGNORECASE):
                        self.add_cmd_output(f"KRB5_TRACE=/dev/stdout \
                                            kinit -k '{hostname}'")
                        break


class RedHatKrb5(Krb5, RedHatPlugin):

    packages = ('krb5-libs', 'krb5-server')
    kdcdir = "/var/kerberos/krb5kdc"


class UbuntuKrb5(Krb5, DebianPlugin, UbuntuPlugin):

    packages = ('krb5-kdc', 'krb5-config', 'krb5-user')
    kdcdir = "/var/lib/krb5kdc"

# vim: set et ts=4 sw=4 :
