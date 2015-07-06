# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

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
        self.add_cmd_output("postconf")


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
