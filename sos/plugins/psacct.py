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


class Psacct(Plugin):
    """Process accounting information
    """
    plugin_name = "psacct"
    profiles = ('system',)

    option_list = [("all", "collect all process accounting files",
                    "slow", False)]

    packages = ["psacct"]


class RedHatPsacct(Psacct, RedHatPlugin):

    packages = ["psacct"]

    def setup(self):
        super(RedHatPsacct, self).setup()
        self.add_copy_spec("/var/account/pacct")
        if self.get_option("all"):
            self.add_copy_spec("/var/account/pacct*.gz")


class DebianPsacct(Psacct, DebianPlugin, UbuntuPlugin):

    plugin_name = "acct"
    packages = ["acct"]

    def setup(self):
        super(DebianPsacct, self).setup()
        self.add_copy_spec(["/var/log/account/pacct", "/etc/default/acct"])
        if self.get_option("all"):
            self.add_copy_spec("/var/log/account/pacct*.gz")

# vim: set et ts=4 sw=4 :
