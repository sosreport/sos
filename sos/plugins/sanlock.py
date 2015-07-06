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

from sos.plugins import Plugin, RedHatPlugin


class SANLock(Plugin):
    """SANlock daemon
    """
    plugin_name = "sanlock"
    profiles = ('cluster', 'virt')
    packages = ["sanlock"]

    def setup(self):
        self.add_copy_spec("/var/log/sanlock.log*")
        self.add_cmd_output([
            "sanlock client status -D",
            "sanlock client host_status -D",
            "sanlock client log_dump"
        ])
        return


class RedHatSANLock(SANLock, RedHatPlugin):

    files = ["/etc/sysconfig/sanlock"]

    def setup(self):
        super(RedHatSANLock, self).setup()
        self.add_copy_spec("/etc/sysconfig/sanlock")

# vim: set et ts=4 sw=4 :
