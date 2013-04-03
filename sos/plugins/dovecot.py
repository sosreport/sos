### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class dovecot(Plugin):
    """dovecot server related information
    """

    plugin_name = "dovecot"

    def setup(self):
        self.addCopySpec("/etc/dovecot*")
        self.addCmdOutput("/usr/sbin/dovecot -n")

class RedHatDovecot(dovecot, RedHatPlugin):
    """dovecot server related information for RedHat based distribution
    """
    def setup(self):
        super(RedHatDovecot, self).setup()

    files = ('/etc/dovecot.conf',)

class DebianDovecot(dovecot, DebianPlugin, UbuntuPlugin):
    """dovecot server related information for Debian based distribution
    """
    def setup(self):
        super(DebianDovecot, self).setup()

    files = ('/etc/dovecot/README',)
