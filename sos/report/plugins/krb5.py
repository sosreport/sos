# Copyright (C) 2013,2018 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Krb5(Plugin):

    short_desc = 'Kerberos authentication'
    plugin_name = 'krb5'
    profiles = ('identity', 'system')
    packages = ('krb5-libs', 'krb5-user')

    # This is Debian's default, which is closest to upstream's
    kdcdir = "/var/lib/krb5kdc"

    def setup(self):
        self.add_copy_spec([
            "/etc/krb5.conf",
            "/etc/krb5.conf.d/*",
            "%s/kadm5.acl" % self.kdcdir,
            "%s/kdc.conf" % self.kdcdir,
            "/var/log/krb5kdc.log",
            "/var/log/kadmind.log"
        ])
        self.add_cmd_output("klist -ket %s/.k5*" % self.kdcdir)
        self.add_cmd_output("klist -ket /etc/krb5.keytab")


class RedHatKrb5(Krb5, RedHatPlugin):

    def setup(self):
        self.kdcdir = "/var/kerberos/krb5kdc"
        super(RedHatKrb5, self).setup()


# vim: set et ts=4 sw=4 :
