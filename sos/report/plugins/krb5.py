# Copyright (C) 2013,2018 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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

    def setup(self):
        self.add_copy_spec([
            "/etc/krb5.conf",
            "/etc/krb5.conf.d/*",
            f"{self.kdcdir}/kadm5.acl",
            f"{self.kdcdir}/kdc.conf",
            "/var/log/kadmind.log"
        ])
        self.add_copy_spec("/var/log/krb5kdc.log", tags="kerberos_kdc_log")
        self.add_cmd_output(f"klist -ket {self.kdcdir}/.k5*")
        self.add_cmd_output("klist -ket /etc/krb5.keytab")


class RedHatKrb5(Krb5, RedHatPlugin):

    packages = ('krb5-libs', 'krb5-server')
    kdcdir = "/var/kerberos/krb5kdc"


class UbuntuKrb5(Krb5, DebianPlugin, UbuntuPlugin):

    packages = ('krb5-kdc', 'krb5-config', 'krb5-user')
    kdcdir = "/var/lib/krb5kdc"

# vim: set et ts=4 sw=4 :
