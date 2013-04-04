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

class Pam(Plugin):
    """PAM related information
    """

    plugin_name = "pam"

    def setup(self):
        self.add_copy_spec("/etc/pam.d")
        self.add_copy_spec("/etc/security")

class RedHatPam(pam, RedHatPlugin):
    """PAM related information for RedHat based distribution
    """
    def setup(self):
        super(RedHatPam, self).setup()

        self.add_cmd_output("/bin/ls -lanF /lib*/security")

class DebianPam(pam, DebianPlugin, UbuntuPlugin):
    """PAM related information for Debian based distribution
    """
    def setup(self):
        super(DebianPam, self).setup()

        self.add_cmd_output("/bin/ls -lanF /lib/x86_64-linux-gnu/security")
