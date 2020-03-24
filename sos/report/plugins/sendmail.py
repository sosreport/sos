# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Sendmail(Plugin):
    """sendmail service
    """

    plugin_name = "sendmail"
    profiles = ('services', 'mail')
    packages = ('sendmail',)

    def setup(self):
        self.add_copy_spec("/etc/mail/*")
        self.add_cmd_output([
            'mailq',
            'mailq -Ac'
        ])


class RedHatSendmail(Sendmail, RedHatPlugin):

    files = ('/etc/rc.d/init.d/sendmail',)

    def setup(self):
        super(RedHatSendmail, self).setup()
        self.add_copy_spec('/var/log/maillog')


class DebianSendmail(Sendmail, DebianPlugin, UbuntuPlugin):

    files = ('/etc/init.d/sendmail',)

    def setup(self):
        super(DebianSendmail, self).setup()
        self.add_copy_spec("/var/log/mail.*")

# vim: set et ts=4 sw=4 :
