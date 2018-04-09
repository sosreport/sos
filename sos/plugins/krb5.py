# Copyright (C) 2013 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Krb5(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Kerberos authentication
    """
    plugin_name = 'krb5'
    profiles = ('identity', 'system')
    packages = ('krb5-libs', 'krb5-user')

    def setup(self):
        self.add_copy_spec("/etc/krb5.conf")
        self.add_cmd_output("klist -ket /etc/krb5.keytab")


# vim: set et ts=4 sw=4 :
