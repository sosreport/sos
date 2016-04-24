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


class Dovecot(Plugin):
    """Dovecot IMAP and POP3
    """

    plugin_name = "dovecot"
    profiles = ('mail',)

    def setup(self):
        self.add_copy_spec("/etc/dovecot*")
        self.add_cmd_output("dovecot -n")


class RedHatDovecot(Dovecot, RedHatPlugin):
    """dovecot server related information
    """
    def setup(self):
        super(RedHatDovecot, self).setup()

    packages = ('dovecot', )
    files = ('/etc/dovecot.conf',)


class DebianDovecot(Dovecot, DebianPlugin, UbuntuPlugin):
    """dovecot server related information for Debian based distribution
    """
    def setup(self):
        super(DebianDovecot, self).setup()

    files = ('/etc/dovecot/README',)

# vim: set et ts=4 sw=4 :
