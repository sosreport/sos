# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Postfix(Plugin):
    """Postfix smtp server
    """
    plugin_name = "postfix"
    profiles = ('mail', 'services')

    packages = ('postfix',)

    def setup(self):
        self.add_copy_spec([
            "/etc/postfix/main.cf",
            "/etc/postfix/master.cf"
        ])
        self.add_cmd_output([
            'postconf',
            'mailq'
        ])


class RedHatPostfix(Postfix, RedHatPlugin):

    files = ('/etc/rc.d/init.d/postfix',)
    packages = ('postfix',)

    def setup(self):
        super(RedHatPostfix, self).setup()
        self.add_copy_spec("/etc/mail")


class DebianPostfix(Postfix, DebianPlugin, UbuntuPlugin):

    packages = ('postfix',)

    def setup(self):
        super(DebianPostfix, self).setup()
        self.add_copy_spec("/etc/postfix/dynamicmaps.cf")

# vim: set et ts=4 sw=4 :
