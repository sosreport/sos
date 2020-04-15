# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Dovecot(Plugin):

    short_desc = 'Dovecot IMAP and POP3'

    plugin_name = "dovecot"
    profiles = ('mail',)

    def setup(self):
        self.add_copy_spec("/etc/dovecot*")
        self.add_cmd_output("dovecot -n")


class RedHatDovecot(Dovecot, RedHatPlugin):

    def setup(self):
        super(RedHatDovecot, self).setup()

    packages = ('dovecot', )
    files = ('/etc/dovecot.conf',)


class DebianDovecot(Dovecot, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianDovecot, self).setup()

    files = ('/etc/dovecot/README',)

# vim: set et ts=4 sw=4 :
